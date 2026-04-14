"""Card pixmap utilities shared by ZoneWidget."""
from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
    QTransform,
)

from .constants import CARD_BACK_PATH, CARD_H, CARD_W

_card_back_cache: dict = {}
_card_back_tapped_cache: dict = {}

_ZONE_NAMES: dict[str, str] = {
    "battle":    "バトルゾーン",
    "shield":    "シールドゾーン",
    "deck":      "山札",
    "graveyard": "墓地",
    "mana":      "マナゾーン",
    "hand":      "手札",
    "temp":      "保留",
}


def update_zone_names(zone_defs) -> None:
    """ZoneDefinition リストから _ZONE_NAMES を再構築する。main.py 起動時に呼ぶ。"""
    _ZONE_NAMES.clear()
    for zd in zone_defs:
        _ZONE_NAMES[zd.id] = zd.name

_MARKER_COLORS = {
    "red":    QColor(220, 60,  60),
    "blue":   QColor(60,  130, 220),
    "yellow": QColor(220, 200, 0),
    "green":  QColor(60,  190, 60),
    "purple": QColor(170, 70,  210),
}
_MARKER_LABELS = {
    "red":    "赤",
    "blue":   "青",
    "yellow": "黄",
    "green":  "緑",
    "purple": "紫",
}


def _make_card_back(path: str = CARD_BACK_PATH) -> QPixmap:
    if path in _card_back_cache:
        return _card_back_cache[path]
    pix = QPixmap(path)
    if not pix.isNull():
        result = pix.scaled(CARD_W, CARD_H, Qt.AspectRatioMode.IgnoreAspectRatio,
                            Qt.TransformationMode.SmoothTransformation)
        _card_back_cache[path] = result
        return result
    # fallback
    pix = QPixmap(CARD_W, CARD_H)
    pix.fill(QColor(20, 20, 140))
    p = QPainter(pix)
    p.setPen(QPen(QColor(180, 180, 255), 2))
    p.drawRect(3, 3, CARD_W - 7, CARD_H - 7)
    p.setFont(QFont("Arial", 8, QFont.Weight.Bold))
    p.setPen(QColor(255, 255, 255))
    p.drawText(QRect(0, 0, CARD_W, CARD_H), Qt.AlignmentFlag.AlignCenter, "DM")
    p.end()
    _card_back_cache[path] = pix
    return pix


def _make_card_back_tapped(path: str = CARD_BACK_PATH) -> QPixmap:
    if path in _card_back_tapped_cache:
        return _card_back_tapped_cache[path]
    back = _make_card_back(path)
    t = QTransform().rotate(90)
    rot = back.transformed(t, Qt.TransformationMode.SmoothTransformation)
    result = rot.scaled(CARD_H, CARD_W, Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)
    _card_back_tapped_cache[path] = result
    return result


def _make_fallback(name: str) -> QPixmap:
    pix = QPixmap(CARD_W, CARD_H)
    pix.fill(QColor(70, 70, 70))
    p = QPainter(pix)
    p.setPen(QColor(220, 220, 220))
    p.setFont(QFont("Arial", 7))
    p.drawText(
        QRect(2, 2, CARD_W - 4, CARD_H - 4),
        Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
        name,
    )
    p.end()
    return pix


def _make_marker_icon(key: str) -> QIcon:
    pix = QPixmap(14, 14)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(_MARKER_COLORS[key]))
    p.setPen(QPen(QColor(200, 200, 200), 1))
    p.drawEllipse(1, 1, 12, 12)
    p.end()
    return QIcon(pix)
