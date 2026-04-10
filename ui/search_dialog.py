from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QFrame,
)

from models.game_state import GameCard, GameState, ZoneType
from .signals import game_signals

_THUMB_W = 110
_THUMB_H = 154
_COLS = 4

_DEST_OPTIONS = [
    ("手札", ZoneType.HAND),
    ("保留", ZoneType.TEMP),
    ("マナゾーン", ZoneType.MANA),
    ("墓地", ZoneType.GRAVEYARD),
]


class _CardTile(QFrame):
    _STYLE_NORMAL = (
        "QFrame{background:#2a2a2a;border:1px solid #555;border-radius:4px;}"
    )
    _STYLE_SELECTED = (
        "QFrame{background:#1a4a1a;border:2px solid #44ff44;border-radius:4px;}"
    )

    def __init__(self, gc: GameCard, on_changed, parent=None):
        super().__init__(parent)
        self.gc = gc
        self._on_changed = on_changed
        self._selected = False
        self._build()
        self.setStyleSheet(self._STYLE_NORMAL)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        img = QLabel()
        img.setFixedSize(_THUMB_W, _THUMB_H)
        img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        pix = QPixmap(self.gc.card.image_path)
        if not pix.isNull():
            pix = pix.scaled(
                _THUMB_W, _THUMB_H,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            pix = QPixmap(_THUMB_W, _THUMB_H)
            pix.fill(QColor(70, 70, 70))
        img.setPixmap(pix)
        layout.addWidget(img, 0, Qt.AlignmentFlag.AlignHCenter)

        name_lbl = QLabel(self.gc.card.name)
        name_lbl.setFont(QFont("Arial", 8))
        name_lbl.setStyleSheet("color:#ddd;border:none;")
        name_lbl.setWordWrap(True)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(name_lbl)

        civs = "・".join(self.gc.card.civilizations) if self.gc.card.civilizations else "無色"
        info_lbl = QLabel(f"M{self.gc.card.mana}  {civs}")
        info_lbl.setFont(QFont("Arial", 8))
        info_lbl.setStyleSheet("color:#aaa;border:none;")
        info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(info_lbl)

    def is_selected(self) -> bool:
        return self._selected

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._selected = not self._selected
            self.setStyleSheet(
                self._STYLE_SELECTED if self._selected else self._STYLE_NORMAL
            )
            self._on_changed()


class SearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("山札をサーチ")
        self.resize(560, 680)
        self.setStyleSheet("background:#1a1a2e;color:#ddd;")
        self._tiles: list[_CardTile] = []
        self._build_ui()
        self._populate()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(8, 8, 8, 8)

        # ── フィルタバー ─────────────────────────────────────────
        filter_row = QHBoxLayout()

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("カード名で絞り込み...")
        self._name_edit.setStyleSheet(
            "background:#2a2a3a;color:#ddd;border:1px solid #555;padding:2px 4px;"
        )
        self._name_edit.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self._name_edit, 2)

        self._civ_combo = QComboBox()
        self._civ_combo.setStyleSheet(
            "background:#2a2a3a;color:#ddd;border:1px solid #555;"
        )
        self._civ_combo.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self._civ_combo, 1)

        self._type_combo = QComboBox()
        self._type_combo.setStyleSheet(
            "background:#2a2a3a;color:#ddd;border:1px solid #555;"
        )
        self._type_combo.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self._type_combo, 1)

        root.addLayout(filter_row)

        # ── カードグリッド ───────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea{background:#1a1a1a;}")

        self._grid_widget = QWidget()
        self._grid_widget.setStyleSheet("background:#1a1a1a;")
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._grid.setSpacing(6)
        self._grid.setContentsMargins(6, 6, 6, 6)

        self._scroll.setWidget(self._grid_widget)
        root.addWidget(self._scroll, 1)

        # ── ボトムバー ───────────────────────────────────────────
        bottom = QHBoxLayout()

        self._count_lbl = QLabel("0枚選択中")
        self._count_lbl.setStyleSheet("color:#aaa;font-size:11px;")
        bottom.addWidget(self._count_lbl, 1)

        dest_lbl = QLabel("移動先:")
        dest_lbl.setStyleSheet("color:#ddd;")
        bottom.addWidget(dest_lbl)

        self._dest_combo = QComboBox()
        self._dest_combo.setStyleSheet(
            "background:#2a2a3a;color:#ddd;border:1px solid #555;"
        )
        for label, _ in _DEST_OPTIONS:
            self._dest_combo.addItem(label)
        bottom.addWidget(self._dest_combo)

        self._confirm_btn = QPushButton("確定")
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.setStyleSheet(
            "QPushButton{background:#2a5a2a;color:#eee;border:1px solid #555;"
            "border-radius:3px;padding:4px 16px;}"
            "QPushButton:disabled{background:#333;color:#777;}"
            "QPushButton:hover{background:#3a7a3a;}"
        )
        self._confirm_btn.clicked.connect(self._confirm)
        bottom.addWidget(self._confirm_btn)

        cancel_btn = QPushButton("閉じる")
        cancel_btn.setStyleSheet(
            "QPushButton{background:#3a3a3a;color:#eee;border:1px solid #555;"
            "border-radius:3px;padding:4px 16px;}"
            "QPushButton:hover{background:#4a4a4a;}"
        )
        cancel_btn.clicked.connect(self.reject)
        bottom.addWidget(cancel_btn)

        root.addLayout(bottom)

    def _populate(self):
        gs = GameState.get_instance()
        deck_cards = gs.zones[ZoneType.DECK].cards

        civs = sorted({civ for gc in deck_cards for civ in gc.card.civilizations})
        types = sorted({gc.card.card_type for gc in deck_cards if gc.card.card_type})

        self._civ_combo.blockSignals(True)
        self._civ_combo.addItem("すべての文明")
        for c in civs:
            self._civ_combo.addItem(c)
        self._civ_combo.blockSignals(False)

        self._type_combo.blockSignals(True)
        self._type_combo.addItem("すべてのタイプ")
        for t in types:
            self._type_combo.addItem(t)
        self._type_combo.blockSignals(False)

        for gc in deck_cards:
            tile = _CardTile(gc, self._update_count, self._grid_widget)
            self._tiles.append(tile)

        self._apply_filter()

    def _apply_filter(self):
        # グリッドをクリア（タイルは破棄しない）
        while self._grid.count():
            self._grid.takeAt(0)

        name_q = self._name_edit.text().lower()
        civ_q = self._civ_combo.currentText()
        type_q = self._type_combo.currentText()

        col = row = 0
        for tile in self._tiles:
            c = tile.gc.card
            if name_q and name_q not in c.name.lower():
                tile.hide()
                continue
            if civ_q != "すべての文明" and civ_q not in c.civilizations:
                tile.hide()
                continue
            if type_q != "すべてのタイプ" and c.card_type != type_q:
                tile.hide()
                continue
            tile.show()
            self._grid.addWidget(tile, row, col)
            col += 1
            if col >= _COLS:
                col = 0
                row += 1

        self._update_count()

    def _update_count(self):
        n = sum(1 for t in self._tiles if t.is_selected())
        self._count_lbl.setText(f"{n}枚選択中")
        self._confirm_btn.setEnabled(n > 0)

    def _confirm(self):
        selected = [t for t in self._tiles if t.is_selected()]
        if not selected:
            return
        selected_ids = [t.gc.card.id for t in selected]
        dest_label, dest_zone = _DEST_OPTIONS[self._dest_combo.currentIndex()]
        if GameState.get_instance().search_deck(selected_ids, dest_zone):
            names = "、".join(f"「{t.gc.card.name}」" for t in selected)
            game_signals.action_logged.emit(f"サーチ → {dest_label}: {names}")
            game_signals.zones_updated.emit()
        self.accept()
