# tcg-simulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** dmapp を新リポジトリ tcg-simulator に移行し、ZoneType enum を動的ゾーン定義（game.json）に置き換え、ゾーンのグリッドスナップ自由配置を実装する。

**Architecture:** `ZoneType` enum を廃止して文字列 ID ベースの `ZoneDefinition` に移行。`BoardWindow`/`HandWindow` を汎用 `GameWindow` に統合。`data/game.json` でウィンドウ・ゾーンを定義し、レイアウト編集モードでゾーンをドラッグ→グリッドスナップで再配置できる。

**Tech Stack:** Python 3.12, PyQt6, pytest, pytest-qt

---

## ファイル構成

### 新規作成
| ファイル | 責務 |
|---|---|
| `models/layout_config.py` | `ZoneDefinition`, `WindowDefinition`, `GridPos` dataclass + `game.json` 読み書き |
| `ui/game_window.py` | 汎用ウィンドウ（BoardWindow/HandWindow 統合）|
| `ui/layout_editor.py` | レイアウト編集モード（ドラッグハンドル・グリッドスナップ）|
| `data/game.json` | DM デフォルト設定 |
| `tests/conftest.py` | pytest QApplication フィクスチャ |
| `tests/test_layout_config.py` | layout_config モジュールのユニットテスト |

### 変更
| ファイル | 変更内容 |
|---|---|
| `models/game_state.py` | `ZoneType` 廃止 → `Dict[str, Zone]` |
| `ui/_card_pixmap.py` | `_ZONE_NAMES` を `Dict[str, str]` (zone_id → 名前) に変更 |
| `ui/zone_widget.py` | `zone_type: ZoneType` → `zone_id: str` + `ZoneDefinition` |
| `ui/expand_dialog.py` | `zone_type: ZoneType` → `zone_id: str` |
| `ui/search_dialog.py` | `_DEST_OPTIONS` を zone_id 文字列ベースに変更 |
| `main.py` | game.json 読込 → GameWindow 複数生成 |
| `requirements.txt` | pytest, pytest-qt 追加 |
| `CLAUDE.md` | ディレクトリ構成・アーキテクチャ説明を更新 |

### 削除
- `ui/board_window.py`
- `ui/hand_window.py`

---

## Task 1: 新リポジトリ作成・初期セットアップ

**Files:**
- Modify: `requirements.txt`
- Create: `tests/conftest.py`

- [ ] **Step 1: GitHub に tcg-simulator リポジトリを作成する**

```bash
gh repo create tcg-simulator --public --description "Generic TCG simulator built with PyQt6"
```

- [ ] **Step 2: 既存 dmapp のリモートを変更して push する**

```bash
cd "D:/ユーザー/shoot/ドキュメント/Kiro/dmapp"
git remote add tcg https://github.com/pasmanul/tcg-simulator.git
git push tcg main
```

- [ ] **Step 3: requirements.txt に pytest・pytest-qt を追加する**

```
PyQt6>=6.4.0
pytest>=8.0.0
pytest-qt>=4.4.0
```

- [ ] **Step 4: tests/conftest.py を作成する**

```python
import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app
```

- [ ] **Step 5: インストール確認**

```bash
pip install pytest pytest-qt
pytest --collect-only
```

期待出力: `no tests ran` (エラーなし)

- [ ] **Step 6: コミット**

```bash
git add requirements.txt tests/conftest.py
git commit -m "test: pytest・pytest-qt セットアップ"
```

---

## Task 2: ZoneDefinition データモデル作成

**Files:**
- Create: `models/layout_config.py`
- Create: `tests/test_layout_config.py`

- [ ] **Step 1: テストを書く**

`tests/test_layout_config.py`:

```python
import json
import os
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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_layout_config.py -v
```

期待: `ImportError: cannot import name 'ZoneDefinition'`

- [ ] **Step 3: models/layout_config.py を実装する**

```python
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
```

- [ ] **Step 4: テストを実行して全パスを確認**

```bash
pytest tests/test_layout_config.py -v
```

期待: `4 passed`

- [ ] **Step 5: コミット**

```bash
git add models/layout_config.py tests/test_layout_config.py
git commit -m "feat: ZoneDefinition/WindowDefinition データモデル追加"
```

---

## Task 3: data/game.json デフォルト設定作成

**Files:**
- Create: `data/game.json`

- [ ] **Step 1: data/game.json を作成する**

```json
{
  "windows": [
    {
      "id": "board",
      "title": "フィールド（公開）",
      "width": 960,
      "height": 780,
      "grid_cols": 12,
      "grid_rows": 10
    },
    {
      "id": "hand",
      "title": "手札・デッキ（非公開）",
      "width": 540,
      "height": 720,
      "grid_cols": 6,
      "grid_rows": 12
    }
  ],
  "zones": [
    {
      "id": "battle",
      "name": "バトルゾーン",
      "window_id": "board",
      "grid_pos": {"col": 0, "row": 0, "col_span": 12, "row_span": 4},
      "visibility": "public",
      "tappable": true,
      "card_scale": 1.2,
      "two_row": true
    },
    {
      "id": "shield",
      "name": "シールド",
      "window_id": "board",
      "grid_pos": {"col": 0, "row": 4, "col_span": 4, "row_span": 3},
      "visibility": "private"
    },
    {
      "id": "deck",
      "name": "山札",
      "window_id": "board",
      "grid_pos": {"col": 4, "row": 4, "col_span": 2, "row_span": 3},
      "visibility": "private",
      "pile_mode": true
    },
    {
      "id": "graveyard",
      "name": "墓地",
      "window_id": "board",
      "grid_pos": {"col": 6, "row": 4, "col_span": 3, "row_span": 3},
      "visibility": "public"
    },
    {
      "id": "mana",
      "name": "マナゾーン",
      "window_id": "board",
      "grid_pos": {"col": 0, "row": 7, "col_span": 9, "row_span": 3},
      "visibility": "public",
      "tappable": true
    },
    {
      "id": "hand_view",
      "name": "手札",
      "window_id": "board",
      "grid_pos": {"col": 9, "row": 4, "col_span": 3, "row_span": 6},
      "visibility": "private",
      "masked": true,
      "source_zone_id": "hand"
    },
    {
      "id": "hand",
      "name": "手札",
      "window_id": "hand",
      "grid_pos": {"col": 0, "row": 0, "col_span": 6, "row_span": 5},
      "visibility": "private"
    },
    {
      "id": "temp",
      "name": "保留",
      "window_id": "hand",
      "grid_pos": {"col": 0, "row": 5, "col_span": 6, "row_span": 2},
      "visibility": "private"
    }
  ]
}
```

