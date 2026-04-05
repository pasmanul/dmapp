import uuid
from dataclasses import dataclass, field


@dataclass
class Card:
    name: str
    image_path: str
    count: int = 1
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
