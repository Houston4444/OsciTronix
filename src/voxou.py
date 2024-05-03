from enum import IntEnum
import logging
from typing import Optional
from mentat import Module

from effects import DummyParam, EffParam, EffectOnOff, EffectStatus, Pedal1Type, AmpModel, AmpParam, Pedal2Type, ReverbParam, ReverbType, VoxIndex

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

SYSEX_BEGIN = [240, 66, 48, 0, 1, 52]


class VoxProgram:
    def __init__(self):
        self.program_name = ''
        self.nr_sens = 0
        self.effect_status = EffectStatus.ALL_OFF
        self.amp_model = AmpModel.DELUXE_CL_VIBRATO
        self.amp_params = dict[AmpParam, int]()
        self.pedal1_type = Pedal1Type.COMP
        self.pedal1_params = dict[EffParam, int]()
        self.pedal2_type = Pedal2Type.FLANGER
        self.pedal2_params = dict[EffParam, int]()
        self.reverb_type = ReverbType.ROOM
        self.reverb_params = dict[ReverbParam, int]()

    def read_data(self, shargs: list[int]):
        program_name_ints, shargs = shargs[:16], shargs[16:]
        self.program_name = ''.join([chr(p) for p in program_name_ints])
        
        # 3 not documented numbers
        shargs = shargs[3:]
        
        self.nr_sens = shargs.pop(0)
        self.effects_status = EffectStatus(shargs.pop(0))
        self.amp_model = AmpModel(shargs.pop(0))

        amp_params = self.amp_params
        amp_params[AmpParam.GAIN] = shargs.pop(0)
        amp_params[AmpParam.TREBLE] = shargs.pop(0)
        
        # undocumented number
        unused = shargs.pop(0)
        
        amp_params[AmpParam.MIDDLE] = shargs.pop(0)
        amp_params[AmpParam.BASS] = shargs.pop(0)
        amp_params[AmpParam.VOLUME] = shargs.pop(0)
        amp_params[AmpParam.TONE] = shargs.pop(0)
        amp_params[AmpParam.RESONANCE] = shargs.pop(0)
        amp_params[AmpParam.BRIGHT_CAP] = shargs.pop(0)
        amp_params[AmpParam.LOW_CUT] = shargs.pop(0)
        
        # undocumented number
        unused = shargs.pop(0)
        
        amp_params[AmpParam.MID_BOOST] = shargs.pop(0)
        amp_params[AmpParam.BIAS_SHIFT] = shargs.pop(0)
        amp_params[AmpParam.CLASS] = shargs.pop(0)
        
        pedal1_type_int = shargs.pop(0)
        pedal1_values, shargs = shargs[:8], shargs[8:]
        
        # delete one unused number
        pedal1_values.__delitem__(3)

        self.pedal1_type = Pedal1Type(pedal1_type_int)
        self.pedal1_params.clear()

        eff_param: EffParam
        for eff_param in self.pedal1_type.param_type():
            if eff_param.value == 0:
                value = pedal1_values[0] + pedal1_values[1] * 256
            else:
                value = pedal1_values[eff_param.value + 1]
        
            self.pedal1_params[eff_param] = value
        
        pedal2_type_int = shargs.pop(0)
        pedal2_values, shargs = shargs[:9], shargs[9:]
        
        # delete one unused number
        pedal2_values.__delitem__(2)
        
        self.pedal2_type = Pedal2Type(pedal2_type_int)
        self.pedal2_params.clear()
        
        for eff_param in self.pedal2_type.param_type():
            if eff_param.value == 0:
                value = pedal2_values[0] + pedal2_values[1] * 256
            else:
                value = pedal2_values[eff_param.value + 1]
        
            self.pedal2_params[eff_param] = value
        
        # 8 documented reserved numbers + 2 undocumented
        shargs = shargs[8:]
                    
        reverb_type_int = shargs.pop(0)
        reverb_values, shargs = shargs[:6], shargs[6:]
        reverb_values.__delitem__(0)

        self.reverb_type = ReverbType(reverb_type_int)
        self.reverb_params.clear()

        for reverb_param in ReverbParam:
            self.reverb_params[reverb_param] = reverb_values[reverb_param.value]
    
        print('prog name :', self.program_name)
        print('AMP :', self.amp_model.name)
        amp_param: AmpParam
        for amp_param, value in self.amp_params.items():
            mini, maxi, unit = amp_param.range_unit()
            if value < mini:
                _logger.warning(f'{amp_param.name} : value {value} is < to min {mini}')
            elif value > maxi:
                _logger.warning(f'{amp_param.name} : value {value} is > to max {maxi}')
            print('  ', amp_param.name, ':', value, unit)
    
        print('PEDAL1 :', self.pedal1_type.name, bool(self.effect_status & EffectStatus.PEDAL1_ON))
        for eff_param, value in self.pedal1_params.items():
            mini, maxi, unit = eff_param.range_unit()
            if value < mini:
                _logger.warning(f'{eff_param.name} : value {value} is < to min {mini}')
            elif value > maxi:
                _logger.warning(f'{eff_param.name} : value {value} is > to max {maxi}')
            print('  ', eff_param.name, ':', value, unit)
        
        print('PEDAL2 :', self.pedal2_type.name, bool(self.effect_status & EffectStatus.PEDAL2_ON))
        for eff_param, value in self.pedal2_params.items():
            mini, maxi, unit = eff_param.range_unit()
            if value < mini:
                _logger.warning(f'{eff_param.name} : value {value} is < to min {mini}')
            elif value > maxi:
                _logger.warning(f'{eff_param.name} : value {value} is > to max {maxi}')
            print('  ', eff_param.name, ':', value, unit)
            
        print('REVERB :', self.reverb_type.name, bool(self.effect_status & EffectStatus.REVERB_ON))
        for eff_param, value in self.reverb_params.items():
            mini, maxi, unit = eff_param.range_unit()
            if value < mini:
                _logger.warning(f'{eff_param.name} : value {value} is < to min {mini}')
            elif value > maxi:
                _logger.warning(f'{eff_param.name} : value {value} is > to max {maxi}')
            
            print('  ', eff_param.name, ':', value, unit)


