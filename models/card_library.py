import json
import os
import uuid
from dataclasses import dataclass, field
from typing import List


LIBRARY_PATH = "data/cards.json"

CIVILIZATIONS = ["無色", "光", "水", "闇", "火", "自然"]
CIV_COLORS = {
    "火":   "#ff4444",
    "水":   "#4488ff",
    "自然": "#44bb44",
    "光":   "#ffdd44",
    "闇":   "#aa44aa",
    "無色": "#aaaaaa",
}

CARD_TYPES = [
    "タマシード",
    "クリーチャー",
    "ネオ進化",
    "Gネオ進化",
    "スター進化",
    "S-MAX進化",
    "ツインパクト",
    "呪文",
    "クロスギア",
    "D2フィールド",
]
CARD_TYPE_COLORS = {
    "クリーチャー": "#ff8844",
    "呪文":         "#cc88ff",
    "クロスギア":   "#44aaff",
    "D2フィールド": "#44ffcc",
    "タマシード":   "#ffcc44",
    "スター進化":   "#ffff44",
    "S-MAX進化":    "#ff44aa",
    "ネオ進化":     "#88ff44",
    "Gネオ進化":    "#44ff88",
    "ツインパクト": "#ffffff",
}


@dataclass
class LibraryCard:
    name: str
    image_path: str
    mana: int = 0
    civilizations: List[str] = field(default_factory=list)
    card_type: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


class CardLibrary:
    _instance: "CardLibrary | None" = None

    def __init__(self):
        self.cards: List[LibraryCard] = []

    @classmethod
    def get_instance(cls) -> "CardLibrary":
        if cls._instance is None:
            cls._instance = cls.load()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    def add_card(self, card: LibraryCard):
        self.cards.append(card)

    def remove_card(self, card_id: str):
        self.cards = [c for c in self.cards if c.id != card_id]

    def to_dict(self) -> dict:
        return {
            "cards": [
                {
                    "id": c.id,
                    "name": c.name,
                    "image_path": c.image_path,
                    "mana": c.mana,
                    "civilizations": c.civilizations,
                    "card_type": c.card_type,
                }
                for c in self.cards
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CardLibrary":
        lib = cls()
        for c in data.get("cards", []):
            lib.cards.append(LibraryCard(
                name=c["name"],
                image_path=c["image_path"],
                mana=c.get("mana", 0),
                civilizations=c.get("civilizations", []),
                card_type=c.get("card_type", ""),
                id=c.get("id", str(uuid.uuid4())),
            ))
        return lib

    def save(self):
        os.makedirs(os.path.dirname(os.path.abspath(LIBRARY_PATH)), exist_ok=True)
        with open(LIBRARY_PATH, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls) -> "CardLibrary":
        if os.path.exists(LIBRARY_PATH):
            with open(LIBRARY_PATH, "r", encoding="utf-8") as f:
                return cls.from_dict(json.load(f))
        return cls()
