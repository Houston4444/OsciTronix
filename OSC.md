
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


-------------------

All messages start with : /oscitronix/

/oscitronix/register
/oscitronix/unregister
/oscitronix/current/amp/gain i

messages that a registered program can receive
* reg/communication_state i (#TODO)
* reg/program_changed s (json string)
* reg/mode_changed s (can be PRESET, USER or MANUAL)
* reg/current/nr_sens i (noise gate)
* reg/current/amp/type s (amp model name)
* reg/current/amp/PARAM iiis (value, min, max, unit)
    where PARAM can be:
        gain
        treble
        middle
        bass
        volume
        tone
        presence
        resonance
        bright_cap
        low_cut
        mid_boost
        bias_shift
        class
* reg/current/pedal1/type s (pedal1 type)
* reg/current/pedal1/active i (1 active, 0 bypassed)
* reg/current/pedal1/PARAM iiis (value, min, max, unit)
    where PARAM can be:
        sens
        level
        attack
        voice
        speed
        depth
        manual
        mix
        low_cut
        high_cut
        drive
        tone
        treble
        middle
        basse
* reg/current/pedal2/type s (pedal2 type)
* reg/current/pedal2/active i (1 active, 0 bypassed)
* reg/current/reverb/type s (reverb type)
