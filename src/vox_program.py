import logging

from effects import (
    EffectOnOff, AmpModel, AmpParam, Pedal1Type, Pedal2Type,
    ReverbType, EffectStatus, ReverbParam, EffParam)

_logger = logging.getLogger(__name__)

class VoxProgram:
    def __init__(self):
        self.program_name = ''
        self.nr_sens = 0
        self.active_effects = dict[EffectOnOff, int]()
        self.amp_model = AmpModel.DELUXE_CL_VIBRATO
        self.amp_params = dict[AmpParam, int]()
        self.pedal1_type = Pedal1Type.COMP
        self.pedal1_values = [0, 0, 0, 0, 0, 0]
        self.pedal2_type = Pedal2Type.FLANGER
        self.pedal2_values = [0, 0, 0, 0, 0, 0]
        self.reverb_type = ReverbType.ROOM
        self.reverb_values = [0, 0, 0, 0, 0]

    def copy(self) -> 'VoxProgram':
        p = VoxProgram()
        p.program_name = self.program_name
        p.nr_sens = self.nr_sens
        for effonoff, value in self.active_effects.items():
            p.active_effects[effonoff] = value
        p.amp_model = self.amp_model
        for amp_param, value in self.amp_params.items():
            p.amp_params[amp_param] = value
        p.pedal1_type = self.pedal1_type
        for i in range(6):
            p.pedal1_values[i] = self.pedal1_values[i]
        p.pedal2_type = self.pedal2_type
        for i in range(6):
            p.pedal2_values[i] = self.pedal2_values[i]
        p.reverb_type = self.reverb_type
        for i in range(5):
            p.reverb_values[i] = self.reverb_values[i]
        
        return p

    def read_data(self, shargs: list[int]):
        pname_int, shargs = shargs[:17], shargs[17:]
        pname_int = pname_int[:8] + pname_int[9:]
        self.program_name = ''.join([chr(p) for p in pname_int])

        # 2 not documented numbers
        shargs = shargs[2:]
        
        self.nr_sens = shargs.pop(0)
        effects_status = EffectStatus(shargs.pop(0))
        self.active_effects.clear()

        if effects_status & EffectStatus.PEDAL1_ON:
            self.active_effects[EffectOnOff.PEDAL1] = 1
        else:
            self.active_effects[EffectOnOff.PEDAL1] = 0
            
        if effects_status & EffectStatus.PEDAL2_ON:
            self.active_effects[EffectOnOff.PEDAL2] = 1
        else:
            self.active_effects[EffectOnOff.PEDAL2] = 0
        
        if effects_status & EffectStatus.REVERB_ON:
            self.active_effects[EffectOnOff.REVERB] = 1
        else:
            self.active_effects[EffectOnOff.REVERB] = 0
        
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

        self.pedal1_values[0] = pedal1_values[0] + pedal1_values[1] * 256
        for i in range(1, 6):
            self.pedal1_values[i] = pedal1_values[i + 1]
        
        pedal2_type_int = shargs.pop(0)
        pedal2_values, shargs = shargs[:9], shargs[9:]
        
        # delete one unused number
        pedal2_values.__delitem__(2)
        
        self.pedal2_type = Pedal2Type(pedal2_type_int)
        
        self.pedal2_values[0] = pedal2_values[0] + pedal2_values[1] * 256
        for i in range(1, 6):
            self.pedal2_values[i] = pedal2_values[i + 1]
        
        # 8 documented reserved numbers + 2 undocumented
        shargs = shargs[8:]
                    
        reverb_type_int = shargs.pop(0)
        reverb_values, shargs = shargs[:6], shargs[6:]
        reverb_values.__delitem__(0)

        self.reverb_type = ReverbType(reverb_type_int)

        for reverb_param in ReverbParam:
            self.reverb_values[reverb_param.value] = \
                reverb_values[reverb_param.value]

    def read_data_preset(self, shargs: list[int]):
        # 16 samples reserved + 3 undocumented
        shargs = shargs[19:]
        print('odo', shargs)
        # shargs.pop(0)
        
        self.nr_sens = shargs.pop(0)
        
        tralala = shargs.pop(0)
        print(tralala, EffectStatus(tralala))
        data_bits = EffectStatus(tralala)
        if data_bits & EffectStatus.PEDAL1_ON:
            self.active_effects[EffectOnOff.PEDAL1] = 1
        else:
            self.active_effects[EffectOnOff.PEDAL1] = 0
    
        if data_bits & EffectStatus.PEDAL2_ON:
            self.active_effects[EffectOnOff.PEDAL2] = 1
        else:
            self.active_effects[EffectOnOff.PEDAL2] = 0
            
        if data_bits & EffectStatus.REVERB_ON:
            self.active_effects[EffectOnOff.REVERB] = 1
        else:
            self.active_effects[EffectOnOff.REVERB] = 0
        
        self.amp_model = AmpModel(shargs.pop(0))
        
        # 5 documented reserved
        shargs = shargs[6:]
        
        self.amp_params[AmpParam.TONE] = shargs.pop(0)
        self.amp_params[AmpParam.RESONANCE] = shargs.pop(0)
        self.amp_params[AmpParam.BRIGHT_CAP] = shargs.pop(0)
        self.amp_params[AmpParam.LOW_CUT] = shargs.pop(0)
        self.amp_params[AmpParam.MID_BOOST] = shargs.pop(0)
        self.amp_params[AmpParam.BIAS_SHIFT] = shargs.pop(0)
        
        unused = shargs.pop(0)
        
        self.amp_params[AmpParam.CLASS] = shargs.pop(0)
        
        self.pedal1_type = Pedal1Type(shargs.pop(0))
        pedal1_values, shargs = shargs[:7], shargs[7:]
        
        eff_param: EffParam
        for eff_param in self.pedal1_type.param_type():
            if eff_param.value == 0:
                value = pedal1_values[0] + pedal1_values[1] * 256
            else:
                value = pedal1_values[eff_param.value + 1]
        
            self.pedal1_values[eff_param.value] = value   
        
        # self.pedal2_type = Pedal2Type(shargs.pop(0))
        # pedal2_values, shargs = shargs[:7], shargs[7:]

        # self.pedal2_params.clear()
        
        # for eff_param in self.pedal2_type.param_type():
        #     if eff_param.value == 0:
        #         value = pedal2_values[0] + pedal2_values[1] * 256
        #     else:
        #         value = pedal2_values[eff_param.value + 1]
        
        #     self.pedal2_params[eff_param] = value
        
        # # 7 reserved documented
        # shargs = shargs[7:]
        
        # self.reverb_type = ReverbType(shargs.pop(0))
        # reverb_values, shargs = shargs[:6], shargs[6:]
        
        # for reverb_param in ReverbParam:
        #     self.reverb_params[reverb_param] = reverb_values[reverb_param.value]
        
        
    def print_program(self):
        print('prog name :', self.program_name)
        print('nr sens', self.nr_sens)
        print('AMP :', self.amp_model.name)
        amp_param: AmpParam
        for amp_param, value in self.amp_params.items():
            mini, maxi, unit = amp_param.range_unit()
            if value < mini:
                _logger.warning(f'{amp_param.name} : value {value} is < to min {mini}')
            elif value > maxi:
                _logger.warning(f'{amp_param.name} : value {value} is > to max {maxi}')
            print('  ', amp_param.name, ':', value, unit)
    
        print('PEDAL1 :', self.pedal1_type.name, self.active_effects[EffectOnOff.PEDAL1])
        eff_param: EffParam
        for eff_param in self.pedal1_type.param_type():
            value = self.pedal1_values[eff_param.value]
        
            mini, maxi, unit = eff_param.range_unit()
            if value < mini:
                _logger.warning(f'{eff_param.name} : value {value} is < to min {mini}')
            elif value > maxi:
                _logger.warning(f'{eff_param.name} : value {value} is > to max {maxi}')
            print('  ', eff_param.name, ':', value, unit)
        
        print('PEDAL2 :', self.pedal2_type.name, self.active_effects[EffectOnOff.PEDAL2])
        for eff_param in self.pedal2_type.param_type():
            value = self.pedal2_values[eff_param.value]
            
            mini, maxi, unit = eff_param.range_unit()
            if value < mini:
                _logger.warning(f'{eff_param.name} : value {value} is < to min {mini}')
            elif value > maxi:
                _logger.warning(f'{eff_param.name} : value {value} is > to max {maxi}')
            print('  ', eff_param.name, ':', value, unit)
            
        print('REVERB :', self.reverb_type.name, self.active_effects[EffectOnOff.REVERB])
        for reverb_param in ReverbParam:
            value = self.reverb_values[reverb_param.value]
            mini, maxi, unit = reverb_param.range_unit()
            if value < mini:
                _logger.warning(f'{reverb_param.name} : value {value} is < to min {mini}')
            elif value > maxi:
                _logger.warning(f'{reverb_param.name} : value {value} is > to max {maxi}')
            
            print('  ', reverb_param.name, ':', value, unit)

    def change_pedal1_type(self, pedal1_type: Pedal1Type):
        self.pedal1_type = pedal1_type
                
    def change_pedal2_type(self, pedal2_type: Pedal2Type):
        self.pedal2_type = pedal2_type
