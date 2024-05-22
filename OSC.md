
/oscitronix/get_current_program
set_current_program s
list_custom_programs
    /reply path *program_names

/oscitronix/register i (0: normal, 1: json)
    renvoie pour chaque valeur et à chaque fois que ça change
    /oscitronix/current/program_name s
    /oscitronix/current/nr_sens i
    /oscitronix/current/amp_model s
    /oscitronix/current/amp/gain iii (value, min, maxi)
    ...
    /oscitronix/current/pedal1 s i (type, onoff)
    /oscitronix/current/pedal1/sens i i i s (value, min, max, unit)
    ...

/oscitronix/current/set/program_name
/oscitronix/current/get_json
/oscitronix/custom/set custom_name

/oscitronix/current/get_json
 -> /oscitronix/current/json s
list_params
    for each param
    /reply path 