from enum import IntEnum, Enum
from lib2to3.pytree import Base
import logging
from pathlib import Path
from typing import Callable, Optional
import json

import xdg
from mentat import Module
from effects import (
    DummyParam, EffParam, EffectOnOff, Pedal1Type,
    AmpModel, AmpParam, Pedal2Type, ReverbParam, ReverbType,
    VoxIndex, VoxMode)
from vox_program import VoxProgram


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


class ConnectState(Enum):
    DISCONNECTED = 0
    CHECKING = 1
    CONNECTED = 2


SYSEX_BEGIN = [240, 66, 48, 0, 1, 52]
    

class Voxou(Module):
    def __init__(self, name: str,
                 protocol: Optional[str] = None,
                 port: int|str|None = None,
                 parent=None):
        super().__init__(name, protocol=protocol, port=port, parent=parent)

        self.current_program = VoxProgram()
        self.programs = [VoxProgram() for i in range(8)]
        self.factory_programs = [VoxProgram() for i in range(60)]
        self.user_presets = [VoxProgram() for i in range(4)]
        
        self.voxmode = VoxMode.PRESET
        self.prog_num = 0
        self.connected = ConnectState.DISCONNECTED
        
        self._param_change_cb: Optional[Callable] = None

        self.solo = False

    def set_param_change_cb(self, cb: Callable):
        self._param_change_cb = cb
    
    def _send_vox(self, *args):
        self.send('/sysex', *(SYSEX_BEGIN + list(args) + [247]))
        self.connected = ConnectState.CHECKING
        if self._param_change_cb:
            self._param_change_cb('CONNECT_STATE', False)
    
    def _send_cb(self, *args):
        if self._param_change_cb:
            self._param_change_cb(*args)
    
    def ask_connection(self):
        self._send_vox(FunctionCode.MODE_REQUEST)
        
        for bank_n in range(8):
            self._send_vox(
                FunctionCode.PROGRAM_DATA_DUMP_REQUEST,
                VoxMode.USER.value,
                bank_n)

        for factobank_n in range(60):
            self._send_vox(
                FunctionCode.PROGRAM_DATA_DUMP_REQUEST,
                VoxMode.PRESET.value,
                factobank_n)

        self._send_vox(FunctionCode.CURRENT_PROGRAM_DATA_DUMP_REQUEST)
        
        for user_preset_n in range(3):
            self._send_vox(
                FunctionCode.CUSTOM_AMPFX_DATA_DUMP_REQUEST, 0, user_preset_n)

    def route(self, address, args: list):
        print('routptutt', address, args)
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
        
        self.connected = ConnectState.CONNECTED
        # send connect state OK to gui
        self._send_cb('CONNECT_STATE', True)
        
        if function_code is FunctionCode.CURRENT_PROGRAM_DATA_DUMP:
            print('______CURRENT PROGRAM____________')
            self.current_program.read_data(shargs)
            self._send_cb('ALL_CURRENT', self.current_program)
            
        elif function_code is FunctionCode.PROGRAM_DATA_DUMP:
            voxmode_int = shargs.pop(0)
            prog_num = shargs.pop(0)
            
            vox_mode = VoxMode(voxmode_int)
            print(f'______PROGRAM N°{prog_num} _________', vox_mode)
            
            if vox_mode is VoxMode.USER:
                self.programs[prog_num].read_data(shargs)
            elif vox_mode is VoxMode.PRESET:
                self.factory_programs[prog_num].read_data(shargs)
            # self.programs[prog_num].print_program()
        
        elif function_code is FunctionCode.PARAMETER_CHANGE:
            vox_index = VoxIndex(shargs.pop(0))
            param_index = shargs.pop(0)
            value = shargs.pop(0)
            big_value = shargs.pop(0)
            
            if vox_index is VoxIndex.NR_SENS:
                if param_index == 0:
                    self.current_program.nr_sens = value
            
            elif vox_index is VoxIndex.EFFECT_STATUS:
                effect_on_off = EffectOnOff(param_index)
                self.current_program.active_effects[effect_on_off] = value
                        
            elif vox_index is VoxIndex.EFFECT_MODEL:
                effect = EffectOnOff(param_index)
                if effect is EffectOnOff.AMP:
                    self.current_program.amp_model = AmpModel(value)
                elif effect is EffectOnOff.PEDAL1:
                    self.current_program.pedal1_type = Pedal1Type(value)
                elif effect is EffectOnOff.PEDAL2:
                    self.current_program.pedal2_type = Pedal2Type(value)
                elif effect is EffectOnOff.REVERB:
                    self.current_program.reverb_type = ReverbType(value)
            
            elif vox_index is VoxIndex.AMP:
                amp_param = AmpParam(param_index)
                self.current_program.amp_params[amp_param] = value
                for key, value in self.current_program.amp_params.items():
                    print('', key.name, ':', value)
                
            elif vox_index is VoxIndex.PEDAL1:
                eff_param: EffParam = \
                    self.current_program.pedal1_type.param_type()(param_index)
                self.current_program.pedal1_values[eff_param.value] = \
                    value + big_value * 128
            
            elif vox_index is VoxIndex.PEDAL2:
                eff_param: EffParam = \
                    self.current_program.pedal2_type.param_type()(param_index)
                self.current_program.pedal2_values[eff_param.value] = \
                    value + big_value * 128

            elif vox_index is VoxIndex.REVERB:
                self.current_program.reverb_values[param_index] = value
                    
            self._send_cb(
                'PARAM_CHANGED',
                (self.current_program, vox_index, param_index))

        elif function_code is FunctionCode.MODE_DATA:
            voxmode_int = shargs.pop(0)
            self.voxmode = VoxMode(voxmode_int)
            self._send_cb('MODE_CHANGED', self.voxmode)

        elif function_code is FunctionCode.MODE_CHANGE:
            voxmode_int = shargs.pop(0)
            self.voxmode = VoxMode(voxmode_int)
            self.prog_num = shargs.pop(0)
            
            if self.voxmode is VoxMode.USER:
                self.current_program = self.programs[self.prog_num].copy()
                self._send_cb('ALL_CURRENT', self.current_program)
            
            elif self.voxmode is VoxMode.PRESET:
                self.current_program = \
                    self.factory_programs[self.prog_num].copy()
                self._send_cb('ALL_CURRENT', self.current_program)

            elif self.voxmode is VoxMode.MANUAL:
                # reask the VOX for all current values
                self._send_vox(FunctionCode.CURRENT_PROGRAM_DATA_DUMP_REQUEST)
                
            self._send_cb('MODE_CHANGED', self.voxmode)

        elif function_code is FunctionCode.CUSTOM_AMPFX_DATA_DUMP:
            unused = shargs.pop(0)
            preset_n = shargs.pop(0)
            
            preset = self.user_presets[preset_n]
            print(f'____USER PRESET {preset_n} ________________')
            preset.read_data_preset(shargs)
            # if preset_n == 0:
            #     preset.print_program()
            
            
            
        
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
            pass
            # num = args[8]
            # print('ok ko voisss', num)
            # rem_list = self.rems_user_presets.get(num)
            # if rem_list is not None:
            #     print('sso', rem_list == args)
            #     if rem_list != args:
            #         print('ah une diff', num)
            #         print('nannni', rem_list)
            #         print('nakkou', args)
            # self.rems_user_presets[num] = args.copy()
    
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
        
        if vox_index is VoxIndex.NR_SENS:
            if param is DummyParam.DUMMY:
                self.current_program.nr_sens = value
            
        elif vox_index is VoxIndex.EFFECT_MODEL:
            if param is EffectOnOff.AMP:
                self.current_program.amp_model = AmpModel(value)

            elif param is EffectOnOff.PEDAL1:
                self.current_program.pedal1_type = Pedal1Type(value)
            
            elif param is EffectOnOff.PEDAL2:
                self.current_program.pedal2_type = Pedal2Type(value)
            
            elif param is EffectOnOff.REVERB:
                self.current_program.reverb_type = ReverbType(value)
        
        elif vox_index is VoxIndex.AMP:
            cvalue = self.current_program.amp_params.get(param)
            if cvalue is None:
                _logger.error(
                    f'attempting to change a not known amp parameter {param}')
                return
            
            value = self._rail_value(param, value)
            self.current_program.amp_params[param] = value
            
        elif vox_index is VoxIndex.EFFECT_STATUS:
            value = self._rail_value(param, value)            
            self.current_program.active_effects[param] = value
        
        elif vox_index is VoxIndex.PEDAL1:
            cvalue = self.current_program.pedal1_values[param.value]
            
            # cvalue = self.current_program.pedal1_params.get(param)
            # if cvalue is None:
            #     _logger.error(f'attempting to change a not known pedal1 param {param}')
            #     return
            
            value = self._rail_value(param, value)
            self.current_program.pedal1_values[param.value] = value
            
            if param.value == 0:
                value_big, value = divmod(value, 256)
            
        elif vox_index is VoxIndex.PEDAL2:
            cvalue = self.current_program.pedal1_values[param.value]
            
            # cvalue = self.current_program.pedal2_params.get(param)
            # if cvalue is None:
            #     _logger.error(f'attempting to change a not known pedal2 param {param}')
            #     return
            
            value = self._rail_value(param, value)
            self.current_program.pedal2_values[param.value] = value
            
            if param.value == 0:
                value_big, value = divmod(value, 256)
            
        elif vox_index is VoxIndex.REVERB:
            cvalue = self.current_program.reverb_values[param.value]
            # cvalue = self.current_program.reverb_params.get(param)
            # if cvalue is None:
            #     _logger.error(f'attempting to change a not known reverb param {param}')
            #     return
            
            value = self._rail_value(param, value)
            self.current_program.reverb_values[param.value] = value
        
        self._send_vox(FunctionCode.PARAMETER_CHANGE.value,
                       vox_index.value, param.value, value, value_big)
    
    def set_program_name(self, new_name: str):
        if len(new_name) > 16:
            new_name = new_name[:16]
        
        str_as_ints = [ord(c) % 128 for c in new_name]
        while len(str_as_ints) < 16:
            str_as_ints.append(ord(' '))

        for i in range(len(str_as_ints)):
            self._send_vox(
                FunctionCode.PARAMETER_CHANGE.value,
                VoxIndex.PROGRAM_NAME.value,
                i, str_as_ints[i], 0)
        
    def set_mode(self, vox_mode: VoxMode):
        if vox_mode is VoxMode.MANUAL:
            self._send_vox(FunctionCode.MODE_CHANGE, vox_mode.value, 0)
            self._send_vox(FunctionCode.CURRENT_PROGRAM_DATA_DUMP_REQUEST)

        elif vox_mode is VoxMode.PRESET:
            for i in range(len(self.factory_programs)):
                if (self.factory_programs[i].amp_model
                        is self.current_program.amp_model):
                    break
            else:
                i = 0

            self._send_vox(FunctionCode.MODE_CHANGE, vox_mode.value, i)
            self.current_program = self.factory_programs[i].copy()
            self._send_cb('ALL_CURRENT', self.current_program)

        elif vox_mode is VoxMode.USER:
            for i in range(len(self.programs)):
                if (self.programs[i].amp_model
                        is self.current_program.amp_model):
                    break
            else:
                i = 0
            
            self._send_vox(FunctionCode.MODE_CHANGE, vox_mode.value, i)
            self.current_program = self.programs[i].copy()
            self._send_cb('ALL_CURRENT', self.current_program)

    # file managing
    def save_user_programs(self, filepath: Path):
        try:
            with open(filepath, 'w') as f:
                json.dump([p.to_json_dict() for p in self.programs], f,
                          indent=2)

        except BaseException as e:
            _logger.error(f"Failed to save json file {filepath}"
                          f"{str(e)}")            

    def set_normal(self):
        self.set_param_value(VoxIndex.EFFECT_MODEL, DummyParam.DUMMY, AmpModel.VOX_AC30TB)
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
        self.set_param_value(VoxIndex.EFFECT_MODEL, DummyParam.DUMMY, AmpModel.BRIT_OR_MKII)
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
        