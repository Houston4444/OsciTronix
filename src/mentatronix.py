from typing import Optional, Callable

from mentat import Engine
from voxou import Voxou

engine = Engine('Mentatronix', 4677, 'Mentatronix')


def start_mentat(callback: Optional[Callable] =None, cb_dict: dict ={}):
    voxou = Voxou('voxou', protocol='midi')
    if callback:
        voxou.set_gui_cb(callback)
        cb_dict['voxou'] = voxou
    engine.add_module(voxou)
    
    if False and callback is None:
        engine.autorestart()
    engine.start()
    

def stop_mentat():
    engine.stop()


if __name__ == '__main__':
    start_mentat()
