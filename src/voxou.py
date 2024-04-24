from enum import IntEnum
import logging
from typing import Optional
from mentat import Module

from effects import Pedal1Type

_logger = logging.getLogger(__name__)


class FunctionCode(IntEnum):
    MODE_REQUEST = 0x12
    CURRENT_PROGRAM_DATA_DUMP_REQUEST = 0x10
    PROGRAM_DATA_DUMP_REQUEST = 0x1c
    CUSTOM_AMPFX_DATA_DUMP_REQUEST = 0x31
    PROGRAM_WRITE_REQUEST = 0x11
    MODE_DATA = 0x42
    CURRENT_PROGRAM_DATA_DUMP = 0x40
    PROGRAM_DATA_DUMP = 0x4c
    CUSTOM_AMPFX_DATA_DUMP = 0x65
    MODE_CHANGE = 0x4e
    PARAMETER_CHANGE = 0x41
    DATA_FORMAT_ERROR = 0x26
    DATA_LOAD_COMPLETED = 0x23
    DATA_LOAD_ERROR = 0x24
    WRITE_COMPLETED = 0x21
    WRITE_ERROR = 0x22


class ParamIndex(IntEnum):
    NR_SENS = 26
    EFFECTS = 27 # (2)
    AMP_MODEL = 28
    GAIN = 29
    TREBLE = 30
    MIDDLE = 32
    BASS = 33
    VOLUME = 34
    TONE = 35
    RESONANCE = 36
    BRIGHT_CAP = 37
    LOW_CUT = 38
    MID_BOOST = 40
    BIAS_SHIFT = 41
    CLASS = 42
    EFFECT2_SOMETHING = 47 #(32 -> 0)
    EFFECT2_TYPE = 52
    TREMOLO_SPEED_MINOR = 53
    TREMOLO_SPEED_MAJOR = 54
    TREMOLO_DEPTH = 56
    TREMOLO_DUTY = 57
    TREMOLO_SHAPE = 58
    TREMOLO_LEVEL = 59
    REVERB_TYPE = 70
    REVERB_MIX = 72
    REVERB_TIME = 73
    REVERB_PREDELAY = 74
    REVERB_LOW_DAMP = 75
    REVERB_HIGH_DAMP = 76


class AmpFader(IntEnum):
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


class ReverbType(IntEnum):
    ROOM = 0
    SPRING = 1
    HALL = 2
    PLATE = 3
    

class ReverbParam(IntEnum):
    MIX = 0
    TIME = 1
    PREDELAY = 2
    LOW_DAMP = 3
    HIGH_DAMP = 4


AMP_FADER_LINK = {
    AmpFader.GAIN: ParamIndex.GAIN,
    AmpFader.TREBLE: ParamIndex.TREBLE,
    AmpFader.MIDDLE: ParamIndex.MIDDLE,
    AmpFader.BASS: ParamIndex.BASS,
    AmpFader.VOLUME: ParamIndex.VOLUME,
    AmpFader.TONE: ParamIndex.TONE,
    AmpFader.RESONANCE: ParamIndex.RESONANCE,
    AmpFader.BRIGHT_CAP: ParamIndex.BRIGHT_CAP,
    AmpFader.LOW_CUT: ParamIndex.LOW_CUT,
    AmpFader.MID_BOOST: ParamIndex.MID_BOOST,
    AmpFader.BIAS_SHIFT: ParamIndex.BIAS_SHIFT,
    AmpFader.CLASS: ParamIndex.CLASS
}

REVERB_PARAM_LINK = {
    ReverbParam.MIX: ParamIndex.REVERB_MIX,
    ReverbParam.TIME: ParamIndex.REVERB_TIME,
    ReverbParam.PREDELAY: ParamIndex.REVERB_PREDELAY,
    ReverbParam.LOW_DAMP: ParamIndex.REVERB_LOW_DAMP,
    ReverbParam.HIGH_DAMP: ParamIndex.REVERB_HIGH_DAMP
}

SYSEX_BEGIN = [240, 66, 48, 0, 1, 52]


