from enum import Enum, auto

class Menu(Enum):
    HOME = auto()

    # Display on local machine
    RECORD = auto()
    PLAY = auto()
    LIVE = auto()
    ADJUST = auto()

    # Pop up windows at remote client
    REMOTE_RECORD = auto()
    REMOTE_LIVE = auto()
    REMOTE_PLAY = auto()
    REMOTE_ADJUST = auto()

    # No GUI
    HEADLESS_RECORD = auto()
    HEADLESS_LIVE = auto()

    def __str__(self):
        return self.name.replace("_", " ").title()
    