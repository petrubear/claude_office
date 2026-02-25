from enum import Enum, auto


class AgentState(Enum):
    IDLE = auto()
    WANDERING = auto()
    WALKING = auto()
    SITTING = auto()
    WORKING = auto()
    THINKING = auto()
    WAITING = auto()     # needs permission / asking user
    SPAWNING = auto()
    EXITING = auto()