- [ ] **Step 2: data/game.json が .gitignore 対象外であることを確認**

`.gitignore` に `data/game.json` の除外行がないことを確認する（このファイルはリポジトリに含める）。

- [ ] **Step 3: コミット**

```bash
git add data/game.json
git commit -m "feat: DM デフォルト game.json 追加"
```

---

## Task 4: GameState から ZoneType を除去

**Files:**
- Modify: `models/game_state.py`

- [ ] **Step 1: game_state.py を開いて ZoneType enum の定義を確認する**

`models/game_state.py` の `class ZoneType(Enum)` ブロック（行 12-19）を読む。

- [ ] **Step 2: ZoneType を削除し zones を Dict[str, Zone] に変更する**

`models/game_state.py` の変更:

```python
# 削除: class ZoneType(Enum): ... 全ブロック

# GameState.__init__ を変更:
def __init__(self):
    # zones は game.json ロード後に初期化される。
    # デフォルトは DM 標準ゾーン ID で空ゾーンを用意。
    _DEFAULT_ZONE_IDS = ["battle", "shield", "deck", "graveyard", "mana", "hand", "temp"]
    self.zones: dict[str, Zone] = {zid: Zone(zid) for zid in _DEFAULT_ZONE_IDS}
    self.current_deck = None
    self.back_image_path: str = ""
    self._undo_stack: deque = deque(maxlen=self._UNDO_LIMIT)

# Zone.__init__ を変更:
class Zone:
    def __init__(self, zone_id: str):
        self.zone_id = zone_id   # ZoneType → str
        self.cards: list[GameCard] = []
    # add_card / insert_card / remove_card / __len__ は変更なし

# initialize_zones メソッドを追加（game.json ロード後に呼ぶ）:
def initialize_zones(self, zone_ids: list[str]):
    """zone_ids リストに合わせてゾーンを再構築する。既存データは破棄。"""
    self.zones = {zid: Zone(zid) for zid in zone_ids}

# GameState.to_dict / from_dict を変更:
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

# draw_card を変更（ZoneType.DECK → "deck", ZoneType.HAND → "hand"）:
def draw_card(self) -> bool:
    deck = self.zones.get("deck")
    if not deck or not deck.cards:
        return False
    self.push_snapshot()
    gc = deck.remove_card(len(deck) - 1)
    if gc:
        gc.face_down = False
        self.zones["hand"].add_card(gc)
        return True
    return False

# search_deck を変更:
def search_deck(self, card_ids: list, dest: str = "hand") -> bool:
    deck = self.zones.get("deck")
    if not deck:
        return False
    id_set = set(card_ids)
    targets = [gc for gc in deck.cards if gc.card.id in id_set]
    if not targets:
        return False
    self.push_snapshot()
    for gc in targets:
        deck.cards.remove(gc)
        gc.face_down = False
        self.zones[dest].add_card(gc)
    return True

# reset_field を変更:
def reset_field(self):
    for zid in ["battle", "shield", "deck", "graveyard", "mana"]:
        if zid in self.zones:
            self.zones[zid].cards.clear()

# initialize_field を変更:
def initialize_field(self):
    self.reset_field()
    for zid in ["hand", "temp"]:
        if zid in self.zones:
            self.zones[zid].cards.clear()
    if self.current_deck is None:
        return
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
    for gc in cards[:5]:
        gc.face_down = True
        self.zones["shield"].add_card(gc)
    for gc in cards[5:10]:
        self.zones["hand"].add_card(gc)
    for gc in cards[10:]:
        gc.face_down = False
        self.zones["deck"].add_card(gc)
```

- [ ] **Step 3: from models.game_state import ZoneType の import を全ファイルで検索する**

```bash
grep -rn "ZoneType" --include="*.py" .
```

出力に残っているファイルを記録する（次タスク以降で修正する）。

- [ ] **Step 4: コミット**

```bash
git add models/game_state.py
git commit -m "refactor: GameState ZoneType 廃止 → Dict[str, Zone]"
```

---

## Task 5: _card_pixmap.py の ZoneType 参照を除去

**Files:**
- Modify: `ui/_card_pixmap.py`

- [ ] **Step 1: _card_pixmap.py の _ZONE_NAMES を変更する**

`ui/_card_pixmap.py` の先頭:

```python
# 削除: from models.game_state import ZoneType

# _ZONE_NAMES を Dict[str, str] に変更（zone_id → 表示名）
# デフォルト値は DM 標準。game.json ロード後に update_zone_names() で更新する。
_ZONE_NAMES: dict[str, str] = {
    "battle":    "バトルゾーン",
    "shield":    "シールドゾーン",
    "deck":      "山札",
    "graveyard": "墓地",
    "mana":      "マナゾーン",
    "hand":      "手札",
    "temp":      "保留",
}


def update_zone_names(zone_defs):
    """ZoneDefinition リストから _ZONE_NAMES を再構築する。main.py 起動時に呼ぶ。"""
    _ZONE_NAMES.clear()
    for zd in zone_defs:
        _ZONE_NAMES[zd.id] = zd.name
```

- [ ] **Step 2: コミット**

