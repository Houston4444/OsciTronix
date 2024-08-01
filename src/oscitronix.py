#!/usr/bin/env python3

import logging
import signal
import sys
import threading
from ctypes import cdll, byref, create_string_buffer
from pathlib import Path

from qtpy.QtWidgets import QApplication, QStyleFactory
from qtpy.QtGui import QIcon
from qtpy.QtCore import QTimer, QSettings, QLocale, QTranslator, QLibraryInfo

import xdg
import midi_client
import nsm_osci
import osc
from app_infos import APP_NAME, CONFIG_FILE, LOCAL_PROGRAMS_DIRNAME
from engine import Engine
from frontend.main_window import MainWindow


_logger = logging.getLogger()


def set_proc_name(new_name: str):
    # use the app name instead of 'python' in processes list. 
    # solution was found here: 
    # https://stackoverflow.com/questions/564695/is-there-a-way-to-change-effective-process-name-in-python
    try:
        libc = cdll.LoadLibrary('libc.so.6')
        buff = create_string_buffer(len(new_name)+1)
        buff.value = new_name.encode()
        libc.prctl(15, byref(buff), 0, 0, 0)

    except BaseException as e:
        _logger.info(
            f'impossible to set process name to {new_name}, '
            'it should not be strong.')
        _logger.info(str(e))

def signal_handler(sig, frame):
    QApplication.quit()

def read_args(*args: str) -> tuple[int, int]:
    reading = ''
    osc_port = 0
    logging_level = logging.WARNING
    
    for arg in args:
        if reading == 'osc_port':
            try:
                osc_port = int(arg)
            except:
                sys.stderr.write(f'Invalid osc port : {arg}\n')
                sys.exit(1)
        
        elif reading == 'log':
            try:
                assert arg.upper() in (
                    'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
                logging_level = logging.__dict__[arg.upper()]
            except:
                sys.stderr.write(f'Invalid log level : {arg}\n')
        
        if arg == '--osc-port':
            reading = 'osc_port'
        elif arg == '--log':
            reading = 'log'
        elif arg == '--help':
            sys.stdout.write(
                f'{APP_NAME.lower()} help\n'
                '    --osc-port  PORT   set port number for OSC\n'
                '    --log       LEVEL  log level can be '
                        'DEBUG, INFO, WARNING, ERROR, CRITICAL\n'
                '    --help             print this help\n')
            sys.exit(0)

    return osc_port, logging_level

def main():
    osc_port, logging_level = read_args(*sys.argv[1:])
    logging.basicConfig(level=logging_level)
    set_proc_name(APP_NAME.lower())

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon.fromTheme(APP_NAME.lower()))
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setDesktopFileName(APP_NAME.lower())
    
    # force Fusion style because of param widgets
    app.setStyle(QStyleFactory.create('Fusion'))
    
    ### Translation process
    locale_path = Path(__file__).parent.parent / 'locale'

    app_translator = QTranslator()
    if app_translator.load(QLocale(), APP_NAME.lower(),
                           '_', str(locale_path)):
        app.installTranslator(app_translator)

    sys_translator = QTranslator()
    path_sys_translations = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
    if sys_translator.load(QLocale(), 'qt', '_', path_sys_translations):
        app.installTranslator(sys_translator)
    
    settings = QSettings()

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
        engine.set_project_path(
            xdg.xdg_data_home() / APP_NAME / LOCAL_PROGRAMS_DIRNAME)
        osc_server = osc.OscUdpServer(osc_port)
        osc_server.set_engine(engine)
        osc_thread = threading.Thread(target=osc_server.run_loop)
        osc_thread.start()

        main_win.show()

    app.exec()

    midi_client.stop_loop()
    if nsm_osci.is_under_nsm():
        nsm_osci.stop_loop()
    else:
        osc_server.stop_loop()

    if not nsm_osci.is_under_nsm():
        engine.config.save_in_file(config_path)


if __name__ == '__main__':
    main()
