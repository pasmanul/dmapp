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
    real_zone_ids = [z.id for z in zone_defs if z.source_zone_id is None and z.ui_widget is None]
    gs.initialize_zones(real_zone_ids)

    # ── ウィンドウを生成・表示 ────────────────────────────────────────
    windows = []
    for win_def in win_defs:
        w = GameWindow(win_def, zone_defs, win_defs)
        w.show()
        windows.append(w)

    # ── デッキ復元後に初期化（DM 標準 40 枚デッキ）───────────────────
    if gs.current_deck and gs.current_deck.total_count == 40:
        gs.initialize_field()
        game_signals.zones_updated.emit()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
