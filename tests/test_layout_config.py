import json
import pytest
from models.layout_config import ZoneDefinition, WindowDefinition, GridPos, load_game_config, save_game_config


def test_grid_pos_defaults():
    gp = GridPos(col=0, row=1)
    assert gp.col_span == 1
    assert gp.row_span == 1


def test_zone_definition_defaults():
    zd = ZoneDefinition(id="battle", name="バトルゾーン", window_id="board",
                        grid_pos=GridPos(col=0, row=0, col_span=12, row_span=3))
    assert zd.visibility == "public"
    assert zd.pile_mode is False
    assert zd.tappable is False
    assert zd.card_scale == 1.0
    assert zd.two_row is False
    assert zd.masked is False
    assert zd.source_zone_id is None


def test_load_game_config(tmp_path):
    config = {
        "windows": [
            {"id": "board", "title": "フィールド", "width": 960, "height": 780,
             "grid_cols": 12, "grid_rows": 8}
        ],
        "zones": [
            {"id": "battle", "name": "バトルゾーン", "window_id": "board",
             "grid_pos": {"col": 0, "row": 0, "col_span": 12, "row_span": 3},
             "visibility": "public", "tappable": True, "card_scale": 1.2,
             "two_row": True}
        ]
    }
    path = tmp_path / "game.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    windows, zones = load_game_config(str(path))

    assert len(windows) == 1
    assert windows[0].id == "board"
    assert windows[0].grid_cols == 12
    assert len(zones) == 1
    assert zones[0].id == "battle"
    assert zones[0].tappable is True
    assert zones[0].two_row is True
    assert zones[0].grid_pos.col_span == 12


def test_save_and_reload_game_config(tmp_path):
    windows = [WindowDefinition(id="board", title="フィールド", width=960, height=780,
                                grid_cols=12, grid_rows=8)]
    zones = [ZoneDefinition(id="mana", name="マナ", window_id="board",
                            grid_pos=GridPos(col=0, row=5, col_span=9, row_span=3),
                            tappable=True)]
    path = str(tmp_path / "out.json")
    save_game_config(path, windows, zones)

    w2, z2 = load_game_config(path)
    assert z2[0].id == "mana"
    assert z2[0].tappable is True
    assert z2[0].grid_pos.col == 0
