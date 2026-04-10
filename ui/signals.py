from PyQt6.QtCore import QObject, pyqtSignal


class GameSignals(QObject):
    zones_updated = pyqtSignal()
    action_logged = pyqtSignal(str)


game_signals = GameSignals()
