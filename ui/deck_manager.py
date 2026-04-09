import os
import re
import uuid

from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QColor, QDrag, QFont, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from models.card import Card
from models.card_library import (
    CARD_TYPE_COLORS,
    CARD_TYPES,
    CIVILIZATIONS,
    CIV_COLORS,
    CardLibrary,
    LibraryCard,
)
from models.deck import Deck

DECKS_DIR = "data/decks"
DECK_THUMB_W, DECK_THUMB_H = 110, 154
LIB_THUMB_W, LIB_THUMB_H = 110, 154

_SORT_OPTIONS = ["マナ↑", "マナ↓", "名前順", "タイプ順"]

def _apply_sort(cards: list, option: str) -> list:
    if option == "マナ↑":
        return sorted(cards, key=lambda c: (c.mana, c.name))
    if option == "マナ↓":
        return sorted(cards, key=lambda c: (-c.mana, c.name))
    if option == "タイプ順":
        return sorted(cards, key=lambda c: (c.card_type, c.mana, c.name))
    return sorted(cards, key=lambda c: c.name)  # 名前順

CARD_MIME = "application/x-library-card-id"

_DIALOG_STYLE = """
    QDialog, QWidget, QSplitter { background-color: #1a1a2e; color: #ddd; }
    QLineEdit, QSpinBox, QComboBox {
        background: #2a2a4a; color: #ddd; border: 1px solid #555;
        padding: 2px 4px;
    }
    QPushButton {
        background: #3a3a6a; color: #ddd; border: 1px solid #555;
        border-radius: 3px; padding: 2px 8px;
    }
    QPushButton:hover { background: #4a4a8a; }
    QListWidget { background: #2a2a4a; color: #ddd; border: 1px solid #555; }
    QListWidget::item:selected { background: #4a4a8a; }
    QScrollArea { background: #1a1a2e; border: none; }
    QLabel { color: #ddd; }
    QCheckBox { color: #ddd; }
"""


def _sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', name).strip()


def _is_rainbow(civs: list[str]) -> bool:
    return len([c for c in civs if c != "無色"]) >= 2


# ---------------------------------------------------------------------------
# Civilization dots (reusable)
# ---------------------------------------------------------------------------

