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
        for effect_on_off in EffectOnOff:
            self.active_effects[effect_on_off] = 0
        self.amp_model = AmpModel.DELUXE_CL_VIBRATO
        self.amp_params = dict[AmpParam, int]()
        for amp_param in AmpParam:
            self.amp_params[amp_param] = 0
        self.pedal1_type = Pedal1Type.COMP
        self.pedal2_type = Pedal2Type.FLANGER
        self.reverb_type = ReverbType.ROOM
        self.pedal1_values = [0, 0, 0, 0, 0, 0]
        self.pedal2_values = [0, 0, 0, 0, 0, 0]
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
        p.pedal2_type = self.pedal2_type
        p.reverb_type = self.reverb_type

        for i in range(6):
            p.pedal1_values[i] = self.pedal1_values[i]
            p.pedal2_values[i] = self.pedal2_values[i]
            if i < 5:
                p.reverb_values[i] = self.reverb_values[i]
        
        return p

    def to_json_dict(self) -> dict:
        d = {}
        d['program_name'] = self.program_name
        d['nr_sens'] = self.nr_sens
        
        dae = {}
        for eff_onff, value in self.active_effects.items():
            dae[eff_onff.name] = value
        d['active_effects'] = dae
        
        d['amp_model'] = self.amp_model.name
        
        dam = {}
        for amp_param, value in self.amp_params.items():
            dam[amp_param.name] = value
        d['amp_params'] = dam
        
        d['pedal1_type'] = self.pedal1_type.name
        d['pedal1_values'] = self.pedal1_values.copy()
        d['pedal2_type'] = self.pedal2_type.name
        d['pedal2_values'] = self.pedal2_values.copy()
        d['reverb_type'] = self.reverb_type.name
        d['reverb_values'] = self.reverb_values.copy()
        
        return d
    
    @staticmethod
    def from_json_dict(d: dict) -> 'VoxProgram':
        p = VoxProgram()

        try:
            p.program_name = str(d['program_name'])
            p.nr_sens = int(d['nr_sens'])

            for effect_on_off in EffectOnOff:
                p.active_effects[effect_on_off] = \
                    int(d['active_effects'][effect_on_off.name])

            p.amp_model = AmpModel[d['amp_model']]

            for amp_param in AmpParam:
                p.amp_params[amp_param] = int(d['amp_params'][amp_param.name])

            p.pedal1_type = Pedal1Type[d['pedal1_type']]
            p.pedal2_type = Pedal2Type(d['pedal2_type'])
            p.reverb_type = ReverbType(d['reverb_type'])
            
            for i in range(6):
                p.pedal1_values[i] = int(d['pedal1_values'][i])
                p.pedal2_values[i] = int(d['pedal2_values'][i])
                if i < 5:
                    p.reverb_values[i] = int(d['reverb_values'][i])

        except BaseException as e:
            _logger.error(
                "Failed to read input dict vox program !"
                f"Program may have some default values. \n{str(e)}")

        return p
        
    def read_data(self, shargs: list[int]):
        unused = shargs.pop(0)
        pname_intor, shargs = shargs[:18], shargs[18:]
        pname_int = pname_intor[:7] + pname_intor[8:15] + pname_intor[16:18]
        self.program_name = ''.join([chr(p) for p in pname_int])
        
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
        pedal1_exceed_i = shargs.pop(0)
        
        amp_params[AmpParam.MID_BOOST] = shargs.pop(0)
        amp_params[AmpParam.BIAS_SHIFT] = shargs.pop(0)
        amp_params[AmpParam.CLASS] = shargs.pop(0)
        
        pedal1_type_int = shargs.pop(0)
        pedal1_values, shargs = shargs[:8], shargs[8:]
        
        # delete one unused number
        pedal2_exceed_i = pedal1_values.pop(3)

        self.pedal1_type = Pedal1Type(pedal1_type_int)

        self.pedal1_values[0] = pedal1_values[0] + pedal1_values[1] * 256
        if pedal1_exceed_i & 0x10:
            self.pedal1_values[0] += 128

        for i in range(1, 6):
            self.pedal1_values[i] = pedal1_values[i + 1]
        
        pedal2_type_int = shargs.pop(0)
        pedal2_values, shargs = shargs[:9], shargs[9:]
        
        # delete one unused number
        pedal2_values.__delitem__(2)
        
        self.pedal2_type = Pedal2Type(pedal2_type_int)
        
        self.pedal2_values[0] = pedal2_values[0] + pedal2_values[1] * 256
        if pedal2_exceed_i & 0x20:
            self.pedal2_values[0] += 128

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

    def data_write(self) -> list[int]:
        out = list[int]()
        
        # 1 unused
        out.append(0)
        
        # program name
        name_ints = [ord(c) for c in self.program_name]
        name_ints.insert(7, 0)
        name_ints.insert(15, 0)
        out += name_ints
        
        print(len(out), 'aft_name')
        
        # noise gate
        out.append(self.nr_sens)

        effect_status = EffectStatus.ALL_OFF
        if self.active_effects[EffectOnOff.PEDAL1]:
            effect_status |= EffectStatus.PEDAL1_ON
        if self.active_effects[EffectOnOff.PEDAL2]:
            effect_status |= EffectStatus.PEDAL2_ON
        if self.active_effects[EffectOnOff.REVERB]:
            effect_status |= EffectStatus.REVERB_ON
        out.append(effect_status.value)
        
        print(len(out), 'aft eff status')
        
        out.append(self.amp_model.value)
        
        # amp params
        out.append(self.amp_params[AmpParam.GAIN])
        out.append(self.amp_params[AmpParam.TREBLE])
        out.append(0)
        out.append(self.amp_params[AmpParam.MIDDLE])
        out.append(self.amp_params[AmpParam.BASS])
        out.append(self.amp_params[AmpParam.VOLUME])
        out.append(self.amp_params[AmpParam.TONE])
        out.append(self.amp_params[AmpParam.RESONANCE])
        out.append(self.amp_params[AmpParam.BRIGHT_CAP])
        out.append(self.amp_params[AmpParam.LOW_CUT])
        
        # Amp needs to know if chorus first value exceed 127
        out.append(16 if self.pedal1_values[0] % 256 > 127 else 0)

        out.append(self.amp_params[AmpParam.MID_BOOST])
        out.append(self.amp_params[AmpParam.BIAS_SHIFT])
        out.append(self.amp_params[AmpParam.CLASS])
        
        print(len(out), 'aft amp params')
        
        out.append(self.pedal1_type.value)
            
        big, small = divmod(self.pedal1_values[0], 256)
        out.append(small % 128)
        out.append(big)
        out.append(self.pedal1_values[1])        
        
        # Amp needs to know if effect2 first value exceed 127
        out.append(32 if self.pedal2_values[0] % 256 > 127 else 0)

        out += self.pedal1_values[2:]
        
        print(len(out), 'aft pedal1 params')
        
        out.append(self.pedal2_type.value)
        big, small = divmod(self.pedal2_values[0], 256)
        out.append(small % 128)
        out.append(big)
        out.append(0)
        out += self.pedal2_values[1:]
        
        print(len(out), 'aft pedal2 params')
        
        for i in range(9):
            out.append(0)
        
        print(len(out), 'before reverb')
        
        out.append(self.reverb_type.value)
        out.append(0)
        out += self.reverb_values
        
        out.append(0)
        out.append(247)
        
        return out

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

