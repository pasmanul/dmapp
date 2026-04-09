import json
import os
import re

from PyQt6.QtCore import QMimeData, Qt, pyqtSignal
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
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from models.card import Card
from models.card_library import (
    CardLibrary, LibraryCard,
    CIVILIZATIONS, CIV_COLORS,
    CARD_TYPES, CARD_TYPE_COLORS,
)
from models.deck import Deck

DECKS_DIR = "data/decks"
LIBRARY_MIME = "application/x-dmapp-library-card"
LIB_THUMB_W, LIB_THUMB_H = 110, 154
DECK_THUMB_W, DECK_THUMB_H = 110, 154
EDIT_THUMB_W, EDIT_THUMB_H = 52, 73


def _sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', name).strip()


def _civ_label(civs: list[str]) -> str:
    return "".join(civs) if civs else ""


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
# Library card tile (drag source)
# ---------------------------------------------------------------------------

class _LibraryCardEntry(QFrame):
    def __init__(self, lib_card: LibraryCard, on_click=None, parent=None):
        super().__init__(parent)
        self.lib_card = lib_card
        self._on_click = on_click
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._set_normal_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        thumb = QLabel()
        thumb.setFixedSize(LIB_THUMB_W, LIB_THUMB_H)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        pix = QPixmap(lib_card.image_path)
        if not pix.isNull():
            pix = pix.scaled(LIB_THUMB_W, LIB_THUMB_H,
                             Qt.AspectRatioMode.IgnoreAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        else:
            pix = QPixmap(LIB_THUMB_W, LIB_THUMB_H)
            pix.fill(QColor(70, 70, 70))
        thumb.setPixmap(pix)
        layout.addWidget(thumb, 0, Qt.AlignmentFlag.AlignHCenter)

        name_lbl = QLabel(lib_card.name)
        name_lbl.setFont(QFont("Arial", 7))
        name_lbl.setStyleSheet("color: #ddd; border: none;")
        name_lbl.setWordWrap(True)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(name_lbl)

        if lib_card.civilizations:
            dots = _CivDots(lib_card.civilizations)
            layout.addWidget(dots, 0, Qt.AlignmentFlag.AlignHCenter)

        if lib_card.card_type:
            type_color = CARD_TYPE_COLORS.get(lib_card.card_type, "#aaa")
            type_lbl = QLabel(lib_card.card_type)
            type_lbl.setFont(QFont("Arial", 7, QFont.Weight.Bold))
            type_lbl.setStyleSheet(f"color: {type_color}; border: none;")
            type_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            type_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout.addWidget(type_lbl)

        mana_lbl = QLabel(f"M{lib_card.mana}")
        mana_lbl.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        mana_lbl.setStyleSheet("color: #44bbff; border: none;")
        mana_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mana_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(mana_lbl)

    def _set_normal_style(self):
        self.setStyleSheet(
            "QFrame { background: #2a2a2a; border: 1px solid #555; border-radius: 4px; }"
        )

    def set_selected(self, selected: bool):
        if selected:
            self.setStyleSheet(
                "QFrame { background: #3a3a5a; border: 2px solid #7799ff; border-radius: 4px; }"
            )
        else:
            self._set_normal_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._on_click:
            self._on_click(self.lib_card)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        drag = QDrag(self)
        mime = QMimeData()
        payload = json.dumps({
            "id": self.lib_card.id,
            "name": self.lib_card.name,
            "image_path": self.lib_card.image_path,
            "mana": self.lib_card.mana,
            "civilizations": self.lib_card.civilizations,
            "card_type": self.lib_card.card_type,
        })
        mime.setData(LIBRARY_MIME, payload.encode())
        drag.setMimeData(mime)
        pix = QPixmap(self.lib_card.image_path)
        if not pix.isNull():
            pix = pix.scaled(LIB_THUMB_W, LIB_THUMB_H,
                             Qt.AspectRatioMode.IgnoreAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        else:
            pix = QPixmap(LIB_THUMB_W, LIB_THUMB_H)
            pix.fill(QColor(70, 70, 70))
        drag.setPixmap(pix)
        drag.setHotSpot(event.pos())
        drag.exec(Qt.DropAction.CopyAction)


# ---------------------------------------------------------------------------
# Library card grid (scroll + filter)
# ---------------------------------------------------------------------------

class _CardLibraryGrid(QWidget):
    card_selected = pyqtSignal(object)  # LibraryCard
    _TILE_W = LIB_THUMB_W + 8 + 6  # thumb + padding + spacing

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

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

        self._all_cards: list[LibraryCard] = []
        self._entries: list[_LibraryCardEntry] = []
        self._selected_id: str | None = None
        self._current_filter: str = ""
        self._cols: int = 4

    def _calc_cols(self) -> int:
        return max(2, (self.width() - 12 - 10) // self._TILE_W)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        new_cols = self._calc_cols()
        if new_cols != self._cols:
            self._cols = new_cols
            self._apply_filter(self._current_filter)

    def refresh(self, cards: list[LibraryCard]):
        self._all_cards = list(cards)
        self._apply_filter(self._current_filter)

    def filter(self, text: str):
        self._current_filter = text
        self._apply_filter(text)

    def _apply_filter(self, text: str):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._entries.clear()

        filtered = (
            [c for c in self._all_cards if text.lower() in c.name.lower()]
            if text else self._all_cards
        )
        for i, card in enumerate(filtered):
            entry = _LibraryCardEntry(
                card,
                on_click=lambda c: self.card_selected.emit(c),
            )
            if card.id == self._selected_id:
                entry.set_selected(True)
            self._entries.append(entry)
            self._grid.addWidget(entry, i // self._cols, i % self._cols)

    def set_selected(self, card_id: str | None):
        self._selected_id = card_id
        for entry in self._entries:
            entry.set_selected(entry.lib_card.id == card_id)


# ---------------------------------------------------------------------------
# Deck card tile (drop target item)
# ---------------------------------------------------------------------------

class _DeckCardTile(QFrame):
    def __init__(self, card: Card, index: int, on_click=None, parent=None):
        super().__init__(parent)
        self.card = card
        self.index = index
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

        # Mana + Count
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
            self._on_click(self.index)
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# Deck card grid (thumbnail grid, drop target)
# ---------------------------------------------------------------------------

class _DeckCardGrid(QWidget):
    card_dropped = pyqtSignal(object)   # dict from MIME
    _TILE_W = DECK_THUMB_W + 8 + 6  # thumb + padding + spacing

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setStyleSheet("background: #1a1a1a;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

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
        self._container.setAcceptDrops(True)
        self._grid = QGridLayout(self._container)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._grid.setSpacing(6)
        self._grid.setContentsMargins(6, 6, 6, 6)

        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll)

        self._entries: list[_DeckCardTile] = []
        self._selected_index: int = -1
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

    # ---- drop events (on outer widget and container) ----

    def _accept_mime(self, event):
        if event.mimeData().hasFormat(LIBRARY_MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragEnterEvent(self, event):
        self._accept_mime(event)

    def dragMoveEvent(self, event):
        self._accept_mime(event)

    def dropEvent(self, event):
        if event.mimeData().hasFormat(LIBRARY_MIME):
            data = json.loads(event.mimeData().data(LIBRARY_MIME).data())
            self.card_dropped.emit(data)
            event.acceptProposedAction()
        else:
            event.ignore()

    # ---- grid management ----

    def refresh(self, deck: Deck | None):
        self._current_deck = deck
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._entries.clear()
        self._selected_index = -1

        if not deck:
            return
        for i, card in enumerate(deck.cards):
            tile = _DeckCardTile(card, i, on_click=self._on_tile_click)
            self._entries.append(tile)
            self._grid.addWidget(tile, i // self._cols, i % self._cols)

    def _on_tile_click(self, index: int):
        self._selected_index = index
        for e in self._entries:
            e.set_selected(e.index == index)

    def get_selected_index(self) -> int:
        return self._selected_index


# ---------------------------------------------------------------------------
# Main dialog
# ---------------------------------------------------------------------------

class DeckManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("デッキ管理")
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.setStyleSheet("""
            QDialog, QWidget, QSplitter { background-color: #1a1a2e; color: #ddd; }
            QLineEdit, QSpinBox, QComboBox { background: #2a2a4a; color: #ddd; border: 1px solid #555; }
            QPushButton { background: #3a3a6a; color: #ddd; border: 1px solid #555; border-radius: 3px; padding: 2px 8px; }
            QPushButton:hover { background: #4a4a8a; }
            QListWidget { background: #2a2a4a; color: #ddd; border: 1px solid #555; }
            QListWidget::item:selected { background: #4a4a8a; }
            QScrollArea { background: #1a1a2e; border: none; }
            QLabel { color: #ddd; }
            QCheckBox { color: #ddd; }
        """)
        self.resize(1150, 700)
        self.current_deck: Deck | None = None
        self.library = CardLibrary.get_instance()
        self._selected_lib_card: LibraryCard | None = None
        self._lib_img_path: str = ""
        self._civ_checks: dict[str, QCheckBox] = {}
        self._setup_ui()
        self._load_deck_list()
        self._refresh_library()

    # -----------------------------------------------------------------------
    # UI setup
    # -----------------------------------------------------------------------

    def _setup_ui(self):
        root = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_deck_panel())
        splitter.addWidget(self._build_library_panel())
        splitter.addWidget(self._build_editor_panel())
        splitter.setSizes([160, 470, 390])
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
        root = QVBoxLayout(w)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        root.addWidget(QLabel("カードライブラリ"))

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("カード名で検索...")
        self.search_edit.textChanged.connect(self._on_search)
        root.addWidget(self.search_edit)

        # 縦スプリッター: 上=グリッド, 下=編集フォーム
        vsplit = QSplitter(Qt.Orientation.Vertical)
        vsplit.setStyleSheet("QSplitter::handle:vertical { background: #3a3a5a; height: 4px; }")

        self.lib_grid = _CardLibraryGrid()
        self.lib_grid.card_selected.connect(self._on_lib_card_selected)
        vsplit.addWidget(self.lib_grid)

        # 編集フォームをスクロールエリアに収める
        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setStyleSheet("QScrollArea { background: #1a1a2e; border: none; }")
        form_scroll.viewport().setStyleSheet("background: #1a1a2e;")
        form_w = QWidget()
        form_w.setStyleSheet("background: #1a1a2e;")
        layout = QVBoxLayout(form_w)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(6)

        layout.addWidget(self._make_separator())
        layout.addWidget(QLabel("カード情報"))

        img_row = QHBoxLayout()
        self.lib_img_label = QLabel()
        self.lib_img_label.setFixedSize(EDIT_THUMB_W, EDIT_THUMB_H)
        self.lib_img_label.setStyleSheet("border: 1px solid #888;")
        self.lib_img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_row.addWidget(self.lib_img_label)
        img_right = QVBoxLayout()
        self.lib_img_path_label = QLabel("画像未選択")
        self.lib_img_path_label.setWordWrap(True)
        img_right.addWidget(self.lib_img_path_label)
        sel_btn = QPushButton("画像を選択…")
        sel_btn.clicked.connect(self._select_lib_image)
        img_right.addWidget(sel_btn)
        img_row.addLayout(img_right)
        layout.addLayout(img_row)

        cn_row = QHBoxLayout()
        cn_row.addWidget(QLabel("カード名:"))
        self.lib_name_edit = QLineEdit()
        cn_row.addWidget(self.lib_name_edit)
        layout.addLayout(cn_row)

        cm_row = QHBoxLayout()
        cm_row.addWidget(QLabel("マナ:"))
        self.lib_mana_spin = QSpinBox()
        self.lib_mana_spin.setRange(0, 99)
        cm_row.addWidget(self.lib_mana_spin)
        cm_row.addStretch()
        layout.addLayout(cm_row)

        ct_row = QHBoxLayout()
        ct_row.addWidget(QLabel("タイプ:"))
        self.lib_type_combo = QComboBox()
        self.lib_type_combo.addItem("（未設定）", "")
        for ct in CARD_TYPES:
            self.lib_type_combo.addItem(ct, ct)
        ct_row.addWidget(self.lib_type_combo)
        ct_row.addStretch()
        layout.addLayout(ct_row)

        layout.addLayout(self._build_civ_ui())

        btns = QHBoxLayout()
        add_btn = QPushButton("ライブラリに追加")
        add_btn.clicked.connect(self._add_lib_card)
        upd_btn = QPushButton("更新")
        upd_btn.clicked.connect(self._update_lib_card)
        del_btn = QPushButton("削除")
        del_btn.clicked.connect(self._delete_lib_card)
        btns.addWidget(add_btn)
        btns.addWidget(upd_btn)
        btns.addWidget(del_btn)
        layout.addLayout(btns)
        layout.addStretch()

        form_scroll.setWidget(form_w)
        vsplit.addWidget(form_scroll)
        vsplit.setSizes([420, 280])

        root.addWidget(vsplit, 1)
        return w

    def _build_civ_ui(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel("文明:"))
        for civ in CIVILIZATIONS:
            cb = QCheckBox(civ)
            cb.setStyleSheet(f"QCheckBox {{ color: {CIV_COLORS[civ]}; }}")
            cb.stateChanged.connect(self._on_civ_changed)
            self._civ_checks[civ] = cb
            row.addWidget(cb)
        colorless_cb = QCheckBox("無色")
        colorless_cb.setStyleSheet(f"QCheckBox {{ color: {CIV_COLORS['無色']}; }}")
        colorless_cb.stateChanged.connect(self._on_civ_changed)
        self._civ_checks["無色"] = colorless_cb
        row.addWidget(colorless_cb)
        self._rainbow_label = QLabel("レインボー")
        self._rainbow_label.setStyleSheet(
            "color: white; font-weight: bold; border: 1px solid #888; padding: 1px 4px; border-radius: 3px;"
        )
        self._rainbow_label.setVisible(False)
        row.addWidget(self._rainbow_label)
        row.addStretch()
        return row

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

        layout.addWidget(QLabel("デッキ内容  ← カードをドロップして追加"))

        self.deck_card_grid = _DeckCardGrid()
        self.deck_card_grid.card_dropped.connect(self._on_card_dropped)
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
    # Civilization helpers
    # -----------------------------------------------------------------------

    def _on_civ_changed(self):
        sender = self.sender()
        colorless_cb = self._civ_checks["無色"]
        color_cbs = [self._civ_checks[c] for c in CIVILIZATIONS]
        if sender is colorless_cb and colorless_cb.isChecked():
            for cb in color_cbs:
                cb.blockSignals(True)
                cb.setChecked(False)
                cb.blockSignals(False)
        elif sender in color_cbs and sender.isChecked():
            colorless_cb.blockSignals(True)
            colorless_cb.setChecked(False)
            colorless_cb.blockSignals(False)
        self._rainbow_label.setVisible(_is_rainbow(self._get_selected_civs()))

    def _get_selected_civs(self) -> list[str]:
        return [civ for civ in (CIVILIZATIONS + ["無色"]) if self._civ_checks[civ].isChecked()]

    def _set_civs(self, civs: list[str]):
        for civ, cb in self._civ_checks.items():
            cb.blockSignals(True)
            cb.setChecked(civ in civs)
            cb.blockSignals(False)
        self._rainbow_label.setVisible(_is_rainbow(civs))

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
            self._refresh_deck_grid()
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"読み込み失敗: {e}")

    def _new_deck(self):
        self.current_deck = Deck()
        self.deck_name_edit.setText(self.current_deck.name)
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

    # -----------------------------------------------------------------------
    # Library
    # -----------------------------------------------------------------------

    def _refresh_library(self):
        self.lib_grid.refresh(self.library.cards)

    def _on_search(self, text: str):
        self.lib_grid.filter(text)

    def _on_lib_card_selected(self, card: LibraryCard):
        self._selected_lib_card = card
        self.lib_grid.set_selected(card.id)
        self.lib_name_edit.setText(card.name)
        self.lib_mana_spin.setValue(card.mana)
        idx = self.lib_type_combo.findData(card.card_type)
        self.lib_type_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._set_civs(card.civilizations)
        self.lib_img_path_label.setText(os.path.basename(card.image_path))
        self._lib_img_path = card.image_path
        pix = QPixmap(card.image_path)
        if not pix.isNull():
            pix = pix.scaled(EDIT_THUMB_W, EDIT_THUMB_H,
                             Qt.AspectRatioMode.IgnoreAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
            self.lib_img_label.setPixmap(pix)
        else:
            self.lib_img_label.clear()

    def _select_lib_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "カード画像を選択", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif)"
        )
        if path:
            self._lib_img_path = path
            self.lib_img_path_label.setText(os.path.basename(path))
            pix = QPixmap(path)
            if not pix.isNull():
                pix = pix.scaled(EDIT_THUMB_W, EDIT_THUMB_H,
                                 Qt.AspectRatioMode.IgnoreAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
                self.lib_img_label.setPixmap(pix)
            else:
                self.lib_img_label.clear()

    def _add_lib_card(self):
        name = self.lib_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "エラー", "カード名を入力してください")
            return
        if not self._lib_img_path:
            QMessageBox.warning(self, "エラー", "画像を選択してください")
            return
        card = LibraryCard(
            name=name,
            image_path=self._lib_img_path,
            mana=self.lib_mana_spin.value(),
            civilizations=self._get_selected_civs(),
            card_type=self.lib_type_combo.currentData(),
        )
        self.library.add_card(card)
        self.library.save()
        self._refresh_library()

    def _update_lib_card(self):
        if not self._selected_lib_card:
            QMessageBox.warning(self, "エラー", "カードを選択してください")
            return
        self._selected_lib_card.name = self.lib_name_edit.text().strip()
        self._selected_lib_card.mana = self.lib_mana_spin.value()
        self._selected_lib_card.card_type = self.lib_type_combo.currentData()
        self._selected_lib_card.civilizations = self._get_selected_civs()
        if self._lib_img_path:
            self._selected_lib_card.image_path = self._lib_img_path
        self.library.save()
        self._refresh_library()

    def _delete_lib_card(self):
        if not self._selected_lib_card:
            QMessageBox.warning(self, "エラー", "カードを選択してください")
            return
        if (QMessageBox.question(
                self, "確認",
                f"「{self._selected_lib_card.name}」をライブラリから削除しますか？")
                != QMessageBox.StandardButton.Yes):
            return
        self.library.remove_card(self._selected_lib_card.id)
        self.library.save()
        self._selected_lib_card = None
        self.lib_grid.set_selected(None)
        self._refresh_library()

    # -----------------------------------------------------------------------
    # Deck editor
    # -----------------------------------------------------------------------

    def _refresh_deck_grid(self):
        self.deck_card_grid.refresh(self.current_deck)
        total = self.current_deck.total_count if self.current_deck else 0
        self.count_label.setText(f"{total} / 40")

    def _on_card_dropped(self, data: dict):
        if not self.current_deck:
            QMessageBox.warning(self, "エラー", "先にデッキを選択または新規作成してください")
            return
        for c in self.current_deck.cards:
            if c.id == data["id"]:
                if self.current_deck.total_count >= Deck.MAX_SIZE:
                    QMessageBox.warning(self, "エラー", "40枚を超えます")
                    return
                c.count += 1
                self._refresh_deck_grid()
                return
        if self.current_deck.total_count >= Deck.MAX_SIZE:
            QMessageBox.warning(self, "エラー", "40枚を超えます")
            return
        self.current_deck.cards.append(Card(
            name=data["name"],
            image_path=data["image_path"],
            mana=data["mana"],
            civilizations=data.get("civilizations", []),
            card_type=data.get("card_type", ""),
            count=1,
            id=data["id"],
        ))
        self._refresh_deck_grid()

    def _get_selected_deck_card(self) -> Card | None:
        if not self.current_deck:
            return None
        idx = self.deck_card_grid.get_selected_index()
        if idx < 0 or idx >= len(self.current_deck.cards):
            return None
        return self.current_deck.cards[idx]

    def _inc_card(self):
        card = self._get_selected_deck_card()
        if not card or not self.current_deck:
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
