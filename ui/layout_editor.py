from __future__ import annotations
from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from models.layout_config import GridPos, WindowDefinition, ZoneDefinition, save_game_config


class _GridCanvas(QWidget):
    """グリッドとゾーンブロックを描画するキャンバス。ドラッグでゾーンを移動できる。"""

    CELL_COLOR = QColor(40, 40, 60)
    ZONE_COLOR = QColor(60, 90, 140, 200)
    ZONE_HOVER_COLOR = QColor(80, 120, 180, 220)
    CONFLICT_COLOR = QColor(180, 40, 40, 200)
    GRID_LINE_COLOR = QColor(80, 80, 100)

    def __init__(self, win_def: WindowDefinition, zone_defs: list[ZoneDefinition], parent=None):
        super().__init__(parent)
        self.win_def = win_def
        # コピーを持つ（変更はローカルで管理）
        from dataclasses import replace
        self.zone_defs = [replace(z) for z in zone_defs]
        self._drag_zone_id: str | None = None
        self._drag_offset: QPoint = QPoint(0, 0)
        self._hover_col: int = -1
        self._hover_row: int = -1
        self._conflict: bool = False
        self.setMinimumSize(600, 400)
        self.setMouseTracking(True)

    @property
    def _cols(self) -> int:
        return self.win_def.grid_cols

    @property
    def _rows(self) -> int:
        return self.win_def.grid_rows

    def _cell_size(self) -> tuple[float, float]:
        return self.width() / self._cols, self.height() / self._rows

    def _cell_at(self, pos: QPoint) -> tuple[int, int]:
        cw, ch = self._cell_size()
        col = min(max(0, int(pos.x() / cw)), self._cols - 1)
        row = min(max(0, int(pos.y() / ch)), self._rows - 1)
        return col, row

    def _zone_rect(self, zd: ZoneDefinition) -> QRect:
        cw, ch = self._cell_size()
        return QRect(
            int(zd.grid_pos.col * cw), int(zd.grid_pos.row * ch),
            int(zd.grid_pos.col_span * cw), int(zd.grid_pos.row_span * ch),
        )

    def _occupied_cells(self, exclude_id: str) -> set[tuple[int, int]]:
        occupied = set()
        for zd in self.zone_defs:
            if zd.id == exclude_id:
                continue
            for c in range(zd.grid_pos.col, zd.grid_pos.col + zd.grid_pos.col_span):
                for r in range(zd.grid_pos.row, zd.grid_pos.row + zd.grid_pos.row_span):
                    occupied.add((c, r))
        return occupied

    def _check_conflict(self, zone_id: str, new_col: int, new_row: int) -> bool:
        zd = next(z for z in self.zone_defs if z.id == zone_id)
        occupied = self._occupied_cells(zone_id)
        for c in range(new_col, new_col + zd.grid_pos.col_span):
            for r in range(new_row, new_row + zd.grid_pos.row_span):
                if c >= self._cols or r >= self._rows:
                    return True
                if (c, r) in occupied:
                    return True
        return False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cw, ch = self._cell_size()

        # グリッド線
        painter.setPen(QPen(self.GRID_LINE_COLOR, 1))
        for c in range(self._cols + 1):
            x = int(c * cw)
            painter.drawLine(x, 0, x, self.height())
        for r in range(self._rows + 1):
            y = int(r * ch)
            painter.drawLine(0, y, self.width(), y)

        # ゾーンブロック
        for zd in self.zone_defs:
            rect = self._zone_rect(zd)
            is_dragging = (zd.id == self._drag_zone_id)
            color = self.ZONE_HOVER_COLOR if is_dragging else self.ZONE_COLOR
            if is_dragging and self._conflict:
                color = self.CONFLICT_COLOR
            painter.fillRect(rect, color)
            painter.setPen(QPen(QColor(180, 200, 255), 1))
            painter.drawRect(rect)
            painter.setPen(QColor(220, 230, 255))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, zd.name)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position().toPoint()
        for zd in reversed(self.zone_defs):
            if self._zone_rect(zd).contains(pos):
                self._drag_zone_id = zd.id
                rect = self._zone_rect(zd)
                self._drag_offset = pos - rect.topLeft()
                break

    def mouseMoveEvent(self, event):
        if self._drag_zone_id is None:
            return
        pos = event.position().toPoint()
        cw, ch = self._cell_size()
        snap_pos = pos - self._drag_offset
        snap_col = min(max(0, int(snap_pos.x() / cw)), self._cols - 1)
        snap_row = min(max(0, int(snap_pos.y() / ch)), self._rows - 1)
        self._hover_col, self._hover_row = snap_col, snap_row
        self._conflict = self._check_conflict(self._drag_zone_id, snap_col, snap_row)

        zd = next(z for z in self.zone_defs if z.id == self._drag_zone_id)
        zd.grid_pos = GridPos(
            col=snap_col, row=snap_row,
            col_span=zd.grid_pos.col_span,
            row_span=zd.grid_pos.row_span,
        )
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._drag_zone_id = None
        self._conflict = False
        self.update()


class LayoutEditorDialog(QDialog):
    def __init__(self, win_def: WindowDefinition, zone_defs: list[ZoneDefinition], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"レイアウト編集 — {win_def.title}")
        self.resize(700, 500)
        self._win_def = win_def
        self._all_zone_defs = zone_defs  # 全ゾーン（他ウィンドウ含む）

        layout = QVBoxLayout(self)

        self._canvas = _GridCanvas(win_def, [z for z in zone_defs if z.window_id == win_def.id])
        layout.addWidget(self._canvas, 1)

        hint = QLabel("ゾーンをドラッグしてグリッドセルに移動できます。赤色 = 衝突（移動不可）。")
        hint.setStyleSheet("color:#aaa;font-size:10px;")
        layout.addWidget(hint)

        btns = QHBoxLayout()
        btns.addStretch()
        save_btn = QPushButton("保存")
        save_btn.setFixedHeight(28)
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.setFixedHeight(28)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def _save(self):
        # キャンバスで編集したゾーン定義を全ゾーンリストに反映
        edited = {zd.id: zd for zd in self._canvas.zone_defs}
        merged = [edited.get(z.id, z) for z in self._all_zone_defs]

        # game.json に保存
        from models.layout_config import load_game_config
        win_defs, _ = load_game_config("data/game.json")
        save_game_config("data/game.json", win_defs, merged)

        self.accept()
