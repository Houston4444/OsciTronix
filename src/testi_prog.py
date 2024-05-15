envoi = [240, 66, 48, 0, 1, 52, 64, 0, 67, 104, 105, 108, 108, 105, 98, 0, 111, 117, 109, 97, 100, 32, 32, 0, 32, 32, 41, 16, 7, 72, 61, 0, 51, 50, 70, 39, 58, 1, 0, 0, 0, 0, 0, 5, 50, 0, 100, 0, 64, 50, 50, 50, 4, 80, 20, 0, 41, 13, 26, 50, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 21, 32, 0, 0, 0, 0, 247]

envoi = [240, 66, 48, 0, 1, 52, 64, 0, 122, 112, 101, 111, 102, 107, 32, 0, 32, 32, 32, 32, 32, 32, 32, 0, 32, 32, 41, 22, 7, 72, 61, 0, 51, 50, 70, 39, 58, 1, 0, 0, 0, 0, 0, 5, 50, 0, 100, 32, 64, 50, 50, 50, 4, 19, 20, 0, 41, 13, 26, 50, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 21, 32, 0, 0, 0, 0, 247]

from vox_program import VoxProgram
from voxou import SYSEX_BEGIN, FunctionCode
shargs = envoi[6:]
function_code = FunctionCode(shargs.pop(0))

vox_program = VoxProgram()
vox_program.read_data(shargs.copy())

# unused = envoil.pop(0)

print(shargs)


datav = vox_program.data_write()
print(datav)
print(len(datav), len(shargs))

print(vox_program.to_json_dict())

for i in range(min(len(datav), len(shargs))):
    if datav[i] != shargs[i]:
        print('tamzm', i, '|', datav[i], '!=', shargs[i])

"""
si Valeur % 256 > 127:
    

avec CHORUS
    si <= 127:
        ok
    sinon:
        item 32 = 16

avec phasers ou DELAY
    toutes les valeurs sont bonnes
avec FLANGER ou TREMOLO
    # ATTENTION avec FLANGER
        si V % 256 <= 127:
            item 40 = 0
            valeur OK 
        sinon
            item 40 = 32
            resultat 128 trop bas, il faut ajouter 128
"""

# name_ints, envoil = envoil[:18], envoil[18:]
# name_ints = name_ints[:7] + name_ints[8:15] + name_ints[16:18]

# program_name = ''.join([chr(i) for i in name_ints])

# print(function_code.name)
# print(f"'{program_name}'")
# print(envoil)