from mentat import Engine
from voxou import Voxou

if __name__ == '__main__':
    print('top départ')
    engine = Engine('Mentatronix', 4681, 'Mentatronix')
    engine.add_module(Voxou('voxou', protocol='midi'))
    engine.autorestart()
    engine.start()