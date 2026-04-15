from PyQt6.QtCore import QObject, pyqtSignal


class GameSignals(QObject):
    zones_updated = pyqtSignal()
    action_logged = pyqtSignal(str)
    layout_updated = pyqtSignal(list)


game_signals = GameSignals()
