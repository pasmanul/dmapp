import os
import random
from datetime import datetime

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from models.card_library import card_sort_key
from models.game_state import GameState, ZoneType

from . import keybindings as kb
from .action_log_widget import ActionLogWidget
from .constants import BATTLE_CARD_SCALE, CARD_H
from .deck_manager import DeckManagerDialog
from .signals import game_signals
from .theme import (
    MENUBAR_STYLE, SPLITTER_STYLE, WIN_BG,
    btn_dice, btn_draw, btn_reset, btn_shuffle, btn_sort,
)
from .zone_widget import ZoneWidget, rebuild_key_zone


class BoardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("デュエルマスターズ — フィールド（画面共有用）")
        self.resize(960, 780)
        self.setStyleSheet(f"QMainWindow, QWidget {{ background-color: {WIN_BG}; }}")
        self.menuBar().setStyleSheet(MENUBAR_STYLE)
        self._setup_menu()
        self._setup_ui()
        self._setup_shortcuts()

    def _setup_menu(self):
        menu = self.menuBar()
        game_menu = menu.addMenu("ファイル")
        game_menu.addAction("初期状態にリセット", self._initialize_field)
        game_menu.addSeparator()
        save_action = QAction("試合を保存", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self._save_game)
        game_menu.addAction(save_action)
        game_menu.addAction("試合をロード…", self._load_game)
        undo_action = QAction("アンドゥ", self)
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        undo_action.triggered.connect(self._undo)
        game_menu.addAction(undo_action)
        game_menu.addSeparator()
        game_menu.addAction("デッキ管理を開く", self._open_deck_manager)

        settings_menu = menu.addMenu("設定")
        settings_menu.addAction("キーバインド設定…", self._open_keybinding_settings)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setSpacing(8)
        outer.setContentsMargins(10, 8, 10, 10)

        # ── Toolbar ──────────────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

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

        # ── Vertical splitter ─────────────────────────────────────────
        vsplit = QSplitter(Qt.Orientation.Vertical)
        vsplit.setStyleSheet(SPLITTER_STYLE)

        # Battle zone
        battle_ch = int(CARD_H * BATTLE_CARD_SCALE)
        self.battle_zone = ZoneWidget(ZoneType.BATTLE, "バトルゾーン", card_scale=BATTLE_CARD_SCALE)
        battle_min_h = battle_ch + battle_ch // 2 + ZoneWidget.TITLE_H + 8
        self.battle_zone.setMinimumHeight(battle_min_h)
        vsplit.addWidget(self._make_tap_panel(self.battle_zone, ZoneType.BATTLE))

        # Middle row: Shield | Deck | Graveyard | ActionLog
        mid = QSplitter(Qt.Orientation.Horizontal)
        mid.setStyleSheet(SPLITTER_STYLE)
        self.shield_zone = ZoneWidget(ZoneType.SHIELD, "シールド")
        mid.addWidget(self.shield_zone)
        mid.addWidget(self._make_deck_panel())
        self.grave_zone = ZoneWidget(ZoneType.GRAVEYARD, "墓地")
        mid.addWidget(self.grave_zone)
        self.action_log = ActionLogWidget()
        self.action_log.setMinimumWidth(120)
        mid.addWidget(self.action_log)
        mid.setSizes([480, 150, 150, 180])
        vsplit.addWidget(mid)

        # Mana zone + Public hand (horizontal)
        mana_row = QSplitter(Qt.Orientation.Horizontal)
        mana_row.setStyleSheet(SPLITTER_STYLE)

        self.mana_zone = ZoneWidget(ZoneType.MANA, "マナゾーン")
        self.mana_zone.setMinimumHeight(80)
        mana_row.addWidget(self._make_tap_panel(self.mana_zone, ZoneType.MANA))

        self.public_hand_zone = ZoneWidget(ZoneType.HAND, "手札", mask_cards=True)
        self.public_hand_zone.setMinimumHeight(80)
        mana_row.addWidget(self.public_hand_zone)

        mana_row.setSizes([780, 180])
        vsplit.addWidget(mana_row)

        vsplit.setSizes([439, 160, 220])
        outer.addWidget(vsplit)

    def _make_tap_panel(self, zone_widget: ZoneWidget, zone_type: ZoneType) -> ZoneWidget:
        _overlay_style = (
            "QPushButton { background: rgba(10,14,32,210); color: #99bbdd;"
            " border: 1px solid rgba(60,90,140,180); border-radius: 3px;"
            " font-size: 9px; font-family: 'Yu Gothic UI'; padding: 0 4px; }"
            "QPushButton:hover { background: rgba(30,50,100,230); color: #cce0ff; }"
        )
        untap_btn = QPushButton("全解除", zone_widget)
        untap_btn.setFixedSize(44, 18)
        untap_btn.setStyleSheet(_overlay_style)
        untap_btn.raise_()
        untap_btn.clicked.connect(lambda: self._set_all_tap(zone_type, False))

        tap_btn = QPushButton("全タップ", zone_widget)
        tap_btn.setFixedSize(52, 18)
        tap_btn.setStyleSheet(_overlay_style)
        tap_btn.raise_()
        tap_btn.clicked.connect(lambda: self._set_all_tap(zone_type, True))

        sort_btn = None
        if zone_type == ZoneType.BATTLE:
            sort_btn = QPushButton("ソート", zone_widget)
            sort_btn.setFixedSize(48, 18)
            sort_btn.setStyleSheet(_overlay_style)
            sort_btn.raise_()
            sort_btn.clicked.connect(self._sort_battle_zone)

        def reposition():
            w = zone_widget.width()
            untap_btn.move(w - 46, 2)
            tap_btn.move(w - 46 - 54, 2)
            if sort_btn:
                sort_btn.move(w - 46 - 54 - 52, 2)

        zone_widget.installEventFilter(self)
        zone_widget._reposition_tap_btns = reposition
        reposition()

        return zone_widget

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Resize and hasattr(obj, '_reposition_tap_btns'):
            obj._reposition_tap_btns()
        return super().eventFilter(obj, event)

    def _sort_battle_zone(self):
        gs = GameState.get_instance()
        gs.push_snapshot()
        row0 = sorted([gc for gc in gs.zones[ZoneType.BATTLE].cards if gc.row == 0], key=lambda gc: card_sort_key(gc.card))
        row1 = sorted([gc for gc in gs.zones[ZoneType.BATTLE].cards if gc.row == 1], key=lambda gc: card_sort_key(gc.card))
        gs.zones[ZoneType.BATTLE].cards[:] = row0 + row1
        game_signals.zones_updated.emit()

    def _set_all_tap(self, zone_type: ZoneType, tapped: bool):
        gs = GameState.get_instance()
        gs.push_snapshot()
        for gc in gs.zones[zone_type].cards:
            gc.tapped = tapped
        game_signals.zones_updated.emit()

    def _make_deck_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.deck_zone = ZoneWidget(ZoneType.DECK, "山札", pile_mode=True)
        layout.addWidget(self.deck_zone)

        # ── Controls ──────────────────────────────────────────────────
        ctrl = QHBoxLayout()
        ctrl.setSpacing(4)

        draw_btn = QPushButton("ドロー")
        draw_btn.setFixedHeight(26)
        draw_btn.setStyleSheet(btn_draw())
        draw_btn.clicked.connect(self._draw_card)
        ctrl.addWidget(draw_btn)

        shuffle_btn = QPushButton("シャッフル")
        shuffle_btn.setFixedHeight(26)
        shuffle_btn.setStyleSheet(btn_shuffle())
        shuffle_btn.clicked.connect(self._shuffle_deck)
        ctrl.addWidget(shuffle_btn)

        layout.addLayout(ctrl)
        return panel

    def _draw_card(self):
        if GameState.get_instance().draw_card():
            game_signals.action_logged.emit("ドロー")
            game_signals.zones_updated.emit()

    def _shuffle_deck(self):
        gs = GameState.get_instance()
        deck = gs.zones[ZoneType.DECK]
        if not deck.cards:
            return
        gs.push_snapshot()
        random.shuffle(deck.cards)
        game_signals.action_logged.emit("山札をシャッフル")
        game_signals.zones_updated.emit()
        self.deck_zone.start_shuffle_anim()

    def _initialize_field(self):
        gs = GameState.get_instance()
        if gs.current_deck is None:
            msg = "デッキが読み込まれていません。全ゾーンを空にしますか？"
        else:
            msg = f"「{gs.current_deck.name}」でゲームを開始しますか？\nデッキをシャッフルし、シールド5枚・手札5枚を配ります。"
        if QMessageBox.question(self, "確認", msg) != QMessageBox.StandardButton.Yes:
            return
        gs.initialize_field()
        game_signals.action_logged.emit("ゲームを開始")
        game_signals.zones_updated.emit()

    def _reset_field(self):
        if QMessageBox.question(self, "確認", "フィールドのカードをすべて削除しますか？") \
                != QMessageBox.StandardButton.Yes:
            return
        GameState.get_instance().reset_field()
        game_signals.action_logged.emit("フィールドをリセット")
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

    def _save_game(self):
        os.makedirs("data/saves", exist_ok=True)
        default = os.path.join(
            "data/saves",
            datetime.now().strftime("game_%Y%m%d_%H%M%S.json"),
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "試合を保存", default, "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            GameState.get_instance().save(path)
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"保存失敗: {e}")

    def _load_game(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "試合をロード", "data/saves", "JSON Files (*.json)"
        )
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

    def _open_dice(self):
        from .dice_dialog import DiceDialog
        if not hasattr(self, "_dice_dialog") or not self._dice_dialog.isVisible():
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
