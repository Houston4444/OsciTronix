from effects import AmpModel, EffParam, Pedal1Type, Pedal2Type, ReverbType

if __name__ == '__main__':
    for pedal_type in (Pedal1Type, Pedal2Type, ReverbType):
        print(pedal_type)
        
        params = [45, 14, 12, 65, 67, 23, 84]
        pedal_1_type_int = 7
        
        if pedal_type is Pedal1Type:
            eff_type = Pedal1Type(pedal_1_type_int)
            print('ZMMEMC', eff_type)
            eff_param: EffParam

            for eff_param in eff_type.param_type():
                if eff_param.value == 0:
                    value = params[0] + params[1] * 128
                else:
                    value = params[eff_param.value + 1]
                
                mini, maxi, unit = eff_param.range_unit()
                if value < mini:
                    print('trop petit', value, '<', mini)
                    value = mini
                elif value > maxi:
                    print('trop grand', value, '>', maxi)
                    value = maxi
                
                print('', eff_param.name, ':', value, unit)
                # if eff_param.value == 0:
                #     print('', eff_param.name, ':', params[0] + params[1] * 128,
                #           eff_param.range_unit()[2])
                # else:
                #     print('', eff_param.name, ':', params[eff_param.value + 1],
                #           eff_param.range_unit()[2])
        
        # for eff_type in pedal_type:
        #     print('', eff_type.value, eff_type.name)
        #     eff_param: EffParam
        #     for eff_param in eff_type.param_type():
        #         mini, maxi, unit = eff_param.range_unit()
        #         print('  ', eff_type.index_prefix(), eff_param.value, eff_param.name, mini, maxi, unit)