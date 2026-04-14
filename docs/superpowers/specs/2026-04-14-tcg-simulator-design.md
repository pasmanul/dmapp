# tcg-simulator 設計ドキュメント

**日付:** 2026-04-14  
**対象:** dmapp → tcg-simulator リポジトリ移行 + 汎用カードゲームアプリ化（v1）

---

## 概要

デュエルマスターズ専用だった `dmapp` を、任意のカードゲームに対応できる汎用シミュレーターに改修する。新リポジトリ `tcg-simulator` を作成し、dmapp を clone してから開始する。

v1 の主目標は **ゾーンの自由配置**（レイアウト編集モード）と **ゾーン定義の汎用化**。DM固有の初期化ルール（シールド5枚・手札5枚）は v2 以降で対応する。

---

## アーキテクチャ

### アプローチ B：コア維持・UI層汎用化

- `ZoneType` enum を廃止し、設定ファイルで動的にゾーンを定義する
- `BoardWindow` / `HandWindow` を廃止し、汎用の `GameWindow` に統一する
- ゾーンの配置は QGridLayout ベースのグリッドスナップ方式（ドラッグで移動）
- 設定は `data/game.json` で管理し、UI からも JSON 直接編集でも変更可能

---

## データモデル

### 変更前（dmapp）

```python
class ZoneType(Enum):
    BATTLE = "battle"
    SHIELD = "shield"
    DECK = "deck"
    GRAVEYARD = "graveyard"
    MANA = "mana"
    HAND = "hand"
    TEMP = "temp"

class GameState:
    zones: Dict[ZoneType, Zone]
```

### 変更後（tcg-simulator）

```python
@dataclass
class GridPos:
    col: int
    row: int
    col_span: int = 1
    row_span: int = 1

@dataclass
class ZoneDefinition:
    id: str              # ユニークID（例: "battle", "hand"）
    name: str            # 表示名（例: "バトルゾーン"）
    window_id: str       # 所属ウィンドウのID
    grid_pos: GridPos    # グリッド上の位置（col, row, col_span, row_span）
    pile_mode: bool = False   # True: 枚数のみ表示（山札）
    hidden: bool = False      # True: 裏面強制表示（非公開ゾーン）
    tappable: bool = False    # True: タップ/アンタップ操作あり
    card_scale: float = 1.0   # カードサイズ倍率

@dataclass
class WindowDefinition:
    id: str
    title: str
    width: int
    height: int
    grid_cols: int
    grid_rows: int

class GameState:
    zones: Dict[str, Zone]        # zone_id → Zone
    zone_defs: List[ZoneDefinition]
    window_defs: List[WindowDefinition]
```

---

## 設定ファイル（data/game.json）

```json
{
  "windows": [
    {
      "id": "board",
      "title": "フィールド（公開）",
      "width": 960,
      "height": 780,
      "grid_cols": 12,
      "grid_rows": 8
    },
    {
      "id": "hand",
      "title": "手札（非公開）",
      "width": 540,
      "height": 720,
      "grid_cols": 6,
      "grid_rows": 10
    }
  ],
  "zones": [
    {
      "id": "battle",
      "name": "バトルゾーン",
      "window_id": "board",
      "grid_pos": { "col": 0, "row": 0, "col_span": 12, "row_span": 3 },
      "tappable": true,
      "card_scale": 1.2
    },
    {
      "id": "shield",
      "name": "シールド",
      "window_id": "board",
      "grid_pos": { "col": 0, "row": 3, "col_span": 4, "row_span": 2 },
      "hidden": true
    },
    {
      "id": "deck",
      "name": "山札",
      "window_id": "board",
      "grid_pos": { "col": 4, "row": 3, "col_span": 2, "row_span": 2 },
      "pile_mode": true
    },
    {
      "id": "graveyard",
      "name": "墓地",
      "window_id": "board",
      "grid_pos": { "col": 6, "row": 3, "col_span": 3, "row_span": 2 }
    },
    {
      "id": "mana",
      "name": "マナゾーン",
      "window_id": "board",
      "grid_pos": { "col": 0, "row": 5, "col_span": 9, "row_span": 3 },
      "tappable": true
    },
    {
      "id": "hand",
      "name": "手札",
      "window_id": "hand",
      "grid_pos": { "col": 0, "row": 0, "col_span": 6, "row_span": 5 },
      "hidden": true
    },
    {
      "id": "temp",
      "name": "保留",
      "window_id": "hand",
      "grid_pos": { "col": 0, "row": 5, "col_span": 6, "row_span": 2 },
      "hidden": true
    }
  ]
}
```

