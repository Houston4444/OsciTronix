from enum import Enum

class MidiConnectState(Enum):
    ABSENT_DEVICE = 0
    DISCONNECTED = 1
    INPUT_ONLY = 2
    OUTPUT_ONLY = 3
    CONNECTED = 4
