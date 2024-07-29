import logging
from typing import Callable, Iterator, Optional
import json

from liblo import Message, Server, Address

from engine import CommunicationState, Engine, EngineCallback
from vox_program import VoxProgram
from app_infos import APP_NAME
from effects import (
    AmpModel, AmpParam, ChorusParam, CompParam, DelayParam,
    DistortionParam, DummyParam, EffParam, EffectOnOff,
    FlangerParam, OverdriveParam, Pedal1Type, Pedal2Type,
    PhaserParam, ReverbParam, ReverbType, TremoloParam,
    VoxIndex, VoxMode)


_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)

PFX = f'/{APP_NAME.lower()}/'


def pedal1_params() -> Iterator[EffParam]:
    for comp_param in CompParam:
        yield comp_param
    for chorus_param in ChorusParam:
        yield chorus_param
    for overdrive_param in OverdriveParam:
        yield overdrive_param
    for distortion_param in DistortionParam:
        yield distortion_param

def pedal2_params() -> Iterator[EffParam]:
    for flanger_param in FlangerParam:
        yield flanger_param
    for phaser_param in PhaserParam:
        yield phaser_param
    for tremolo_param in TremoloParam:
        yield tremolo_param
    for delay_param in DelayParam:
        yield delay_param


class OscUdpServer(Server):
    def __init__(self, port=0):
        if port:
            Server.__init__(self, port)
        else:
            Server.__init__(self)
            
        self.terminate = False
        self.engine: Optional[Engine] = None

        self._add_m('register', '', self._register)
        self._add_m('unregister', '', self._unregister)
        self._add_m('load_local_program', 's', self._load_local_program)
        self._add_m('current/set_param_value', 'iii', self._set_param_value)
        self._add_m('current/program_name', 's', self._set_program_name)

        # set OSC methods with one int argument
        ipaths = set[str]()
        
        ipaths.add('current/nr_sens')

        for eff in ('amp', 'pedal1', 'pedal2', 'reverb'):
            ipaths.add(f'current/{eff}/type')
            if eff != 'amp':
                ipaths.add(f'current/{eff}/active')

        for amp_param in AmpParam:
            ipaths.add(f'current/amp/{amp_param.name.lower()}')
        ipaths.add('current/amp/presence')

        for pedal1_param in pedal1_params():
            ipaths.add(f'current/pedal1/{pedal1_param.name.lower()}')

        for pedal2_param in pedal2_params():
            ipaths.add(f'current/pedal2/{pedal2_param.name.lower()}')

        for reverb_param in ReverbParam:
            ipaths.add(f'current/reverb/{reverb_param.name.lower()}')
        
        for ipath in ipaths:
            self._add_m(ipath, 'i', self._set_current_param_int)
        
        # set OSC methods with one string argument
        
        spaths = [f'current/{p}/type'
                  for p in ('amp', 'pedal1', 'pedal2', 'reverb')]
        for spath in spaths:
            self._add_m(spath, 's', self._set_current_param_str)
        
        self._registereds = set[Address]()

    def json_short(self) -> str:
        'returns the current program state in a condensed json format string'
        return json.dumps(
            self.engine.current_program.to_json_dict(),
            separators=(',', ':'))

    def engine_callback(self, cb: EngineCallback, arg):        
        PFXREG = PFX + 'reg/'
        msg = None
        
        if cb is EngineCallback.COMMUNICATION_STATE:
            comm_state: CommunicationState = arg
            msg = Message(PFXREG + 'communication_state',
                          int(comm_state.is_ok()))

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
                msg = Message(PCUR + 'nr_sens', program.nr_sens, 0, 100, '%')

            elif vox_index is VoxIndex.EFFECT_MODEL:
                param = EffectOnOff(param_index)
                path = PCUR + param.name.lower() + '/type'

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
                    f'{PCUR}amp/{amp_param.name.lower()}',
                    program.amp_params[amp_param],
                    *amp_param.range_unit())
            
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
                    value = program.reverb_values[param_index]
                
                msg = Message(
                    f'{PCUR}{vox_index.name.lower()}/{param.name.lower()}',
                    value, *param.range_unit())

        if msg is None:
            return
        
        for reg in self._registereds:
            self.send(reg, msg)

    def _set_current_param_int(
            self, path: str, args: list[int], types: str, src_addr: Address):
        # here path startswith '/oscitronix/current/'
        _logger.debug(f'_set_current_param_int {path}, {args[0]}')
        assert path.startswith('/oscitronix/current/')

        vox_index: Optional[VoxIndex] = None
        param: Optional[EffParam] = None
        value = args[0]

        start_cut = len(PFX) + len('current/')
        pathcur = path[start_cut:]

        if pathcur == 'nr_sens':
            vox_index = VoxIndex.NR_SENS
            param = DummyParam.DUMMY

        else:
            try:
                vox_index_str, param_name = pathcur.split('/')
                vox_index = VoxIndex[vox_index_str.upper()]
            except:
                _logger.debug(f'incorrect OSC path: {path}')
                return

        if param_name == 'active':
            if vox_index in (
                    VoxIndex.PEDAL1, VoxIndex.PEDAL2, VoxIndex.REVERB):   
                param = EffectOnOff[vox_index.name]
                vox_index = VoxIndex.EFFECT_STATUS
            else:
                _logger.debug(f'incorrect OSC path: {path}')
                return
        
        elif param_name == 'type':
            try:
                if vox_index is VoxIndex.AMP:
                    value = AmpModel(value).value
                    param = EffectOnOff.AMP
                elif vox_index is VoxIndex.PEDAL1:
                    value = Pedal1Type(value).value
                    param = EffectOnOff.PEDAL1
                elif vox_index is VoxIndex.PEDAL2:
                    value = Pedal2Type(value).value
                    param = EffectOnOff.PEDAL2
                elif vox_index is VoxIndex.REVERB:
                    value = ReverbType(value).value
                    param = EffectOnOff.REVERB
                else:
                    _logger.debug(f'incorrect OSC path: {path}')
                    return
            except:
                _logger.debug(f'incorrect OSC path: {path}')
                return
            
            vox_index = VoxIndex.EFFECT_MODEL
            
        elif vox_index is VoxIndex.AMP:
            if param_name == 'presence':
                param_name = 'tone'

            try:
                param = AmpParam[param_name.upper()]
            except:
                _logger.debug(f'incorrect OSC path: {path}')
                return
            
        elif vox_index is VoxIndex.PEDAL1:
            try:
                param = self.engine.current_program.pedal1_type.param_type()[
                    param_name.upper()]
            except:
                _logger.debug(f'incorrect OSC path: {path}')
                return
            
        elif vox_index is VoxIndex.PEDAL2:
            try:
                param = self.engine.current_program.pedal2_type.param_type()[
                    param_name.upper()]
            except:
                _logger.debug(f'incorrect OSC path: {path}')
                return
        
        elif vox_index is VoxIndex.REVERB:
            try:
                param = ReverbParam[param_name.upper()]
            except:
                _logger.debug(f'incorrect OSC path: {path}')
                return
        
        if param is None:
            _logger.debug(f'incorrect OSC path: {path}')
            return

        self.engine.set_param_value(vox_index, param, value)

    def _set_current_param_str(
            self, path: str, args: list[str], types: str, src_addr: Address):
        _logger.debug(f'_set_current_param_str {path}, {args[0]}')
        assert path.startswith('/oscitronix/current/')
        
        start_cut = len(PFX) + len('current/')
        pathcur = path[start_cut:]
        
        vox_index: Optional[VoxIndex] = None
        param: Optional[EffParam] = None
        value_str = args[0].upper().replace(' ', '_')
        value = 0
        
        if pathcur.endswith('/type'):
            vox_index = VoxIndex.EFFECT_MODEL
            pedal = pathcur.rpartition('/')[0]
            try:
                param = EffectOnOff[pedal.upper()]
                if param is EffectOnOff.AMP:
                    value = AmpModel[value_str].value
                elif param is EffectOnOff.PEDAL1:
                    value = Pedal1Type[value_str].value
                elif param is EffectOnOff.PEDAL2:
                    value = Pedal2Type[value_str].value
                elif param is EffectOnOff.REVERB:
                    value = ReverbType[value_str].value
            except:
                _logger.debug(f'Invalid OSC path: path')
            
        if vox_index is None or param is None:
            return
                
        self.engine.set_param_value(vox_index, param, value)

    def set_engine(self, engine: Engine):
        self.engine = engine
        self.engine.add_callback(self.engine_callback)

    def _add_m(self, path: str, type_spec: str, func: Callable):
        self.add_method(PFX + path, type_spec, func)
    
    def _register(self, path: str, args: list, types: str, src_addr: Address):
        self._registereds.add(src_addr)

        cur_prog = self.engine.current_program
        prog_str = json.dumps(cur_prog.to_json_dict(), separators=(',', ':'))
        
        self.send(src_addr, PFX + 'current/get_json', prog_str)
        
    def _unregister(self, path: str, args: list, types: str, src_addr: Address):
        if src_addr in self._registereds:
            self._registereds.remove(src_addr)

    def _load_local_program(
            self, path: str, args: list[str], types: str, src_addr: Address):
        self.engine.load_local_program(args[0])

    def _set_param_value(
            self, path: str, args: list[int], types: str, src_addr: Address):
        self.engine.set_param_value(*args)

    def _set_program_name(
            self, path: str, args: list[str], types: str, src_addr: Address):
        self.engine.set_program_name(args[0])
        
    def run_loop(self):
        while not self.terminate:
            self.recv(50)
    
    def stop_loop(self):
        self.terminate = True
    