```bash
git add ui/_card_pixmap.py
git commit -m "refactor: _card_pixmap ZoneType 参照を zone_id 文字列に変更"
```

---

## Task 6: ZoneWidget を zone_id + ZoneDefinition ベースに変更

**Files:**
- Modify: `ui/zone_widget.py`

- [ ] **Step 1: ZoneWidget のコンストラクタシグネチャを変更する**

`ui/zone_widget.py` の `class ZoneWidget` コンストラクタ（現行: `def __init__(self, zone_type: ZoneType, label: str, pile_mode=False, mask_cards=False, card_scale=1.0, parent=None)`）を変更:

```python
from models.layout_config import ZoneDefinition

class ZoneWidget(QFrame):
    TITLE_H = 22

    def __init__(self, zone_def: ZoneDefinition, parent=None):
        super().__init__(parent)
        self.zone_id: str = zone_def.id
        self.zone_def: ZoneDefinition = zone_def
        self.label: str = zone_def.name
        self.pile_mode: bool = zone_def.pile_mode
        # masked: True なら常に裏面表示。source_zone_id があればそちらのデータを描画。
        self._mask: bool = zone_def.masked or (zone_def.visibility == "private")
        self._render_zone_id: str = zone_def.source_zone_id or zone_def.id
        self._cw = int(CARD_W * zone_def.card_scale)
        self._ch = int(CARD_H * zone_def.card_scale)
        # 以下変更なし（_card_positions, _pix_cache 等）
        ...
```

- [ ] **Step 2: `_zone()` メソッドを変更する**

```python
def _zone(self):
    return GameState.get_instance().zones[self._render_zone_id]
```

- [ ] **Step 3: `_calculate_positions()` の ZoneType.BATTLE チェックを変更する**

```python
# Before: if self.zone_type == ZoneType.BATTLE:
# After:
if self.zone_def.two_row:
```

- [ ] **Step 4: `_KEY_ZONE` を zone_id 文字列ベースに変更する**

```python
# Before:
_KEY_ZONE: dict[str, ZoneType] = {}

def _build_key_zone():
    global _KEY_ZONE
    _KEY_ZONE = {
        _kb.get("move_battle"):    ZoneType.BATTLE,
        ...
    }

# After:
_KEY_ZONE: dict[str, str] = {}

def _build_key_zone():
    global _KEY_ZONE
    _KEY_ZONE = {
        _kb.get("move_battle"):    "battle",
        _kb.get("move_mana"):      "mana",
        _kb.get("move_graveyard"): "graveyard",
        _kb.get("move_hand"):      "hand",
        _kb.get("move_shield"):    "shield",
    }
```

- [ ] **Step 5: `_is_log_private()` の _HIDDEN_ZONES チェックを変更する**

`_is_log_private` 内の `_HIDDEN_ZONES` タプル参照を `zone_def.visibility == "private"` に変更する。
具体的にはゾーンの `zone_def` を `GameState.get_instance()` からゾーン定義を引くか、
`ZoneWidget` のコンストラクタ引数から受け取った `zone_def.visibility` を使う。

```python
# zone_widget.py モジュールレベル変数として追加:
_ZONE_DEFS: dict[str, ZoneDefinition] = {}

def register_zone_defs(zone_defs: list[ZoneDefinition]):
    """main.py 起動時に呼ぶ。zone_id → ZoneDefinition のマップを登録する。"""
    _ZONE_DEFS.clear()
    for zd in zone_defs:
        _ZONE_DEFS[zd.id] = zd

def _is_private_zone(zone_id: str) -> bool:
    zd = _ZONE_DEFS.get(zone_id)
    return zd is not None and zd.visibility == "private"
```

`_is_log_private` メソッド内の `dest_type in _HIDDEN_ZONES` を `_is_private_zone(dest_id)` に変更する。

- [ ] **Step 6: MIME ドラッグペイロードの zone_type.value を zone_id に変更する**

zone_widget.py 内のドラッグ開始コード（`"src": self.zone_type.value`）を:
```python
"src": self.zone_id
```
に変更する。ドロップ受け取り側も同様に `ZoneType(data["src"])` を `data["src"]` に変更する。

- [ ] **Step 7: from models.game_state import ZoneType の import を削除する**

```python
# 削除:
from models.game_state import GameCard, GameState, ZoneType
# 追加:
from models.game_state import GameCard, GameState
from models.layout_config import ZoneDefinition
```

- [ ] **Step 8: コミット**

```bash
git add ui/zone_widget.py
git commit -m "refactor: ZoneWidget を zone_id + ZoneDefinition ベースに変更"
```

---

## Task 7: expand_dialog.py と search_dialog.py を更新

**Files:**
- Modify: `ui/expand_dialog.py`
- Modify: `ui/search_dialog.py`

- [ ] **Step 1: expand_dialog.py を変更する**

`expand_dialog.py` の `_CardLabel` と `ExpandDialog` の `zone_type: ZoneType` を `zone_id: str` に変更:

```python
# 削除: from models.game_state import GameCard, GameState, ZoneType
# 追加:
from models.game_state import GameCard, GameState

class _CardLabel(QLabel):
    def __init__(self, gc: GameCard, index: int, zone_id: str, on_remove=None, parent=None):
        super().__init__(parent)
        self.gc = gc
        self.index = index
        self.zone_id = zone_id   # ZoneType → str
        ...

    def _remove(self):
        gs = GameState.get_instance()
        gs.push_snapshot()
        gs.zones[self.zone_id].remove_card(self.index)   # zone_type → zone_id
        game_signals.zones_updated.emit()
        if self._on_remove:
            self._on_remove()

    def mouseMoveEvent(self, event):
        ...
        payload = json.dumps({
            "source_zone": self.zone_id,   # zone_type.value → zone_id
            ...
        })
        ...


class ExpandDialog(QDialog):
    def __init__(self, zone_id: str, label: str, parent=None):
        super().__init__(parent)
        self.zone_id = zone_id   # ZoneType → str
        ...

    def _rebuild(self):
        ...
        zone = GameState.get_instance().zones[self.zone_id]   # zone_type → zone_id
        for i, gc in enumerate(zone.cards):
            lbl = _CardLabel(gc, i, self.zone_id, on_remove=self._rebuild)
            ...
```

