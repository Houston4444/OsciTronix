from typing import Callable, Optional
import json
from app_infos import APP_NAME
from effects import AmpParam, CompParam, DummyParam, EffParam, EffectOnOff, Pedal1Type, ReverbParam, VoxIndex, VoxMode

from liblo import Message, Server, make_method, Address

from engine import Engine, EngineCallback
from vox_program import VoxProgram


def osci_method():
    pass


PFX = f'/{APP_NAME.lower()}/'


class OscUdpServer(Server):
    def __init__(self, port=0):
        if port:
            Server.__init__(self, port)
        else:
            Server.__init__(self)
        self.engine: Optional[Engine] = None

        self._add_m('register', '', self._register)
        self._add_m('unregister', '', self._unregister)
        self._add_m('current/set_param_value', 'iii', self._set_param_value)
        
        self._add_m('current/program_name', 's', self._set_program_name)
        
        self._clients = set[Address]()

    def json_short(self) -> str:
        'returns the current program state in a condensed json format string'
        return json.dumps(
            self.engine.current_program.to_json_dict(),
            separators=(',', ':'))

    def engine_callback(self, cb: EngineCallback, arg):
        PFXREG = PFX + 'reg/'
        msg = None
        
        if cb is EngineCallback.COMMUNICATION_STATE:
            comm_state: bool = arg
            msg = Message(PFXREG + 'communication_state', int(comm_state))

        elif cb is EngineCallback.CURRENT_CHANGED:
            msg = Message(
                PFXREG + 'program_changed', self.json_short())

        elif cb is EngineCallback.MODE_CHANGED:
            vox_mode: VoxMode = arg
            msg = Message(PFXREG + 'mode_changed', vox_mode.name)

        elif cb is EngineCallback.PARAM_CHANGED:
            program, vox_index, param_index = arg
            program: VoxProgram
            vox_index: VoxIndex
            param_index: int
            
            PCUR = PFXREG + 'current/'
            
            if vox_index is VoxIndex.NR_SENS:
                msg = Message(PCUR + 'nr_sens', program.nr_sens)

            elif vox_index is VoxIndex.EFFECT_MODEL:
                param = EffectOnOff(param_index)
                path = PCUR + param.name.lower()

                if param is EffectOnOff.AMP:
                    msg = Message(path, program.amp_model.name)
                    
                elif param is EffectOnOff.PEDAL1:
                    msg = Message(path, program.pedal1_type.name)

                elif param is EffectOnOff.PEDAL2:
                    msg = Message(path, program.pedal2_type.name)
                
                elif param is EffectOnOff.REVERB:
                    msg = Message(path, program.reverb_type.name)
                    
            elif vox_index is VoxIndex.AMP:
                amp_param = AmpParam(param_index)
                msg = Message(
                    f'{PCUR}amp/{amp_param.name.lower()}/',
                    program.amp_params[amp_param])
            
            elif vox_index is VoxIndex.EFFECT_STATUS:
                param = EffectOnOff(param_index)
                if param is EffectOnOff.AMP:
                    return

                msg = Message(PCUR + param.name.lower() + '/active',
                              program.active_effects[param])
            
            elif vox_index in (
                    VoxIndex.PEDAL1, VoxIndex.PEDAL2, VoxIndex.REVERB):
                if vox_index is VoxIndex.PEDAL1:
                    param = program.pedal1_type.param_type()(param_index)
                    value = program.pedal1_values[param_index]
                elif vox_index is VoxIndex.PEDAL2:
                    param = program.pedal2_type.param_type()(param_index)
                    value = program.pedal2_values[param_index]
                else:
                    param = ReverbParam(param_index)
                    value = program.pedal2_values[param_index]
                
                msg = Message(
                    f'{PCUR}{vox_index.name.lower()}/{param.name.lower()}',
                    value)
        
        if msg is None:
            return
        
        for reg in self._clients:
            self.send(reg, msg)

    def set_engine(self, engine: Engine):
        self.engine = engine
        self.engine.add_callback(self.engine_callback)

    def _add_m(self, path: str, type_spec: str, func: Callable):
        self.add_method(PFX + path, type_spec, func)
    
    # @make_method('/oscitronix/register', '')
    def _register(self, path: str, args: list, types: str, src_addr: Address):
        print('_register', src_addr.url)
        self._clients.add(src_addr)

        cur_prog = self.engine.current_program
        prog_str = json.dumps(cur_prog.to_json_dict(), separators=(',', ':'))
        
        self.send(src_addr, PFX + 'current/get_json', prog_str)
        
    def _unregister(self, path: str, args: list, types: str, src_addr: Address):
        if src_addr in self._clients:
            self._clients.remove(src_addr)

    def _set_param_value(
            self, path: str, args: list[int], types: str, src_addr: Address):
        print('sett param value', args)
        self.engine.set_param_value(*args)

    def _set_program_name(
            self, path: str, args: list[str], types: str, src_addr: Address):
        program_name = args[0]
        # self.engine.current_program.program_name
    