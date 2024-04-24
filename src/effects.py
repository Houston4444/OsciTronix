
from enum import IntEnum


class AmpModel(IntEnum):
    DELUXE_CL_VIBRATO = 0
    DELUXE_CL_NORMAL = 1
    TWEED_4X10_BRIGHT = 2
    TWEED_4X10_NORMAL = 3
    BOUTIQUE_CL = 4
    BOUTIQUE_OD = 5
    VOX_AC30 = 6
    VOX_AC30TB = 7
    BRIT_1959_TREBLE = 8
    BRIT_1959_NORMAL = 9
    BRIT_800 = 10
    BRIT_VM = 11
    SL_OD = 12
    DOUBLE_REC = 13
    CALI_ELATION = 14
    ERUPT_III_CH2 = 15
    ERUPT_III_CH3 = 16
    BOUTIQUE_METAL = 17
    BRIT_OR_MKII = 18
    ORIGINAL_CL = 19
    
    def presence_is_tone(self) -> bool:
        return self in (AmpModel.VOX_AC30, AmpModel.VOX_AC30TB)
    
    def has_bright_cap(self) -> bool:
        return self not in (
            AmpModel.DELUXE_CL_NORMAL,
            AmpModel.TWEED_4X10_NORMAL,
            AmpModel.BRIT_1959_NORMAL,
            AmpModel.ERUPT_III_CH2,
            AmpModel.BOUTIQUE_METAL
        )


class Pedal1Type(IntEnum):
    COMP = 0
    CHORUS = 1
    
    # OVERDRIVE
    TUBE_OD = 2
    GOLD_DRIVE = 3
    TREBLE_BOOST = 4
    RC_TURBO = 5
    
    #DISTORTION
    ORANGE_DIST = 6
    FAT_DIST = 7
    BRIT_LEAD = 8
    FUZZ = 9
    
    def is_comp(self) -> bool:
        return self is Pedal1Type.COMP

    def is_chorus(self) -> bool:
        return self is Pedal1Type.CHORUS
    
    def is_overdrive(self) -> bool:
        return self in (
            Pedal1Type.TUBE_OD,
            Pedal1Type.GOLD_DRIVE,
            Pedal1Type.TREBLE_BOOST,
            Pedal1Type.RC_TURBO
        )
    
    def is_distortion(self) -> bool:
        return self in (
            Pedal1Type.ORANGE_DIST,
            Pedal1Type.FAT_DIST,
            Pedal1Type.BRIT_LEAD,
            Pedal1Type.FUZZ
        )


class CompParams(IntEnum):
    SENS = 0
    LEVEL = 1
    ATTACK = 2
    VOICE = 3
    
    def range(self) -> tuple[int, int]:
        if self is CompParams.VOICE:
            return (0, 2)
        return (0, 100)
    

class ChorusParams(IntEnum):
    SPEED = 0
    DEPTH = 1
    MANUAL = 2
    MIX = 3
    LOW_CUT = 4
    HIGH_CUT = 5
    
    def range(self) -> tuple[int, int]:
        if self is ChorusParams.SPEED:
            return (100, 10000)        
        if self in (ChorusParams.LOW_CUT, ChorusParams.HIGH_CUT):
            return (0, 1)
        return (0, 100)
    
    
class OverdriveParam(IntEnum):
    DRIVE = 0
    TONE = 1
    LEVEL = 2
    TREBLE = 3
    MIDDLE = 4
    BASS = 5
    
    def range(self) -> tuple[int, int]:
        return (0, 100)
    
    
class DistortionParam(IntEnum):
    DRIVE = 0
    TONE = 1
    LEVEL = 2
    TREBLE = 3
    MIDDLE = 4
    BASS = 5
    
    def range(self) -> tuple[int, int]:
        return (0, 100)