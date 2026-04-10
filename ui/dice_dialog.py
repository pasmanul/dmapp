import random

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .signals import game_signals

_DICE = [4, 6, 8, 10, 12, 20]

# d6 のドット配置（ウィジェット座標 0–100 の相対値）
_D6_DOTS = {
    1: [(50, 50)],
    2: [(30, 30), (70, 70)],
    3: [(30, 30), (50, 50), (70, 70)],
    4: [(30, 30), (70, 30), (30, 70), (70, 70)],
    5: [(30, 30), (70, 30), (50, 50), (30, 70), (70, 70)],
    6: [(30, 25), (70, 25), (30, 50), (70, 50), (30, 75), (70, 75)],
}


class _DiceFaceWidget(QWidget):
    """ダイスの面をカスタム描画するウィジェット。"""

    SIZE = 120

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sides = 6
        self.value = 0  # 0 = 未投擲
        self._rolling = False
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._anim_tick)
        self._anim_ticks = 0
        self._anim_final = 0
        self.setFixedSize(self.SIZE, self.SIZE)

    def roll_animation(self, final: int):
        self._anim_final = final
        self._anim_ticks = 10
        self._rolling = True
        self._anim_timer.start(40)

    def _anim_tick(self):
        self._anim_ticks -= 1
        if self._anim_ticks <= 0:
            self._anim_timer.stop()
            self.value = self._anim_final
            self._rolling = False
        else:
            self.value = random.randint(1, self.sides)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景の角丸正方形（サイコロの面）
        margin = 8
        size = self.SIZE - margin * 2
        face_color = QColor(35, 35, 60) if not self._rolling else QColor(50, 50, 80)
        border_color = QColor(100, 120, 220) if not self._rolling else QColor(160, 180, 255)
        p.setBrush(QBrush(face_color))
        p.setPen(QPen(border_color, 2))
        p.drawRoundedRect(margin, margin, size, size, 14, 14)

        if self.value == 0:
            p.setPen(QColor(80, 80, 110))
            p.setFont(QFont("Arial", 16))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "?")
            return

        if self.sides == 6 and self.value in _D6_DOTS:
            # d6: ドットで描画
            p.setBrush(QBrush(QColor(255, 240, 80)))
            p.setPen(Qt.PenStyle.NoPen)
            r = 7
            for rx, ry in _D6_DOTS[self.value]:
                cx = margin + int(rx / 100 * size)
                cy = margin + int(ry / 100 * size)
                p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
        else:
            # その他: 数字で描画
            font_size = 38 if self.value < 10 else 30
            p.setPen(QColor(255, 240, 80))
            p.setFont(QFont("Arial", font_size, QFont.Weight.Bold))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, str(self.value))

        # ダイス種別を右下に小さく表示
        p.setPen(QColor(120, 130, 170))
        p.setFont(QFont("Arial", 9))
        p.drawText(
            0, self.SIZE - margin - 4, self.SIZE - margin - 2, margin + 2,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            f"d{self.sides}",
        )


class DiceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool)
        self.setWindowTitle("ダイス")
        self.setFixedWidth(260)
        self.setStyleSheet("background:#1a1a2e; color:#ddd;")
        self._history: list[str] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # ── ダイス種別ボタン ─────────────────────────────────────
        die_row = QHBoxLayout()
        die_row.setSpacing(4)
        self._die_btns: dict[int, QPushButton] = {}
        btn_style = (
            "QPushButton{background:#2a2a4a;color:#bbb;border:1px solid #555;"
            "border-radius:3px;padding:3px 0;font-size:11px;}"
            "QPushButton:checked{background:#3a3a8a;color:#fff;border:1px solid #88f;}"
            "QPushButton:hover{background:#3a3a6a;}"
        )
        for d in _DICE:
            btn = QPushButton(f"d{d}")
            btn.setCheckable(True)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(lambda _checked, sides=d: self._select_die(sides))
            die_row.addWidget(btn)
            self._die_btns[d] = btn
        layout.addLayout(die_row)

        # ── ダイス面 ──────────────────────────────────────────────
        self._face = _DiceFaceWidget()
        layout.addWidget(self._face, 0, Qt.AlignmentFlag.AlignHCenter)

        # ── 振るボタン ────────────────────────────────────────────
        self._roll_btn = QPushButton("振る！")
        self._roll_btn.setFixedHeight(38)
        self._roll_btn.setStyleSheet(
            "QPushButton{background:#3a3a8a;color:#fff;border:1px solid #66f;"
            "border-radius:4px;font-size:15px;font-weight:bold;}"
            "QPushButton:hover{background:#5a5aaa;}"
            "QPushButton:pressed{background:#2a2a6a;}"
        )
        self._roll_btn.clicked.connect(self._roll)
        layout.addWidget(self._roll_btn)

        # ── 履歴 ──────────────────────────────────────────────────
        self._history_lbl = QLabel("履歴: -")
        self._history_lbl.setStyleSheet("color:#777;font-size:10px;")
        self._history_lbl.setWordWrap(True)
        layout.addWidget(self._history_lbl)

        self._select_die(6)

    def _select_die(self, sides: int):
        self._face.sides = sides
        self._face.value = 0
        self._face.update()
        for d, btn in self._die_btns.items():
            btn.setChecked(d == sides)

    def _roll(self):
        sides = self._face.sides
        result = random.randint(1, sides)
        self._face.roll_animation(result)

        entry = f"d{sides}={result}"
        self._history.insert(0, entry)
        if len(self._history) > 10:
            self._history.pop()
        self._history_lbl.setText("履歴: " + "  ".join(self._history))

        game_signals.action_logged.emit(f"d{sides} → {result}")

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Space):
            self._roll()
        else:
            super().keyPressEvent(event)
