import json
import os
import random
from datetime import datetime

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QFileDialog, QGridLayout, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from models.card_library import card_sort_key
from models.deck import Deck
from models.game_state import GameState
from models.layout_config import WindowDefinition, ZoneDefinition
from .action_log_widget import ActionLogWidget
from .constants import GAME_CONFIG_PATH, UI_WIDGET_DECK_LIST
from .deck_list_widget import DeckListWidget
from .deck_manager import DeckManagerDialog
from .signals import game_signals
from .theme import MENUBAR_STYLE, WIN_BG, btn_dice, btn_load, btn_reset, btn_zone_overlay
from .zone_widget import ZoneWidget, rebuild_key_zone
from . import keybindings as kb


_CONFIG_PATH = "data/config.json"


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config(data: dict):
    os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class GameWindow(QMainWindow):
    def __init__(self, win_def: WindowDefinition, zone_defs: list[ZoneDefinition],
                 win_defs: list[WindowDefinition] | None = None):
        super().__init__()
        self.win_def = win_def
        self._win_defs = win_defs or [win_def]
        self._all_zone_defs = zone_defs  # 全ウィンドウのゾーン定義（layout editor 保存用）
        # この window に属するゾーン定義（source_zone_id を持つビューゾーンも含む）
        self.zone_defs = [z for z in zone_defs if z.window_id == win_def.id]
        self.zone_widgets: dict[str, ZoneWidget] = {}  # zone_id → ZoneWidget
        self._is_hand_window = (win_def.id == "hand")
        self._action_log = None
        self._dice_dialog = None

        self.setWindowTitle(win_def.title)
        self.resize(win_def.width, win_def.height)
        self.setStyleSheet(f"QMainWindow, QWidget {{ background-color: {WIN_BG}; }}")
        self.menuBar().setStyleSheet(MENUBAR_STYLE)
        self._setup_menu()
        self._setup_ui()
        self._setup_shortcuts()

        game_signals.layout_updated.connect(self._reload_layout)

        if self._is_hand_window:
            self._restore_last_deck()

    # ── UI セットアップ ──────────────────────────────────────────────

    def _setup_menu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("ファイル")
        file_menu.addAction("初期状態にリセット", self._initialize_field)
        file_menu.addSeparator()
        save_action = QAction("試合を保存", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self._save_game)
        file_menu.addAction(save_action)
        file_menu.addAction("試合をロード…", self._load_game)
        undo_action = QAction("アンドゥ", self)
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        undo_action.triggered.connect(self._undo)
        file_menu.addAction(undo_action)
        file_menu.addSeparator()
        file_menu.addAction("デッキ管理を開く", self._open_deck_manager)

        settings_menu = menu.addMenu("設定")
        settings_menu.addAction("キーバインド設定…", self._open_keybinding_settings)
        settings_menu.addAction("レイアウト編集…", self._open_layout_editor)

    def _apply_grid_stretches(self):
        for c in range(self.win_def.grid_cols):
            self._grid_layout.setColumnStretch(c, 1)
        for r in range(self.win_def.grid_rows):
            self._grid_layout.setRowStretch(r, 1)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setSpacing(8)
        outer.setContentsMargins(10, 8, 10, 10)

        # ── ツールバー ──────────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        if not self._is_hand_window:
            dice_btn = QPushButton("ダイス")
            dice_btn.setFixedHeight(28)
            dice_btn.setStyleSheet(btn_dice())
            dice_btn.clicked.connect(self._open_dice)
            toolbar.addWidget(dice_btn)

            toolbar.addStretch()

            reset_btn = QPushButton("初期状態にリセット")
            reset_btn.setFixedHeight(28)
            reset_btn.setStyleSheet(btn_reset())
            reset_btn.clicked.connect(self._initialize_field)
            toolbar.addWidget(reset_btn)

        outer.addLayout(toolbar)

        # ── ゾーングリッド ──────────────────────────────────────────
        self._grid_container = QWidget()
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(4)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)

        self._apply_grid_stretches()

        for zd in self.zone_defs:
            widget = self._make_zone_widget(zd)
            self.zone_widgets[zd.id] = widget
            gp = zd.grid_pos
            self._grid_layout.addWidget(widget, gp.row, gp.col, gp.row_span, gp.col_span)
            if zd.ui_widget == UI_WIDGET_DECK_LIST:
                self.deck_list = widget

        # アクションログ（手札ウィンドウ以外に追加）
        if not self._is_hand_window:
            self._action_log = ActionLogWidget()
            self._action_log.setMinimumWidth(120)
            self._action_log.setMaximumWidth(180)
            # グリッドの右端に追加（全行span）
            self._grid_layout.addWidget(
                self._action_log, 0, self.win_def.grid_cols, self.win_def.grid_rows, 1
            )

        outer.addWidget(self._grid_container, 1)

        # ── 手札ウィンドウ専用: デッキ読み込みパネル ─────────────────
        if self._is_hand_window:
            ctrl = QHBoxLayout()
            self.deck_label = QLabel("デッキ未選択")
            self.deck_label.setStyleSheet("color:#6688aa;font-size:10px;font-family:'Yu Gothic UI';")
            ctrl.addWidget(self.deck_label, 1)
            load_btn = QPushButton("デッキ読み込み")
            load_btn.setFixedHeight(26)
            load_btn.setStyleSheet(btn_load())
            load_btn.clicked.connect(self._load_deck)
            ctrl.addWidget(load_btn)
            mgr_btn = QPushButton("デッキ管理")
            mgr_btn.setFixedHeight(26)
            mgr_btn.setStyleSheet(btn_load())
            mgr_btn.clicked.connect(self._open_deck_manager)
            ctrl.addWidget(mgr_btn)
            reset_btn = QPushButton("初期状態にリセット")
            reset_btn.setFixedHeight(26)
            reset_btn.setStyleSheet(btn_reset())
            reset_btn.clicked.connect(self._initialize_field)
            ctrl.addWidget(reset_btn)
            outer.insertLayout(0, ctrl)

    def _make_zone_widget(self, zd: ZoneDefinition):
        if zd.ui_widget == UI_WIDGET_DECK_LIST:
            return DeckListWidget()

        widget = ZoneWidget(zd)

        if zd.tappable:
            self._add_tap_buttons(widget, zd)

        if zd.id == "deck" or (zd.source_zone_id == "deck"):
            self._add_deck_buttons(widget)

        if zd.id == "hand" and self._is_hand_window:
            self._add_hand_buttons(widget)

        return widget

    def _add_tap_buttons(self, zone_widget: ZoneWidget, zd: ZoneDefinition):
        untap_btn = QPushButton("全解除", zone_widget)
        untap_btn.setFixedSize(44, 18)
        untap_btn.setStyleSheet(btn_zone_overlay())
        untap_btn.clicked.connect(lambda: self._set_all_tap(zd.id, False))

        tap_btn = QPushButton("全タップ", zone_widget)
        tap_btn.setFixedSize(52, 18)
        tap_btn.setStyleSheet(btn_zone_overlay())
        tap_btn.clicked.connect(lambda: self._set_all_tap(zd.id, True))

        if zd.two_row:
            sort_btn = QPushButton("ソート", zone_widget)
            sort_btn.setFixedSize(48, 18)
            sort_btn.setStyleSheet(btn_zone_overlay())
            sort_btn.clicked.connect(self._sort_battle_zone)
        else:
            sort_btn = None

        def reposition():
            w = zone_widget.width()
            untap_btn.move(w - 46, 2)
            tap_btn.move(w - 46 - 54, 2)
            if sort_btn:
                sort_btn.move(w - 46 - 54 - 52, 2)

        zone_widget.installEventFilter(self)
        zone_widget._reposition_tap_btns = reposition
        reposition()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Resize:
            for attr in ('_reposition_tap_btns', '_reposition_deck_btns', '_reposition_hand_btns'):
                if hasattr(obj, attr):
                    getattr(obj, attr)()
        return super().eventFilter(obj, event)

    def _add_deck_buttons(self, zone_widget: ZoneWidget):
        """山札ゾーンにドロー・シャッフルボタンをオーバーレイする。"""
        draw_btn = QPushButton("ドロー", zone_widget)
        draw_btn.setFixedSize(48, 18)
        draw_btn.setStyleSheet(btn_zone_overlay())
        draw_btn.clicked.connect(self._draw_card)

        shuffle_btn = QPushButton("シャッフル", zone_widget)
        shuffle_btn.setFixedSize(60, 18)
        shuffle_btn.setStyleSheet(btn_zone_overlay())
        shuffle_btn.clicked.connect(self._shuffle_deck)

        def reposition():
            w = zone_widget.width()
            draw_btn.move(w - 50, 2)
            shuffle_btn.move(w - 50 - 62, 2)

        zone_widget.installEventFilter(self)
        zone_widget._reposition_deck_btns = reposition
        reposition()

    def _add_hand_buttons(self, zone_widget: ZoneWidget):
        """手札ゾーンにソートボタンをオーバーレイする。"""
        sort_btn = QPushButton("ソート", zone_widget)
        sort_btn.setFixedSize(44, 18)
        sort_btn.setStyleSheet(btn_zone_overlay())
        sort_btn.clicked.connect(self._sort_hand)

        def reposition():
            sort_btn.move(zone_widget.width() - 46, 2)

        zone_widget.installEventFilter(self)
        zone_widget._reposition_hand_btns = reposition
        reposition()

    def _sort_hand(self):
        gs = GameState.get_instance()
        hand = gs.zones.get("hand")
        if hand is None or not hand.cards:
            return
        gs.push_snapshot()
        hand.cards.sort(key=lambda gc: card_sort_key(gc.card))
        game_signals.zones_updated.emit()

    def _setup_shortcuts(self):
        self._reset_action = QAction("ゲームリセット", self)
        self._reset_action.setShortcut(QKeySequence(kb.get("game_reset")))
        self._reset_action.triggered.connect(self._initialize_field)
        self.addAction(self._reset_action)

        self._draw_action = QAction("ドロー", self)
        self._draw_action.setShortcut(QKeySequence(kb.get("draw")))
        self._draw_action.triggered.connect(self._draw_card)
        self.addAction(self._draw_action)

    def _refresh_shortcuts(self):
        self._reset_action.setShortcut(QKeySequence(kb.get("game_reset")))
        self._draw_action.setShortcut(QKeySequence(kb.get("draw")))
        rebuild_key_zone()

    # ── ゲームアクション ─────────────────────────────────────────────

    def _draw_card(self):
        if GameState.get_instance().draw_card():
            game_signals.action_logged.emit("ドロー")
            game_signals.zones_updated.emit()

    def _sort_battle_zone(self):
        gs = GameState.get_instance()
        gs.push_snapshot()
        row0 = sorted([gc for gc in gs.zones["battle"].cards if gc.row == 0],
                      key=lambda gc: card_sort_key(gc.card))
        row1 = sorted([gc for gc in gs.zones["battle"].cards if gc.row == 1],
                      key=lambda gc: card_sort_key(gc.card))
        gs.zones["battle"].cards[:] = row0 + row1
        game_signals.zones_updated.emit()

    def _set_all_tap(self, zone_id: str, tapped: bool):
        gs = GameState.get_instance()
        gs.push_snapshot()
        for gc in gs.zones[zone_id].cards:
            gc.tapped = tapped
        game_signals.zones_updated.emit()

    def _shuffle_deck(self):
        gs = GameState.get_instance()
        deck = gs.zones.get("deck")
        if not deck or not deck.cards:
            return
        gs.push_snapshot()
        random.shuffle(deck.cards)
        game_signals.action_logged.emit("山札をシャッフル")
        game_signals.zones_updated.emit()
        if "deck" in self.zone_widgets:
            self.zone_widgets["deck"].start_shuffle_anim()

    def _initialize_field(self):
        gs = GameState.get_instance()
        msg = (f"「{gs.current_deck.name}」でゲームを開始しますか？\nデッキをシャッフルし、シールド5枚・手札5枚を配ります。"
               if gs.current_deck else "デッキが読み込まれていません。全ゾーンを空にしますか？")
        if QMessageBox.question(self, "確認", msg) != QMessageBox.StandardButton.Yes:
            return
        gs.initialize_field()
        game_signals.action_logged.emit("ゲームを開始")
        game_signals.zones_updated.emit()

    # ── 保存・ロード ─────────────────────────────────────────────────

    def _save_game(self):
        os.makedirs("data/saves", exist_ok=True)
        default = os.path.join("data/saves", datetime.now().strftime("game_%Y%m%d_%H%M%S.json"))
        path, _ = QFileDialog.getSaveFileName(self, "試合を保存", default, "JSON Files (*.json)")
        if not path:
            return
        try:
            GameState.get_instance().save(path)
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"保存失敗: {e}")

    def _load_game(self):
        path, _ = QFileDialog.getOpenFileName(self, "試合をロード", "data/saves", "JSON Files (*.json)")
        if not path:
            return
        gs = GameState.get_instance()
        snapshot = gs.to_dict()
        try:
            gs.load_file(path)
            gs.push_dict(snapshot)
            game_signals.zones_updated.emit()
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"ロード失敗: {e}")

    def _undo(self):
        if GameState.get_instance().undo():
            game_signals.action_logged.emit("アンドゥ")
            game_signals.zones_updated.emit()

    # ── デッキ読み込み（手札ウィンドウ専用）───────────────────────────

    def _load_deck(self):
        path, _ = QFileDialog.getOpenFileName(self, "デッキファイルを選択", "data/decks", "JSON Files (*.json)")
        if not path:
            return
        self._apply_deck(path)

    def _apply_deck(self, path: str):
        try:
            deck = Deck.load(path)
            self.deck_label.setText(deck.name)
            self.deck_list.set_deck(deck)
            gs = GameState.get_instance()
            gs.current_deck = deck
            gs.back_image_path = deck.back_image_path
            game_signals.zones_updated.emit()
            cfg = _load_config()
            cfg["last_deck"] = path
            _save_config(cfg)
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"読み込み失敗: {e}")

    def _restore_last_deck(self):
        path = _load_config().get("last_deck")
        if path and os.path.exists(path):
            self._apply_deck(path)

    # ── ダイアログ ──────────────────────────────────────────────────

    def _open_dice(self):
        from .dice_dialog import DiceDialog
        if self._dice_dialog is None or not self._dice_dialog.isVisible():
            self._dice_dialog = DiceDialog(self)
            self._dice_dialog.show()
        else:
            self._dice_dialog.raise_()
            self._dice_dialog.activateWindow()

    def _open_keybinding_settings(self):
        from .keybinding_dialog import KeybindingDialog
        dlg = KeybindingDialog(self)
        if dlg.exec():
            self._refresh_shortcuts()

    def _open_deck_manager(self):
        DeckManagerDialog(self).exec()

    def _open_layout_editor(self):
        from .layout_editor import LayoutEditorDialog
        dlg = LayoutEditorDialog(self.win_def, self._win_defs, self._all_zone_defs, self)
        dlg.exec()

    def _reload_layout(self, zone_defs: list[ZoneDefinition]):
        from .zone_widget import register_zone_defs

        self._all_zone_defs = zone_defs
        self.zone_defs = [z for z in zone_defs if z.window_id == self.win_def.id]
        register_zone_defs(zone_defs)

        # グリッドの全アイテムを取り出す（ウィジェット自体は消えない）
        while self._grid_layout.count():
            self._grid_layout.takeAt(0)

        # stretch を再設定
        self._apply_grid_stretches()

        # ゾーンウィジェットを新しい位置に再配置し、内部の zone_def も更新
        for zd in self.zone_defs:
            widget = self.zone_widgets.get(zd.id)
            if widget is None:
                continue
            if isinstance(widget, ZoneWidget):
                widget.zone_def = zd
            gp = zd.grid_pos
            self._grid_layout.addWidget(widget, gp.row, gp.col, gp.row_span, gp.col_span)

        # アクションログを右端に再追加
        if self._action_log is not None:
            self._grid_layout.addWidget(
                self._action_log, 0, self.win_def.grid_cols, self.win_def.grid_rows, 1
            )

        # Qt にレイアウト再計算を強制
        self._grid_layout.activate()
        self._grid_container.update()
