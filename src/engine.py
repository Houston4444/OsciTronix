from enum import IntEnum, Enum
import logging
from pathlib import Path
from queue import Queue
from typing import Any, Callable, Optional
import json
import time

from unidecode import unidecode
from app_infos import APP_NAME

import xdg
from config import Config
from midi_enums import MidiConnectState
from effects import (
    DummyParam, EffParam, EffectOnOff, Pedal1Type,
    AmpModel, AmpParam, Pedal2Type, ReverbType,
    VoxIndex, VoxMode)
from vox_program import VoxProgram


_logger = logging.getLogger(__name__)


class CommunicationState(Enum):
    # No message received since at least 100ms, 
    # despite the fact we were waiting a response
    LOSED = 0

    # No message sent since last message received
    OK = 1
    
    # At least one message send waiting 
    # for an answer for less than 100ms
    YES_BUT_CHECKING = 2
    
    # Same as YES_BUT_CHECKING, but previous state was LOSED
    NO_BUT_CHECKING = 3
    
    def is_ok(self) -> bool:
        return  self in (self.OK, self.YES_BUT_CHECKING)
    
    def is_checking(self) -> bool:
        return self in (self.YES_BUT_CHECKING, self.NO_BUT_CHECKING)
    
    def exported(self) -> 'CommunicationState':
        return self.OK if self.is_ok() else self.LOSED


class EngineCallback(Enum):
    DATA_ERROR = -1
    COMMUNICATION_STATE = 0
    MIDI_CONNECT_STATE = 1
    CURRENT_CHANGED = 2
    PARAM_CHANGED = 3
    MODE_CHANGED = 4
    USER_BANKS_READ = 5
    FACTORY_BANKS_READ = 6
    PROGRAM_NAME_CHANGED = 7
    LOCAL_PROGRAMS_CHANGED = 8


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

def in_midi_thread():
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            engine: 'Engine' = args[0]
            engine.event_queue.put((func, args, kwargs))
        return wrapper
    return decorator


