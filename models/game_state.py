import json
import os
import random
import uuid
from collections import deque
from typing import Optional

from .card import Card


class GameCard:
    def __init__(self, card: Card):
        self.card = card
        self.tapped: bool = False
        self.face_down: bool = False
        self.revealed: bool = False  # 手札を相手に公開するフラグ
        self.under_cards: list["GameCard"] = []
        self.row: int = 0  # 0=下段, 1=上段（バトルゾーン用）
        self.marker: Optional[str] = None  # 色マーク (例: "red", "blue", ...)

    def to_dict(self) -> dict:
        c = self.card
        return {
            "card": {
                "name": c.name, "image_path": c.image_path, "id": c.id,
                "mana": c.mana, "civilizations": c.civilizations, "card_type": c.card_type,
            },
            "tapped": self.tapped,
            "face_down": self.face_down,
            "revealed": self.revealed,
            "row": self.row,
            "marker": self.marker,
            "under_cards": [uc.to_dict() for uc in self.under_cards],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GameCard":
        cd = d["card"]
        card = Card(
            name=cd["name"], image_path=cd["image_path"], id=cd["id"],
            mana=cd.get("mana", 0),
            civilizations=cd.get("civilizations", []),
            card_type=cd.get("card_type", ""),
        )
        gc = cls(card)
        gc.tapped = d["tapped"]
        gc.face_down = d["face_down"]
        gc.revealed = d.get("revealed", False)
        gc.row = d.get("row", 0)
        gc.marker = d.get("marker", None)
        gc.under_cards = [cls.from_dict(c) for c in d.get("under_cards", [])]
        return gc


class Zone:
    def __init__(self, zone_id: str):
        self.zone_id = zone_id
        self.cards: list[GameCard] = []

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
        _DEFAULT_ZONE_IDS = ["battle", "shield", "deck", "graveyard", "mana", "hand", "temp"]
        self.zones: dict[str, Zone] = {zid: Zone(zid) for zid in _DEFAULT_ZONE_IDS}
        self.current_deck = None
        self.back_image_path: str = ""
        self._undo_stack: deque = deque(maxlen=self._UNDO_LIMIT)

    @classmethod
    def get_instance(cls) -> "GameState":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize_zones(self, zone_ids: list[str]):
        """zone_ids リストに合わせてゾーンを再構築する。game.json ロード後に呼ぶ。"""
        self.zones = {zid: Zone(zid) for zid in zone_ids}
        self._undo_stack.clear()

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
                zid: [gc.to_dict() for gc in zone.cards]
                for zid, zone in self.zones.items()
            }
        }

    def from_dict(self, d: dict):
        for zid in self.zones:
            self.zones[zid].cards.clear()
        for zid, cards in d.get("zones", {}).items():
            if zid in self.zones:
                for gc_dict in cards:
                    self.zones[zid].add_card(GameCard.from_dict(gc_dict))

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
        deck = self.zones.get("deck")
        hand = self.zones.get("hand")
        if not deck or not hand or not deck.cards:
            return False
        self.push_snapshot()
        gc = deck.remove_card(len(deck) - 1)
        if gc:
            gc.face_down = False
            hand.add_card(gc)
            return True
        return False

    def search_deck(self, card_ids: list, dest: str = "hand") -> bool:
        """指定IDのカードを山札から抜き取り dest ゾーンへ移動する。"""
        deck = self.zones.get("deck")
        dest_zone = self.zones.get(dest)
        if not deck or not dest_zone:
            return False
        id_set = set(card_ids)
        targets = [gc for gc in deck.cards if gc.card.id in id_set]
        if not targets:
            return False
        self.push_snapshot()
        for gc in targets:
            deck.cards.remove(gc)
            gc.face_down = False
            dest_zone.add_card(gc)
        return True

    def reset_field(self):
        for zid in ["battle", "shield", "deck", "graveyard", "mana"]:
            if zid in self.zones:
                self.zones[zid].cards.clear()

    def initialize_field(self):
        self.reset_field()
        for zid in ["hand", "temp"]:
            if zid in self.zones:
                self.zones[zid].cards.clear()
        if self.current_deck is None:
            return
        # デッキカードを枚数分展開してシャッフル
        cards: list[GameCard] = []
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
            self.zones["shield"].add_card(gc)
        # 手札5枚
        for gc in cards[5:10]:
            self.zones["hand"].add_card(gc)
        # 残りを山札へ
        for gc in cards[10:]:
            gc.face_down = False
            self.zones["deck"].add_card(gc)
