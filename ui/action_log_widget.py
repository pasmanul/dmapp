from collections import deque
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget

from .signals import game_signals

_MAX_ENTRIES = 200


class ActionLogWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: deque[str] = deque(maxlen=_MAX_ENTRIES)
        self._build_ui()
        game_signals.action_logged.connect(self._add_entry)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        title = QLabel("アクションログ")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFixedHeight(20)
        title.setStyleSheet("color:#aaa;font-size:10px;font-weight:bold;background:transparent;")
        layout.addWidget(title)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont("Consolas", 9))
        self._text.setStyleSheet(
            "QTextEdit{"
            "  background:#0e0e1a;"
            "  color:#bbb;"
            "  border:1px solid #3a3a5a;"
            "  font-size:10px;"
            "}"
        )
        layout.addWidget(self._text)

    def _add_entry(self, text: str):
        ts = datetime.now().strftime("%H:%M")
        self._entries.appendleft(f"[{ts}] {text}")
        self._text.setPlainText("\n".join(self._entries))
