import json

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QDrag, QFont, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .constants import CARD_H, CARD_W, MIME_TYPE

THUMB_W = 110
THUMB_H = 154


class _DeckCardEntry(QFrame):
    """Single draggable card tile in the deck list (image + name + count)."""

    def __init__(self, card, parent=None):
        super().__init__(parent)
        self.card = card
        self.setCursor(Qt.CursorShape.OpenHandCursor)
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

        # Count
        count_lbl = QLabel(f"×{card.count}")
        count_lbl.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        count_lbl.setStyleSheet("color: #ffdd44; border: none;")
        count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        count_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(count_lbl)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        drag = QDrag(self)
        from PyQt6.QtCore import QMimeData
        mime = QMimeData()
        payload = json.dumps({
            "source_zone": "deck_list",
            "card_id": self.card.id,
            "card_name": self.card.name,
            "image_path": self.card.image_path,
        })
        mime.setData(MIME_TYPE, payload.encode())
        drag.setMimeData(mime)

        pix = QPixmap(self.card.image_path)
        if not pix.isNull():
            pix = pix.scaled(CARD_W, CARD_H,
                             Qt.AspectRatioMode.IgnoreAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        else:
            pix = QPixmap(CARD_W, CARD_H)
            pix.fill(QColor(70, 70, 70))
        drag.setPixmap(pix)
        drag.setHotSpot(event.pos())
        drag.exec(Qt.DropAction.CopyAction)


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
