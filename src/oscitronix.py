import json
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
from engine import Voxou
from main_window import MainWindow

_logger = logging.getLogger(__name__)


def signal_handler(sig, frame):
    QApplication.quit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon.fromTheme(APP_NAME.lower()))
    
    # force Fusion style because of param widgets
    app.setStyle(QStyleFactory.create('Fusion'))

    voxou = Voxou()
    main_win = MainWindow(voxou)

    config_path = xdg.xdg_config_home() / APP_NAME / CONFIG_FILE

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    timer = QTimer()
    timer.start(200)
    timer.timeout.connect(lambda: None)

    midi_client.init(voxou)
    
    midi_thread = threading.Thread(target=midi_client.run_loop)
    midi_thread.start()
    
    if nsm_osci.is_under_nsm():
        QApplication.setQuitOnLastWindowClosed(False)
        nsm_osci.set_main_win(main_win)
        nsm_osci.set_voxou(voxou)
        nsm_thread = threading.Thread(target=nsm_osci.run_loop)
        nsm_thread.start()
    else:
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    voxou.config.adjust_from_dict(json.load(config_path))
            except BaseException as e:
                _logger.warning(
                    f'Failed to open config file {str(e)}')

        main_win.show()

    app.exec()

    midi_client.stop_loop()
    nsm_osci.stop_loop()
    
    if not nsm_osci.is_under_nsm():
        try:
            with open(config_path, 'w') as f:
                json.dump(voxou.config.to_dict(), f, indent=2)
        except BaseException as e:
            _logger.warning(f'Failed to save config file\n{str(e)}')