---

## UIコンポーネント

### GameWindow（汎用ウィンドウ）

- `BoardWindow` / `HandWindow` を統合した汎用クラス
- `WindowDefinition` を受け取り、対応する `ZoneDefinition` を `game.json` から取得して `ZoneWidget` を QGridLayout に配置する
- `main.py` が `game.json` を読み込み、`windows` の数だけ `GameWindow` を生成する

### レイアウト編集モード

- メニュー「設定 → レイアウト編集」で ON/OFF 切替
- 編集モード中：
  - 各 ZoneWidget の上部にドラッグハンドルを表示
  - ゾーンをドラッグすると左上角が最近傍グリッドセルにスナップして移動（col_span / row_span はドラッグ中も維持）
  - いずれかのグリッドセルが他のゾーンと重複する位置には移動不可（対象セルを赤ハイライトで通知）
  - 「保存」ボタンで `game.json` に書き込み
- ゲームモード中：通常のカード操作が可能（ドラッグ移動は無効）

### ZoneWidget の変更点

- コンストラクタ引数を `ZoneDefinition` を受け取る形に変更
- `zone_type: ZoneType` → `zone_id: str` に変更
- `_HIDDEN_ZONES` タプルを廃止し、`ZoneDefinition.hidden` フラグで判定
- プライバシー判定ロジックも `hidden` フラグベースに変更

---

## ファイル変更一覧

| ファイル | 変更内容 |
|---|---|
| `models/game_state.py` | `ZoneType` 廃止、`ZoneDefinition` / `WindowDefinition` 追加、`zones` を `Dict[str, Zone]` に変更 |
| `models/layout_config.py` | 新規: `game.json` の読み書きロジック |
| `ui/game_window.py` | 新規: 汎用 `GameWindow`（board / hand 統合） |
| `ui/board_window.py` | 削除 |
| `ui/hand_window.py` | 削除 |
| `ui/zone_widget.py` | `ZoneType` 参照を `zone_id: str` + `ZoneDefinition` に変更 |
| `main.py` | `game.json` 読込 → `GameWindow` 複数生成に変更 |
| `data/game.json` | 新規: DM デフォルト設定（同梱プリセット） |

---

## v1 スコープ

### 含む
- 新リポジトリ `tcg-simulator` 作成（dmapp を clone）
- `ZoneType` enum → 動的 `ZoneDefinition` への移行
- `BoardWindow` / `HandWindow` → `GameWindow` 汎用化
- `game.json` にDMデフォルト設定を同梱
- レイアウト編集モード（グリッドスナップ、保存機能）

### 含まない（v2以降）
- 初期化ルールの汎用化（現在のDM固有ロジックはそのまま維持）
- ゾーン追加・削除・名前変更のUI
- 複数ゲームプリセット（MTG、遊戯王等）
- ウィンドウ追加・削除のUI

---

## 移行・互換性

- 既存の `data/saves/*.json` は zone_type の文字列値（`"battle"` 等）が zone_id と一致するため、既存セーブデータとの後方互換性は保たれる
- `data/decks/*.json` は変更なし
- `.gitignore` に `.superpowers/` を追加する

---

## エラーハンドリング

- `game.json` が存在しない場合：デフォルト設定（DM標準）で起動し、警告を表示
- `game.json` の形式が不正な場合：起動時にエラーダイアログを表示して終了
- レイアウト保存失敗時：警告ダイアログを表示し、変更を破棄する選択肢を提示
