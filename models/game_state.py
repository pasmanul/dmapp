import json
import os
import uuid
from collections import deque
from enum import Enum
from typing import Dict, List, Optional

from .card import Card


def _dummy_card() -> "GameCard":
    card = Card(name="ダミー", image_path="", id=f"dummy_{uuid.uuid4()}")
    gc = GameCard(card)
    gc.face_down = True
    return gc


def _gc_to_dict(gc: "GameCard") -> dict:
    return {
        "card": {"name": gc.card.name, "image_path": gc.card.image_path, "id": gc.card.id},
        "tapped": gc.tapped,
        "face_down": gc.face_down,
        "under_cards": [_gc_to_dict(c) for c in gc.under_cards],
    }


def _gc_from_dict(d: dict) -> "GameCard":
    card = Card(name=d["card"]["name"], image_path=d["card"]["image_path"], id=d["card"]["id"])
    gc = GameCard(card)
    gc.tapped = d["tapped"]
    gc.face_down = d["face_down"]
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
        self.under_cards: List["GameCard"] = []


class Zone:
    def __init__(self, zone_type: ZoneType):
        self.zone_type = zone_type
        self.cards: List[GameCard] = []

    def add_card(self, game_card: GameCard):
        self.cards.append(game_card)

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
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def load_file(self, path: str):
        with open(path, encoding="utf-8") as f:
            self.from_dict(json.load(f))

    # ------------------------------------------------------------------
    # Field helpers
    # ------------------------------------------------------------------

    def reset_field(self):
        for zt in [ZoneType.BATTLE, ZoneType.SHIELD, ZoneType.DECK, ZoneType.GRAVEYARD, ZoneType.MANA]:
            self.zones[zt].cards.clear()

    def initialize_field(self):
        self.reset_field()
        for _ in range(5):
            self.zones[ZoneType.SHIELD].add_card(_dummy_card())
        for _ in range(30):
            self.zones[ZoneType.DECK].add_card(_dummy_card())
