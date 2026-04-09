import json
from typing import List, Optional, Tuple

from PyQt6.QtCore import QMimeData, QPoint, QRect, Qt, QTimer
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QDrag,
    QFont,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
    QTransform,
)
from PyQt6.QtWidgets import QFrame, QMenu, QMessageBox

from models.card import Card
from models.game_state import GameCard, GameState, ZoneType

from .constants import BATTLE_CARD_SCALE, CARD_BACK_PATH, CARD_H, CARD_W, MIME_TYPE
from .signals import game_signals


_card_back_cache: Optional[QPixmap] = None
_card_back_tapped_cache: Optional[QPixmap] = None

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


def _make_card_back() -> QPixmap:
    global _card_back_cache
    if _card_back_cache is not None:
        return _card_back_cache
    pix = QPixmap(CARD_BACK_PATH)
    if not pix.isNull():
        _card_back_cache = pix.scaled(CARD_W, CARD_H, Qt.AspectRatioMode.IgnoreAspectRatio,
                                      Qt.TransformationMode.SmoothTransformation)
        return _card_back_cache
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
    _card_back_cache = pix
    return _card_back_cache


def _make_card_back_tapped() -> QPixmap:
    global _card_back_tapped_cache
    if _card_back_tapped_cache is not None:
        return _card_back_tapped_cache
    back = _make_card_back()
    t = QTransform().rotate(90)
    rot = back.transformed(t, Qt.TransformationMode.SmoothTransformation)
    _card_back_tapped_cache = rot.scaled(CARD_H, CARD_W, Qt.AspectRatioMode.IgnoreAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
    return _card_back_tapped_cache


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

    def __init__(self, zone_type: ZoneType, label: str, pile_mode: bool = False, mask_cards: bool = False, card_scale: float = 1.0, parent=None):
        super().__init__(parent)
        self.zone_type = zone_type
        self.label = label
        self.pile_mode = pile_mode  # DECK zone: show as a pile with count
        self.mask_cards = mask_cards  # always render cards face-down
        self._cw = int(CARD_W * card_scale)  # このゾーンのカード幅
        self._ch = int(CARD_H * card_scale)  # このゾーンのカード高
        self._card_positions: List[Tuple[int, int, int]] = []  # (x, y, card_index)
        self._positions_dirty: bool = True
        self._pix_cache: dict = {}  # (card_id, face_down) -> QPixmap
        self._drag_start: Optional[QPoint] = None
        self._hover_idx: int = -1  # マウスオーバー中のカードインデックス
        self._flash_alpha: int = 0  # シャッフルアニメーション用フラッシュ透明度
        self._flash_timer = QTimer(self)
        self._flash_timer.timeout.connect(self._flash_tick)

        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumHeight(self._ch + self.TITLE_H + 10)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        game_signals.zones_updated.connect(self._on_zones_updated)

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------

    def _zone(self):
        return GameState.get_instance().zones[self.zone_type]

    def _card_w(self, gc: GameCard) -> int:
        return self._ch if gc.tapped else self._cw

    def _battle_row_y(self, row: int) -> int:
        """バトルゾーン各行の y 座標を返す。row=1 が上段、row=0 が下段。"""
        area_y = self.TITLE_H + 2
        return area_y if row == 1 else area_y + self._ch // 2

    def _battle_row_from_pos(self, y: int) -> int:
        """ドロップ y 座標から行(0 or 1)を判定する。"""
        return 1 if y < self.TITLE_H + 2 + self._ch * 3 // 4 else 0

    def _layout_single_row(self, row_cards: list, area_x: int, area_y: int, area_w: int) -> list:
        """1行分のカード位置リスト [(x, y, card_index), ...] を返す。"""
        if not row_cards:
            return []
        widths = [self._card_w(gc) for _, gc in row_cards]
        total = sum(widths) + (len(row_cards) - 1) * 4
        positions = []
        if total <= area_w:
            x = area_x + max(0, (area_w - total) // 2)
            for (idx, gc), w in zip(row_cards, widths):
                positions.append((x, area_y, idx))
                x += w + 4
        else:
            max_w = max(widths)
            spacing = max(16, (area_w - max_w) // max(1, len(row_cards) - 1))
            for j, (idx, _) in enumerate(row_cards):
                positions.append((area_x + j * spacing, area_y, idx))
        return positions

    def _calculate_positions(self):
        if not self._positions_dirty:
            return
        self._positions_dirty = False
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
            cx = area_x + max(0, (area_w - self._cw) // 2)
            self._card_positions = [(cx, area_y, n - 1)]
            return

        if self.zone_type == ZoneType.BATTLE:
            # 下段(row=0)を先に、上段(row=1)を後に追加（描画・ヒットテスト順）
            row0 = [(i, gc) for i, gc in enumerate(cards) if gc.row == 0]
            row1 = [(i, gc) for i, gc in enumerate(cards) if gc.row == 1]
            self._card_positions = (
                self._layout_single_row(row0, area_x, self._battle_row_y(0), area_w) +
                self._layout_single_row(row1, area_x, self._battle_row_y(1), area_w)
            )
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
        if not cards or self.pile_mode:
            return False
        area_w = self.width() - 8
        if self.zone_type == ZoneType.BATTLE:
            for row in (0, 1):
                rc = [gc for gc in cards if gc.row == row]
                if not rc:
                    continue
                widths = [self._card_w(gc) for gc in rc]
                if sum(widths) + (len(rc) - 1) * 4 > area_w:
                    return True
            return False
        widths = [self._card_w(gc) for gc in cards]
        return sum(widths) + (len(cards) - 1) * 4 > area_w

    # ------------------------------------------------------------------
    # Pixmap helpers
    # ------------------------------------------------------------------

    def _get_pixmap(self, gc: GameCard) -> QPixmap:
        # mask_cards=True でも revealed=True なら表向きにする
        face_down = gc.face_down or (self.mask_cards and not gc.revealed)
        key = (gc.card.id, face_down)
        if key not in self._pix_cache:
            if face_down:
                pix = _make_card_back()
            else:
                pix = QPixmap(gc.card.image_path)
                if pix.isNull():
                    pix = _make_fallback(gc.card.name)
                pix = pix.scaled(
                    self._cw, self._ch,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            self._pix_cache[key] = pix
        return self._pix_cache[key]

    def _invalidate_cache(self):
        self._pix_cache.clear()

    def _on_zones_updated(self):
        self._positions_dirty = True
        self.update()

    def start_shuffle_anim(self):
        """山札シャッフル時の白フラッシュアニメーションを開始する。"""
        self._flash_alpha = 220
        self._flash_timer.start(25)

    def _flash_tick(self):
        self._flash_alpha = max(0, self._flash_alpha - 14)
        self.update()
        if self._flash_alpha == 0:
            self._flash_timer.stop()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._positions_dirty = True

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
            painter.drawPixmap(x, y, self._cw, self._ch, _make_card_back())
            count_rect = QRect(x, y + self._ch - 24, self._cw, 24)
            painter.fillRect(count_rect, QColor(0, 0, 0, 200))
            painter.setFont(QFont("Arial", 13, QFont.Weight.Bold))
            painter.setPen(QColor(255, 255, 0))
            painter.drawText(count_rect, Qt.AlignmentFlag.AlignCenter, str(n))
            # シャッフルフラッシュ
            if self._flash_alpha > 0:
                painter.fillRect(QRect(x, y, self._cw, self._ch),
                                 QColor(255, 255, 255, self._flash_alpha))
            return

        for x, y, i in self._card_positions:
            if i >= len(zone.cards):
                continue
            gc = zone.cards[i]
            pix = self._get_pixmap(gc)

            # 進化スタックの影
            stack_count = len(gc.under_cards)
            for s in range(min(stack_count, 3), 0, -1):
                offset = s * 3
                painter.setOpacity(0.5)
                if gc.tapped:
                    oy = (self._ch - self._cw) // 2
                    painter.drawPixmap(x - offset, y + oy + offset, self._ch, self._cw, _make_card_back_tapped())
                else:
                    painter.drawPixmap(x - offset, y + offset, self._cw, self._ch, _make_card_back())
                painter.setOpacity(1.0)

            if gc.tapped:
                t = QTransform().rotate(90)
                rot = pix.transformed(t, Qt.TransformationMode.SmoothTransformation)
                rot = rot.scaled(
                    self._ch, self._cw,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                oy = (self._ch - self._cw) // 2
                painter.drawPixmap(x, y + oy, rot)
                painter.setPen(QPen(QColor(255, 200, 0), 2))
                painter.drawRect(x, y + oy, self._ch - 1, self._cw - 1)
            elif self.zone_type == ZoneType.MANA:
                t = QTransform().rotate(180)
                rot = pix.transformed(t, Qt.TransformationMode.SmoothTransformation)
                painter.drawPixmap(x, y, self._cw, self._ch, rot)
            else:
                painter.drawPixmap(x, y, self._cw, self._ch, pix)

            # スタック枚数バッジ
            if stack_count > 0:
                badge = QRect(x, y, 20, 16)
                painter.fillRect(badge, QColor(180, 60, 0, 220))
                painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, str(stack_count + 1))

            # カラーマーク（右上に色付き円）
            if gc.marker and gc.marker in _MARKER_COLORS:
                r = 7
                if gc.tapped:
                    oy = (self._ch - self._cw) // 2
                    mx = x + self._ch - r - 3
                    my = y + oy + r + 3
                else:
                    mx = x + self._cw - r - 3
                    my = y + r + 3
                painter.setBrush(QBrush(_MARKER_COLORS[gc.marker]))
                painter.setPen(QPen(QColor(255, 255, 255), 1))
                painter.drawEllipse(QPoint(mx, my), r, r)

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
        n = len(zone.cards)
        for x, y, i in reversed(self._card_positions):
            if i >= n:
                continue
            gc = zone.cards[i]
            if gc.tapped:
                oy = (self._ch - self._cw) // 2
                rect = QRect(x, y + oy, self._ch, self._cw)
            else:
                rect = QRect(x, y, self._cw, self._ch)
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
            _, self._hover_idx = self._card_at(event.pos())
            return
        if self._drag_start is None:
            return
        gc, idx = self._card_at(self._drag_start)
        if gc is None:
            return
        self._drag_start = None
        self._hover_idx = -1
        self._start_drag(gc, idx)

    def enterEvent(self, event):
        self.setFocus()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_idx = -1
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        if self._hover_idx == -1:
            super().keyPressEvent(event)
            return
        cards = self._zone().cards
        idx = self._hover_idx
        key = event.key()

        # 上下キー: バトルゾーンの行移動
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down) and self.zone_type == ZoneType.BATTLE:
            gc = cards[idx]
            new_row = 1 if key == Qt.Key.Key_Up else 0
            if gc.row != new_row:
                GameState.get_instance().push_snapshot()
                gc.row = new_row
                self._positions_dirty = True
                game_signals.zones_updated.emit()
        # 左右キー: 同行内で位置移動
        elif key == Qt.Key.Key_Left and idx > 0:
            GameState.get_instance().push_snapshot()
            cards[idx], cards[idx - 1] = cards[idx - 1], cards[idx]
            self._hover_idx -= 1
            self._positions_dirty = True
            game_signals.zones_updated.emit()
        elif key == Qt.Key.Key_Right and idx < len(cards) - 1:
            GameState.get_instance().push_snapshot()
            cards[idx], cards[idx + 1] = cards[idx + 1], cards[idx]
            self._hover_idx += 1
            self._positions_dirty = True
            game_signals.zones_updated.emit()
        else:
            super().keyPressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._drag_start is not None:
            gc, _ = self._card_at(self._drag_start)
            if gc and self.zone_type in (ZoneType.MANA, ZoneType.BATTLE):
                self._toggle_tap(gc)
        self._drag_start = None

    def mouseDoubleClickEvent(self, event):
        gc, _ = self._card_at(event.pos())
        if gc is None and len(self._zone().cards) > 0:
            self._open_expand()

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------

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

    _HIDDEN_ZONES = (ZoneType.HAND, ZoneType.SHIELD, ZoneType.DECK)

    def _start_drag(self, gc: GameCard, idx: int):
        drag = QDrag(self)
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
        # 非公開ゾーン（手札・シールド・山札）またはマスク中のゾーンからのドラッグは
        # カーソルに裏面を表示し、画面共有時に内容が漏れないようにする
        use_back = gc.face_down or self.mask_cards or (self.zone_type in self._HIDDEN_ZONES)
        drag.setPixmap(_make_card_back() if use_back else self._get_pixmap(gc))
        drag.setHotSpot(QPoint(self._cw // 2, self._ch // 2))
        drag.exec(Qt.DropAction.MoveAction)

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
        gs = GameState.get_instance()
        src = data.get("source_zone", "")

        # 山札へのドロップはダイアログで一番上/下を選ぶ。
        # QMessageBox をドラッグイベント中に開くと Qt がクラッシュするため、
        # カードを先に抜き取り、QTimer でイベント完了後にダイアログを表示する。
        if self.zone_type == ZoneType.DECK and src != "deck_list":
            try:
                src_type = ZoneType(src)
            except ValueError:
                return
            gs.push_snapshot()
            card_id = data.get("card_id")
            src_cards = gs.zones[src_type].cards
            idx = next((i for i, c in enumerate(src_cards) if c.card.id == card_id),
                       data.get("card_index", -1))
            gc = gs.zones[src_type].remove_card(idx)
            if not gc:
                return
            all_cards = [gc] + gc.under_cards
            gc.under_cards = []
            for c in all_cards:
                c.tapped = False
                c.row = 0
                c.face_down = False
            event.acceptProposedAction()
            self._invalidate_cache()
            game_signals.zones_updated.emit()
            QTimer.singleShot(0, lambda cards=all_cards: self._ask_deck_position(cards))
            return

        gs.push_snapshot()
        self._handle_drop(data, drop_pos)
        event.acceptProposedAction()
        self._invalidate_cache()
        game_signals.zones_updated.emit()

    def _calc_insert_index(self, drop_pos: QPoint, src_idx: int) -> int:
        """ドロップ位置 X 座標から、src_idx の card を取り除いた後の挿入インデックスを返す。"""
        positions = self._card_positions  # [(x, y, card_idx), ...] — 左から順
        if not positions:
            return 0
        drop_x = drop_pos.x()
        old_insert = len(self._zone().cards)  # デフォルト: 末尾
        for x, y, card_idx in positions:
            card_center_x = x + self._cw // 2
            if drop_x < card_center_x:
                old_insert = card_idx
                break
        # src_idx の card を取り除くとインデックスがずれる
        if src_idx < old_insert:
            return old_insert - 1
        return old_insert

    def _handle_drop(self, data: dict, drop_pos: QPoint = None):
        gs = GameState.get_instance()
        src = data["source_zone"]

        is_same_zone = (src == self.zone_type.value and src != "deck_list")

        # 同一ゾーン並び替え: カード除去前に挿入インデックスを計算
        target_insert_idx = None
        if is_same_zone and drop_pos is not None:
            self._calculate_positions()
            card_id_pre = data.get("card_id")
            src_cards_pre = gs.zones[self.zone_type].cards
            src_idx_pre = next(
                (i for i, c in enumerate(src_cards_pre) if c.card.id == card_id_pre),
                data["card_index"],
            )
            target_insert_idx = self._calc_insert_index(drop_pos, src_idx_pre)

        if src == "deck_list":
            card = Card(
                name=data["card_name"], image_path=data["image_path"], id=data["card_id"],
                mana=data.get("mana", 0),
                civilizations=data.get("civilizations", []),
                card_type=data.get("card_type", ""),
            )
            gc = GameCard(card)
        else:
            try:
                src_type = ZoneType(src)
            except ValueError:
                return
            card_id = data.get("card_id")
            src_cards = gs.zones[src_type].cards
            idx = next((i for i, c in enumerate(src_cards) if c.card.id == card_id), data["card_index"])
            gc = gs.zones[src_type].remove_card(idx)

        if not gc:
            return

        # カード除去後は位置キャッシュが古くなるので再計算フラグを立てる
        self._positions_dirty = True

        # バトルゾーンで既存カードの上にドロップ → 進化（同一ゾーン含む）
        if self.zone_type == ZoneType.BATTLE and drop_pos is not None:
            target, _ = self._card_at(drop_pos)
            if target and target is not gc:
                gc.tapped = target.tapped
                gc.row = target.row
                gc.under_cards = [target] + target.under_cards
                target.under_cards = []
                zone = gs.zones[self.zone_type]
                for i, card in enumerate(zone.cards):
                    if card is target:
                        zone.cards[i] = gc
                        break
                return

        # バトルゾーンはドロップ位置の y で行を決定
        if self.zone_type == ZoneType.BATTLE and drop_pos is not None:
            gc.row = self._battle_row_from_pos(drop_pos.y())

        # 同一ゾーン内並び替え
        if is_same_zone and target_insert_idx is not None:
            gs.zones[self.zone_type].insert_card(target_insert_idx, gc)
            return

        # ゾーン移動時に公開フラグをリセット
        gc.revealed = False

        # バトルゾーン以外への移動時、進化スタックを分離して個別に追加
        if self.zone_type != ZoneType.BATTLE and gc.under_cards:
            all_cards = [gc] + gc.under_cards
            gc.under_cards = []
            for c in all_cards:
                c.tapped = False
                c.row = 0
                if self.zone_type == ZoneType.SHIELD:
                    c.face_down = True
                elif self.zone_type == ZoneType.DECK:
                    c.face_down = False
                gs.zones[self.zone_type].add_card(c)
            return

        if self.zone_type == ZoneType.SHIELD:
            gc.face_down = True
        elif self.zone_type == ZoneType.DECK:
            gc.face_down = False
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
        if not gc.face_down and not self.mask_cards:
            menu.addAction("拡大表示", lambda: self._show_zoom(gc))

        # マークサブメニュー
        mark_menu = menu.addMenu("マーク")
        mark_menu.addAction("なし", lambda: self._set_marker(gc, None))
        mark_menu.addSeparator()
        for key, label in _MARKER_LABELS.items():
            action = mark_menu.addAction(label, lambda k=key: self._set_marker(gc, k))
            pix = QPixmap(14, 14)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setBrush(QBrush(_MARKER_COLORS[key]))
            p.setPen(QPen(QColor(200, 200, 200), 1))
            p.drawEllipse(1, 1, 12, 12)
            p.end()
            action.setIcon(QIcon(pix))

        if self.zone_type == ZoneType.HAND:
            menu.addSeparator()
            reveal_text = "非公開にする" if gc.revealed else "公開する"
            menu.addAction(reveal_text, lambda: self._toggle_revealed(gc))
        if self.zone_type == ZoneType.BATTLE:
            menu.addSeparator()
            if gc.row == 0:
                menu.addAction("上段へ移動", lambda: self._move_row(gc, 1))
            else:
                menu.addAction("下段へ移動", lambda: self._move_row(gc, 0))
        if gc.under_cards:
            menu.addSeparator()
            menu.addAction(f"スタックを確認（{len(gc.under_cards) + 1}枚）",
                           lambda: self._show_stack(gc))
            menu.addAction("一番下を切り離す", lambda: self._pop_stack(gc, idx))
        menu.exec(pos)

    def _move_row(self, gc: GameCard, row: int):
        GameState.get_instance().push_snapshot()
        gc.row = row
        self._positions_dirty = True
        game_signals.zones_updated.emit()

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
        for under in gc.under_cards:
            under.tapped = gc.tapped
        self._invalidate_cache()
        game_signals.zones_updated.emit()

    def _toggle_face(self, gc: GameCard):
        GameState.get_instance().push_snapshot()
        gc.face_down = not gc.face_down
        self._invalidate_cache()
        game_signals.zones_updated.emit()

    def _toggle_revealed(self, gc: GameCard):
        GameState.get_instance().push_snapshot()
        gc.revealed = not gc.revealed
        self._invalidate_cache()
        game_signals.zones_updated.emit()

    def _set_marker(self, gc: GameCard, color: Optional[str]):
        GameState.get_instance().push_snapshot()
        gc.marker = color
        game_signals.zones_updated.emit()

    def _ask_deck_position(self, cards):
        """ドラッグ完了後に呼ばれる。一番上/下を選択して山札に挿入する。"""
        box = QMessageBox(self)
        box.setWindowTitle("山札に追加")
        box.setText("どこに追加しますか？")
        top_btn = box.addButton("一番上", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("一番下", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        deck = GameState.get_instance().zones[ZoneType.DECK]
        if box.clickedButton() is top_btn:
            # 末尾 = 一番上。先頭カードが一番上になるよう逆順で追加
            for c in reversed(cards):
                deck.add_card(c)
        else:
            # 先頭 = 一番下。先頭カードが一番下になるよう逆順でinsert
            for c in reversed(cards):
                deck.insert_card(0, c)
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
