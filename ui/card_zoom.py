from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel

from models.game_state import GameCard
from .constants import CARD_W, CARD_H

_ZOOM = 3.0


class CardZoomDialog(QDialog):
    """Click anywhere to close."""

    def __init__(self, gc: GameCard, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        w = int(CARD_W * _ZOOM)
        h = int(CARD_H * _ZOOM)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel()
        label.setFixedSize(w, h)

        pix = QPixmap(gc.card.image_path)
        if pix.isNull():
            pix = QPixmap(CARD_W, CARD_H)
            pix.fill(QColor(70, 70, 70))
            p = QPainter(pix)
            p.setPen(QColor(220, 220, 220))
            p.setFont(QFont("Arial", 7))
            from PyQt6.QtCore import QRect
            p.drawText(
                QRect(2, 2, CARD_W - 4, CARD_H - 4),
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                gc.card.name,
            )
            p.end()

        label.setPixmap(
            pix.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
        )
        layout.addWidget(label)
        self.adjustSize()

    def mousePressEvent(self, event):
        self.accept()

    def keyPressEvent(self, event):
        self.accept()
