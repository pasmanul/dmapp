from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class GridPos:
    col: int
    row: int
    col_span: int = 1
    row_span: int = 1


@dataclass
class ZoneDefinition:
    id: str
    name: str
    window_id: str
    grid_pos: GridPos
    visibility: str = "public"   # "public" | "private"
    pile_mode: bool = False
    tappable: bool = False
    card_scale: float = 1.0
    two_row: bool = False        # バトルゾーンの2段レイアウト
    masked: bool = False         # 常に裏面強制表示（同ゾーンの別ビュー用）
    source_zone_id: Optional[str] = None  # 別ゾーンのデータを表示する場合


@dataclass
class WindowDefinition:
    id: str
    title: str
    width: int
    height: int
    grid_cols: int
    grid_rows: int


def load_game_config(path: str) -> tuple[list[WindowDefinition], list[ZoneDefinition]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    windows = [
        WindowDefinition(
            id=w["id"], title=w["title"],
            width=w["width"], height=w["height"],
            grid_cols=w["grid_cols"], grid_rows=w["grid_rows"],
        )
        for w in data["windows"]
    ]

    zones = []
    for z in data["zones"]:
        gp = z["grid_pos"]
        zones.append(ZoneDefinition(
            id=z["id"],
            name=z["name"],
            window_id=z["window_id"],
            grid_pos=GridPos(
                col=gp["col"], row=gp["row"],
                col_span=gp.get("col_span", 1),
                row_span=gp.get("row_span", 1),
            ),
            visibility=z.get("visibility", "public"),
            pile_mode=z.get("pile_mode", False),
            tappable=z.get("tappable", False),
            card_scale=z.get("card_scale", 1.0),
            two_row=z.get("two_row", False),
            masked=z.get("masked", False),
            source_zone_id=z.get("source_zone_id", None),
        ))

    return windows, zones


def save_game_config(path: str, windows: list[WindowDefinition], zones: list[ZoneDefinition]):
    import os
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    data = {
        "windows": [
            {"id": w.id, "title": w.title, "width": w.width, "height": w.height,
             "grid_cols": w.grid_cols, "grid_rows": w.grid_rows}
            for w in windows
        ],
        "zones": [
            {
                "id": z.id, "name": z.name, "window_id": z.window_id,
                "grid_pos": {"col": z.grid_pos.col, "row": z.grid_pos.row,
                             "col_span": z.grid_pos.col_span, "row_span": z.grid_pos.row_span},
                "visibility": z.visibility,
                "pile_mode": z.pile_mode,
                "tappable": z.tappable,
                "card_scale": z.card_scale,
                "two_row": z.two_row,
                "masked": z.masked,
                **({"source_zone_id": z.source_zone_id} if z.source_zone_id else {}),
            }
            for z in zones
        ]
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