class _CivDots(QWidget):
    DOT = 10

    def __init__(self, civs: list[str], parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: transparent;")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(3)
        row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        for civ in civs:
            dot = QLabel()
            dot.setFixedSize(self.DOT, self.DOT)
            color = CIV_COLORS.get(civ, "#888")
            dot.setStyleSheet(
                f"background: {color}; border-radius: {self.DOT // 2}px; border: none;"
            )
            dot.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            row.addWidget(dot)
        if _is_rainbow(civs):
            rb = QLabel("R")
            rb.setFont(QFont("Arial", 7, QFont.Weight.Bold))
            rb.setStyleSheet("color: #ffffff; border: none;")
            rb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            row.addWidget(rb)


# ---------------------------------------------------------------------------
# Library card tile (draggable)
# ---------------------------------------------------------------------------

class _LibraryCardTile(QFrame):
    def __init__(self, card: LibraryCard, on_click=None, parent=None):
        super().__init__(parent)
        self.card = card
        self._on_click = on_click
        self._drag_start = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._set_normal_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        thumb = QLabel()
        thumb.setFixedSize(LIB_THUMB_W, LIB_THUMB_H)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        pix = QPixmap(card.image_path)
        if not pix.isNull():
            pix = pix.scaled(
                LIB_THUMB_W, LIB_THUMB_H,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            pix = QPixmap(LIB_THUMB_W, LIB_THUMB_H)
            pix.fill(QColor(70, 70, 70))
        thumb.setPixmap(pix)
        layout.addWidget(thumb, 0, Qt.AlignmentFlag.AlignHCenter)

        name_lbl = QLabel(card.name)
        name_lbl.setFont(QFont("Arial", 7))
        name_lbl.setStyleSheet("color: #ddd; border: none;")
        name_lbl.setWordWrap(True)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setMaximumWidth(LIB_THUMB_W + 4)
        name_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(name_lbl)

        info_widget = QWidget()
        info_widget.setStyleSheet("background: transparent;")
        info_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        info_row = QHBoxLayout(info_widget)
        info_row.setContentsMargins(0, 0, 0, 0)
        info_row.setSpacing(3)

        mana_lbl = QLabel(f"M{card.mana}")
        mana_lbl.setFont(QFont("Arial", 7, QFont.Weight.Bold))
        mana_lbl.setStyleSheet("color: #44bbff; border: none;")
        mana_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        info_row.addWidget(mana_lbl)

        for civ in card.civilizations:
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(
                f"background: {CIV_COLORS.get(civ, '#888')}; "
                "border-radius: 4px; border: none;"
            )
            dot.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            info_row.addWidget(dot)

        layout.addWidget(info_widget, 0, Qt.AlignmentFlag.AlignHCenter)

    def _set_normal_style(self):
        self.setStyleSheet(
            "QFrame { background: #2a2a2a; border: 1px solid #555; border-radius: 4px; }"
        )

    def set_selected(self, selected: bool):
        if selected:
            self.setStyleSheet(
                "QFrame { background: #2a3a5a; border: 2px solid #5599ff; border-radius: 4px; }"
            )
        else:
            self._set_normal_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.pos()
            if self._on_click:
                self._on_click(self.card.id)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (self._drag_start is not None
                and event.buttons() & Qt.MouseButton.LeftButton):
            dist = (event.pos() - self._drag_start).manhattanLength()
            if dist >= 10:
                self._start_drag()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start = None
        super().mouseReleaseEvent(event)

    def _start_drag(self):
        self._drag_start = None
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(CARD_MIME, self.card.id.encode())
        drag.setMimeData(mime)
        pix = self.grab()
        pix = pix.scaled(
            LIB_THUMB_W, LIB_THUMB_H,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        drag.setPixmap(pix)
        drag.setHotSpot(pix.rect().center())
        drag.exec(Qt.DropAction.CopyAction)


# ---------------------------------------------------------------------------
# Library card grid
# ---------------------------------------------------------------------------

class _LibraryCardGrid(QWidget):
    _TILE_W = LIB_THUMB_W + 8 + 6

    def __init__(self, on_select=None, parent=None):
        super().__init__(parent)
        self._on_select = on_select  # callback(card: LibraryCard | None)
        self.setStyleSheet("background: #1a1a1a;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        ctrl_row = QHBoxLayout()
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("カード名で検索...")
        self._search_edit.textChanged.connect(self._refresh_filter)
        ctrl_row.addWidget(self._search_edit)
        self._sort_combo = QComboBox()
        self._sort_combo.setFixedWidth(80)
        for opt in _SORT_OPTIONS:
            self._sort_combo.addItem(opt)
        self._sort_combo.currentTextChanged.connect(self._refresh_filter)
        ctrl_row.addWidget(self._sort_combo)
        outer.addLayout(ctrl_row)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)

        mana_lbl = QLabel("マナ:")
        mana_lbl.setFixedWidth(30)
        filter_row.addWidget(mana_lbl)
        self._mana_combo = QComboBox()
        self._mana_combo.setFixedWidth(65)
        self._mana_combo.addItem("すべて")
        for i in range(1, 13):
            self._mana_combo.addItem(str(i))
        self._mana_combo.addItem("12+")
        self._mana_combo.currentTextChanged.connect(self._refresh_filter)
        filter_row.addWidget(self._mana_combo)

        civ_lbl = QLabel("文明:")
        civ_lbl.setFixedWidth(30)
        filter_row.addWidget(civ_lbl)
        self._civ_combo = QComboBox()
        self._civ_combo.setFixedWidth(65)
        self._civ_combo.addItem("すべて")
        for civ in CIVILIZATIONS:
            self._civ_combo.addItem(civ)
        self._civ_combo.currentTextChanged.connect(self._refresh_filter)
        filter_row.addWidget(self._civ_combo)

        type_lbl = QLabel("タイプ:")
        type_lbl.setFixedWidth(40)
        filter_row.addWidget(type_lbl)
        self._type_combo = QComboBox()
        self._type_combo.setFixedWidth(110)
        self._type_combo.addItem("すべて")
        for ct in CARD_TYPES:
            self._type_combo.addItem(ct)
        self._type_combo.currentTextChanged.connect(self._refresh_filter)
        filter_row.addWidget(self._type_combo)

        reset_btn = QPushButton("リセット")
        reset_btn.setFixedWidth(55)
        reset_btn.clicked.connect(self._reset_filters)
        filter_row.addWidget(reset_btn)
        filter_row.addStretch()
        outer.addLayout(filter_row)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { background: #1a1a1a; border: none; }
            QScrollBar:vertical { background: #1a1a1a; width: 10px; border: none; }
            QScrollBar::handle:vertical { background: #555; border-radius: 5px; min-height: 20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        self._scroll.viewport().setStyleSheet("background: #1a1a1a;")

        self._container = QWidget()
        self._container.setStyleSheet("background: #1a1a1a;")
        self._grid = QGridLayout(self._container)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._grid.setSpacing(6)
        self._grid.setContentsMargins(6, 6, 6, 6)

        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll)

        self._tiles: list[_LibraryCardTile] = []
        self._selected_id: str | None = None
        self._cols: int = 3
        self._all_cards: list[LibraryCard] = []

    def _calc_cols(self) -> int:
        return max(2, (self.width() - 12 - 10) // self._TILE_W)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        new_cols = self._calc_cols()
        if new_cols != self._cols:
            self._cols = new_cols
            self._refresh_filter()

    def load_library(self, library: CardLibrary):
        self._all_cards = list(library.cards)
        self._refresh_filter()

    def _refresh_filter(self):
        query = self._search_edit.text().lower()
        mana_sel = self._mana_combo.currentText()
        civ_sel = self._civ_combo.currentText()
        type_sel = self._type_combo.currentText()

        filtered = []
        for c in self._all_cards:
            if query and query not in c.name.lower():
                continue
            if mana_sel != "すべて":
                if mana_sel == "12+":
                    if c.mana < 12:
                        continue
                else:
                    if c.mana != int(mana_sel):
                        continue
            if civ_sel != "すべて" and civ_sel not in c.civilizations:
                continue
            if type_sel != "すべて" and c.card_type != type_sel:
                continue
            filtered.append(c)

        self._populate(_apply_sort(filtered, self._sort_combo.currentText()))

    def _reset_filters(self):
        self._search_edit.blockSignals(True)
        self._mana_combo.blockSignals(True)
        self._civ_combo.blockSignals(True)
        self._type_combo.blockSignals(True)
        self._search_edit.clear()
        self._mana_combo.setCurrentIndex(0)
        self._civ_combo.setCurrentIndex(0)
        self._type_combo.setCurrentIndex(0)
        self._search_edit.blockSignals(False)
        self._mana_combo.blockSignals(False)
        self._civ_combo.blockSignals(False)
        self._type_combo.blockSignals(False)
        self._refresh_filter()

    def _populate(self, cards: list[LibraryCard]):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self._tiles.clear()

        for i, card in enumerate(cards):
            tile = _LibraryCardTile(card, on_click=self._on_tile_click)
            self._tiles.append(tile)
            self._grid.addWidget(tile, i // self._cols, i % self._cols)

    def _on_tile_click(self, card_id: str):
        self._selected_id = card_id
        for tile in self._tiles:
            tile.set_selected(tile.card.id == card_id)
        if self._on_select:
            self._on_select(self.get_selected_card())

    def get_selected_card(self) -> LibraryCard | None:
        if self._selected_id is None:
            return None
        return next((c for c in self._all_cards if c.id == self._selected_id), None)

    def clear_selection(self):
        self._selected_id = None
        for tile in self._tiles:
            tile.set_selected(False)


# ---------------------------------------------------------------------------
# Deck card tile
# ---------------------------------------------------------------------------

class _DeckCardTile(QFrame):
    def __init__(self, card: Card, on_click=None, parent=None):
        super().__init__(parent)
        self.card = card
        self._on_click = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._set_normal_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        thumb = QLabel()
        thumb.setFixedSize(DECK_THUMB_W, DECK_THUMB_H)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        pix = QPixmap(card.image_path)
        if not pix.isNull():
            pix = pix.scaled(DECK_THUMB_W, DECK_THUMB_H,
                             Qt.AspectRatioMode.IgnoreAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        else:
            pix = QPixmap(DECK_THUMB_W, DECK_THUMB_H)
            pix.fill(QColor(70, 70, 70))
        thumb.setPixmap(pix)
        layout.addWidget(thumb, 0, Qt.AlignmentFlag.AlignHCenter)

        name_lbl = QLabel(card.name)
        name_lbl.setFont(QFont("Arial", 8))
        name_lbl.setStyleSheet("color: #ddd; border: none;")
        name_lbl.setWordWrap(True)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(name_lbl)

        if card.civilizations:
            dots = _CivDots(card.civilizations)
            layout.addWidget(dots, 0, Qt.AlignmentFlag.AlignHCenter)

        if card.card_type:
            type_color = CARD_TYPE_COLORS.get(card.card_type, "#aaa")
            type_lbl = QLabel(card.card_type)
            type_lbl.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            type_lbl.setStyleSheet(f"color: {type_color}; border: none;")
            type_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            type_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout.addWidget(type_lbl)

        info_widget = QWidget()
        info_widget.setStyleSheet("background: transparent;")
        info_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        info_row = QHBoxLayout(info_widget)
        info_row.setContentsMargins(0, 0, 0, 0)
        info_row.setSpacing(4)

        mana_lbl = QLabel(f"M{card.mana}")
        mana_lbl.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        mana_lbl.setStyleSheet("color: #44bbff; border: none;")
        mana_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        info_row.addWidget(mana_lbl)

        count_lbl = QLabel(f"×{card.count}")
        count_lbl.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        count_lbl.setStyleSheet("color: #ffdd44; border: none;")
        count_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        info_row.addWidget(count_lbl)

        layout.addWidget(info_widget, 0, Qt.AlignmentFlag.AlignHCenter)

    def _set_normal_style(self):
        self.setStyleSheet(
            "QFrame { background: #2a2a2a; border: 1px solid #555; border-radius: 4px; }"
        )

    def set_selected(self, selected: bool):
        if selected:
            self.setStyleSheet(
                "QFrame { background: #3a5a3a; border: 2px solid #55ff55; border-radius: 4px; }"
            )
        else:
            self._set_normal_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._on_click:
            self._on_click(self.card.id)
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# Deck card grid (drop target)
# ---------------------------------------------------------------------------

class _DeckCardGrid(QWidget):
    _TILE_W = DECK_THUMB_W + 8 + 6

    def __init__(self, on_drop=None, parent=None):
        super().__init__(parent)
        self._on_drop = on_drop
        self.setStyleSheet("background: #1a1a1a;")
        self.setAcceptDrops(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        sort_row = QHBoxLayout()
        sort_row.addStretch()
        sort_lbl = QLabel("ソート:")
        sort_lbl.setStyleSheet("color: #aaa; font-size: 11px;")
        sort_row.addWidget(sort_lbl)
        self._sort_combo = QComboBox()
        self._sort_combo.setFixedWidth(80)
        for opt in _SORT_OPTIONS:
            self._sort_combo.addItem(opt)
        self._sort_combo.currentTextChanged.connect(
            lambda: self.refresh(self._current_deck)
        )
        sort_row.addWidget(self._sort_combo)
        outer.addLayout(sort_row)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { background: #1a1a1a; border: none; }
            QScrollBar:vertical { background: #1a1a1a; width: 10px; border: none; }
            QScrollBar::handle:vertical { background: #555; border-radius: 5px; min-height: 20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        self._scroll.viewport().setStyleSheet("background: #1a1a1a;")

        self._container = QWidget()
        self._container.setStyleSheet("background: #1a1a1a;")
        self._grid = QGridLayout(self._container)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._grid.setSpacing(6)
        self._grid.setContentsMargins(6, 6, 6, 6)

        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll)

        self._entries: list[_DeckCardTile] = []
        self._selected_id: str | None = None
        self._cols: int = 4
        self._current_deck: Deck | None = None

    def _calc_cols(self) -> int:
        return max(2, (self.width() - 12 - 10) // self._TILE_W)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        new_cols = self._calc_cols()
        if new_cols != self._cols:
            self._cols = new_cols
            self.refresh(self._current_deck)

    def refresh(self, deck: Deck | None):
        self._current_deck = deck
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self._entries.clear()

        if not deck:
            return
        sorted_cards = _apply_sort(deck.cards, self._sort_combo.currentText())
        for i, card in enumerate(sorted_cards):
            tile = _DeckCardTile(card, on_click=self._on_tile_click)
            self._entries.append(tile)
            self._grid.addWidget(tile, i // self._cols, i % self._cols)
            if card.id == self._selected_id:
                tile.set_selected(True)

    def _on_tile_click(self, card_id: str):
        self._selected_id = card_id
        for e in self._entries:
            e.set_selected(e.card.id == card_id)

    def get_selected_card_id(self) -> str | None:
        return self._selected_id

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasFormat(CARD_MIME):
            card_id = event.mimeData().data(CARD_MIME).data().decode()
            if self._on_drop:
                self._on_drop(card_id)
            event.acceptProposedAction()
        else:
            event.ignore()


# ---------------------------------------------------------------------------
# Main dialog
# ---------------------------------------------------------------------------

class DeckManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("デッキ管理")
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.setStyleSheet(_DIALOG_STYLE)
        self.resize(1100, 720)
        self.current_deck: Deck | None = None
        self._library = CardLibrary.get_instance()
        self._editing_card_id: str | None = None  # None = new card
        self._setup_ui()
        self._load_deck_list()

    # -----------------------------------------------------------------------
    # UI setup
    # -----------------------------------------------------------------------

    def _setup_ui(self):
        root = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_deck_panel())
        splitter.addWidget(self._build_library_panel())
        splitter.addWidget(self._build_editor_panel())
        splitter.setSizes([160, 420, 420])
        root.addWidget(splitter)

    # ---- Panel 1: Deck list ----

    def _build_deck_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("デッキ一覧"))
        self.deck_list = QListWidget()
        self.deck_list.currentTextChanged.connect(self._on_deck_selected)
        layout.addWidget(self.deck_list)
        btns = QHBoxLayout()
        new_btn = QPushButton("新規作成")
        new_btn.clicked.connect(self._new_deck)
        del_btn = QPushButton("削除")
        del_btn.clicked.connect(self._delete_deck)
        btns.addWidget(new_btn)
        btns.addWidget(del_btn)
        layout.addLayout(btns)
        return w

    # ---- Panel 2: Card library ----

    def _build_library_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.addWidget(QLabel("カードプール"))
        header.addStretch()
        self._lib_count_label = QLabel(f"{len(self._library.cards)} 枚")
        self._lib_count_label.setStyleSheet("color: #aaa; font-size: 11px;")
        header.addWidget(self._lib_count_label)
        layout.addLayout(header)

        self.library_grid = _LibraryCardGrid(on_select=self._on_library_card_selected)
        self.library_grid.load_library(self._library)
        layout.addWidget(self.library_grid)

        hint = QLabel("カードをデッキエリアへドラッグ＆ドロップで追加")
        hint.setStyleSheet("color: #888; font-size: 10px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        layout.addWidget(self._build_card_form())
        return w

    def _build_card_form(self) -> QFrame:
        form = QFrame()
        form.setStyleSheet(
            "QFrame#cardForm { border: 1px solid #444; border-radius: 4px; "
            "background: #1e1e35; }"
        )
        form.setObjectName("cardForm")
        g = QGridLayout(form)
        g.setContentsMargins(8, 6, 8, 6)
        g.setHorizontalSpacing(6)
        g.setVerticalSpacing(4)

        # Row 0: name
        g.addWidget(QLabel("カード名:"), 0, 0)
        self._f_name = QLineEdit()
        g.addWidget(self._f_name, 0, 1, 1, 3)

        # Row 1: image
        g.addWidget(QLabel("画像:"), 1, 0)
        self._f_img = QLineEdit()
        self._f_img.textChanged.connect(self._update_form_preview)
        g.addWidget(self._f_img, 1, 1, 1, 2)
        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(28)
        browse_btn.clicked.connect(self._browse_image)
        g.addWidget(browse_btn, 1, 3)

        # Row 2: preview (left) + mana/type (right)
        self._f_preview = QLabel()
        self._f_preview.setFixedSize(LIB_THUMB_W, LIB_THUMB_H)
        self._f_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._f_preview.setStyleSheet("background: #333; border: 1px solid #555;")
        g.addWidget(self._f_preview, 2, 0, 3, 1)

        mana_row = QHBoxLayout()
        mana_row.addWidget(QLabel("マナ:"))
        self._f_mana = QSpinBox()
        self._f_mana.setRange(0, 15)
        self._f_mana.setFixedWidth(55)
        mana_row.addWidget(self._f_mana)
        mana_row.addStretch()
        g.addLayout(mana_row, 2, 1, 1, 3)

        # Row 3: civilizations
        civ_row = QHBoxLayout()
        civ_row.addWidget(QLabel("文明:"))
        self._f_civ_checks: dict[str, QCheckBox] = {}
        for civ in CIVILIZATIONS:
            cb = QCheckBox(civ)
            color = CIV_COLORS.get(civ, "#aaa")
            cb.setStyleSheet(f"color: {color}; border: none;")
            self._f_civ_checks[civ] = cb
            civ_row.addWidget(cb)
        g.addLayout(civ_row, 3, 1, 1, 3)

        # Row 4: card type
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("タイプ:"))
        self._f_type = QComboBox()
        self._f_type.addItem("")
        for t in CARD_TYPES:
            self._f_type.addItem(t)
        type_row.addWidget(self._f_type)
        type_row.addStretch()
        g.addLayout(type_row, 4, 1, 1, 3)

        # Row 5: action buttons
        btn_row = QHBoxLayout()
        clear_btn = QPushButton("新規")
        clear_btn.setToolTip("フォームをクリアして新規入力モードにする")
        clear_btn.clicked.connect(self._clear_card_form)
        btn_row.addWidget(clear_btn)

        self._f_save_btn = QPushButton("登録")
        self._f_save_btn.clicked.connect(self._save_card_form)
        btn_row.addWidget(self._f_save_btn)

        self._f_delete_btn = QPushButton("削除")
        self._f_delete_btn.clicked.connect(self._delete_card)
        self._f_delete_btn.setEnabled(False)
        btn_row.addWidget(self._f_delete_btn)

        g.addLayout(btn_row, 5, 0, 1, 4)

        return form

    # ---- Panel 3: Deck editor ----

    def _build_editor_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("デッキ名:"))
        self.deck_name_edit = QLineEdit()
        self.deck_name_edit.textChanged.connect(self._on_deck_name_changed)
        name_row.addWidget(self.deck_name_edit)
        self.count_label = QLabel("0 / 40")
        name_row.addWidget(self.count_label)
        layout.addLayout(name_row)

        back_row = QHBoxLayout()
        back_row.addWidget(QLabel("裏面画像:"))
        self.back_img_edit = QLineEdit()
        self.back_img_edit.setPlaceholderText("未設定（デフォルト）")
        self.back_img_edit.textChanged.connect(self._on_back_image_changed)
        back_row.addWidget(self.back_img_edit)
        back_browse_btn = QPushButton("...")
        back_browse_btn.setFixedWidth(28)
        back_browse_btn.clicked.connect(self._browse_back_image)
        back_row.addWidget(back_browse_btn)
        back_clear_btn = QPushButton("×")
        back_clear_btn.setFixedWidth(24)
        back_clear_btn.setToolTip("裏面をデフォルトに戻す")
        back_clear_btn.clicked.connect(lambda: self.back_img_edit.clear())
        back_row.addWidget(back_clear_btn)
        layout.addLayout(back_row)

        layout.addWidget(QLabel("デッキ内容（ここへドロップ）"))

        self.deck_card_grid = _DeckCardGrid(on_drop=self._on_library_drop)
        layout.addWidget(self.deck_card_grid)

        count_ctrl = QHBoxLayout()
        plus_btn = QPushButton("+1")
        plus_btn.clicked.connect(self._inc_card)
        minus_btn = QPushButton("-1")
        minus_btn.clicked.connect(self._dec_card)
        remove_btn = QPushButton("削除")
        remove_btn.clicked.connect(self._remove_deck_card)
        count_ctrl.addWidget(plus_btn)
        count_ctrl.addWidget(minus_btn)
        count_ctrl.addWidget(remove_btn)
        layout.addLayout(count_ctrl)

        layout.addWidget(self._make_separator())

        save_btn = QPushButton("デッキを保存")
        save_btn.clicked.connect(self._save_deck)
        layout.addWidget(save_btn)

        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        return w

    def _make_separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #555;")
        return line

    # -----------------------------------------------------------------------
    # Deck list
    # -----------------------------------------------------------------------

    def _load_deck_list(self):
        self.deck_list.clear()
        os.makedirs(DECKS_DIR, exist_ok=True)
        for f in sorted(os.listdir(DECKS_DIR)):
            if f.endswith(".json"):
                self.deck_list.addItem(f[:-5])

    def _on_deck_selected(self, name: str):
        if not name:
            return
        path = os.path.join(DECKS_DIR, f"{name}.json")
        try:
            self.current_deck = Deck.load(path)
            self.deck_name_edit.setText(self.current_deck.name)
            self.back_img_edit.setText(self.current_deck.back_image_path)
            self._refresh_deck_grid()
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"読み込み失敗: {e}")

    def _new_deck(self):
        self.current_deck = Deck()
        self.deck_name_edit.setText(self.current_deck.name)
        self.back_img_edit.clear()
        self._refresh_deck_grid()

    def _delete_deck(self):
        item = self.deck_list.currentItem()
        if not item:
            return
        name = item.text()
        if (QMessageBox.question(self, "確認", f"「{name}」を削除しますか？")
                != QMessageBox.StandardButton.Yes):
            return
        path = os.path.join(DECKS_DIR, f"{name}.json")
        if os.path.exists(path):
            os.remove(path)
        self.current_deck = None
        self._load_deck_list()

    def _on_deck_name_changed(self, text: str):
        if self.current_deck:
            self.current_deck.name = text

    def _on_back_image_changed(self, text: str):
        if self.current_deck:
            self.current_deck.back_image_path = text.strip()

    def _browse_back_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "裏面画像を選択", "",
            "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        if path:
            self.back_img_edit.setText(path)

    # -----------------------------------------------------------------------
    # Card form (inline)
    # -----------------------------------------------------------------------

    def _on_library_card_selected(self, card: LibraryCard | None):
        if card is None:
            self._clear_card_form()
            return
        self._editing_card_id = card.id
        self._f_name.setText(card.name)
        self._f_img.setText(card.image_path)
        self._f_mana.setValue(card.mana)
        for civ, cb in self._f_civ_checks.items():
            cb.setChecked(civ in card.civilizations)
        idx = self._f_type.findText(card.card_type)
        self._f_type.setCurrentIndex(idx if idx >= 0 else 0)
        self._f_save_btn.setText("更新")
        self._f_delete_btn.setEnabled(True)

    def _clear_card_form(self):
        self._editing_card_id = None
        self._f_name.clear()
        self._f_img.clear()
        self._f_mana.setValue(0)
        for cb in self._f_civ_checks.values():
            cb.setChecked(False)
        self._f_type.setCurrentIndex(0)
        self._f_preview.setPixmap(QPixmap())
        self._f_preview.setStyleSheet("background: #333; border: 1px solid #555;")
        self._f_save_btn.setText("登録")
        self._f_delete_btn.setEnabled(False)
        self.library_grid.clear_selection()

    def _update_form_preview(self, path: str):
        pix = QPixmap(path)
        if not pix.isNull():
            pix = pix.scaled(
                LIB_THUMB_W, LIB_THUMB_H,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._f_preview.setPixmap(pix)
            self._f_preview.setStyleSheet("")
        else:
            self._f_preview.setPixmap(QPixmap())
            self._f_preview.setStyleSheet("background: #333; border: 1px solid #555;")

    def _browse_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "画像を選択", "",
            "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        if path:
            self._f_img.setText(path)

    def _save_card_form(self):
        name = self._f_name.text().strip()
        if not name:
            QMessageBox.warning(self, "エラー", "カード名を入力してください")
            return
        civs = [civ for civ, cb in self._f_civ_checks.items() if cb.isChecked()]
        card = LibraryCard(
            name=name,
            image_path=self._f_img.text().strip(),
            mana=self._f_mana.value(),
            civilizations=civs,
            card_type=self._f_type.currentText(),
            id=self._editing_card_id or str(uuid.uuid4()),
        )
        if self._editing_card_id:
            for i, c in enumerate(self._library.cards):
                if c.id == self._editing_card_id:
                    self._library.cards[i] = card
                    break
        else:
            self._library.add_card(card)

        self._library.save()
        self._editing_card_id = card.id
        self._f_save_btn.setText("更新")
        self._f_delete_btn.setEnabled(True)
        self._refresh_library()

    def _delete_card(self):
        if not self._editing_card_id:
            return
        card = next((c for c in self._library.cards if c.id == self._editing_card_id), None)
        if card is None:
            return
        if (QMessageBox.question(self, "確認", f"「{card.name}」を削除しますか？")
                != QMessageBox.StandardButton.Yes):
            return
        self._library.remove_card(self._editing_card_id)
        self._library.save()
        self._clear_card_form()
        self._refresh_library()

    # -----------------------------------------------------------------------
    # Library refresh
    # -----------------------------------------------------------------------

    def _refresh_library(self):
        self._lib_count_label.setText(f"{len(self._library.cards)} 枚")
        self.library_grid.load_library(self._library)

    # -----------------------------------------------------------------------
    # Drop handler: library → deck
    # -----------------------------------------------------------------------

    def _on_library_drop(self, card_id: str):
        if not self.current_deck:
            QMessageBox.warning(self, "エラー", "デッキを選択または新規作成してください")
            return
        lib_card = next((c for c in self._library.cards if c.id == card_id), None)
        if lib_card is None:
            return
        existing = next((c for c in self.current_deck.cards if c.id == card_id), None)
        if existing:
            if existing.count >= 4:
                QMessageBox.warning(self, "エラー", "同じカードは4枚までです")
                return
            if self.current_deck.total_count >= Deck.MAX_SIZE:
                QMessageBox.warning(self, "エラー", "40枚を超えます")
                return
            existing.count += 1
        else:
            if self.current_deck.total_count >= Deck.MAX_SIZE:
                QMessageBox.warning(self, "エラー", "40枚を超えます")
                return
            self.current_deck.cards.append(Card(
                name=lib_card.name,
                image_path=lib_card.image_path,
                mana=lib_card.mana,
                civilizations=lib_card.civilizations,
                card_type=lib_card.card_type,
                id=lib_card.id,
            ))
        self._refresh_deck_grid()

    # -----------------------------------------------------------------------
    # Deck editor
    # -----------------------------------------------------------------------

    def _refresh_deck_grid(self):
        self.deck_card_grid.refresh(self.current_deck)
        total = self.current_deck.total_count if self.current_deck else 0
        self.count_label.setText(f"{total} / 40")

    def _get_selected_deck_card(self) -> Card | None:
        if not self.current_deck:
            return None
        card_id = self.deck_card_grid.get_selected_card_id()
        if not card_id:
            return None
        return next((c for c in self.current_deck.cards if c.id == card_id), None)

    def _inc_card(self):
        card = self._get_selected_deck_card()
        if not card or not self.current_deck:
            return
        if card.count >= 4:
            QMessageBox.warning(self, "エラー", "同じカードは4枚までです")
            return
        if self.current_deck.total_count >= Deck.MAX_SIZE:
            QMessageBox.warning(self, "エラー", "40枚を超えます")
            return
        card.count += 1
        self._refresh_deck_grid()

    def _dec_card(self):
        card = self._get_selected_deck_card()
        if not card:
            return
        if card.count > 1:
            card.count -= 1
            self._refresh_deck_grid()
        else:
            self._remove_deck_card()

    def _remove_deck_card(self):
        card = self._get_selected_deck_card()
        if not card or not self.current_deck:
            return
        self.current_deck.cards = [c for c in self.current_deck.cards if c.id != card.id]
        self._refresh_deck_grid()

    def _save_deck(self):
        if not self.current_deck:
            return
        name = self.current_deck.name.strip()
        if not name:
            QMessageBox.warning(self, "エラー", "デッキ名を入力してください")
            return
        safe_name = _sanitize_filename(name)
        path = os.path.join(DECKS_DIR, f"{safe_name}.json")
        try:
            self.current_deck.save(path)
            self._load_deck_list()
            QMessageBox.information(self, "保存完了", f"「{name}」を保存しました")
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"保存失敗: {e}")
