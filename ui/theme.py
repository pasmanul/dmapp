"""Centralized visual theme for dmapp — 5-Civilization color system."""

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect

# ── Window ────────────────────────────────────────────────────────────
WIN_BG = "#08091a"
FONT_JP = "Yu Gothic UI"

# ── Zone colors ───────────────────────────────────────────────────────
# Each zone maps to a Duel Masters civilization:
#   battle    -> Fire     (crimson)
#   mana      -> Nature   (emerald)
#   shield    -> Light    (amber)
#   graveyard -> Darkness (violet)
#   deck      -> Water    (cyan-blue)
#   hand      -> multi    (teal)
#   temp      -> neutral  (slate)
#
# Tuple: (bg_top_hex, bg_bottom_hex, border_hex, title_fg_hex, title_bar_hex)
_ZONE_PALETTE: dict[str, tuple] = {
    "battle":    ("#1e0a0b", "#0d0506", "#c82030", "#ff8090", "#2c0a10"),
    "mana":      ("#081c0c", "#040e06", "#28a848", "#66dd88", "#082214"),
    "shield":    ("#1c1608", "#0e0b04", "#c89420", "#ffdd66", "#221c06"),
    "graveyard": ("#120818", "#09040e", "#8820b8", "#cc66ee", "#1a0a28"),
    "deck":      ("#061420", "#03080e", "#1880c8", "#44aaff", "#041020"),
    "hand":      ("#061a1a", "#030e0e", "#20a8b0", "#55ddee", "#041818"),
    "temp":      ("#0c1018", "#080c12", "#505c78", "#8899bb", "#0a0e18"),
}


def zone_colors(zone_value: str) -> dict:
    """Return QColor dict for a zone. zone_value is ZoneType.value (str)."""
    t = _ZONE_PALETTE.get(zone_value, _ZONE_PALETTE["temp"])
    return {
        "bg_top":    QColor(t[0]),
        "bg_bottom": QColor(t[1]),
        "border":    QColor(t[2]),
        "title_fg":  QColor(t[3]),
        "title_bar": QColor(t[4]),
    }


# ── Button styles ─────────────────────────────────────────────────────
_BTN_TEMPLATE = (
    "QPushButton {{"
    "  background: {bg};"
    "  color: {fg};"
    "  border: 1px solid {border};"
    "  border-radius: 6px;"
    "  padding: 0 14px;"
    "  font-family: 'Yu Gothic UI';"
    "  font-size: 11px;"
    "}}"
    "QPushButton:hover {{"
    "  background: {hover};"
    "  border-color: {hover_border};"
    "}}"
    "QPushButton:pressed {{"
    "  background: {pressed};"
    "}}"
)


def btn_style(
    bg="#16203a",
    fg="#b8ccee",
    border="#304060",
    hover="#223060",
    hover_border="#4a6090",
    pressed="#0e1828",
) -> str:
    return _BTN_TEMPLATE.format(
        bg=bg, fg=fg, border=border,
        hover=hover, hover_border=hover_border, pressed=pressed,
    )


# Preset button variants
def btn_draw() -> str:
    return btn_style(bg="#0d2a14", fg="#88eea8", border="#28804a",
                     hover="#124020", hover_border="#44aa66", pressed="#081810")

def btn_shuffle() -> str:
    return btn_style(bg="#1a1208", fg="#eecc66", border="#806020",
                     hover="#2a1e0c", hover_border="#aa8030", pressed="#100c04")

def btn_reset() -> str:
    return btn_style(bg="#1a0c0c", fg="#eea0a0", border="#803030",
                     hover="#280e0e", hover_border="#aa4040", pressed="#100808")

def btn_dice() -> str:
    return btn_style(bg="#0e1440", fg="#a0b8ff", border="#283880",
                     hover="#141c60", hover_border="#3a50aa", pressed="#080e28")

def btn_sort() -> str:
    return btn_style(bg="#141428", fg="#aaaaee", border="#383880",
                     hover="#1e1e40", hover_border="#5050a0", pressed="#0c0c1c")

def btn_load() -> str:
    return btn_style(bg="#0c1828", fg="#88aade", border="#284060",
                     hover="#102238", hover_border="#3a5888", pressed="#080e1c")


# ── Drop shadow ───────────────────────────────────────────────────────
def zone_shadow(blur: int = 18, offset_y: int = 4, alpha: int = 160) -> QGraphicsDropShadowEffect:
    """Return a drop shadow effect for zone widgets."""
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur)
    s.setOffset(0, offset_y)
    s.setColor(QColor(0, 0, 0, alpha))
    return s


# ── Splitter stylesheet ────────────────────────────────────────────────
SPLITTER_STYLE = (
    "QSplitter::handle:vertical {{ background: #1e2240; height: 3px; }}"
    "QSplitter::handle:horizontal {{ background: #1e2240; width: 3px; }}"
)

# ── MenuBar stylesheet ─────────────────────────────────────────────────
MENUBAR_STYLE = (
    "QMenuBar {{"
    "  background: #08091a;"
    "  color: #99aabb;"
    "  border-bottom: 1px solid #1e2240;"
    "  font-family: 'Yu Gothic UI';"
    "  font-size: 11px;"
    "}}"
    "QMenuBar::item:selected {{"
    "  background: #1e2848;"
    "  color: #cce0ff;"
    "}}"
    "QMenu {{"
    "  background: #0e1228;"
    "  color: #aabbd0;"
    "  border: 1px solid #2a3550;"
    "  font-family: 'Yu Gothic UI';"
    "  font-size: 11px;"
    "}}"
    "QMenu::item:selected {{"
    "  background: #1e2848;"
    "  color: #cce0ff;"
    "}}"
    "QMenu::separator {{"
    "  background: #2a3550;"
    "  height: 1px;"
    "}}"
)
