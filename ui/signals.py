from PyQt6.QtCore import QObject, pyqtSignal


class GameSignals(QObject):
    zones_updated = pyqtSignal()


game_signals = GameSignals()
