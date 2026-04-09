from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

THUMB_W = 110
THUMB_H = 154


THUMB_W = 110
THUMB_H = 154


class _DeckCardEntry(QFrame):
    """Card tile in the deck list (image + name + count)."""

    def __init__(self, card, parent=None):
        super().__init__(parent)
        self.card = card
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("QFrame { background: #2a2a2a; border: 1px solid #555; border-radius: 4px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # Thumbnail
        thumb = QLabel()
        thumb.setFixedSize(THUMB_W, THUMB_H)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        pix = QPixmap(card.image_path)
        if not pix.isNull():
            pix = pix.scaled(THUMB_W, THUMB_H,
                             Qt.AspectRatioMode.IgnoreAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        else:
            pix = QPixmap(THUMB_W, THUMB_H)
            pix.fill(QColor(70, 70, 70))
        thumb.setPixmap(pix)
        layout.addWidget(thumb, 0, Qt.AlignmentFlag.AlignHCenter)

        # Name
        name_lbl = QLabel(card.name)
        name_lbl.setFont(QFont("Arial", 8))
        name_lbl.setStyleSheet("color: #ddd; border: none;")
        name_lbl.setWordWrap(True)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(name_lbl)

        # Mana + Count row
        info_row_widget = QWidget()
        info_row_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        info_row_widget.setStyleSheet("background: transparent;")
        info_row = QHBoxLayout(info_row_widget)
        info_row.setContentsMargins(0, 0, 0, 0)
        info_row.setSpacing(4)

        mana_lbl = QLabel(f"M{card.mana}")
        mana_lbl.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        mana_lbl.setStyleSheet("color: #44bbff; border: none;")
        mana_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mana_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        info_row.addWidget(mana_lbl)

        count_lbl = QLabel(f"×{card.count}")
        count_lbl.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        count_lbl.setStyleSheet("color: #ffdd44; border: none;")
        count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        count_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        info_row.addWidget(count_lbl)

        layout.addWidget(info_row_widget)


class DeckListWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { background: #1a1a1a; }")

        self._container = QWidget()
        self._container.setStyleSheet("background: #1a1a1a;")
        self._grid = QGridLayout(self._container)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._grid.setSpacing(6)
        self._grid.setContentsMargins(6, 6, 6, 6)

        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll)

    def set_deck(self, deck):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if deck:
            for i, card in enumerate(deck.cards):
                entry = _DeckCardEntry(card)
                self._grid.addWidget(entry, i // 4, i % 4)
