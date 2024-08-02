# OsciTronix OSC documentation

## Introduction

All OsciTronix OSC paths starts with `/oscitronix/`, so, in this documentation, if a mentionned path does not start with a `/`, it means that you have to prepend it with `/oscitronix/`.
For example, full path for `current/amp/gain` is `/oscitronix/current/amp/gain`. 

You can specify the OSC port when you start the program via the command line interface.

Use `oscitronix --osc-port PORT_NUM`.

## Control

### Current program

You can control every parameter of the current program, with the following messages:

`current/nr_sens i`  Noise reduction

`current/amp/type s` set the amp model with its name  
`current/amp/type i` set the amp model with its index (0 to 19)
  
`current/amp/PARAM i`  where PARAM can be  
* gain
* treble
* middle
* bass
* tone
* presence
* resonance
* volume
* low_cut
* mid_boost
* bright_cap
* class
* bias_shift

for example: To set volume to 64/100, send `/oscitronix/current/amp/volume 64`.

`current/pedal1/active i` Pedal 1 On/Off (0: Bypassed, 1: On)  
`current/pedal1/type s` set the pedal 1 model with its name  
`current/pedal1/type i` set the pedal 1 model with its index (0 to 9)

`current/pedal1/PARAM i`  where PARAM can be
* sens
* level
* attack
* voice
* speed
* depth
* manual
* mix
* low_cut
* high_cut
* drive
* tone
* treble
* middle
* bass

`current/pedal2/active i` Pedal 2 On/Off (0: Bypassed, 1: On)  
`current/pedal2/type s` set the pedal 2 model with its name  
`current/pedal2/type i` set the pedal 2 model with its index (0 to 6)

`current/pedal2/PARAM i`  where PARAM can be
* speed
* depth
* manual
* low_cut
* high_cut
* resonance
* duty
* shape
* level
* time
* feedback
* tone
* mod_speed
* mod_depth

`current/reverb/active i` Reverb On/Off (0: Bypassed, 1: On)  
`current/reverb/type s` set the Reverb model with its name  
`current/reverb/type i` set the Reverb model with its index (0 to 3)

`current/reverb/PARAM i`  where PARAM can be
* mix
* time
* pre_delay
* low_damp
* high_damp

### Local Program

Local programs are saved in the computer, but you can not change their location with oscitronix.
If Oscitronix is started under NSM, they are stored in the `local_programs` dir in the NSM project dir, else they should be stored in `~/.local/share/Oscitronix/local_programs`.

You can save the current program to a local program with
`/oscitronix/save_to_local_program s` where argument is the program name.
If program name already exists it will be overwritten.

You can simply change the current program to a local program with this message:
`/oscitronix/load_local_program s` where argument is the program name.

## Register

### How to

You can register to OsciTronix to receive messages when parameters change, this way:   
`/oscitronix/register`

Please unregister if you quit :  
`/oscitronix/unregister`

### General messages

A registered program will receive  
`reg/communication_state i` (1 if communication with device is OK else 0)  

`reg/program_changed s` (json string)  
`reg/mode_changed s` (can be PRESET, USER or MANUAL)  

###  Current program

When a parameter is moved, a registered program will receive a message with the same path as the one used to set it, except the fact it starts with `reg/`.

For example: when volume is moved, the received message will be :  
`/oscitronix/reg/current/amp/volume iiis` (value, min, max, unit)


`reg/current/nr_sens iiis` noise gate (value, min, max, unit)  
`reg/current/amp/type s` amp model name  
`reg/current/amp/PARAM iiis` (value, min, max, unit)  
`reg/current/pedal1/type s`  
`reg/current/pedal1/active i`  
`reg/current/pedal1/PARAM iiis`  
`reg/current/pedal2/type s`  
`reg/current/pedal2/active i`  
`reg/current/reverb/type s`  
`reg/current/reverb/active i`  
`reg/current/reverb/PARAM iiis`  
