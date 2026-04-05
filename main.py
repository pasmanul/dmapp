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

    GameState.get_instance().initialize_field()

    board = BoardWindow()
    board.show()

    hand = HandWindow()
    hand.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
