import json
from typing import List, Optional, Tuple

from PyQt6.QtCore import QPoint, QRect, Qt, QTimer
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QDrag,
    QFont,
    QPainter,
    QPen,
    QPixmap,
    QTransform,
)
from PyQt6.QtWidgets import QFrame, QMenu

from models.card import Card
from models.game_state import GameCard, GameState, ZoneType

from .constants import CARD_BACK_PATH, CARD_H, CARD_W, MIME_TYPE
from .signals import game_signals


def _make_card_back() -> QPixmap:
    pix = QPixmap(CARD_BACK_PATH)
    if not pix.isNull():
        return pix.scaled(CARD_W, CARD_H, Qt.AspectRatioMode.IgnoreAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
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
    return pix


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


class ZoneWidget(QFrame):
    """
    A game zone that renders cards using QPainter.
    Cards spread without overlap when space allows, otherwise overlap.
    Double-click opens the expand dialog.
    Right-click on a card opens a context menu.
    Drag a card to initiate a move; accepts drops from other zones / deck list.
    """

    TITLE_H = 22  # pixels reserved for zone label

    def __init__(self, zone_type: ZoneType, label: str, pile_mode: bool = False, mask_cards: bool = False, parent=None):
        super().__init__(parent)
        self.zone_type = zone_type
        self.label = label
        self.pile_mode = pile_mode  # DECK zone: show as a pile with count
        self.mask_cards = mask_cards  # always render cards face-down
        self._card_positions: List[Tuple[int, int, int]] = []  # (x, y, card_index)
        self._pix_cache: dict = {}  # (card_id, face_down) -> QPixmap
        self._drag_start: Optional[QPoint] = None
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._pending_action = None  # callable fired after double-click interval
        self._click_timer.timeout.connect(self._fire_pending)

        self.setAcceptDrops(True)
        self.setMinimumHeight(CARD_H + self.TITLE_H + 10)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        game_signals.zones_updated.connect(self.update)

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------

    def _zone(self):
        return GameState.get_instance().zones[self.zone_type]

    def _card_w(self, gc: GameCard) -> int:
        return CARD_H if gc.tapped else CARD_W

    def _card_h(self, gc: GameCard) -> int:
        return CARD_W if gc.tapped else CARD_H

    def _calculate_positions(self):
        self._card_positions = []
        zone = self._zone()
        cards = zone.cards
        n = len(cards)
        if n == 0:
            return

        area_x = 4
        area_y = self.TITLE_H + 2
        area_w = self.width() - 8

        if self.pile_mode:
            # Show only top card centred
            cx = area_x + max(0, (area_w - CARD_W) // 2)
            self._card_positions = [(cx, area_y, n - 1)]
            return

        widths = [self._card_w(gc) for gc in cards]
        total_no_overlap = sum(widths) + (n - 1) * 4

        if total_no_overlap <= area_w:
            start_x = area_x + max(0, (area_w - total_no_overlap) // 2)
            x = start_x
            for i, w in enumerate(widths):
                self._card_positions.append((x, area_y, i))
                x += w + 4
        else:
            max_w = max(widths)
            spacing = max(16, (area_w - max_w) // max(1, n - 1))
            for i in range(n):
                self._card_positions.append((area_x + i * spacing, area_y, i))

    def _is_overlapping(self) -> bool:
        cards = self._zone().cards
        n = len(cards)
        if n == 0 or self.pile_mode:
            return False
        widths = [self._card_w(gc) for gc in cards]
        area_w = self.width() - 8
        return sum(widths) + (n - 1) * 4 > area_w

    # ------------------------------------------------------------------
    # Pixmap helpers
    # ------------------------------------------------------------------

    def _get_pixmap(self, gc: GameCard) -> QPixmap:
        face_down = gc.face_down or self.mask_cards
        key = (gc.card.id, face_down)
        if key not in self._pix_cache:
            if face_down:
                pix = _make_card_back()
            else:
                pix = QPixmap(gc.card.image_path)
                if pix.isNull():
                    pix = _make_fallback(gc.card.name)
                pix = pix.scaled(
                    CARD_W, CARD_H,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            self._pix_cache[key] = pix
        return self._pix_cache[key]

    def _invalidate_cache(self):
        self._pix_cache.clear()

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(30, 30, 50))
        painter.setPen(QPen(QColor(80, 90, 140), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        # Title
        painter.setPen(QColor(255, 255, 180))
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        zone = self._zone()
        n = len(zone.cards)
        title = f"{self.label}  ({n})" if n > 0 else self.label
        painter.drawText(4, self.TITLE_H - 4, title)

        self._calculate_positions()

        if self.pile_mode and n > 0:
            # Draw single back card + big count overlay
            x, y, _ = self._card_positions[0]
            painter.drawPixmap(x, y, CARD_W, CARD_H, _make_card_back())
            count_rect = QRect(x, y + CARD_H - 24, CARD_W, 24)
            painter.fillRect(count_rect, QColor(0, 0, 0, 200))
            painter.setFont(QFont("Arial", 13, QFont.Weight.Bold))
            painter.setPen(QColor(255, 255, 0))
            painter.drawText(count_rect, Qt.AlignmentFlag.AlignCenter, str(n))
            return

        for x, y, i in self._card_positions:
            gc = zone.cards[i]
            pix = self._get_pixmap(gc)

            # 進化スタックの影
            stack_count = len(gc.under_cards)
            for s in range(min(stack_count, 3), 0, -1):
                offset = s * 3
                painter.setOpacity(0.5)
                painter.drawPixmap(x - offset, y + offset, CARD_W, CARD_H, _make_card_back())
                painter.setOpacity(1.0)

            if gc.tapped:
                t = QTransform().rotate(90)
                rot = pix.transformed(t, Qt.TransformationMode.SmoothTransformation)
                rot = rot.scaled(
                    CARD_H, CARD_W,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                oy = (CARD_H - CARD_W) // 2
                painter.drawPixmap(x, y + oy, rot)
                painter.setPen(QPen(QColor(255, 200, 0), 2))
                painter.drawRect(x, y + oy, CARD_H - 1, CARD_W - 1)
            elif self.zone_type == ZoneType.MANA:
                t = QTransform().rotate(180)
                rot = pix.transformed(t, Qt.TransformationMode.SmoothTransformation)
                painter.drawPixmap(x, y, CARD_W, CARD_H, rot)
            else:
                painter.drawPixmap(x, y, CARD_W, CARD_H, pix)

            # スタック枚数バッジ
            if stack_count > 0:
                badge = QRect(x, y, 20, 16)
                painter.fillRect(badge, QColor(180, 60, 0, 220))
                painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, str(stack_count + 1))

        if self._is_overlapping():
            painter.setFont(QFont("Arial", 7))
            painter.setPen(QColor(200, 255, 200))
            painter.drawText(2, self.height() - 3, "ダブルクリックで展開")

    # ------------------------------------------------------------------
    # Hit testing
    # ------------------------------------------------------------------

    def _card_at(self, pos: QPoint) -> Tuple[Optional[GameCard], int]:
        self._calculate_positions()
        zone = self._zone()
        for x, y, i in reversed(self._card_positions):
            gc = zone.cards[i]
            if gc.tapped:
                oy = (CARD_H - CARD_W) // 2
                rect = QRect(x, y + oy, CARD_H, CARD_W)
            else:
                rect = QRect(x, y, CARD_W, CARD_H)
            if rect.contains(pos):
                return gc, i
        return None, -1

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.pos()
        elif event.button() == Qt.MouseButton.RightButton:
            gc, idx = self._card_at(event.pos())
            if gc:
                self._show_menu(gc, idx, event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._drag_start is None:
            return
        gc, idx = self._card_at(self._drag_start)
        if gc is None:
            return
        self._drag_start = None
        self._start_drag(gc, idx)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._drag_start is not None:
            gc, _ = self._card_at(self._drag_start)
            if gc:
                if self.zone_type in (ZoneType.MANA, ZoneType.BATTLE):
                    self._pending_action = lambda g=gc: self._toggle_tap(g)
                elif not gc.face_down and not self.mask_cards:
                    pos = event.globalPosition().toPoint()
                    self._pending_action = lambda g=gc, p=pos: self._show_zoom(g, p)
                if self._pending_action:
                    self._click_timer.start(QApplication.doubleClickInterval())
        self._drag_start = None

    def mouseDoubleClickEvent(self, event):
        self._click_timer.stop()
        self._pending_action = None
        if self.zone_type in (ZoneType.MANA, ZoneType.BATTLE):
            gc, _ = self._card_at(event.pos())
            if gc and not gc.face_down:
                self._show_zoom(gc, event.globalPosition().toPoint())
            return
        if len(self._zone().cards) > 0:
            self._open_expand()

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------

    def _fire_pending(self):
        if self._pending_action:
            self._pending_action()
            self._pending_action = None

    def _show_zoom(self, gc: GameCard, global_pos=None):
        from .card_zoom import CardZoomDialog
        dlg = CardZoomDialog(gc, self)
        window = self.window()
        center = window.geometry().center()
        dlg.move(center.x() - dlg.sizeHint().width() // 2,
                 center.y() - dlg.sizeHint().height() // 2)
        dlg.exec()

    # ------------------------------------------------------------------
    # Drag
    # ------------------------------------------------------------------

    def _start_drag(self, gc: GameCard, idx: int):
        drag = QDrag(self)
        from PyQt6.QtCore import QMimeData
        mime = QMimeData()
        payload = json.dumps({
            "source_zone": self.zone_type.value,
            "card_index": idx,
            "card_id": gc.card.id,
            "card_name": gc.card.name,
            "image_path": gc.card.image_path,
        })
        mime.setData(MIME_TYPE, payload.encode())
        drag.setMimeData(mime)
        drag.setPixmap(self._get_pixmap(gc))
        drag.setHotSpot(QPoint(CARD_W // 2, CARD_H // 2))
        drag.exec(Qt.DropAction.MoveAction)

    # ------------------------------------------------------------------
    # Drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME_TYPE):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(MIME_TYPE):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(MIME_TYPE):
            return
        raw = event.mimeData().data(MIME_TYPE)
        data = json.loads(bytes(raw).decode())
        drop_pos = event.position().toPoint()
        GameState.get_instance().push_snapshot()
        self._handle_drop(data, drop_pos)
        event.acceptProposedAction()
        self._invalidate_cache()
        game_signals.zones_updated.emit()

    def _handle_drop(self, data: dict, drop_pos: QPoint = None):
        gs = GameState.get_instance()
        src = data["source_zone"]

        if src == "deck_list":
            card = Card(name=data["card_name"], image_path=data["image_path"], id=data["card_id"])
            gc = GameCard(card)
        else:
            try:
                src_type = ZoneType(src)
            except ValueError:
                return
            gc = gs.zones[src_type].remove_card(data["card_index"])

        if not gc:
            return

        # バトルゾーンで既存カードの上にドロップ → 進化
        if self.zone_type == ZoneType.BATTLE and drop_pos is not None:
            target, _ = self._card_at(drop_pos)
            if target and target is not gc:
                # gc が新しいトップ、target 以下をそのまま引き継ぐ
                gc.tapped = target.tapped
                gc.under_cards = [target] + target.under_cards
                target.under_cards = []
                zone = gs.zones[self.zone_type]
                for i, card in enumerate(zone.cards):
                    if card is target:
                        zone.cards[i] = gc
                        break
                return

        if self.zone_type == ZoneType.SHIELD:
            gc.face_down = True
        gs.zones[self.zone_type].add_card(gc)

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def _show_menu(self, gc: GameCard, idx: int, pos: QPoint):
        menu = QMenu(self)
        tap_text = "アンタップ" if gc.tapped else "タップ"
        menu.addAction(tap_text, lambda: self._toggle_tap(gc))
        face_text = "表向きにする" if gc.face_down else "裏向きにする"
        menu.addAction(face_text, lambda: self._toggle_face(gc))
        if gc.under_cards:
            menu.addSeparator()
            menu.addAction(f"スタックを確認（{len(gc.under_cards) + 1}枚）",
                           lambda: self._show_stack(gc))
            menu.addAction("一番下を切り離す", lambda: self._pop_stack(gc, idx))
        menu.addSeparator()
        menu.addAction("このゾーンから削除", lambda: self._remove_card(idx))
        menu.exec(pos)

    def _show_stack(self, gc: GameCard):
        from .stack_dialog import StackDialog
        dlg = StackDialog(gc, self)
        dlg.exec()
        self._invalidate_cache()
        game_signals.zones_updated.emit()

    def _pop_stack(self, gc: GameCard, idx: int):
        if not gc.under_cards:
            return
        GameState.get_instance().push_snapshot()
        popped = gc.under_cards.pop(0)
        popped.tapped = gc.tapped
        GameState.get_instance().zones[self.zone_type].add_card(popped)
        self._invalidate_cache()
        game_signals.zones_updated.emit()

    def _toggle_tap(self, gc: GameCard):
        GameState.get_instance().push_snapshot()
        gc.tapped = not gc.tapped
        self._invalidate_cache()
        game_signals.zones_updated.emit()

    def _toggle_face(self, gc: GameCard):
        GameState.get_instance().push_snapshot()
        gc.face_down = not gc.face_down
        self._invalidate_cache()
        game_signals.zones_updated.emit()

    def _remove_card(self, idx: int):
        GameState.get_instance().push_snapshot()
        GameState.get_instance().zones[self.zone_type].remove_card(idx)
        self._invalidate_cache()
        game_signals.zones_updated.emit()

    # ------------------------------------------------------------------
    # Expand dialog
    # ------------------------------------------------------------------

    def _open_expand(self):
        from .expand_dialog import ExpandDialog
        dlg = ExpandDialog(self.zone_type, self.label, self)
        dlg.exec()
        self._invalidate_cache()
        game_signals.zones_updated.emit()