- [ ] **Step 2: search_dialog.py を変更する**

`_DEST_OPTIONS` を ZoneType なしに変更:

```python
# 削除: from models.game_state import GameCard, GameState, ZoneType
# 追加:
from models.game_state import GameCard, GameState

# _DEST_OPTIONS を (label, zone_id_str) に変更:
_DEST_OPTIONS = [
    ("手札", "hand"),
    ("保留", "temp"),
    ("マナゾーン", "mana"),
    ("墓地", "graveyard"),
]

# _populate メソッド内:
deck_cards = gs.zones["deck"].cards   # ZoneType.DECK → "deck"

# _confirm メソッド内:
dest_label, dest_zone_id = _DEST_OPTIONS[self._dest_combo.currentIndex()]
if GameState.get_instance().search_deck(selected_ids, dest_zone_id):
    ...
```

- [ ] **Step 3: コミット**

```bash
git add ui/expand_dialog.py ui/search_dialog.py
git commit -m "refactor: expand_dialog・search_dialog の ZoneType を zone_id 文字列に変更"
```

---

## Task 8: GameWindow 作成

**Files:**
- Create: `ui/game_window.py`

GameWindow は game.json の `windows` 配列を1エントリごとにインスタンス化される汎用ウィンドウ。
対応する `zones` を QGridLayout で配置する。
`window_id == "hand"` の場合のみデッキリストパネルを追加する（v1 特殊処理）。

- [ ] **Step 1: ui/game_window.py を作成する**

