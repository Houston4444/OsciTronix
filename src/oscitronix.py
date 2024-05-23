import logging
import signal
import sys
import threading

from qtpy.QtWidgets import QApplication, QStyleFactory
from qtpy.QtGui import QIcon
from qtpy.QtCore import QTimer
from app_infos import APP_NAME, CONFIG_FILE

import xdg
import midi_client
import nsm_osci
from engine import Engine
from main_window import MainWindow

_logger = logging.getLogger(__name__)


def signal_handler(sig, frame):
    QApplication.quit()

def read_args(*args: tuple[str]) -> int:
    reading = ''
    osc_port = 0
    
    for arg in args:
        if reading == 'osc_port':
            try:
                osc_port = int(arg)
            except:
                sys.stderr.write(f'Invalid osc port argument : {arg}\n')
                sys.exit(1)
            
        if arg == '--osc-port':
            reading = 'osc_port'
        elif arg == '--help':
            sys.stdout.write(
                f'{APP_NAME.lower()} help\n'
                '    --osc-port  PORT  set port number for OSC\n'
                '    --help            print this help\n')
            sys.exit(0)

    return osc_port


if __name__ == '__main__':
    osc_port = read_args(*sys.argv[1:])

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon.fromTheme(APP_NAME.lower()))
    
    # force Fusion style because of param widgets
    app.setStyle(QStyleFactory.create('Fusion'))

    engine = Engine()
    main_win = MainWindow(engine)

    config_path = xdg.xdg_config_home() / APP_NAME / CONFIG_FILE

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    timer = QTimer()
    timer.start(200)
    timer.timeout.connect(lambda: None)

    midi_client.init(engine)
    
    midi_thread = threading.Thread(target=midi_client.run_loop)
    midi_thread.start()
    
    if nsm_osci.is_under_nsm():
        QApplication.setQuitOnLastWindowClosed(False)
        nsm_osci.init(osc_port)
        nsm_osci.set_engine(engine)
        nsm_osci.set_main_win(main_win)
        nsm_thread = threading.Thread(target=nsm_osci.run_loop)
        nsm_thread.start()
    else:
        engine.config.load_from_file(config_path)

        main_win.show()

    app.exec()

    midi_client.stop_loop()
    nsm_osci.stop_loop()
    
    if not nsm_osci.is_under_nsm():
        engine.config.save_in_file(config_path)

