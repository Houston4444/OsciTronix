import logging
import os
import sys
from typing import TYPE_CHECKING, Optional
from pathlib import Path

from liblo import Address

import midi_client
from nsm_client import NsmServer, NsmCallback, Err
from app_infos import APP_NAME

if TYPE_CHECKING:
    from main_window import MainWindow

_logger = logging.getLogger(__name__)


class NsmObject:
    def __init__(self):
        self.terminate = False
        
        url = os.getenv('NSM_URL')
        self.server_addr: Optional[Address] = None
        self.main_win: 'Optional[MainWindow]' = None
        self.nsm_server: Optional[NsmServer] = None

        if url:
            try:
                self.server_addr = Address(url)
            except:
                _logger.warning(f'NSM_URL {url} is not a valid OSC url')
        
        if self.server_addr is not None:
            nsm_server = NsmServer(self.server_addr)
            nsm_server.set_callback(NsmCallback.OPEN, open_file)
            nsm_server.set_callback(NsmCallback.SAVE, save_file)
            nsm_server.set_callback(NsmCallback.HIDE_OPTIONAL_GUI,
                                    hide_optional_gui)
            nsm_server.set_callback(NsmCallback.SHOW_OPTIONAL_GUI,
                                    show_optional_gui)
            nsm_server.announce(
                APP_NAME, ':optional-gui:switch:', sys.argv[0])
            self.nsm_server = nsm_server
    
    def set_main_win(self, main_win: 'MainWindow'):
        main_win.set_nsm_visible_callback(
            self.nsm_server.send_gui_state)
        self.main_win = main_win

    def run_loop(self):
        if self.nsm_server is None:
            return
        
        while not self.terminate:
            self.nsm_server.recv(50)

# --- NSM callbacks ---

def open_file(project_path: str, session_name: str,
              full_client_id: str) -> tuple[Err, str]:
    midi_client.restart(full_client_id)
    path = Path(project_path)
    if not path.exists():
        path.mkdir(parents=True)
    
    return (Err.OK, 'open done')

def save_file():
    return (Err.OK, 'Done')

def hide_optional_gui():
    if nsm_object.main_win is None:
        return
    nsm_object.main_win.nsm_hide.emit()

def show_optional_gui():
    if nsm_object.main_win:
        nsm_object.main_win.nsm_show.emit()

# ---------------------

nsm_object = NsmObject()

# --- used by launcher ---

def is_under_nsm() -> bool:
    return nsm_object.server_addr is not None

def set_main_win(main_win: 'MainWindow'):
    nsm_object.set_main_win(main_win)

def run_loop():
    nsm_object.run_loop()

def stop_loop():
    nsm_object.terminate = True
    
