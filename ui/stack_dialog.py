from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from models.game_state import GameCard
from .constants import CARD_H, CARD_W, CARD_BACK_PATH


def _card_pixmap(gc: GameCard) -> QPixmap:
    if gc.face_down:
        pix = QPixmap(CARD_BACK_PATH)
        if pix.isNull():
            pix = QPixmap(CARD_W, CARD_H)
            pix.fill(QColor(20, 20, 140))
    else:
        pix = QPixmap(gc.card.image_path)
        if pix.isNull():
            pix = QPixmap(CARD_W, CARD_H)
            pix.fill(QColor(70, 70, 70))
    return pix.scaled(CARD_W, CARD_H,
                      Qt.AspectRatioMode.IgnoreAspectRatio,
                      Qt.TransformationMode.SmoothTransformation)


class StackDialog(QDialog):
    """Shows all cards in an evolution stack, top to bottom."""

    def __init__(self, gc: GameCard, parent=None):
        super().__init__(parent)
        self.setWindowTitle("進化スタック")
        self.setStyleSheet("background: #1a1a2e; color: #ddd;")
        self.resize(max(120 * (len(gc.under_cards) + 1) + 40, 300), 260)

        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { background: #1a1a2e; border: none; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        row = QHBoxLayout(container)
        row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        row.setSpacing(10)
        row.setContentsMargins(10, 10, 10, 10)

        # Top card first, then under_cards in order
        all_cards = [gc] + gc.under_cards
        for i, card in enumerate(all_cards):
            col = QVBoxLayout()
            col.setSpacing(4)
            col.setAlignment(Qt.AlignmentFlag.AlignHCenter)

            label_text = "（一番上）" if i == 0 else f"下 {i}"
            lbl = QLabel(label_text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #aaa; font-size: 9px;")
            col.addWidget(lbl)

            img = QLabel()
            img.setFixedSize(CARD_W, CARD_H)
            img.setPixmap(_card_pixmap(card))
            img.setToolTip(card.card.name)
            col.addWidget(img)

            name_lbl = QLabel(card.card.name)
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_lbl.setWordWrap(True)
            name_lbl.setFixedWidth(CARD_W)
            name_lbl.setStyleSheet("color: #ddd; font-size: 8px;")
            col.addWidget(name_lbl)

            wrapper = QWidget()
            wrapper.setLayout(col)
            row.addWidget(wrapper)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet(
            "QPushButton { background: #3a3a6a; color: #eee; border: 1px solid #555;"
            " border-radius: 3px; padding: 4px 12px; }"
        )
        layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignRight)
