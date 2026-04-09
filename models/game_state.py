import json
import os
import random
import uuid
from collections import deque
from enum import Enum
from typing import Dict, List, Optional

from .card import Card


def _gc_to_dict(gc: "GameCard") -> dict:
    c = gc.card
    return {
        "card": {
            "name": c.name, "image_path": c.image_path, "id": c.id,
            "mana": c.mana, "civilizations": c.civilizations, "card_type": c.card_type,
        },
        "tapped": gc.tapped,
        "face_down": gc.face_down,
        "revealed": gc.revealed,
        "row": gc.row,
        "marker": gc.marker,
        "under_cards": [_gc_to_dict(c) for c in gc.under_cards],
    }


def _gc_from_dict(d: dict) -> "GameCard":
    cd = d["card"]
    card = Card(
        name=cd["name"], image_path=cd["image_path"], id=cd["id"],
        mana=cd.get("mana", 0),
        civilizations=cd.get("civilizations", []),
        card_type=cd.get("card_type", ""),
    )
    gc = GameCard(card)
    gc.tapped = d["tapped"]
    gc.face_down = d["face_down"]
    gc.revealed = d.get("revealed", False)
    gc.row = d.get("row", 0)
    gc.marker = d.get("marker", None)
    gc.under_cards = [_gc_from_dict(c) for c in d.get("under_cards", [])]
    return gc


class ZoneType(Enum):
    BATTLE = "battle"
    SHIELD = "shield"
    DECK = "deck"
    GRAVEYARD = "graveyard"
    MANA = "mana"
    HAND = "hand"


class GameCard:
    def __init__(self, card: Card):
        self.card = card
        self.tapped: bool = False
        self.face_down: bool = False
        self.revealed: bool = False  # 手札を相手に公開するフラグ
        self.under_cards: List["GameCard"] = []
        self.row: int = 0  # 0=下段, 1=上段（バトルゾーン用）
        self.marker: Optional[str] = None  # 色マーク (例: "red", "blue", ...)


class Zone:
    def __init__(self, zone_type: ZoneType):
        self.zone_type = zone_type
        self.cards: List[GameCard] = []

    def add_card(self, game_card: GameCard):
        self.cards.append(game_card)

    def insert_card(self, index: int, game_card: GameCard):
        self.cards.insert(max(0, min(index, len(self.cards))), game_card)

    def remove_card(self, index: int) -> Optional[GameCard]:
        if 0 <= index < len(self.cards):
            return self.cards.pop(index)
        return None

    def __len__(self) -> int:
        return len(self.cards)


class GameState:
    _instance: Optional["GameState"] = None
    _UNDO_LIMIT = 50

    def __init__(self):
        self.zones: Dict[ZoneType, Zone] = {zt: Zone(zt) for zt in ZoneType}
        self.current_deck = None
        self.back_image_path: str = ""
        self._undo_stack: deque = deque(maxlen=self._UNDO_LIMIT)

    @classmethod
    def get_instance(cls) -> "GameState":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Snapshot / Undo
    # ------------------------------------------------------------------

    def push_snapshot(self):
        self._undo_stack.append(self.to_dict())

    def push_dict(self, snapshot: dict):
        self._undo_stack.append(snapshot)

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        self.from_dict(self._undo_stack.pop())
        return True

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "zones": {
                zt.value: [_gc_to_dict(gc) for gc in zone.cards]
                for zt, zone in self.zones.items()
            }
        }

    def from_dict(self, d: dict):
        for zt in ZoneType:
            self.zones[zt].cards.clear()
            for gc_dict in d.get("zones", {}).get(zt.value, []):
                self.zones[zt].add_card(_gc_from_dict(gc_dict))

    def save(self, path: str):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def load_file(self, path: str):
        with open(path, encoding="utf-8") as f:
            self.from_dict(json.load(f))

    # ------------------------------------------------------------------
    # Field helpers
    # ------------------------------------------------------------------

    def draw_card(self) -> bool:
        """山札の一番上から手札へ1枚ドローする。成功したら True を返す。"""
        deck = self.zones[ZoneType.DECK]
        if not deck.cards:
            return False
        self.push_snapshot()
        gc = deck.remove_card(len(deck) - 1)
        if gc:
            gc.face_down = False
            self.zones[ZoneType.HAND].add_card(gc)
            return True
        return False

    def reset_field(self):
        for zt in [ZoneType.BATTLE, ZoneType.SHIELD, ZoneType.DECK, ZoneType.GRAVEYARD, ZoneType.MANA]:
            self.zones[zt].cards.clear()

    def initialize_field(self):
        self.reset_field()
        self.zones[ZoneType.HAND].cards.clear()
        if self.current_deck is None:
            return
        # デッキカードを枚数分展開してシャッフル
        cards: List[GameCard] = []
        for deck_card in self.current_deck.cards:
            for _ in range(deck_card.count):
                gc = GameCard(Card(
                    name=deck_card.name,
                    image_path=deck_card.image_path,
                    mana=deck_card.mana,
                    civilizations=list(deck_card.civilizations),
                    card_type=deck_card.card_type,
                    id=str(uuid.uuid4()),
                ))
                cards.append(gc)
        random.shuffle(cards)
        # シールド5枚（裏向き）
        for gc in cards[:5]:
            gc.face_down = True
            self.zones[ZoneType.SHIELD].add_card(gc)
        # 手札5枚
        for gc in cards[5:10]:
            self.zones[ZoneType.HAND].add_card(gc)
        # 残りを山札へ
        for gc in cards[10:]:
            gc.face_down = False
            self.zones[ZoneType.DECK].add_card(gc)