```python
import json
import os
import random
from datetime import datetime

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QFileDialog, QGridLayout, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from models.card_library import card_sort_key
from models.deck import Deck
from models.game_state import GameState
from models.layout_config import WindowDefinition, ZoneDefinition
from .action_log_widget import ActionLogWidget
from .deck_list_widget import DeckListWidget
from .deck_manager import DeckManagerDialog
from .signals import game_signals
from .theme import MENUBAR_STYLE, WIN_BG, btn_dice, btn_draw, btn_load, btn_reset, btn_shuffle, btn_sort
from .zone_widget import ZoneWidget, rebuild_key_zone
from . import keybindings as kb


_CONFIG_PATH = "data/config.json"


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config(data: dict):
    os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class GameWindow(QMainWindow):
    def __init__(self, win_def: WindowDefinition, zone_defs: list[ZoneDefinition]):
        super().__init__()
        self.win_def = win_def
        # この window に属するゾーン定義（source_zone_id を持つビューゾーンも含む）
        self.zone_defs = [z for z in zone_defs if z.window_id == win_def.id]
        self.zone_widgets: dict[str, ZoneWidget] = {}  # zone_id → ZoneWidget
        self._is_hand_window = (win_def.id == "hand")

        self.setWindowTitle(win_def.title)
        self.resize(win_def.width, win_def.height)
        self.setStyleSheet(f"QMainWindow, QWidget {{ background-color: {WIN_BG}; }}")
        self.menuBar().setStyleSheet(MENUBAR_STYLE)
        self._setup_menu()
        self._setup_ui()
        self._setup_shortcuts()

        if self._is_hand_window:
            self._restore_last_deck()

    # ── UI セットアップ ──────────────────────────────────────────────

    def _setup_menu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("ファイル")
        file_menu.addAction("初期状態にリセット", self._initialize_field)
        file_menu.addSeparator()
        save_action = QAction("試合を保存", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self._save_game)
        file_menu.addAction(save_action)
        file_menu.addAction("試合をロード…", self._load_game)
        undo_action = QAction("アンドゥ", self)
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        undo_action.triggered.connect(self._undo)
        file_menu.addAction(undo_action)
        file_menu.addSeparator()
        file_menu.addAction("デッキ管理を開く", self._open_deck_manager)

        settings_menu = menu.addMenu("設定")
        settings_menu.addAction("キーバインド設定…", self._open_keybinding_settings)
        settings_menu.addAction("レイアウト編集…", self._open_layout_editor)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setSpacing(8)
        outer.setContentsMargins(10, 8, 10, 10)

        # ── ツールバー ──────────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        if not self._is_hand_window:
            dice_btn = QPushButton("ダイス")
            dice_btn.setFixedHeight(28)
            dice_btn.setStyleSheet(btn_dice())
            dice_btn.clicked.connect(self._open_dice)
            toolbar.addWidget(dice_btn)

        toolbar.addStretch()

        reset_btn = QPushButton("初期状態にリセット")
        reset_btn.setFixedHeight(28)
        reset_btn.setStyleSheet(btn_reset())
        reset_btn.clicked.connect(self._initialize_field)
        toolbar.addWidget(reset_btn)
        outer.addLayout(toolbar)

        # ── ゾーングリッド ──────────────────────────────────────────
        grid_container = QWidget()
        self._grid_layout = QGridLayout(grid_container)
        self._grid_layout.setSpacing(4)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)

        for zd in self.zone_defs:
            widget = self._make_zone_widget(zd)
            self.zone_widgets[zd.id] = widget
            gp = zd.grid_pos
            self._grid_layout.addWidget(widget, gp.row, gp.col, gp.row_span, gp.col_span)

        # アクションログ（手札ウィンドウ以外に追加）
        if not self._is_hand_window:
            from .action_log_widget import ActionLogWidget
            self._action_log = ActionLogWidget()
            self._action_log.setMinimumWidth(120)
            self._action_log.setMaximumWidth(180)
            # グリッドの右端に追加（全行span）
            self._grid_layout.addWidget(self._action_log, 0, win_def.grid_cols, win_def.grid_rows, 1)

        outer.addWidget(grid_container, 1)

        # ── 手札ウィンドウ専用: デッキ読み込みパネル ─────────────────
        if self._is_hand_window:
            ctrl = QHBoxLayout()
            self.deck_label = QLabel("デッキ未選択")
            self.deck_label.setStyleSheet("color:#6688aa;font-size:10px;font-family:'Yu Gothic UI';")
            ctrl.addWidget(self.deck_label, 1)
            load_btn = QPushButton("デッキ読み込み")
            load_btn.setFixedHeight(26)
            load_btn.setStyleSheet(btn_load())
            load_btn.clicked.connect(self._load_deck)
            ctrl.addWidget(load_btn)
            mgr_btn = QPushButton("デッキ管理")
            mgr_btn.setFixedHeight(26)
            mgr_btn.setStyleSheet(btn_load())
            mgr_btn.clicked.connect(self._open_deck_manager)
            ctrl.addWidget(mgr_btn)
            outer.insertLayout(0, ctrl)

            deck_list_label = QLabel("デッキカード一覧")
            deck_list_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            deck_list_label.setStyleSheet("color:#7799bb;font-weight:bold;font-family:'Yu Gothic UI';font-size:10px;padding:2px 0;")
            outer.addWidget(deck_list_label)

            self.deck_list = DeckListWidget()
            outer.addWidget(self.deck_list, 1)

    def _make_zone_widget(self, zd: ZoneDefinition) -> ZoneWidget:
        widget = ZoneWidget(zd)

        if zd.tappable:
            self._add_tap_buttons(widget, zd)

        if zd.id == "deck" or (zd.source_zone_id == "deck"):
            self._add_deck_buttons(widget)

        if zd.id == "hand" and self._is_hand_window:
            self._add_hand_buttons(widget)

        return widget

    def _add_tap_buttons(self, zone_widget: ZoneWidget, zd: ZoneDefinition):
        _overlay_style = (
            "QPushButton { background: rgba(10,14,32,210); color: #99bbdd;"
            " border: 1px solid rgba(60,90,140,180); border-radius: 3px;"
            " font-size: 9px; font-family: 'Yu Gothic UI'; padding: 0 4px; }"
            "QPushButton:hover { background: rgba(30,50,100,230); color: #cce0ff; }"
        )
        untap_btn = QPushButton("全解除", zone_widget)
        untap_btn.setFixedSize(44, 18)
        untap_btn.setStyleSheet(_overlay_style)
        untap_btn.clicked.connect(lambda: self._set_all_tap(zd.id, False))

        tap_btn = QPushButton("全タップ", zone_widget)
        tap_btn.setFixedSize(52, 18)
        tap_btn.setStyleSheet(_overlay_style)
        tap_btn.clicked.connect(lambda: self._set_all_tap(zd.id, True))

        if zd.two_row:
            sort_btn = QPushButton("ソート", zone_widget)
            sort_btn.setFixedSize(48, 18)
            sort_btn.setStyleSheet(_overlay_style)
            sort_btn.clicked.connect(self._sort_battle_zone)
        else:
            sort_btn = None

        def reposition():
            w = zone_widget.width()
            untap_btn.move(w - 46, 2)
            tap_btn.move(w - 46 - 54, 2)
            if sort_btn:
                sort_btn.move(w - 46 - 54 - 52, 2)

        zone_widget.installEventFilter(self)
        zone_widget._reposition_tap_btns = reposition
        reposition()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Resize:
            for attr in ('_reposition_tap_btns', '_reposition_deck_btns', '_reposition_hand_btns'):
                if hasattr(obj, attr):
                    getattr(obj, attr)()
        return super().eventFilter(obj, event)

    def _add_deck_buttons(self, zone_widget: ZoneWidget):
        """山札ゾーンにドロー・シャッフルボタンをオーバーレイする。"""
        _btn_style = (
            "QPushButton { background: rgba(10,14,32,210); color: #99bbdd;"
            " border: 1px solid rgba(60,90,140,180); border-radius: 3px;"
            " font-size: 9px; font-family: 'Yu Gothic UI'; padding: 0 4px; }"
            "QPushButton:hover { background: rgba(30,50,100,230); color: #cce0ff; }"
        )
        draw_btn = QPushButton("ドロー", zone_widget)
        draw_btn.setFixedSize(48, 18)
        draw_btn.setStyleSheet(_btn_style)
        draw_btn.clicked.connect(self._draw_card)

        shuffle_btn = QPushButton("シャッフル", zone_widget)
        shuffle_btn.setFixedSize(60, 18)
        shuffle_btn.setStyleSheet(_btn_style)
        shuffle_btn.clicked.connect(self._shuffle_deck)

        def reposition():
            w = zone_widget.width()
            draw_btn.move(w - 50, 2)
            shuffle_btn.move(w - 50 - 62, 2)

        zone_widget.installEventFilter(self)
        zone_widget._reposition_deck_btns = reposition
        reposition()

    def _add_hand_buttons(self, zone_widget: ZoneWidget):
        """手札ゾーンにソートボタンをオーバーレイする。"""
        _btn_style = (
            "QPushButton { background: rgba(10,14,32,210); color: #99bbdd;"
            " border: 1px solid rgba(60,90,140,180); border-radius: 3px;"
            " font-size: 9px; font-family: 'Yu Gothic UI'; padding: 0 4px; }"
            "QPushButton:hover { background: rgba(30,50,100,230); color: #cce0ff; }"
        )
        sort_btn = QPushButton("ソート", zone_widget)
        sort_btn.setFixedSize(44, 18)
        sort_btn.setStyleSheet(_btn_style)
        sort_btn.clicked.connect(self._sort_hand)

        def reposition():
            sort_btn.move(zone_widget.width() - 46, 2)

        zone_widget.installEventFilter(self)
        zone_widget._reposition_hand_btns = reposition
        reposition()

    def _sort_hand(self):
        from models.card_library import card_sort_key
        gs = GameState.get_instance()
        gs.push_snapshot()
        hand = gs.zones.get("hand")
        if hand:
            hand.cards.sort(key=lambda gc: card_sort_key(gc.card))
        game_signals.zones_updated.emit()

    def _setup_shortcuts(self):
        self._reset_action = QAction("ゲームリセット", self)
        self._reset_action.setShortcut(QKeySequence(kb.get("game_reset")))
        self._reset_action.triggered.connect(self._initialize_field)
        self.addAction(self._reset_action)

        self._draw_action = QAction("ドロー", self)
        self._draw_action.setShortcut(QKeySequence(kb.get("draw")))
        self._draw_action.triggered.connect(self._draw_card)
        self.addAction(self._draw_action)

    def _refresh_shortcuts(self):
        self._reset_action.setShortcut(QKeySequence(kb.get("game_reset")))
        self._draw_action.setShortcut(QKeySequence(kb.get("draw")))
        rebuild_key_zone()

    # ── ゲームアクション ─────────────────────────────────────────────

    def _draw_card(self):
        if GameState.get_instance().draw_card():
            game_signals.action_logged.emit("ドロー")
            game_signals.zones_updated.emit()

    def _sort_battle_zone(self):
        gs = GameState.get_instance()
        gs.push_snapshot()
        row0 = sorted([gc for gc in gs.zones["battle"].cards if gc.row == 0],
                      key=lambda gc: card_sort_key(gc.card))
        row1 = sorted([gc for gc in gs.zones["battle"].cards if gc.row == 1],
                      key=lambda gc: card_sort_key(gc.card))
        gs.zones["battle"].cards[:] = row0 + row1
        game_signals.zones_updated.emit()

    def _set_all_tap(self, zone_id: str, tapped: bool):
        gs = GameState.get_instance()
        gs.push_snapshot()
        for gc in gs.zones[zone_id].cards:
            gc.tapped = tapped
        game_signals.zones_updated.emit()

    def _shuffle_deck(self):
        gs = GameState.get_instance()
        deck = gs.zones.get("deck")
        if not deck or not deck.cards:
            return
        gs.push_snapshot()
        random.shuffle(deck.cards)
        game_signals.action_logged.emit("山札をシャッフル")
        game_signals.zones_updated.emit()
        if "deck" in self.zone_widgets:
            self.zone_widgets["deck"].start_shuffle_anim()

    def _initialize_field(self):
        gs = GameState.get_instance()
        msg = (f"「{gs.current_deck.name}」でゲームを開始しますか？\nデッキをシャッフルし、シールド5枚・手札5枚を配ります。"
               if gs.current_deck else "デッキが読み込まれていません。全ゾーンを空にしますか？")
        if QMessageBox.question(self, "確認", msg) != QMessageBox.StandardButton.Yes:
            return
        gs.initialize_field()
        game_signals.action_logged.emit("ゲームを開始")
        game_signals.zones_updated.emit()

    # ── 保存・ロード ─────────────────────────────────────────────────

    def _save_game(self):
        os.makedirs("data/saves", exist_ok=True)
        default = os.path.join("data/saves", datetime.now().strftime("game_%Y%m%d_%H%M%S.json"))
        path, _ = QFileDialog.getSaveFileName(self, "試合を保存", default, "JSON Files (*.json)")
        if not path:
            return
        try:
            GameState.get_instance().save(path)
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"保存失敗: {e}")

    def _load_game(self):
        path, _ = QFileDialog.getOpenFileName(self, "試合をロード", "data/saves", "JSON Files (*.json)")
        if not path:
            return
        gs = GameState.get_instance()
        snapshot = gs.to_dict()
        try:
            gs.load_file(path)
            gs.push_dict(snapshot)
            game_signals.zones_updated.emit()
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"ロード失敗: {e}")

    def _undo(self):
        if GameState.get_instance().undo():
            game_signals.action_logged.emit("アンドゥ")
            game_signals.zones_updated.emit()

    # ── デッキ読み込み（手札ウィンドウ専用）───────────────────────────

    def _load_deck(self):
        path, _ = QFileDialog.getOpenFileName(self, "デッキファイルを選択", "data/decks", "JSON Files (*.json)")
        if not path:
            return
        self._apply_deck(path)

    def _apply_deck(self, path: str):
        try:
            deck = Deck.load(path)
            self.deck_label.setText(deck.name)
            self.deck_list.set_deck(deck)
            gs = GameState.get_instance()
            gs.current_deck = deck
            gs.back_image_path = deck.back_image_path
            game_signals.zones_updated.emit()
            cfg = _load_config()
            cfg["last_deck"] = path
            _save_config(cfg)
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"読み込み失敗: {e}")

    def _restore_last_deck(self):
        path = _load_config().get("last_deck")
        if path and os.path.exists(path):
            self._apply_deck(path)

    # ── ダイアログ ──────────────────────────────────────────────────

    def _open_dice(self):
        from .dice_dialog import DiceDialog
        if not hasattr(self, "_dice_dialog") or not self._dice_dialog.isVisible():
            self._dice_dialog = DiceDialog(self)
            self._dice_dialog.show()
        else:
            self._dice_dialog.raise_()
            self._dice_dialog.activateWindow()

    def _open_keybinding_settings(self):
        from .keybinding_dialog import KeybindingDialog
        dlg = KeybindingDialog(self)
        if dlg.exec():
            self._refresh_shortcuts()

    def _open_deck_manager(self):
        DeckManagerDialog(self).exec()

    def _open_layout_editor(self):
        from .layout_editor import LayoutEditorDialog
        dlg = LayoutEditorDialog(self.win_def, self.zone_defs, self)
        dlg.exec()
```

