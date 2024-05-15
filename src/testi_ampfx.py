envoi = [240, 66, 48, 0, 1, 52, 101, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 24, 23, 19, 0, 0, 0, 0, 0, 0, 30, 60, 1, 0, 0, 0, 0, 1, 0, 50, 0, 67, 32, 57, 1, 0, 0, 0, 72, 0, 0, 50, 77, 0, 1, 35, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 75, 45, 0, 36, 25, 0, 247]

probab = [240, 66, 48, 0, 1, 52, 101, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 24, 23, 19, 0, 0, 0, 0, 0, 0, 38, 56, 1, 1, 0, 1, 2, 1, 0, 50, 0, 67, 32, 57, 1, 0, 0, 0, 72, 0, 0, 50, 77, 0, 1, 35, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 75, 45, 0, 36, 25, 0, 247]

poroae = [240, 66, 48, 0, 1, 52, 101, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 24, 23, 19, 0, 0, 0, 0, 0, 0, 38, 56, 1, 1, 16, 1, 2, 1, 1, 74, 1, 90, 32, 36, 50, 0, 0, 2, 104, 3, 0, 50, 50, 50, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 75, 77, 0, 16, 9, 0, 247]

"""
SYSEX_BEGIN
code AMPFX 0x65 (101)
0
ampfx number (1, 2, 3)
19 x 0
nr_sens
23 (effect status ? Non ! toujours 23)
amp_model
6x0
Presence/Tone
Resonance
BRIGHT_CAP
LOW_CUT ?
clé 16
MID_BOOST ?
BIAS_SHIFT ?
CLASS ?
Pedal1_type (comp) 
    sens }
    0    }
    LEVEL
    cle 32
    ATTACK
    VOICE
    unused comp
    unused comp
Pedal2Type (flanger) (ou 0)
    speed }
    big_v }
    0
    DEPTH
    MANUAL
    LOW_CUT
    HIGH_CUT
    Resonance
10x0
ReverbType (room) (ou 0)
    MIX
    TIME
    PRE_DELAY
    LOW_DAMP
    HIGH_DAMP
0
247
"""