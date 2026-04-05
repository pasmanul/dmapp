import os
from datetime import datetime

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from models.game_state import GameState, GameCard, ZoneType
from models.card import Card

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
        self.battle_zone = ZoneWidget(ZoneType.BATTLE, "バトルゾーン")
        self.battle_zone.setMinimumHeight(80)
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

        # Mana zone
        self.mana_zone = ZoneWidget(ZoneType.MANA, "マナゾーン")
        self.mana_zone.setMinimumHeight(80)
        vsplit.addWidget(self._make_tap_panel(self.mana_zone, ZoneType.MANA))

        # Public hand
        self.public_hand_zone = ZoneWidget(ZoneType.HAND, "手札", mask_cards=True)
        self.public_hand_zone.setMinimumHeight(80)
        vsplit.addWidget(self.public_hand_zone)

        vsplit.setSizes([240, 160, 220, 120])
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

        def reposition():
            w = zone_widget.width()
            untap_btn.move(w - 46, 2)
            tap_btn.move(w - 46 - 54, 2)

        zone_widget.installEventFilter(self)
        zone_widget._reposition_tap_btns = reposition
        reposition()

        return zone_widget

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Resize and hasattr(obj, '_reposition_tap_btns'):
            obj._reposition_tap_btns()
        return super().eventFilter(obj, event)

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
        ctrl = QHBoxLayout()
        ctrl.setSpacing(4)

        draw_btn = QPushButton("ドロー")
        draw_btn.setFixedHeight(26)
        draw_btn.setStyleSheet(
            "QPushButton { background: #2a5a2a; color: #eee; border: 1px solid #555; border-radius: 3px; }"
            "QPushButton:hover { background: #3a7a3a; }"
        )
        draw_btn.clicked.connect(self._draw_card)
        ctrl.addWidget(draw_btn)

        add_btn = QPushButton("+1")
        add_btn.setFixedHeight(26)
        add_btn.setFixedWidth(60)
        add_btn.setStyleSheet(
            "QPushButton { background: #2a4a6a; color: #eee; border: 1px solid #555; border-radius: 3px; }"
            "QPushButton:hover { background: #3a5a8a; }"
        )
        add_btn.clicked.connect(self._add_deck_card)
        ctrl.addWidget(add_btn)

        self._deck_input = QLineEdit()
        self._deck_input.setFixedHeight(26)
        self._deck_input.setFixedWidth(40)
        self._deck_input.setMaxLength(2)
        self._deck_input.setPlaceholderText("枚")
        self._deck_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._deck_input.setStyleSheet(
            "QLineEdit { background: #2a2a4a; color: #eee; border: 1px solid #555; border-radius: 3px; }"
        )
        self._deck_input.returnPressed.connect(self._set_deck_count)
        ctrl.addWidget(self._deck_input)

        set_btn = QPushButton("セット")
        set_btn.setFixedHeight(26)
        set_btn.setStyleSheet(
            "QPushButton { background: #3a3a6a; color: #eee; border: 1px solid #555; border-radius: 3px; }"
            "QPushButton:hover { background: #4a4a8a; }"
        )
        set_btn.clicked.connect(self._set_deck_count)
        ctrl.addWidget(set_btn)

        layout.addLayout(ctrl)
        return panel

    def _draw_card(self):
        gs = GameState.get_instance()
        deck = gs.zones[ZoneType.DECK]
        if len(deck) == 0:
            return
        gs.push_snapshot()
        deck.remove_card(len(deck) - 1)
        game_signals.zones_updated.emit()

    def _add_deck_card(self):
        from models.game_state import _dummy_card
        gs = GameState.get_instance()
        gs.push_snapshot()
        gs.zones[ZoneType.DECK].add_card(_dummy_card())
        game_signals.zones_updated.emit()

    def _set_deck_count(self):
        text = self._deck_input.text().strip()
        try:
            target = int(text)
        except ValueError:
            return
        if target < 0:
            return
        gs = GameState.get_instance()
        gs.push_snapshot()
        deck = gs.zones[ZoneType.DECK]
        current = len(deck)
        if target > current:
            for _ in range(target - current):
                from models.game_state import _dummy_card
                deck.add_card(_dummy_card())
        elif target < current:
            for _ in range(current - target):
                deck.remove_card(len(deck) - 1)
        self._deck_input.clear()
        game_signals.zones_updated.emit()

    def _initialize_field(self):
        if QMessageBox.question(self, "確認", "フィールドを初期状態（シールド5枚・山札30枚）にリセットしますか？") \
                != QMessageBox.StandardButton.Yes:
            return
        GameState.get_instance().initialize_field()
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
        try:
            GameState.get_instance().push_snapshot()
            GameState.get_instance().load_file(path)
            game_signals.zones_updated.emit()
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"ロード失敗: {e}")

    def _undo(self):
        if GameState.get_instance().undo():
            game_signals.zones_updated.emit()

    def _open_deck_manager(self):
        DeckManagerDialog(self).exec()
