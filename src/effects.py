
from enum import Enum, Flag
import logging


_logger = logging.getLogger(__name__)

# Internal Tools ----------------------------------------------

class EffParam(Enum):
    def range_unit(self) -> tuple[int, int, str]:
        return (0, 100, '%')

    def display_name(self) -> str:
        return ' '.join([s.capitalize() for s in self.name.split('_')])


class DummyParam(EffParam):
    DUMMY = 0


class VoxIndex(Enum):
    ERROR = -1
    PROGRAM = 0
    NR_SENS = 1
    EFFECT_STATUS = 2
    EFFECT_MODEL = 3
    AMP = 4
    PEDAL1 = 5
    PEDAL2 = 6
    REVERB = 8
    
    @classmethod
    def _missing_(cls, value: int) -> 'VoxIndex':
        _logger.error(f'Trying to access to a missing VoxIndex {value}')
        return VoxIndex.ERROR
    

class EffectStatus(Flag):
    ALL_OFF = 0x00
    PEDAL1_ON = 0x02
    PEDAL2_ON = 0x04
    REVERB_ON = 0x10


class EffectOnOff(EffParam):
    AMP = 0
    PEDAL1 = 1
    PEDAL2 = 2
    REVERB = 4

    def range_unit(self) -> tuple[int, int, str]:
        return (0, 1, '')

# AMP ---------------------------------------------------------

class AmpModel(Enum):
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


class AmpParam(EffParam):
    GAIN = 0
    TREBLE = 1
    MIDDLE = 2
    BASS = 3
    VOLUME = 4
    TONE = 5
    RESONANCE = 6
    BRIGHT_CAP = 7
    LOW_CUT = 8
    MID_BOOST = 9
    BIAS_SHIFT = 10
    CLASS = 11
    
    def range_unit(self) -> tuple[int, int, str]:
        if self is AmpParam.BIAS_SHIFT:
            return (0, 2, 'Off,COLD,HOT')
        if self in (AmpParam.BRIGHT_CAP, AmpParam.LOW_CUT,
                    AmpParam.MID_BOOST, AmpParam.CLASS):
            return (0, 1, '')
        return (0, 100, '%')

# PEDAL 1 -----------------------------------------------------

class Pedal1Type(Enum):
    # COMP
    COMP = 0
    
    # CHORUS
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
    
    def index_prefix(self) -> int:
        return 5
    
    def param_type(self) -> EffParam:
        if self is Pedal1Type.COMP:
            return CompParam
        if self is Pedal1Type.CHORUS:
            return ChorusParam
        if self in (Pedal1Type.TUBE_OD, Pedal1Type.GOLD_DRIVE,
                    Pedal1Type.TREBLE_BOOST, Pedal1Type.RC_TURBO):
            return OverdriveParam
        return DistortionParam


class CompParam(EffParam):
    SENS = 0
    LEVEL = 1
    ATTACK = 2
    VOICE = 3
    UNUSED_1 = 4
    UNUSED_2 = 5
    
    def range_unit(self) -> tuple[int, int, str]:
        if self is CompParam.VOICE:
            return (0, 2, '')
        return (0, 100, '%')
    
    def display_name(self) -> str:
        if self in (CompParam.UNUSED_1, CompParam.UNUSED_2):
            return ''
        return super().display_name()


class ChorusParam(EffParam):
    SPEED = 0
    DEPTH = 1
    MANUAL = 2
    MIX = 3
    LOW_CUT = 4
    HIGH_CUT = 5
    
    def range_unit(self) -> tuple[int, int, str]:
        if self is ChorusParam.SPEED:
            return (100, 10000, 'Hz')        
        if self in (ChorusParam.LOW_CUT, ChorusParam.HIGH_CUT):
            return (0, 1, '')
        return (0, 100, '%')
    
    
class OverdriveParam(EffParam):
    DRIVE = 0
    TONE = 1
    LEVEL = 2
    TREBLE = 3
    MIDDLE = 4
    BASS = 5
        
    
class DistortionParam(EffParam):
    DRIVE = 0
    TONE = 1
    LEVEL = 2
    TREBLE = 3
    MIDDLE = 4
    BASS = 5
    
# PEDAL 2 -----------------------------------------------------

class Pedal2Type(Enum):
    # FLANGER
    FLANGER = 0
    
    # PHASER
    BLACK = 1
    ORANGE_1 = 2
    ORANGE_2 = 3

    # TREMOLO    
    TREMOLO = 4

    # DELAY
    TAPE_ECHO = 5
    ANALOG_DELAY = 6
    
    def index_prefix(self) -> int:
        return 6
    
    def param_type(self) -> EffParam:
        if self is Pedal2Type.FLANGER:
            return FlangerParam
        if self in (Pedal2Type.BLACK,
                    Pedal2Type.ORANGE_1,
                    Pedal2Type.ORANGE_2):
            return PhaserParam
        if self is Pedal2Type.TREMOLO:
            return TremoloParam
        return DelayParam


class FlangerParam(EffParam):
    SPEED = 0
    DEPTH = 1
    MANUAL = 2
    LOW_CUT = 3
    HIGH_CUT = 4
    RESONANCE = 5
    
    def range_unit(self) -> tuple[int, int, str]:
        if self is FlangerParam.SPEED:
            return (100, 5000, 'Hz')
        if self in (FlangerParam.LOW_CUT, FlangerParam.HIGH_CUT):
            return (0, 1, '')
        return (0, 100, '%')
    

class PhaserParam(EffParam):
    SPEED = 0
    RESONANCE = 1
    MANUAL = 2
    DEPTH = 3
    UNUSED_1 = 4
    UNUSED_2 = 5
      
    def range_unit(self) -> tuple[int, int, str]:
        if self is PhaserParam.SPEED:
            return (100, 10000, 'Hz')
        return (0, 100, '%')
    
    def display_name(self) -> str:
        if self in (self.UNUSED_1, self.UNUSED_2):
            return ''
        return super().display_name()
    

class TremoloParam(EffParam):
    SPEED = 0
    DEPTH = 1
    DUTY = 2
    SHAPE = 3
    LEVEL = 4
    UNUSED_1 = 5
    
    def range_unit(self) -> tuple[int, int, str]:
        if self is TremoloParam.SPEED:
            return (1650, 10000, 'Hz')
        return (0, 100, '%')
    
    def display_name(self) -> str:
        if self is self.UNUSED_1:
            return ''
        return super().display_name()

class DelayParam(EffParam):
    TIME = 0
    LEVEL = 1
    FEEDBACK = 2
    TONE = 3
    MOD_SPEED = 4
    MOD_DEPTH = 5
    
    def range_unit(self) -> tuple[int, int, str]:
        if self is DelayParam.TIME:
            return (30, 1200, 'ms')
        return (0, 100, '%')
    
# REVERB ------------------------------------------------------

class ReverbType(Enum):
    ROOM = 0
    SPRING = 1
    HALL = 2
    PLATE = 3
    
    def index_prefix(self) -> int:
        return 8
    
    def param_type(self) -> EffParam:
        return ReverbParam


class ReverbParam(EffParam):
    MIX = 0
    TIME = 1
    PRE_DELAY = 2
    LOW_DAMP = 3
    HIGH_DAMP = 4
    
    def range_unit(self) -> tuple[int, int, str]:
        if self is ReverbParam.PRE_DELAY:
            return (0, 70, 'ms')
        return (0, 100, '%')

    