- [ ] **Step 2: コミット**

```bash
git add ui/game_window.py
git commit -m "feat: 汎用 GameWindow 追加（BoardWindow/HandWindow 統合）"
```

---

## Task 9: main.py を更新

**Files:**
- Modify: `main.py`

- [ ] **Step 1: main.py を書き換える**

```python
import os
import sys


def main():
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

    from PyQt6.QtWidgets import QApplication, QMessageBox

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    from models.game_state import GameState
    from models.layout_config import load_game_config
    from ui._card_pixmap import update_zone_names
    from ui.game_window import GameWindow
    from ui.signals import game_signals
    from ui.zone_widget import register_zone_defs

    # ── game.json 読み込み ──────────────────────────────────────────
    config_path = "data/game.json"
    try:
        win_defs, zone_defs = load_game_config(config_path)
    except FileNotFoundError:
        QMessageBox.critical(None, "エラー", f"{config_path} が見つかりません。")
        sys.exit(1)
    except Exception as e:
        QMessageBox.critical(None, "設定エラー", f"game.json の読み込みに失敗:\n{e}")
        sys.exit(1)

    # ── ゾーン定義を各モジュールに登録 ──────────────────────────────
    register_zone_defs(zone_defs)
    update_zone_names(zone_defs)

    # ── GameState を game.json のゾーン定義で初期化 ─────────────────
    gs = GameState.get_instance()
    # source_zone_id を持つビューゾーンは GameState には持たない
    real_zone_ids = [z.id for z in zone_defs if z.source_zone_id is None]
    gs.initialize_zones(real_zone_ids)

    # ── ウィンドウを生成・表示 ────────────────────────────────────────
    windows = []
    for win_def in win_defs:
        w = GameWindow(win_def, zone_defs)
        w.show()
        windows.append(w)

    # ── デッキ復元後に初期化（DM 標準 40 枚デッキ）───────────────────
    if gs.current_deck and gs.current_deck.total_count == 40:
        gs.initialize_field()
        game_signals.zones_updated.emit()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: アプリを起動して動作確認する**

```bash
python main.py
```

期待: game.json を読み込み、ウィンドウが2つ開く。既存のカード操作（ドロー・ドラッグ）が動作する。

- [ ] **Step 3: コミット**

```bash
git add main.py
git commit -m "feat: main.py を game.json ベースの GameWindow 生成に変更"
```

---

## Task 10: board_window.py・hand_window.py を削除

**Files:**
- Delete: `ui/board_window.py`
- Delete: `ui/hand_window.py`

- [ ] **Step 1: 残っている ZoneType 参照がないか確認する**

```bash
grep -rn "ZoneType\|board_window\|hand_window" --include="*.py" .
```

期待: 0件（main.py と game_window.py 以外に参照がない）

- [ ] **Step 2: ファイルを削除する**

```bash
git rm ui/board_window.py ui/hand_window.py
git commit -m "refactor: BoardWindow・HandWindow を削除（GameWindow に統合済み）"
```

---

## Task 11: レイアウト編集モード実装

**Files:**
- Create: `ui/layout_editor.py`

レイアウト編集ダイアログ。ゾーンをドラッグしてグリッドセルにスナップ移動できる。

- [ ] **Step 1: ui/layout_editor.py を作成する**

```python
from __future__ import annotations
from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from models.layout_config import GridPos, WindowDefinition, ZoneDefinition, save_game_config