class VoxProgram:
    def __init__(self):
        self.program_name = ''
        self.nr_sens = 0
        self.effect_status = 0
        self.amp_model = 0
        self.amp_faders = dict[AmpFader, int]()
        self.pedal1_type = 0
        self.pedal1_params = list[int]()
        self.pedal2_type = 0
        self.pedal2_params = list[int]()
        self.reverb_type = 0
        self.reverb_params = list[int]()

    def read_data(self, shargs: list[int]):
        program_name_ints, shargs = shargs[:16], shargs[16:]
        self.program_name = ''.join([chr(p) for p in program_name_ints])
        
        # 3 not documented numbers
        shargs = shargs[3:]
        
        self.nr_sens = shargs.pop(0)
        self.effects_status = shargs.pop(0)
        self.amp_model = shargs.pop(0)

        amp_params = self.amp_faders
        amp_params[AmpFader.GAIN] = shargs.pop(0)
        amp_params[AmpFader.TREBLE] = shargs.pop(0)
        
        # undocumented number
        unused = shargs.pop(0)
        
        amp_params[AmpFader.MIDDLE] = shargs.pop(0)
        amp_params[AmpFader.BASS] = shargs.pop(0)
        amp_params[AmpFader.VOLUME] = shargs.pop(0)
        amp_params[AmpFader.TONE] = shargs.pop(0)
        amp_params[AmpFader.RESONANCE] = shargs.pop(0)
        amp_params[AmpFader.BRIGHT_CAP] = shargs.pop(0)
        amp_params[AmpFader.LOW_CUT] = shargs.pop(0)
        
        # undocumented number
        unused = shargs.pop(0)
        
        amp_params[AmpFader.MID_BOOST] = shargs.pop(0)
        amp_params[AmpFader.BIAS_SHIFT] = shargs.pop(0)
        amp_params[AmpFader.CLASS] = shargs.pop(0)
        
        self.pedal1_type = shargs.pop(0)
        self.pedal1_params, shargs = shargs[:7], shargs[7:]
        print('Pedal type', Pedal1Type(self.pedal1_type).name)
        print('prefv', self.pedal1_params)
        
        # undocumented number
        unused = shargs.pop(0)
        
        self.pedal2_type = shargs.pop(0)
        self.pedal2_params, shargs = shargs[:7], shargs[7:]
        
        # 8 documented reserved numbers + 2 undocumented
        shargs = shargs[10:]
                    
        self.reverb_type = shargs.pop(0)
        self.reverb_params, shargs = shargs[:6], shargs[6:]
    