class Engine:
    def __init__(self):
        self.config = Config()
        self.project_path = xdg.xdg_data_home() / APP_NAME
        
        self.current_program = VoxProgram()
        self.programs = [VoxProgram() for i in range(8)]
        self.factory_programs = [VoxProgram() for i in range(60)]
        self.local_programs = dict[str, VoxProgram]()
        self.current_local_pg_name = ''

        # There are 4 user ampfxs in the amp,
        # even if physically, only 3 exists
        self.user_ampfxs = [VoxProgram() for i in range(4)]
        
        self.voxmode = VoxMode.PRESET
        self.prog_num = 0
        self.communication_state = CommunicationState.LOSED
        self._send_count = 0
        self.last_send_time = 0.0

        self._last_sent_message = tuple[FunctionCode, tuple[int]]()
        self._midi_connect_state = MidiConnectState.ABSENT_DEVICE

        self._midi_out_func: Optional[Callable] = None
        self._cbs = set[Callable]() # callbacks (GUI and OSC)
        self._ready_cbs = set[Callable]()
        
        self.event_queue = Queue()

    @in_midi_thread()
    def add_callback(self, cb: Callable[[FunctionCode, Any], None]):
        self._cbs.add(cb)
    
    def set_a_ready_cb(self, cb: Callable):
        self._ready_cbs.add(cb)
    
    def set_midi_out_func(self, midi_out_func: Callable):
        self._midi_out_func = midi_out_func

    def set_midi_connect_state(self, connect_state: MidiConnectState):
        if (self.communication_state.is_ok()
                and self._midi_connect_state is MidiConnectState.CONNECTED
                and connect_state is not MidiConnectState.CONNECTED):
            # device was midi connected and communication working
            # let's try now if communication is still working
            # (very probably not !).
            self._send_vox(FunctionCode.MODE_REQUEST)
             
        self._midi_connect_state = connect_state
        self._send_cb(EngineCallback.MIDI_CONNECT_STATE, connect_state)

    def set_communication_state(self, comm_state: CommunicationState):
        if comm_state.is_ok() is not self.communication_state.is_ok():
            self._send_cb(EngineCallback.COMMUNICATION_STATE,
                          comm_state.exported())
        
        self.communication_state = comm_state

        if comm_state is CommunicationState.OK:
            self._send_count -= 1
        elif comm_state.is_checking():
            self._send_count += 1
            self.last_send_time = time.time()

        if self._send_count == 0:
            for ready_cb in self._ready_cbs:
                ready_cb()

    def _send_vox(self, function_code: FunctionCode, *args: tuple[int]):
        self._last_sent_message = (function_code, args)

        if self._midi_out_func is None:
            _logger.warning(
                "Trying to send midi message while midi port is not ready !")
            return

        self._midi_out_func(
            SYSEX_BEGIN + [function_code.value] + list(args) + [247])

        if self.communication_state.is_ok():
            self.set_communication_state(CommunicationState.YES_BUT_CHECKING)
        else:
            self.set_communication_state(CommunicationState.NO_BUT_CHECKING)
    
    def _send_cb(self, engine_callback: EngineCallback, arg=None):
        for cb in self._cbs:
            cb(engine_callback, arg)
    
    def start_communication(self):
        self._send_count = 0
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

        function_code_int = shargs.pop(0)

        try:
            function_code = FunctionCode(function_code_int)
        except:
            _logger.critical(
                f'Received Unknown function code {hex(function_code_int)}')
            return
        
        _logger.debug(f'message received from device {function_code.name}')

        if function_code in (FunctionCode.DATA_LOAD_ERROR,
                             FunctionCode.DATA_FORMAT_ERROR):
            _logger.warning(
                f'error received from device {function_code.name}')
            orig_func_code = self._last_sent_message[0]
            _logger.warning(f'last sent message is {orig_func_code.name}')
            self._send_cb(EngineCallback.DATA_ERROR, orig_func_code)

        self.set_communication_state(CommunicationState.OK)
        
        if function_code is FunctionCode.CURRENT_PROGRAM_DATA_DUMP:
            try:
                self.current_program.data_read(shargs)
            except BaseException as e:
                _logger.error(
                    f'Failed to read current program data.\n{str(e)}')
                return

            self._send_cb(EngineCallback.CURRENT_CHANGED, self.current_program)
        
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
                        self._send_cb(EngineCallback.USER_BANKS_READ)
                    
                elif vox_mode is VoxMode.PRESET:
                    self.factory_programs[prog_num].data_read(shargs)
                    if prog_num == 59:
                        self._send_cb(EngineCallback.FACTORY_BANKS_READ)

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
                EngineCallback.PARAM_CHANGED,
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
                
            self._send_cb(EngineCallback.MODE_CHANGED, self.voxmode)

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
                self._send_cb(EngineCallback.CURRENT_CHANGED,
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
                self._send_cb(EngineCallback.CURRENT_CHANGED,
                              self.current_program)

            elif self.voxmode is VoxMode.MANUAL:
                # reask the VOX for all current values
                self._send_vox(FunctionCode.CURRENT_PROGRAM_DATA_DUMP_REQUEST)
                
            self._send_cb(EngineCallback.MODE_CHANGED, self.voxmode)

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
    
    @in_midi_thread()
    def set_param_value(
            self, vox_index: VoxIndex|int, param: EffParam|int, value: int):
        if isinstance(vox_index, int):
            try:
                vox_index = VoxIndex(vox_index)
            except:
                _logger.warning(
                    f'set_param_value : vox_index {vox_index}'
                    f' does not exists, operation ignored')
                return
        
        if VoxIndex is VoxIndex.ERROR:
            return
        
        value_big = 0
        
        if vox_index is VoxIndex.NR_SENS:
            self.current_program.nr_sens = value
            param = DummyParam.DUMMY
            
        elif vox_index is VoxIndex.EFFECT_MODEL:
            if isinstance(param, int):
                try: param = EffectOnOff(param)
                except: return
            
            if param is EffectOnOff.AMP:
                self.current_program.amp_model = AmpModel(value)

            elif param is EffectOnOff.PEDAL1:
                self.current_program.pedal1_type = Pedal1Type(value)
            
            elif param is EffectOnOff.PEDAL2:
                self.current_program.pedal2_type = Pedal2Type(value)
            
            elif param is EffectOnOff.REVERB:
                self.current_program.reverb_type = ReverbType(value)
        
        elif vox_index is VoxIndex.AMP:
            if isinstance(param, int):
                try: param = AmpParam(param)
                except: return

            value = self._rail_value(param, value)
            self.current_program.amp_params[param] = value
            
        elif vox_index is VoxIndex.EFFECT_STATUS:
            if isinstance(param, int):
                try: param = EffectOnOff(param)
                except: return
            
            value = self._rail_value(param, value)            
            self.current_program.active_effects[param] = value
        
        elif vox_index is VoxIndex.PEDAL1:
            if isinstance(param, int):
                try: param = \
                    self.current_program.pedal1_type.param_type()(param)
                except: return
            
            value = self._rail_value(param, value)
            self.current_program.pedal1_values[param.value] = value
            
            if param.value == 0:
                value_big, value = divmod(value, 128)
            
        elif vox_index is VoxIndex.PEDAL2:
            if isinstance(param, int):
                try: param = \
                    self.current_program.pedal2_type.param_type()(param)
                except: return
            
            value = self._rail_value(param, value)
            self.current_program.pedal2_values[param.value] = value
            
            if param.value == 0:
                value_big, value = divmod(value, 128)
            
        elif vox_index is VoxIndex.REVERB:
            if isinstance(param, int):
                try: param = \
                    self.current_program.reverb_type.param_type()(param)
                except: return
            
            value = self._rail_value(param, value)
            self.current_program.reverb_values[param.value] = value
        
        self._send_vox(FunctionCode.PARAMETER_CHANGE,
                       vox_index.value, param.value, value, value_big)
        self._send_cb(EngineCallback.PARAM_CHANGED, 
                      (self.current_program, vox_index, param.value))
    
    @in_midi_thread()
    def set_program_name(self, new_name: str):
        new_name = unidecode(new_name)
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
        self._send_cb(EngineCallback.PROGRAM_NAME_CHANGED, new_name)
    
    @in_midi_thread()
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
            self._send_cb(EngineCallback.CURRENT_CHANGED, self.current_program)

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
            self._send_cb(EngineCallback.CURRENT_CHANGED, self.current_program)

    @in_midi_thread()
    def set_user_bank_num(self, bank_num: int):
        bank_num = min(max(bank_num, 0), 7)
        self._send_vox(
            FunctionCode.MODE_CHANGE, VoxMode.USER.value, bank_num)
        self.current_program = self.programs[bank_num].copy()
        self.prog_num = bank_num
        self._send_cb(EngineCallback.CURRENT_CHANGED, self.current_program)

    @in_midi_thread()
    def set_preset_num(self, bank_num: int):
        bank_num = min(max(bank_num, 0), 59)
        self._send_vox(
            FunctionCode.MODE_CHANGE, VoxMode.PRESET.value, bank_num)
        self.current_program = self.factory_programs[bank_num].copy()
        self.prog_num = bank_num
        self._send_cb(EngineCallback.CURRENT_CHANGED, self.current_program)

    @in_midi_thread()
    def upload_current_to_user_program(self, bank_num: int):
        self._send_vox(
            FunctionCode.PROGRAM_DATA_DUMP,
            VoxMode.USER.value,
            bank_num,
            *self.current_program.data_write())
        self.programs[bank_num] = self.current_program.copy()

    @in_midi_thread()
    def upload_current_to_user_ampfx(self, ampfx_num: int):
        self._send_vox(
            FunctionCode.CUSTOM_AMPFX_DATA_DUMP,
            0,
            ampfx_num,
            *self.current_program.ampfx_data_write())

        self.user_ampfxs[ampfx_num] = self.current_program.copy()
        
    # file managing

    @in_midi_thread()
    def set_project_path(self, project_path: Path):
        self.project_path = project_path
        if not self.project_path.exists():
            return
        
        for path in self.project_path.iterdir():
            if len(path.name) > 21:
                # do not accept too long file name
                # 16 chrs + '.json'
                continue
            
            if not str(path).endswith('.json'):
                continue
            
            try:
                with open(path, 'r') as f:
                    program = VoxProgram.from_json_dict(json.load(f))
            except:
                _logger.warning(
                    f'Failed to load {path.name} in local programs')
                continue
            
            program_name = unidecode(path.name.rpartition('.')[0])
            program.program_name = program_name
            self.local_programs[program_name] = program
        
        self._send_cb(EngineCallback.LOCAL_PROGRAMS_CHANGED, None)

    @in_midi_thread()
    def save_to_local_program(self, program_name: str):
        try:
            self.project_path.mkdir(exist_ok=True, parents=True)
        except:
            _logger.warning(
                f'Failed to create {self.project_path} dir, '
                'impossible to save program')
            return
        
        program_path = self.project_path / f'{program_name}.json'
        try:
            with open(program_path, 'w') as f:
                json.dump(self.current_program.to_json_dict(), f)
        except:
            _logger.warning(
                f'Failed to save {program_name} in {program_path}')
            return
        
        self.local_programs[program_name] = self.current_program.copy()
        self._send_cb(EngineCallback.LOCAL_PROGRAMS_CHANGED, None)
    
    @in_midi_thread()
    def load_local_program(self, program_name: str):
        local_pg = self.local_programs.get(program_name)
        if local_pg is None:
            _logger.critical(
                f'program {program_name} does not exists in local programs')
            return
        
        self.current_local_pg_name = program_name
        self._send_vox(
            FunctionCode.CURRENT_PROGRAM_DATA_DUMP,
            *local_pg.data_write())
        self.current_program = local_pg.copy()
        self._send_cb(EngineCallback.CURRENT_CHANGED, self.current_program)
        self._send_cb(EngineCallback.LOCAL_PROGRAMS_CHANGED, program_name)
    
    def save_current_program_to_disk(self, filepath: Path):
        try:
            with open(filepath, 'w') as f:
                json.dump(self.current_program.to_json_dict(), f, indent=2)
        except BaseException as e:
            _logger.error(f"Failed to save json file {filepath}"
                          f"{str(e)}")
    
    @in_midi_thread()
    def load_program_from_disk(self, filepath: Path):
        try:
            with open(filepath , 'r') as f:
                program = VoxProgram.from_json_dict(json.load(f))
        except BaseException as e:
            _logger.error(f'Failed to load program {filepath}\n{str(e)}')
            return
        
        self.load_program(program)
    
    @in_midi_thread()
    def load_program(self, program: VoxProgram):
        self._send_vox(
            FunctionCode.CURRENT_PROGRAM_DATA_DUMP,
            *program.data_write())
        self.current_program = program.copy()
        self._send_cb(EngineCallback.CURRENT_CHANGED, self.current_program)
    
    @in_midi_thread()
    def load_bank(self, in_program: VoxProgram, out_bank_index: int):
        if not 0 <= out_bank_index <= 7:
            _logger.error(
                f'can not load bank to out_bank_index {out_bank_index}')
            return
        
        self._send_vox(
            FunctionCode.PROGRAM_DATA_DUMP,
            VoxMode.USER.value,
            out_bank_index,
            *in_program.data_write())
        
        self.programs[out_bank_index] = in_program.copy()
    
    @in_midi_thread()
    def load_ampfx(self, in_program: VoxProgram, out_ampfx_index: int):
        if not 0 <= out_ampfx_index <= 3:
            _logger.error(
                f'can not load ampfx to ampfx index {out_ampfx_index}')
            return
        self._send_vox(
            FunctionCode.CUSTOM_AMPFX_DATA_DUMP,
            0,
            out_ampfx_index,
            *in_program.ampfx_data_write())
        
        self.user_ampfxs[out_ampfx_index] = in_program.copy()
    
    def save_all_amp(self, filepath: Path, with_ampfxs=True):
        full_dict = {}
        full_dict['banks'] = [p.to_json_dict() for p in self.programs]
        if with_ampfxs:
            full_dict['ampfxs'] = [p.to_json_dict(for_ampfx=True)
                                   for p in self.user_ampfxs]

        try:
            with open(filepath, 'w') as f:
                json.dump(full_dict, f, indent=2)

        except BaseException as e:
            _logger.error(f"Failed to save json file {filepath}"
                          f"{str(e)}")
    
    @in_midi_thread()
    def load_full_amp(self, filepath: Path, with_ampfxs=True) -> False:
        try:
            with open(filepath, 'r') as f:
                full_dict = json.load(f)
        except BaseException as e:
            _logger.error(
                f'Failed to load full amp file {filepath}\n{str(e)}')
            return False
        
        if not isinstance(full_dict, dict):
            return False
        
        banks_dict = full_dict.get('banks')
        if not isinstance(banks_dict, list):
            return False

        for bank_num in range(len(banks_dict)):
            if bank_num > 7:
                break
            
            program = VoxProgram.from_json_dict(banks_dict[bank_num])
            
            self._send_vox(
                FunctionCode.PROGRAM_DATA_DUMP,
                VoxMode.USER.value,
                bank_num,
                *program.data_write())
            
            self.programs[bank_num] = program
            
        if not with_ampfxs:
            return True
        
        ampfxs_dict = full_dict.get('ampfxs')
        if not isinstance(ampfxs_dict, list):
            return False
        
        for ampfx_n in range(len(ampfxs_dict)):
            if ampfx_n > 3:
                break
            
            program = VoxProgram.from_json_dict(ampfxs_dict[ampfx_n])
            
            self._send_vox(
                FunctionCode.CUSTOM_AMPFX_DATA_DUMP,
                0,
                ampfx_n,
                *program.ampfx_data_write())
            
            self.user_ampfxs[ampfx_n] = program