class Voxou(Module):
    def __init__(self, name: str,
                 protocol: Optional[str] = None,
                 port: int|str|None = None,
                 parent=None):
        super().__init__(name, protocol=protocol, port=port, parent=parent)
        self.rems_banks = dict[int, list[int]]()
        self.rems_user_presets = dict[int, list[int]]()
        self.rems_states = list[int]()

        self.current_program = VoxProgram()
        self.programs = [VoxProgram() for i in range(8)]

        self.program_name = ''
        self.nr_sens = 0
        self.effect_status = 0
        self.amp_model = 0
        self.amp_faders = dict[AmpParam, int]()
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
            print('______CURRENT PROGRAM____________')
            self.current_program.read_data(shargs)
            
        elif function_code is FunctionCode.PROGRAM_DATA_DUMP:
            unused = shargs.pop(0)
            prog_num = shargs.pop(0)
            print(f'______PROGRAM N°{prog_num} _________')
            self.programs[prog_num].read_data(shargs)
        
        elif function_code is FunctionCode.PARAMETER_CHANGE:
            vox_index = VoxIndex(shargs.pop(0))
            param_index = shargs.pop(0)
            value = shargs.pop(0)
            
            if vox_index is VoxIndex.NR_SENS:
                if param_index == 0:
                    self.current_program.nr_sens = value
            
            elif vox_index is VoxIndex.EFFECT_STATUS:
                if param_index == 1:
                    if value:
                        self.current_program.effect_status |= EffectStatus.PEDAL1_ON
                    else:
                        self.current_program.effect_status &= ~EffectStatus.PEDAL1_ON
                elif param_index == 2:
                    if value:
                        self.current_program.effect_status |= EffectStatus.PEDAL2_ON
                    else:
                        self.current_program.effect_status &= ~EffectStatus.PEDAL2_ON
                elif param_index == 4:
                    if value:
                        self.current_program.effect_status |= EffectStatus.REVERB_ON
                    else:
                        self.current_program.effect_status &= ~EffectStatus.REVERB_ON
                        
            elif vox_index is VoxIndex.AMP_MODEL:
                if param_index == 0:
                    self.current_program.amp_model = AmpModel(value)
            
            elif vox_index is VoxIndex.AMP:
                amp_param = AmpParam(param_index)
                self.current_program.amp_params[amp_param] = value
                for key, value in self.current_program.amp_params.items():
                    print('', key.name, ':', value)
                
            elif vox_index is VoxIndex.PEDAL1:
                eff_param = self.current_program.pedal1_type.param_type()(param_index)
                self.current_program.pedal1_params[eff_param] = value
                for key, value in self.current_program.pedal1_params.items():
                    print('', key.name, ':', value)
            
            elif vox_index is VoxIndex.PEDAL2:
                eff_param = self.current_program.pedal2_type.param_type()(param_index)
                self.current_program.pedal1_params[eff_param] = value
                for key, value in self.current_program.pedal2_params.items():
                    print('', key.name, ':', value)
            
            elif vox_index is VoxIndex.REVERB:
                rev_param = self.current_program.reverb_type.param_type()(param_index)
                self.current_program.pedal1_params[rev_param] = value
                for key, value in self.current_program.reverb_params.items():
                    print('', key.name, ':', value)

        
        # if args[:8] == [240, 66, 48, 0, 1, 52, 76, 0]:
        #     # probablement BANKS
        #     num = args[8]
        #     print('ok je voisss', num)
        #     rem_list = self.rems_banks.get(num)
        #     if rem_list is not None and rem_list != args:
        #         print('ah une diff', num)
        #         print('nannni', rem_list)
        #         print('nakkou', args)
        #     self.rems_banks[num] = args
            
        if args[:8] == [240, 66, 48, 0, 1, 52, 101, 0]:
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
        
        # elif args[:8] == [240, 66, 48, 0, 1, 52, 64, 0]:
        #     rem_list = self.rems_states
        #     if rem_list:
        #         print('ezoak', args == rem_list)
        #         if args != rem_list:
        #             print('une diff dans le 64')
        #             for i in range(len(args)):
        #                 if args[i] != rem_list[i]:
        #                     print('diffici', i, ':', rem_list[i], '->', args[i])

        #     for param_index in ParamIndex:
        #         self.states[param_index] = args[param_index.value]
        #         for amp_fader, pam_id in AMP_FADER_LINK.items():
        #             if pam_id is param_index:
        #                 self.amp_faders[amp_fader] = args[param_index.value]
        #                 break
        #         else:
        #             for rev_param, pam_id in REVERB_PARAM_LINK.items():
        #                 if pam_id is param_index:
        #                     self.reverb_params[rev_param] = args[param_index.value]
        #                     break

        #         # print('koz', param_index.name, ':', self.states[param_index])
        #     self.rems_states = args.copy()
            
        # elif args[:7] == [240, 66, 48, 0, 1, 52, 65]:
        #     if args[7] == 4:
        #         try:
        #             amp_fader = AmpFader(args[8])
        #         except:
        #             print('amp fader non géré', args[8], args[9])

        #         self.amp_faders[amp_fader] = args[9]
        else:
            print('schil', address, args)
    
    def set_amp_model(self, amp_model: int):
        if amp_model == self.amp_model or not 0 <= amp_model <= 13:
            return
        
        self._send_vox(65, 3, 0, amp_model, 0)
    
    def set_amp_fader(self, amp_param: AmpParam, value: int):
        self._send_vox(65, 4, amp_param.value, value, 0)
    
    def set_reverb_type(self, reverb_type: ReverbType):
        if reverb_type is self.reverb_type:
            return
        self._send_vox(65, 3, 4, reverb_type.value, 0)
    
    def set_reverb_on_off(self, onoff: bool|int):
        self._send_vox(65, 2, 4, 1 if onoff else 0, 0)
    
    def set_reverb_param(self, reverb_param: ReverbParam, value: int):
        self._send_vox(65, 8, reverb_param.value, value, 0)
    
    @staticmethod
    def _rail_value(param: EffParam, value: int) -> int:
        mini, maxi, unit = param.range_unit()
        if value < mini:
            _logger.warning(
                f'attempting to set too low value to {param.name}, {value} < {mini}')
            return mini
        elif value > maxi:
            _logger.warning(
                f'attempting to set too high value to {param.name}, {value} > {maxi}')
            return maxi
        return value
    
    def set_param_value(self, vox_index: VoxIndex, param: EffParam, value: int):
        if VoxIndex is VoxIndex.ERROR:
            return
        
        value_big = 0
        
        if vox_index is VoxIndex.AMP_MODEL:
            amp_model = AmpModel(value)
            param = DummyParam.DUMMY
            self.current_program.amp_model = amp_model
            value = amp_model.value
        
        elif vox_index is VoxIndex.AMP:
            cvalue = self.current_program.amp_params.get(param)
            if cvalue is None:
                _logger.error(f'attempting to change a not known amp parameter {param}')
                return
            
            value = self._rail_value(param, value)
            self.current_program.amp_params[param] = value
            
        elif vox_index is VoxIndex.EFFECT_STATUS:
            value = self._rail_value(param, value)
            
            if param is EffectOnOff.PEDAL1:
                if value:
                    self.current_program.effect_status |= EffectStatus.PEDAL1_ON
                else:
                    self.current_program.effect_status &= ~EffectStatus.PEDAL1_ON
            
            elif param is EffectOnOff.PEDAL2:
                if value:
                    self.current_program.effect_status |= EffectStatus.PEDAL2_ON
                else:
                    self.current_program.effect_status &= ~EffectStatus.PEDAL2_ON
            
            elif param is EffectOnOff.REVERB:
                if value:
                    self.current_program.effect_status |= EffectStatus.REVERB_ON
                else:
                    self.current_program.effect_status &= ~EffectStatus.REVERB_ON
        
        elif vox_index is VoxIndex.PEDAL1:
            cvalue = self.current_program.pedal1_params.get(param)
            if cvalue is None:
                _logger.error(f'attempting to change a not known pedal1 param {param}')
                return
            
            value = self._rail_value(param, value)
            self.current_program.pedal1_params[param] = value
            
            if param.value == 0:
                big_value, value = divmod(value, 256)
            
        elif vox_index is VoxIndex.PEDAL2:
            cvalue = self.current_program.pedal2_params.get(param)
            if cvalue is None:
                _logger.error(f'attempting to change a not known pedal2 param {param}')
                return
            
            value = self._rail_value(param, value)
            self.current_program.pedal2_params[param] = value
            
            if param.value == 0:
                big_value, value = divmod(value, 256)
            
        elif vox_index is VoxIndex.REVERB:
            cvalue = self.current_program.reverb_params.get(param)
            if cvalue is None:
                _logger.error(f'attempting to change a not known reverb param {param}')
                return
            
            value = self._rail_value(param, value)
            self.current_program.reverb_params[param] = value
        
        self._send_vox(FunctionCode.PARAMETER_CHANGE.value,
                       vox_index.value, param.value, value, value_big)
    
    def set_normal(self):
        self.set_param_value(VoxIndex.AMP_MODEL, DummyParam.DUMMY, AmpModel.VOX_AC30TB)
        self.set_param_value(VoxIndex.AMP, AmpParam.GAIN, 58)
        self.set_param_value(VoxIndex.AMP, AmpParam.VOLUME, 80)
        self.set_param_value(VoxIndex.REVERB, ReverbParam.TIME, 16)
        # amp_model = 7
        # self.set_amp_model(7)
        # self.set_amp_fader(AmpFader.GAIN, 90)
        # self.set_amp_fader(AmpFader.TREBLE, 14)
        # self.set_amp_fader(AmpFader.MIDDLE, 15)
        # self.set_amp_fader(AmpFader.BASS, 16)
        # self.set_amp_fader(AmpFader.VOLUME, 70)
        # self.set_amp_fader(AmpFader.MID_BOOST, 0)
        # self.set_reverb_type(ReverbType.ROOM)
        # self.set_reverb_param(ReverbParam.MIX, 20)
    
    def set_solo(self):
        self.set_param_value(VoxIndex.AMP_MODEL, DummyParam.DUMMY, AmpModel.BRIT_OR_MKII)
        self.set_param_value(VoxIndex.AMP, AmpParam.GAIN, 98)
        self.set_param_value(VoxIndex.AMP, AmpParam.VOLUME, 45)
        self.set_param_value(VoxIndex.REVERB, ReverbParam.TIME, 98)
        
        # self.set_amp_model(7)
        # self.set_amp_fader(AmpFader.GAIN, 30)
        # self.set_amp_fader(AmpFader.TREBLE, 72)
        # self.set_amp_fader(AmpFader.MIDDLE, 71)
        # self.set_amp_fader(AmpFader.BASS, 69)
        # self.set_amp_fader(AmpFader.VOLUME, 60)
        # self.set_amp_fader(AmpFader.MID_BOOST, 1)
        # self.set_reverb_type(ReverbType.SPRING)
        # self.set_reverb_param(ReverbParam.MIX, 50)
        