import os
import sys


def main():
    # Ensure working directory is the project root
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    from models.game_state import GameState
    from ui.board_window import BoardWindow
    from ui.hand_window import HandWindow
    from ui.signals import game_signals

    board = BoardWindow()
    board.show()

    hand = HandWindow()
    hand.show()

    # デッキ復元後に40枚デッキがあれば自動で初期状態にする
    gs = GameState.get_instance()
    if gs.current_deck and gs.current_deck.total_count == 40:
        gs.initialize_field()
        game_signals.zones_updated.emit()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
