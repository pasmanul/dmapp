import os
from datetime import datetime

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from models.game_state import GameState, ZoneType

from .constants import BATTLE_CARD_SCALE, CARD_H
from .deck_manager import DeckManagerDialog
from .signals import game_signals
from .zone_widget import ZoneWidget


class BoardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("デュエルマスターズ — フィールド（画面共有用）")
        self.resize(960, 780)
        self.setStyleSheet("background-color: #1a1a2e;")
        self._setup_menu()
        self._setup_ui()
        self._setup_shortcuts()

    def _setup_menu(self):
        menu = self.menuBar()
        game_menu = menu.addMenu("ファイル")
        game_menu.addAction("初期状態にリセット", self._initialize_field)
        game_menu.addAction("フィールドを全消去", self._reset_field)
        game_menu.addSeparator()
        game_menu.addAction("試合を保存　Ctrl+S", self._save_game)
        game_menu.addAction("試合をロード…", self._load_game)
        game_menu.addAction("アンドゥ　Ctrl+Z", self._undo)
        game_menu.addSeparator()
        game_menu.addAction("デッキ管理を開く", self._open_deck_manager)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setSpacing(4)
        outer.setContentsMargins(6, 6, 6, 6)

        # ── Toolbar ──────────────────────────────────────────────────
        toolbar = QHBoxLayout()
        reset_btn = QPushButton("初期状態にリセット")
        reset_btn.setFixedHeight(28)
        reset_btn.setStyleSheet(
            "QPushButton { background: #3a3a6a; color: #ddd; border: 1px solid #666; border-radius: 4px; padding: 0 12px; }"
            "QPushButton:hover { background: #4a4a8a; }"
        )
        reset_btn.clicked.connect(self._initialize_field)
        toolbar.addStretch()
        toolbar.addWidget(reset_btn)
        outer.addLayout(toolbar)

        # ── Vertical splitter ─────────────────────────────────────────
        vsplit = QSplitter(Qt.Orientation.Vertical)
        vsplit.setStyleSheet(
            "QSplitter::handle:vertical { background: #3a3a5a; height: 4px; }"
            "QSplitter::handle:horizontal { background: #3a3a5a; width: 4px; }"
        )

        # Battle zone
        battle_ch = int(CARD_H * BATTLE_CARD_SCALE)
        self.battle_zone = ZoneWidget(ZoneType.BATTLE, "バトルゾーン", card_scale=BATTLE_CARD_SCALE)
        battle_min_h = battle_ch + battle_ch // 2 + ZoneWidget.TITLE_H + 8
        self.battle_zone.setMinimumHeight(battle_min_h)
        vsplit.addWidget(self._make_tap_panel(self.battle_zone, ZoneType.BATTLE))

        # Middle row: Shield | Deck | Graveyard
        mid = QSplitter(Qt.Orientation.Horizontal)
        mid.setStyleSheet("QSplitter::handle { background: #3a3a5a; width: 4px; }")
        self.shield_zone = ZoneWidget(ZoneType.SHIELD, "シールド")
        mid.addWidget(self.shield_zone)
        mid.addWidget(self._make_deck_panel())
        self.grave_zone = ZoneWidget(ZoneType.GRAVEYARD, "墓地")
        mid.addWidget(self.grave_zone)
        mid.setSizes([620, 170, 170])
        vsplit.addWidget(mid)

        # Mana zone + Public hand (horizontal)
        mana_row = QSplitter(Qt.Orientation.Horizontal)
        mana_row.setStyleSheet("QSplitter::handle { background: #3a3a5a; width: 4px; }")

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
        btn_style = (
            "QPushButton { background: rgba(40,40,80,200); color: #ccc;"
            " border: 1px solid #555; border-radius: 2px; font-size: 9px; padding: 0 4px; }"
            "QPushButton:hover { background: rgba(70,70,130,220); }"
        )
        untap_btn = QPushButton("全解除", zone_widget)
        untap_btn.setFixedSize(44, 18)
        untap_btn.setStyleSheet(btn_style)
        untap_btn.raise_()
        untap_btn.clicked.connect(lambda: self._set_all_tap(zone_type, False))

        tap_btn = QPushButton("全タップ", zone_widget)
        tap_btn.setFixedSize(52, 18)
        tap_btn.setStyleSheet(btn_style)
        tap_btn.raise_()
        tap_btn.clicked.connect(lambda: self._set_all_tap(zone_type, True))

        sort_btn = None
        if zone_type == ZoneType.BATTLE:
            sort_btn = QPushButton("ソート", zone_widget)
            sort_btn.setFixedSize(48, 18)
            sort_btn.setStyleSheet(btn_style)
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
        _CIV_ORDER = ["無色", "光", "水", "闇", "火", "自然"]
        _TYPE_ORDER = [
            "タマシード", "クリーチャー", "ネオ進化", "Gネオ進化", "スター進化", "S-MAX進化",
            "ツインパクト", "呪文", "クロスギア", "D2フィールド",
        ]

        def _sort_key(gc):
            c = gc.card
            civs = c.civilizations or []
            n = len(civs)
            if n == 0:
                civ_rank = 0                       # 無色
            elif n == 1:
                civ_rank = _CIV_ORDER.index(civs[0]) + 1 if civs[0] in _CIV_ORDER else len(_CIV_ORDER) + 1
            else:
                civ_rank = len(_CIV_ORDER) + n    # 多色：色数が少ない順
            type_rank = _TYPE_ORDER.index(c.card_type) if c.card_type in _TYPE_ORDER else len(_TYPE_ORDER)
            return (c.mana, type_rank, civ_rank, c.name)

        gs = GameState.get_instance()
        gs.push_snapshot()
        row0 = sorted([gc for gc in gs.zones[ZoneType.BATTLE].cards if gc.row == 0], key=_sort_key)
        row1 = sorted([gc for gc in gs.zones[ZoneType.BATTLE].cards if gc.row == 1], key=_sort_key)
        gs.zones[ZoneType.BATTLE].cards[:] = row0 + row1
        game_signals.zones_updated.emit()

    def _set_all_tap(self, zone_type: ZoneType, tapped: bool):
        GameState.get_instance().push_snapshot()
        for gc in GameState.get_instance().zones[zone_type].cards:
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
        btn_style = (
            "QPushButton {{ background: {bg}; color: #eee; border: 1px solid #555; border-radius: 3px; }}"
            "QPushButton:hover {{ background: {hover}; }}"
        )
        ctrl = QHBoxLayout()
        ctrl.setSpacing(4)

        draw_btn = QPushButton("ドロー")
        draw_btn.setFixedHeight(26)
        draw_btn.setStyleSheet(btn_style.format(bg="#2a5a2a", hover="#3a7a3a"))
        draw_btn.clicked.connect(self._draw_card)
        ctrl.addWidget(draw_btn)

        shuffle_btn = QPushButton("シャッフル")
        shuffle_btn.setFixedHeight(26)
        shuffle_btn.setStyleSheet(btn_style.format(bg="#5a3a2a", hover="#7a4a3a"))
        shuffle_btn.clicked.connect(self._shuffle_deck)
        ctrl.addWidget(shuffle_btn)

        layout.addLayout(ctrl)
        return panel

    def _draw_card(self):
        gs = GameState.get_instance()
        deck = gs.zones[ZoneType.DECK]
        if len(deck) == 0:
            return
        gs.push_snapshot()
        gc = deck.remove_card(len(deck) - 1)  # 山札の一番上（末尾）
        if gc:
            gc.face_down = False
            gs.zones[ZoneType.HAND].add_card(gc)
        game_signals.zones_updated.emit()

    def _shuffle_deck(self):
        import random
        gs = GameState.get_instance()
        deck = gs.zones[ZoneType.DECK]
        if len(deck) == 0:
            return
        gs.push_snapshot()
        random.shuffle(deck.cards)
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
        game_signals.zones_updated.emit()

    def _reset_field(self):
        if QMessageBox.question(self, "確認", "フィールドのカードをすべて削除しますか？") \
                != QMessageBox.StandardButton.Yes:
            return
        GameState.get_instance().reset_field()
        game_signals.zones_updated.emit()

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._save_game)
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self._undo)

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
            game_signals.zones_updated.emit()

    def _open_deck_manager(self):
        DeckManagerDialog(self).exec()
