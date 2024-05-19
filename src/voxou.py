from enum import IntEnum, Enum
import logging
from pathlib import Path
import time
from typing import Any, Callable, Optional
import json

from midi_enums import MidiConnectState
from effects import (
    DummyParam, EffParam, EffectOnOff, Pedal1Type,
    AmpModel, AmpParam, Pedal2Type, ReverbType,
    VoxIndex, VoxMode)
from vox_program import VoxProgram


_logger = logging.getLogger(__name__)


class GuiCallback(Enum):
    DATA_ERROR = -1
    COMMUNICATION_STATE = 0
    MIDI_CONNECT_STATE = 1
    CURRENT_CHANGED = 2
    PARAM_CHANGED = 3
    MODE_CHANGED = 4
    USER_BANKS_READ = 5
    FACTORY_BANKS_READ = 6


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


def rail_int(value: int, mini: int, maxi: int) -> int:
    return max(min(value, maxi), mini)


class Voxou:
    def __init__(self):
        self.current_program = VoxProgram()
        self.programs = [VoxProgram() for i in range(8)]
        self.factory_programs = [VoxProgram() for i in range(60)]
        
        # There are 4 user ampfxs in the amp,
        # even if physically, only 3 exists
        self.user_ampfxs = [VoxProgram() for i in range(4)]
        
        self.voxmode = VoxMode.PRESET
        self.prog_num = 0
        self.communication_state = False
        
        self._last_sent_message = tuple[FunctionCode, tuple[int]]()
        self._midi_connect_state = MidiConnectState.ABSENT_DEVICE

        self._midi_out_func: Optional[Callable] = None
        self._gui_cb: Optional[Callable] = None

    def set_gui_cb(self, cb: Callable[[FunctionCode, Any], None]):
        self._gui_cb = cb
    
    def set_midi_out_func(self, midi_out_func: Callable):
        self._midi_out_func = midi_out_func

    def set_communication_state(self, comm_state: bool):
        self.communication_state = comm_state
        self._send_cb(GuiCallback.COMMUNICATION_STATE, comm_state)

    def set_midi_connect_state(self, connect_state: MidiConnectState):
        if (self.communication_state
                and self._midi_connect_state is MidiConnectState.CONNECTED
                and connect_state is not MidiConnectState.CONNECTED):
            # device was midi connected and communication working
            # let's try now if everything is still working
            # (very probably not !).
            self._send_vox(FunctionCode.MODE_REQUEST)
             
        self._midi_connect_state = connect_state
        self._send_cb(GuiCallback.MIDI_CONNECT_STATE, connect_state)

    def _send_vox(self, function_code: FunctionCode, *args):
        self._last_sent_message = (function_code, args)

        if self._midi_out_func is None:
            _logger.warning(
                "Trying to send midi message while midi port is not ready !")
            return

        self._midi_out_func(
            SYSEX_BEGIN + [function_code.value] + list(args) + [247])

        self.set_communication_state(False)
    
    def _send_cb(self, gui_callback: GuiCallback, arg=None):
        if self._gui_cb:
            self._gui_cb(gui_callback, arg)
    
    def start_communication(self):
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
        
        for user_preset_n in range(4):
            self._send_vox(
                FunctionCode.CUSTOM_AMPFX_DATA_DUMP_REQUEST, 0, user_preset_n)

    def receive_sysex(self, args: list[int]):
        shargs = args
        
        if len(shargs) < 6:
            _logger.info('Too short sysex message received')
            return
        
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
            _logger.critical(
                f'Received Unknown function code {hex(function_code)}')
            return
        
        _logger.debug(f'message received from device {function_code.name}')

        if function_code in (FunctionCode.DATA_LOAD_ERROR,
                             FunctionCode.DATA_FORMAT_ERROR):
            _logger.warning(
                f'error received from device {function_code.name}')
            orig_func_code = self._last_sent_message[0]
            _logger.warning(f'last sent message is {orig_func_code.name}')
            self._send_cb(GuiCallback.DATA_ERROR, orig_func_code)

        self.set_communication_state(True)
        
        if function_code is FunctionCode.CURRENT_PROGRAM_DATA_DUMP:
            try:
                self.current_program.data_read(shargs)
            except BaseException as e:
                _logger.error(
                    f'Failed to read current program data.\n{str(e)}')
                return

            self._send_cb(GuiCallback.CURRENT_CHANGED, self.current_program)
        
        elif function_code is FunctionCode.PROGRAM_DATA_DUMP:
            voxmode_int = shargs.pop(0)
            prog_num = shargs.pop(0)
            
            try:
                vox_mode = VoxMode(voxmode_int)
            except:
                _logger.critical(
                    f'Received {function_code.name} with unknown mode')
                return

            try:
                if vox_mode is VoxMode.USER:
                    self.programs[prog_num].data_read(shargs)
                    if prog_num == 7:
                        self._send_cb(GuiCallback.USER_BANKS_READ)
                    
                elif vox_mode is VoxMode.PRESET:
                    self.factory_programs[prog_num].data_read(shargs)
                    if prog_num == 59:
                        self._send_cb(GuiCallback.FACTORY_BANKS_READ)

            except BaseException as e:
                _logger.error(
                    f"Failed to write incoming program.\n{str(e)}")
                return
        
        elif function_code is FunctionCode.PARAMETER_CHANGE:
            try:
                vox_index = VoxIndex(shargs.pop(0))
            except:
                _logger.critical(
                    f"Received {function_code.name} with wrong first index")
                return

            if len(shargs) < 3:
                _logger.critical(
                    f"Received too short {function_code.name} message")
                return

            param_index = shargs.pop(0)
            value = shargs.pop(0)
            big_value = shargs.pop(0)

            if vox_index is VoxIndex.NR_SENS:
                if param_index == 0:
                    self.current_program.nr_sens = min(max(value, 0), 100)

            elif vox_index is VoxIndex.EFFECT_STATUS:
                try:
                    effect_on_off = EffectOnOff(param_index)
                    self.current_program.active_effects[effect_on_off] = value
                except:
                    _logger.critical(
                        f"unknown effect in {function_code.name}: "
                        f"{param_index}")
                    return

            elif vox_index is VoxIndex.EFFECT_MODEL:
                try:
                    effect = EffectOnOff(param_index)
                except:
                    _logger.critical(
                        f"unknown effect in {function_code.name}: "
                        f"{param_index}")
                    return

                if effect is EffectOnOff.AMP:
                    self.current_program.amp_model = AmpModel(value)
                elif effect is EffectOnOff.PEDAL1:
                    self.current_program.pedal1_type = Pedal1Type(value)
                elif effect is EffectOnOff.PEDAL2:
                    self.current_program.pedal2_type = Pedal2Type(value)
                elif effect is EffectOnOff.REVERB:
                    self.current_program.reverb_type = ReverbType(value)
            
            elif vox_index is VoxIndex.AMP:
                try:
                    amp_param = AmpParam(param_index)
                except:
                    _logger.critical(
                        f"Unknown amp param in {function_code.name}: "
                        f"{amp_param}")
                    return

                self.current_program.amp_params[amp_param] = value
                
            elif vox_index is VoxIndex.PEDAL1:
                try:
                    assert 0 <= param_index <= 5
                except:
                    _logger.critical(
                        'Message received with wrong param_index '
                        f'{param_index}')
                    return
                
                self.current_program.pedal1_values[param_index] = \
                    value + big_value * 128
            
            elif vox_index is VoxIndex.PEDAL2:
                try:
                    assert 0 <= param_index <= 5
                except:
                    _logger.critical(
                        'Message received with wrong param_index '
                        f'{param_index}')
                    return

                self.current_program.pedal2_values[param_index] = \
                    value + big_value * 128

            elif vox_index is VoxIndex.REVERB:
                try:
                    assert 0 <= param_index <= 4
                except:
                    _logger.critical(
                        'Message received with wrong param_index '
                        f'{param_index}')
                    return
                
                self.current_program.reverb_values[param_index] = value
                    
            self._send_cb(
                GuiCallback.PARAM_CHANGED,
                (self.current_program, vox_index, param_index))

        elif function_code is FunctionCode.MODE_DATA:
            if len(shargs) < 2:
                _logger.critical(
                    f"Received {function_code.name} with too short message")
                return
            
            voxmode_int = shargs.pop(0)
            self.prog_num = shargs.pop(0)
            
            try:
                self.voxmode = VoxMode(voxmode_int)
            except:
                _logger.critical(
                    f"Received {function_code.name} with unknown mode: "
                    f"{voxmode_int}")
                return
                
            self._send_cb(GuiCallback.MODE_CHANGED, self.voxmode)

        elif function_code is FunctionCode.MODE_CHANGE:
            if len(shargs) < 2:
                _logger.critical(
                    f"Received {function_code.name} with too short message")
                return

            voxmode_int = shargs.pop(0)
            prog_num = shargs.pop(0)

            try:
                self.voxmode = VoxMode(voxmode_int)
            except:
                _logger.critical(
                    f"Received {function_code.name} with unknown mode: "
                    f"{voxmode_int}")
                return
            
            if self.voxmode is VoxMode.USER:
                try:
                    assert(0 <= prog_num < len(self.programs))
                except:
                    _logger.critical(
                        f"Received {function_code.name} with wrong "
                        f"prog num :{prog_num}")
                    return
                
                self.prog_num = prog_num
                self.current_program = self.programs[self.prog_num].copy()
                self._send_cb(GuiCallback.CURRENT_CHANGED,
                              self.current_program)
            
            elif self.voxmode is VoxMode.PRESET:
                try:
                    assert(0 <= prog_num < len(self.factory_programs))
                except:
                    _logger.critical(
                        f"Received {function_code.name} with wrong "
                        f"prog num :{prog_num}")
                    return
                
                self.current_program = \
                    self.factory_programs[self.prog_num].copy()
                self._send_cb(GuiCallback.CURRENT_CHANGED,
                              self.current_program)

            elif self.voxmode is VoxMode.MANUAL:
                # reask the VOX for all current values
                self._send_vox(FunctionCode.CURRENT_PROGRAM_DATA_DUMP_REQUEST)
                
            self._send_cb(GuiCallback.MODE_CHANGED, self.voxmode)

        elif function_code is FunctionCode.CUSTOM_AMPFX_DATA_DUMP:
            if len(shargs) < 2:
                _logger.critical(
                    f"Received {function_code.name} with too short message")
                return
            
            unused = shargs.pop(0)
            ampfx_num = shargs.pop(0)
            
            try:
                assert(0 <= ampfx_num <= 3)
            except:
                _logger.critical(
                        f"Received {function_code.name} with wrong "
                        f"ampfx num :{ampfx_num}")
                return
                
            self.user_ampfxs[ampfx_num].ampfx_data_read(shargs)
            
        elif function_code is FunctionCode.WRITE_COMPLETED:
            if len(shargs) < 2:
                _logger.critical(
                    f"Received {function_code.name} with too short message")
                return
            
            reserved = shargs.pop(0)
            bank_num = shargs.pop(0)
            
            try:
                assert(0 <= bank_num <= 7)
            except:
                _logger.critical(
                    f"Received {function_code.name} with wrong "
                    f"bank num :{bank_num}")
                
            self.programs[bank_num] = self.current_program.copy()

    @staticmethod
    def _rail_value(param: EffParam, value: int) -> int:
        mini, maxi, unit = param.range_unit()
        if value < mini:
            _logger.warning(
                'attempting to set too low value to '
                f'{param.name}, {value} < {mini}')
            return mini
        elif value > maxi:
            _logger.warning(
                'attempting to set too high value to '
                f'{param.name}, {value} > {maxi}')
            return maxi
        return value
    
    def set_param_value(
            self, vox_index: VoxIndex, param: EffParam, value: int):
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
            value = self._rail_value(param, value)
            self.current_program.pedal1_values[param.value] = value
            
            if param.value == 0:
                value_big, value = divmod(value, 128)
            
        elif vox_index is VoxIndex.PEDAL2:
            cvalue = self.current_program.pedal1_values[param.value]
            value = self._rail_value(param, value)
            self.current_program.pedal2_values[param.value] = value
            
            if param.value == 0:
                value_big, value = divmod(value, 128)
            
        elif vox_index is VoxIndex.REVERB:
            cvalue = self.current_program.reverb_values[param.value]
            value = self._rail_value(param, value)
            self.current_program.reverb_values[param.value] = value
        
        self._send_vox(FunctionCode.PARAMETER_CHANGE,
                       vox_index.value, param.value, value, value_big)
    
    def set_program_name(self, new_name: str):
        if len(new_name) > 16:
            new_name = new_name[:16]
        
        str_as_ints = [ord(c) % 128 for c in new_name]
        while len(str_as_ints) < 16:
            str_as_ints.append(ord(' '))

        for i in range(len(str_as_ints)):
            self._send_vox(
                FunctionCode.PARAMETER_CHANGE,
                VoxIndex.PROGRAM_NAME.value,
                i, str_as_ints[i], 0)

        self.current_program.program_name = new_name
        
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
            self.prog_num = i
            self._send_cb(GuiCallback.CURRENT_CHANGED, self.current_program)

        elif vox_mode is VoxMode.USER:
            for i in range(len(self.programs)):
                if (self.programs[i].amp_model
                        is self.current_program.amp_model):
                    break
            else:
                i = 0
            
            self._send_vox(FunctionCode.MODE_CHANGE, vox_mode.value, i)
            self.current_program = self.programs[i].copy()
            self.prog_num = i
            self._send_cb(GuiCallback.CURRENT_CHANGED, self.current_program)

    def set_user_bank_num(self, bank_num: int):
        bank_num = min(max(bank_num, 0), 7)
        self._send_vox(
            FunctionCode.MODE_CHANGE, VoxMode.USER.value, bank_num)
        self.current_program = self.programs[bank_num].copy()
        self.prog_num = bank_num
        self._send_cb(GuiCallback.CURRENT_CHANGED, self.current_program)

    def set_preset_num(self, bank_num: int):
        bank_num = min(max(bank_num, 0), 59)
        self._send_vox(
            FunctionCode.MODE_CHANGE, VoxMode.PRESET.value, bank_num)
        self.current_program = self.factory_programs[bank_num].copy()
        self.prog_num = bank_num
        self._send_cb(GuiCallback.CURRENT_CHANGED, self.current_program)

    # file managing
    def save_all_amp(self, filepath: Path):
        full_dict = {}
        full_dict['banks'] = [p.to_json_dict() for p in self.programs]
        full_dict['ampfxs'] = [p.to_json_dict(for_ampfx=True)
                               for p in self.user_ampfxs]
        
        try:
            with open(filepath, 'w') as f:
                json.dump(full_dict, f, indent=2)

        except BaseException as e:
            _logger.error(f"Failed to save json file {filepath}"
                          f"{str(e)}")

    def upload_current_to_user_program(self, bank_num: int):
        self._send_vox(
            FunctionCode.PROGRAM_DATA_DUMP,
            VoxMode.USER.value,
            bank_num,
            *self.current_program.data_write())
        self.programs[bank_num] = self.current_program.copy()

    def upload_current_to_user_ampfx(self, ampfx_num: int):
        self._send_vox(
            FunctionCode.CUSTOM_AMPFX_DATA_DUMP,
            0,
            ampfx_num,
            *self.current_program.ampfx_data_write())

        self.user_ampfxs[ampfx_num] = self.current_program.copy()