class Voxou(Module):
    def __init__(self, name: str,
                 protocol: Optional[str] = None,
                 port: int|str|None = None,
                 parent=None):
        super().__init__(name, protocol=protocol, port=port, parent=parent)
        self.rems_banks = dict[int, list[int]]()
        self.rems_user_presets = dict[int, list[int]]()
        self.rems_states = list[int]()
        self.states = dict[ParamIndex, int]()

        self.current_program = VoxProgram()

        self.program_name = ''
        self.nr_sens = 0
        self.effect_status = 0
        self.amp_model = 0
        self.amp_faders = dict[AmpFader, int]()
        self.reverb_type = ReverbType.ROOM
        
        self.reverb_params = dict[ReverbParam, int]()
        
        self.solo = False
    
    def _send_vox(self, *args):
        self.send('/sysex', *(SYSEX_BEGIN + list(args) + [247]))
    
    def ask_connection(self):
        for bank_n in range(8):
            self._send_vox(28, 0, bank_n)

        self._send_vox(16)
        
        for user_preset_n in range(4):
            self._send_vox(49, 0, user_preset_n)

    def route(self, address, args: list):
        if address == '/note_on':
            chn, note, velo = args
            if note == 36:
                print('ask connection', args)
                self.ask_connection()
            elif note == 35:
                if self.solo:
                    self.set_normal()
                else:
                    self.set_solo()
                self.solo = not self.solo
        
        if address != '/sysex':
            return
        
        shargs = args.copy()
        header, shargs = shargs[:6], shargs[6:]
        
        if header != SYSEX_BEGIN:
            header_str = ', '.join([hex(h)[2:] for h in header])
            _logger.info(
                'Message received sysex message not coming from valvetronix'
                f' with header ({header_str})')
            return
        
        function_code = shargs.pop(0)
        try:
            function_code = FunctionCode(function_code)
        except:
            _logger.error(f'Received Unknown function code {hex(function_code)}')
            return
        
        if function_code is FunctionCode.CURRENT_PROGRAM_DATA_DUMP:
            self.current_program.read_data(shargs)
            
            
        
        if args[:8] == [240, 66, 48, 0, 1, 52, 76, 0]:
            # probablement BANKS
            num = args[8]
            print('ok je voisss', num)
            rem_list = self.rems_banks.get(num)
            if rem_list is not None and rem_list != args:
                print('ah une diff', num)
                print('nannni', rem_list)
                print('nakkou', args)
            self.rems_banks[num] = args
            
        elif args[:8] == [240, 66, 48, 0, 1, 52, 101, 0]:
            # probablement USER PRESET
            num = args[8]
            print('ok ko voisss', num)
            rem_list = self.rems_user_presets.get(num)
            if rem_list is not None:
                print('sso', rem_list == args)
                if rem_list != args:
                    print('ah une diff', num)
                    print('nannni', rem_list)
                    print('nakkou', args)
            self.rems_user_presets[num] = args.copy()
        
        elif args[:8] == [240, 66, 48, 0, 1, 52, 64, 0]:
            rem_list = self.rems_states
            if rem_list:
                print('ezoak', args == rem_list)
                if args != rem_list:
                    print('une diff dans le 64')
                    for i in range(len(args)):
                        if args[i] != rem_list[i]:
                            print('diffici', i, ':', rem_list[i], '->', args[i])

            for param_index in ParamIndex:
                self.states[param_index] = args[param_index.value]
                for amp_fader, pam_id in AMP_FADER_LINK.items():
                    if pam_id is param_index:
                        self.amp_faders[amp_fader] = args[param_index.value]
                        break
                else:
                    for rev_param, pam_id in REVERB_PARAM_LINK.items():
                        if pam_id is param_index:
                            self.reverb_params[rev_param] = args[param_index.value]
                            break

                print('koz', param_index.name, ':', self.states[param_index])
            self.rems_states = args.copy()
            
        elif args[:7] == [240, 66, 48, 0, 1, 52, 65]:
            if args[7] == 4:
                try:
                    amp_fader = AmpFader(args[8])
                except:
                    print('amp fader non géré', args[8], args[9])

                self.amp_faders[amp_fader] = args[9]
        else:
            print('schil', address, args)
    
    def set_amp_model(self, amp_model: int):
        if amp_model == self.amp_model or not 0 <= amp_model <= 13:
            return
        
        self._send_vox(65, 3, 0, amp_model, 0)
    
    def set_amp_fader(self, amp_fader: AmpFader, value: int):
        self._send_vox(65, 4, amp_fader.value, value, 0)
    
    def set_reverb_type(self, reverb_type: ReverbType):
        if reverb_type is self.reverb_type:
            return
        self._send_vox(65, 3, 4, reverb_type.value, 0)
    
    def set_reverb_on_off(self, onoff: bool|int):
        self._send_vox(65, 2, 4, 1 if onoff else 0, 0)
    
    def set_reverb_param(self, reverb_param: ReverbParam, value: int):
        self._send_vox(65, 8, reverb_param.value, value, 0)
    
    
    
    def set_normal(self):
        # amp_model = 7
        # self.set_amp_model(7)
        self.set_amp_fader(AmpFader.GAIN, 90)
        self.set_amp_fader(AmpFader.TREBLE, 14)
        self.set_amp_fader(AmpFader.MIDDLE, 15)
        self.set_amp_fader(AmpFader.BASS, 16)
        # self.set_amp_fader(AmpFader.VOLUME, 70)
        # self.set_amp_fader(AmpFader.MID_BOOST, 0)
        # self.set_reverb_type(ReverbType.ROOM)
        # self.set_reverb_param(ReverbParam.MIX, 20)
    
    def set_solo(self):
        # self.set_amp_model(7)
        self.set_amp_fader(AmpFader.GAIN, 30)
        self.set_amp_fader(AmpFader.TREBLE, 72)
        self.set_amp_fader(AmpFader.MIDDLE, 71)
        self.set_amp_fader(AmpFader.BASS, 69)
        # self.set_amp_fader(AmpFader.VOLUME, 60)
        # self.set_amp_fader(AmpFader.MID_BOOST, 1)
        # self.set_reverb_type(ReverbType.SPRING)
        # self.set_reverb_param(ReverbParam.MIX, 50)
        