class _GridCanvas(QWidget):
    """グリッドとゾーンブロックを描画するキャンバス。ドラッグでゾーンを移動できる。"""

    CELL_COLOR = QColor(40, 40, 60)
    ZONE_COLOR = QColor(60, 90, 140, 200)
    ZONE_HOVER_COLOR = QColor(80, 120, 180, 220)
    CONFLICT_COLOR = QColor(180, 40, 40, 200)
    GRID_LINE_COLOR = QColor(80, 80, 100)

    def __init__(self, win_def: WindowDefinition, zone_defs: list[ZoneDefinition], parent=None):
        super().__init__(parent)
        self.win_def = win_def
        # コピーを持つ（変更はローカルで管理）
        self.zone_defs = [ZoneDefinition(**{k: getattr(z, k) for k in z.__dataclass_fields__}) for z in zone_defs]
        self._drag_zone_id: str | None = None
        self._drag_offset: QPoint = QPoint(0, 0)
        self._hover_col: int = -1
        self._hover_row: int = -1
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

    def _cell_at(self, pos: QPoint) -> tuple[int, int]:
        cw, ch = self._cell_size()
        col = min(max(0, int(pos.x() / cw)), self._cols - 1)
        row = min(max(0, int(pos.y() / ch)), self._rows - 1)
        return col, row

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

    def _check_conflict(self, zone_id: str, new_col: int, new_row: int) -> bool:
        zd = next(z for z in self.zone_defs if z.id == zone_id)
        occupied = self._occupied_cells(zone_id)
        for c in range(new_col, new_col + zd.grid_pos.col_span):
            for r in range(new_row, new_row + zd.grid_pos.row_span):
                if c >= self._cols or r >= self._rows:
                    return True
                if (c, r) in occupied:
                    return True
        return False

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
        for zd in self.zone_defs:
            rect = self._zone_rect(zd)
            is_dragging = (zd.id == self._drag_zone_id)
            color = self.ZONE_HOVER_COLOR if is_dragging else self.ZONE_COLOR
            if is_dragging and self._conflict:
                color = self.CONFLICT_COLOR
            painter.fillRect(rect, color)
            painter.setPen(QPen(QColor(180, 200, 255), 1))
            painter.drawRect(rect)
            painter.setPen(QColor(220, 230, 255))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, zd.name)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position().toPoint()
        for zd in reversed(self.zone_defs):
            if self._zone_rect(zd).contains(pos):
                self._drag_zone_id = zd.id
                rect = self._zone_rect(zd)
                self._drag_offset = pos - rect.topLeft()
                break

    def mouseMoveEvent(self, event):
        if self._drag_zone_id is None:
            return
        pos = event.position().toPoint()
        cw, ch = self._cell_size()
        snap_pos = pos - self._drag_offset
        snap_col = min(max(0, int(snap_pos.x() / cw)), self._cols - 1)
        snap_row = min(max(0, int(snap_pos.y() / ch)), self._rows - 1)
        self._hover_col, self._hover_row = snap_col, snap_row
        self._conflict = self._check_conflict(self._drag_zone_id, snap_col, snap_row)

        zd = next(z for z in self.zone_defs if z.id == self._drag_zone_id)
        zd.grid_pos = GridPos(
            col=snap_col, row=snap_row,
            col_span=zd.grid_pos.col_span,
            row_span=zd.grid_pos.row_span,
        )
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._drag_zone_id and self._conflict:
            # 衝突している場合は元の位置には戻さない（mouseMoveで既に更新済み）
            # ユーザーに通知して直前の位置のままにする
            pass
        self._drag_zone_id = None
        self._conflict = False
        self.update()


