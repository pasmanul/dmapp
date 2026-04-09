import json
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models.deck import Deck
from models.game_state import GameState, ZoneType
from .signals import game_signals

from .deck_list_widget import DeckListWidget
from .deck_manager import DeckManagerDialog
from .zone_widget import ZoneWidget

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


class HandWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("手札・デッキ（非公開）")
        self.resize(540, 720)
        self.setStyleSheet("background-color: #1a1a2e;")
        self.current_deck: Deck | None = None
        self._setup_ui()
        self._restore_last_deck()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(6)
        layout.setContentsMargins(6, 6, 6, 6)

        # ── Control bar ──────────────────────────────────────────────
        ctrl = QHBoxLayout()
        self.deck_label = QLabel("デッキ未選択")
        self.deck_label.setStyleSheet("color: #aaa; font-size: 10px;")
        ctrl.addWidget(self.deck_label, 1)

        load_btn = QPushButton("デッキ読み込み")
        load_btn.clicked.connect(self._load_deck)
        ctrl.addWidget(load_btn)

        mgr_btn = QPushButton("デッキ管理")
        mgr_btn.clicked.connect(self._open_manager)
        ctrl.addWidget(mgr_btn)

        layout.addLayout(ctrl)

        # ── Hand zone ────────────────────────────────────────────────
        hand_header = QHBoxLayout()
        hand_title = QLabel("手札")
        hand_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hand_title.setStyleSheet("color: #ddd; font-weight: bold;")
        hand_header.addWidget(hand_title, 1)

        btn_style = (
            "QPushButton {{ background: {bg}; color: #eee; border: 1px solid #555; border-radius: 3px; padding: 0 10px; }}"
            "QPushButton:hover {{ background: {hover}; }}"
        )

        draw_btn = QPushButton("ドロー")
        draw_btn.setFixedHeight(24)
        draw_btn.setStyleSheet(btn_style.format(bg="#2a5a2a", hover="#3a7a3a"))
        draw_btn.clicked.connect(self._draw_card)
        hand_header.addWidget(draw_btn)

        sort_btn = QPushButton("ソート")
        sort_btn.setFixedHeight(24)
        sort_btn.setStyleSheet(btn_style.format(bg="#3a3a6a", hover="#4a4a8a"))
        sort_btn.clicked.connect(self._sort_hand)
        hand_header.addWidget(sort_btn)
        layout.addLayout(hand_header)

        self.hand_zone = ZoneWidget(ZoneType.HAND, "手札")
        self.hand_zone.setMinimumHeight(130)
        layout.addWidget(self.hand_zone)

        # ── Deck card list ───────────────────────────────────────────
        list_title = QLabel("デッキカード一覧  （ドラッグして各ゾーンに配置）")
        list_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        list_title.setStyleSheet("color: #ddd; font-weight: bold;")
        layout.addWidget(list_title)

        self.deck_list = DeckListWidget()
        layout.addWidget(self.deck_list, 1)

    def _sort_hand(self):
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
                civ_rank = 0
            elif n == 1:
                civ_rank = _CIV_ORDER.index(civs[0]) + 1 if civs[0] in _CIV_ORDER else len(_CIV_ORDER) + 1
            else:
                civ_rank = len(_CIV_ORDER) + n
            type_rank = _TYPE_ORDER.index(c.card_type) if c.card_type in _TYPE_ORDER else len(_TYPE_ORDER)
            return (c.mana, type_rank, civ_rank, c.name)

        gs = GameState.get_instance()
        gs.push_snapshot()
        gs.zones[ZoneType.HAND].cards.sort(key=_sort_key)
        game_signals.zones_updated.emit()

    def _draw_card(self):
        gs = GameState.get_instance()
        deck = gs.zones[ZoneType.DECK]
        if len(deck) == 0:
            return
        gs.push_snapshot()
        gc = deck.remove_card(len(deck) - 1)
        if gc:
            gc.face_down = False
            gs.zones[ZoneType.HAND].add_card(gc)
        game_signals.zones_updated.emit()

    def _load_deck(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "デッキファイルを選択", "data/decks", "JSON Files (*.json)"
        )
        if not path:
            return
        self._apply_deck(path)

    def _apply_deck(self, path: str):
        try:
            self.current_deck = Deck.load(path)
            self.deck_label.setText(self.current_deck.name)
            self.deck_list.set_deck(self.current_deck)
            GameState.get_instance().current_deck = self.current_deck
            cfg = _load_config()
            cfg["last_deck"] = path
            _save_config(cfg)
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"読み込み失敗: {e}")

    def _restore_last_deck(self):
        path = _load_config().get("last_deck")
        if path and os.path.exists(path):
            self._apply_deck(path)

    def _open_manager(self):
        DeckManagerDialog(self).exec()
