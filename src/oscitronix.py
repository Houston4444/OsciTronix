import signal
import sys
import threading

from qtpy.QtWidgets import QApplication, QStyleFactory
from qtpy.QtGui import QIcon
from qtpy.QtCore import QTimer

import midi_client
from voxou import Voxou
from main_window import MainWindow


def signal_handler(sig, frame):
    QApplication.quit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon.fromTheme('oscitronix'))
    
    # force Fusion style because of param widgets
    app.setStyle(QStyleFactory.create('Fusion'))

    voxou = Voxou()
    main_win = MainWindow(voxou)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    timer = QTimer()
    timer.start(200)
    timer.timeout.connect(lambda: None)

    midi_client.init(voxou)
    
    midi_thread = threading.Thread(target=midi_client.run_loop)
    midi_thread.start()

    main_win.show()
    app.exec()

    midi_client.stop()