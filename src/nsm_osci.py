import logging
import os
import sys
import json
from typing import TYPE_CHECKING, Optional
from pathlib import Path
from config import NsmMode

from liblo import Address

import midi_client
from nsm_client import NsmServer, NsmCallback, Err
from app_infos import APP_NAME, CONFIG_FILE, CURRENT_PROGRAM_FILE
from engine import CommunicationState, Engine
from osc import OscUdpServer

if TYPE_CHECKING:
    from main_window import MainWindow

_logger = logging.getLogger(__name__)


# --- NSM callbacks ---

def open_file(project_path: str, session_name: str,
              full_client_id: str) -> tuple[Err, str]:
    midi_client.restart(full_client_id)
    nsm_object.load_project_path(Path(project_path))
    return (Err.OK, 'open done')

def save_file():
    nsm_object.save_file()
    fla = nsm_object.engine.current_program.to_json_dict()
    stra = json.dumps(fla, separators=(',', ':'))
    print(stra, len(stra))
    return (Err.OK, 'Done')

def hide_optional_gui():
    if nsm_object.main_win is None:
        return
    nsm_object.main_win.nsm_hide.emit()

def show_optional_gui():
    if nsm_object.main_win:
        nsm_object.main_win.nsm_show.emit()


class NsmObject:
    def __init__(self):
        self.terminate = False
        
        url = os.getenv('NSM_URL')
        self.server_addr: Optional[Address] = None
        self.main_win: 'Optional[MainWindow]' = None
        self.nsm_server: Optional[NsmServer] = None
        self.engine: Optional[Engine] = None

        self.project_path = Path()
        self._pending_path_to_load: Optional[Path] = None

        if url:
            try:
                self.server_addr = Address(url)
            except:
                _logger.warning(f'NSM_URL {url} is not a valid OSC url')

    def init(self, port=0):
        if self.server_addr is None:
            return

        nsm_server = NsmServer(self.server_addr, port)
        nsm_server.set_callback(NsmCallback.OPEN, open_file)
        nsm_server.set_callback(NsmCallback.SAVE, save_file)
        nsm_server.set_callback(NsmCallback.HIDE_OPTIONAL_GUI,
                                hide_optional_gui)
        nsm_server.set_callback(NsmCallback.SHOW_OPTIONAL_GUI,
                                show_optional_gui)
        nsm_server.announce(
            APP_NAME, ':optional-gui:switch:', sys.argv[0])
        
        print('pafkpafe', nsm_server.port)
        self.nsm_server = nsm_server
    
    def set_main_win(self, main_win: 'MainWindow'):
        main_win.set_nsm_visible_callback(
            self.nsm_server.send_gui_state)
        self.main_win = main_win

    def set_engine(self, engine: Engine):
        self.engine = engine
        self.engine.set_a_ready_cb(self.engine_is_ready)
        self.nsm_server.set_engine(engine)
        
    def engine_is_ready(self):
        if self._pending_path_to_load is not None:
            self.engine.load_program_from_disk(
                self._pending_path_to_load)
            self._pending_path_to_load = None

    def load_project_path(self, project_path: Path):
        self.project_path = project_path

        if self.engine is None:
            return

        config_path = self.project_path / CONFIG_FILE
        program_path = self.project_path / CURRENT_PROGRAM_FILE

        self.engine.config.load_from_file(config_path)

        if self.main_win is not None:
            self.main_win.config_changed.emit()

        if self.engine.config.nsm_mode is not NsmMode.LOAD_SAVED_PROGRAM:
            return

        if not program_path.exists():
            return
        
        if not self.engine.communication_state.is_ok():
            _logger.info(
                'communication_state is not ok for loading program now')
            self._pending_path_to_load = program_path
            return
        
        self.engine.load_program_from_disk(program_path)

    def save_file(self):
        try:
            self.project_path.mkdir(exist_ok=True, parents=True)
        except:
            _logger.critical('Failed to create the project directory')
            return

        config_path = self.project_path / CONFIG_FILE
        program_path = self.project_path / CURRENT_PROGRAM_FILE

        if self.engine is None:
            return

        self.engine.config.save_in_file(config_path)

        if not self.engine.communication_state.is_ok():
            _logger.critical('communication_state is not ok for saving')
            return

        program_dict = self.engine.current_program.to_json_dict()
        try:
            with open(program_path, 'w') as f:
                json.dump(program_dict, f, indent=2)
        except:
            _logger.critical(f'Failed to save file {program_path}')

    def run_loop(self):
        if self.nsm_server is None:
            return
        
        while not self.terminate:
            self.nsm_server.recv(50)


nsm_object = NsmObject()


# --- used by the launcher ---

def is_under_nsm() -> bool:
    return nsm_object.server_addr is not None

def init(port=0):
    nsm_object.init(port)

def set_main_win(main_win: 'MainWindow'):
    nsm_object.set_main_win(main_win)

def set_engine(engine: Engine):
    nsm_object.set_engine(engine)

def run_loop():
    nsm_object.run_loop()

def stop_loop():
    nsm_object.terminate = True
    
