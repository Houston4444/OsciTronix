# OsciTronix

OsciTronix is a controller for VTX guitar amps by VOX (VT20X, VT40X and VT100X), available for GNU/Linux systems.

It is written in python with the Qt framework.


## Features

OsciTronix is an alternative to ToneRoom (the official VOX controller), with a less attractive GUI, and with very few devices supported. Ok, so, what is the interest ?

* It does not needs Wine
* full OSC control (see [OSC.md](./OSC.md))
* Any control in one click
* Faster startup
* NSM support
* Be aware of disconnection/connection of the device

## Build

### Build dependencies

* `pyqt6-dev-tools` or `pyqt5-dev-tools`
* `qt-chooser`

in debian Bookworm you can install all build and runtime dependencies as root with
`apt install pyqt5-dev-tools qt-chooser python3-unidecode python3-qtpy python3-liblo python3-pyalsa`

As usual, simply run

`make`

`sudo make install` 

If you prefer to use Oscitronix with Qt6, instead run

`QT_VERSION=6 make`

`sudo make install`

### Runtime dependencies

* unidecode
* qtpy
* PyQt5 or PyQt6
* pyliblo
* pyalsa

The executable is

`oscitronix`

### Tips
you can run directly the program without install. In the source code folder, simply type:
`./src/oscitronix.py` or `QT_API=PyQt6 ./src/oscitronix.py` if you have build it with Qt6.
