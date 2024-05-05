from typing import Optional, Callable

from mentat import Engine
from voxou import Voxou

engine = Engine('Mentatronix', 4675, 'Mentatronix')


def start_mentat(callback: Optional[Callable] =None):
    print('top départ')
    
    voxou = Voxou('voxou', protocol='midi')
    if callback:
        voxou.set_param_change_cb(callback)
    engine.add_module(voxou)
    
    if False and callback is None:
        engine.autorestart()
    engine.start()
    

def stop_mentat():
    engine.stop()


if __name__ == '__main__':
    start_mentat()