class LayoutEditorDialog(QDialog):
    def __init__(self, win_def: WindowDefinition, zone_defs: list[ZoneDefinition], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"レイアウト編集 — {win_def.title}")
        self.resize(700, 500)
        self._win_def = win_def
        self._all_zone_defs = zone_defs  # 全ゾーン（他ウィンドウ含む）

        layout = QVBoxLayout(self)

        self._canvas = _GridCanvas(win_def, [z for z in zone_defs if z.window_id == win_def.id])
        layout.addWidget(self._canvas, 1)

        hint = QLabel("ゾーンをドラッグしてグリッドセルに移動できます。赤色 = 衝突（移動不可）。")
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
        # キャンバスで編集したゾーン定義を全ゾーンリストに反映
        edited = {zd.id: zd for zd in self._canvas.zone_defs}
        merged = [edited.get(z.id, z) for z in self._all_zone_defs]

        # game.json に保存
        from models.layout_config import load_game_config
        win_defs, _ = load_game_config("data/game.json")
        save_game_config("data/game.json", win_defs, merged)

        self.accept()
```

- [ ] **Step 2: アプリを起動してレイアウト編集ダイアログを開く**

```bash
python main.py
```

メニュー「設定 → レイアウト編集…」を開いてゾーンをドラッグできることを確認する。

- [ ] **Step 3: コミット**

```bash
git add ui/layout_editor.py
git commit -m "feat: レイアウト編集モード追加（グリッドスナップ・game.json 保存）"
```

---

## Task 12: テーマ更新（DESIGN.md）

**Files:**
- Modify: `ui/theme.py`

DESIGN.md の Composio インスパイアカラーを PyQt6 QSS に適用する。

- [ ] **Step 1: ui/theme.py を開いて現在の定義を確認する**

`ui/theme.py` を読み、色変数とボタンスタイル関数の定義を確認する。

- [ ] **Step 2: Composio カラートークンを定数に追加する**

`ui/theme.py` の先頭付近に追加（既存の `WIN_BG` 等は置き換え）:

```python
# ── Composio-inspired color tokens ─────────────────────────────────
VOID_BLACK       = "#0f0f0f"   # メインウィンドウ背景
PURE_BLACK       = "#000000"   # ゾーン内部・カード背景
ELECTRIC_CYAN    = "#00ffff"   # アクセント（レイアウト編集ハイライト）
SIGNAL_BLUE      = "#0089ff"   # ボタン border・フォーカス
OCEAN_BLUE       = "#0096ff"   # CTA ボタン border
PURE_WHITE       = "#ffffff"   # 強調テキスト
GHOST_WHITE      = "rgba(255,255,255,0.6)"   # セカンダリテキスト
BORDER_MIST_10   = "rgba(255,255,255,0.10)"  # 標準 border
BORDER_MIST_06   = "rgba(255,255,255,0.06)"  # 微かな区切り

# 後方互換（既存コードが WIN_BG を使用）
WIN_BG = VOID_BLACK
```

- [ ] **Step 3: ゾーンのスタイルを zone_colors() で更新する**

`zone_colors()` 関数（または既存のゾーン色定義）を確認し、
`background: PURE_BLACK` + `border: BORDER_MIST_10` に更新する:

```python
def zone_colors(zone_id: str = "") -> str:
    return (
        f"background-color: {PURE_BLACK};"
        f"border: 1px solid {BORDER_MIST_10};"
        "border-radius: 4px;"
    )
```

- [ ] **Step 4: 起動して視覚的に確認する**

```bash
python main.py
```

ウィンドウ背景・ゾーン背景が Composio テーマになっていることを確認。

- [ ] **Step 5: コミット**

```bash
git add ui/theme.py
git commit -m "style: Composio インスパイアカラートークンをテーマに適用"
```

---

## Task 13: CLAUDE.md 更新と最終確認

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: 全テストを実行する**

```bash
pytest -v
```

期待: 全テストが PASS。

- [ ] **Step 2: アプリを起動して主要操作を確認する**

```bash
python main.py
```

確認項目:
- ゲーム起動 → 2ウィンドウが開く
- デッキ読み込み → ゲーム開始
- カードのドラッグ移動（手札→バトル、バトル→マナ等）
- タップ/アンタップ
- ドロー・シャッフル
- アンドゥ（Ctrl+Z）
- サーチダイアログ
- レイアウト編集 → ゾーン移動 → 保存 → 再起動後に反映されている

- [ ] **Step 3: CLAUDE.md の ZoneType・BoardWindow・HandWindow 記述を更新する**

CLAUDE.md 内:
- `ZoneType(Enum)` → `ZoneDefinition` + `game.json` の説明に変更
- `board_window.py` / `hand_window.py` → `game_window.py` に変更
- `models/layout_config.py`, `ui/layout_editor.py` を新規ファイルとして追記

- [ ] **Step 4: 最終コミット**

```bash
git add CLAUDE.md
git commit -m "docs: CLAUDE.md をリファクタリング後の構成に更新"
```

- [ ] **Step 5: tcg-simulator リモートに push する**

```bash
git push tcg main
```
