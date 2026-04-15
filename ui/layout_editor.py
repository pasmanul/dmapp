from __future__ import annotations
from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from models.layout_config import GridPos, WindowDefinition, ZoneDefinition, save_game_config

_HANDLE_PX = 10  # リサイズハンドルの感知幅（ピクセル）


class _GridCanvas(QWidget):
    """グリッドとゾーンブロックを描画するキャンバス。ドラッグでゾーンを移動・リサイズできる。"""

    CELL_COLOR = QColor(40, 40, 60)
    ZONE_COLOR = QColor(60, 90, 140, 200)
    ZONE_HOVER_COLOR = QColor(80, 120, 180, 220)
    CONFLICT_COLOR = QColor(180, 40, 40, 200)
    GRID_LINE_COLOR = QColor(80, 80, 100)
    HANDLE_COLOR = QColor(160, 200, 255, 180)

    def __init__(self, win_def: WindowDefinition, zone_defs: list[ZoneDefinition], parent=None):
        super().__init__(parent)
        self.win_def = win_def
        from dataclasses import replace
        self.zone_defs = [replace(z) for z in zone_defs]

        # ドラッグ状態
        self._drag_zone_id: str | None = None
        self._drag_offset: QPoint = QPoint(0, 0)

        # リサイズ状態: "right" | "bottom" | "corner" | None
        self._resize_zone_id: str | None = None
        self._resize_edge: str | None = None

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

    def _check_conflict(self, zone_id: str, col: int, row: int, col_span: int, row_span: int) -> bool:
        occupied = self._occupied_cells(zone_id)
        for c in range(col, col + col_span):
            for r in range(row, row + row_span):
                if c >= self._cols or r >= self._rows or c < 0 or r < 0:
                    return True
                if (c, r) in occupied:
                    return True
        return False

    def _hit_edge(self, pos: QPoint, rect: QRect) -> str | None:
        """pos がゾーン rect のどのリサイズエッジにあるか ("right"|"bottom"|"corner"|None)"""
        near_right = abs(pos.x() - rect.right()) <= _HANDLE_PX and rect.top() <= pos.y() <= rect.bottom()
        near_bottom = abs(pos.y() - rect.bottom()) <= _HANDLE_PX and rect.left() <= pos.x() <= rect.right()
        if near_right and near_bottom:
            return "corner"
        if near_right:
            return "right"
        if near_bottom:
            return "bottom"
        return None

    def _update_cursor(self, pos: QPoint):
        for zd in reversed(self.zone_defs):
            rect = self._zone_rect(zd)
            edge = self._hit_edge(pos, rect)
            if edge == "corner":
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                return
            if edge == "right":
                self.setCursor(Qt.CursorShape.SizeHorCursor)
                return
            if edge == "bottom":
                self.setCursor(Qt.CursorShape.SizeVerCursor)
                return
            if rect.contains(pos):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                return
        self.setCursor(Qt.CursorShape.ArrowCursor)

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
        active_id = self._drag_zone_id or self._resize_zone_id
        for zd in self.zone_defs:
            rect = self._zone_rect(zd)
            is_active = (zd.id == active_id)
            color = self.ZONE_HOVER_COLOR if is_active else self.ZONE_COLOR
            if is_active and self._conflict:
                color = self.CONFLICT_COLOR
            painter.fillRect(rect, color)
            painter.setPen(QPen(QColor(180, 200, 255), 1))
            painter.drawRect(rect)
            painter.setPen(QColor(220, 230, 255))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, zd.name)

            # リサイズハンドル（右端・下端・右下角）
            h = _HANDLE_PX
            painter.fillRect(QRect(rect.right() - h, rect.top(), h, rect.height()), self.HANDLE_COLOR)
            painter.fillRect(QRect(rect.left(), rect.bottom() - h, rect.width(), h), self.HANDLE_COLOR)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position().toPoint()
        for zd in reversed(self.zone_defs):
            rect = self._zone_rect(zd)
            edge = self._hit_edge(pos, rect)
            if edge:
                self._resize_zone_id = zd.id
                self._resize_edge = edge
                self._conflict = False
                return
            if rect.contains(pos):
                self._drag_zone_id = zd.id
                self._drag_offset = pos - rect.topLeft()
                self._conflict = False
                return

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        cw, ch = self._cell_size()

        if self._resize_zone_id:
            zd = next(z for z in self.zone_defs if z.id == self._resize_zone_id)
            col = zd.grid_pos.col
            row = zd.grid_pos.row
            new_col_span = zd.grid_pos.col_span
            new_row_span = zd.grid_pos.row_span

            if self._resize_edge in ("right", "corner"):
                end_col = min(max(col + 1, int(pos.x() / cw) + 1), self._cols)
                new_col_span = end_col - col

            if self._resize_edge in ("bottom", "corner"):
                end_row = min(max(row + 1, int(pos.y() / ch) + 1), self._rows)
                new_row_span = end_row - row

            self._conflict = self._check_conflict(zd.id, col, row, new_col_span, new_row_span)
            if not self._conflict:
                zd.grid_pos = GridPos(col=col, row=row, col_span=new_col_span, row_span=new_row_span)
            self.update()
            return

        if self._drag_zone_id:
            zd = next(z for z in self.zone_defs if z.id == self._drag_zone_id)
            snap_pos = pos - self._drag_offset
            snap_col = min(max(0, int(snap_pos.x() / cw)), self._cols - 1)
            snap_row = min(max(0, int(snap_pos.y() / ch)), self._rows - 1)
            self._conflict = self._check_conflict(
                zd.id, snap_col, snap_row, zd.grid_pos.col_span, zd.grid_pos.row_span
            )
            zd.grid_pos = GridPos(
                col=snap_col, row=snap_row,
                col_span=zd.grid_pos.col_span, row_span=zd.grid_pos.row_span,
            )
            self.update()
            return

        self._update_cursor(pos)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._drag_zone_id = None
        self._resize_zone_id = None
        self._resize_edge = None
        self._conflict = False
        self.update()


class LayoutEditorDialog(QDialog):
    def __init__(self, win_def: WindowDefinition, win_defs: list[WindowDefinition],
                 zone_defs: list[ZoneDefinition], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"レイアウト編集 — {win_def.title}")
        self.resize(700, 500)
        self._win_def = win_def
        self._win_defs = win_defs
        self._all_zone_defs = zone_defs

        layout = QVBoxLayout(self)

        self._canvas = _GridCanvas(win_def, [z for z in zone_defs if z.window_id == win_def.id])
        layout.addWidget(self._canvas, 1)

        hint = QLabel("ゾーンをドラッグして移動、右端・下端をドラッグしてリサイズできます。赤色 = 衝突。")
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
        from .signals import game_signals
        edited = {zd.id: zd for zd in self._canvas.zone_defs}
        merged = [edited.get(z.id, z) for z in self._all_zone_defs]
        save_game_config("data/game.json", self._win_defs, merged)
        self.accept()
        game_signals.layout_updated.emit(merged)
