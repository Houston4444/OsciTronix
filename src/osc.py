import time
from typing import Optional
import json

from liblo import Server, make_method, Address

from engine import Engine

def osci_method():
    pass


class OscUdpServer(Server):
    def __init__(self, port=0):
        if port:
            Server.__init__(self, port)
        else:
            Server.__init__(self)
        self.engine: Optional[Engine] = None
        print('chapootiio')

    def set_engine(self, engine: Engine):
        self.engine = engine
        
    @make_method('/oscitronix/get_current_program', '')
    def _get_current_program_json(
            self, path: str, args: list, types: str, src_addr: Address):
        program_dict = self.engine.current_program.to_json_dict()
        prog_str = json.dumps(program_dict, separators=(',', ':'))
        self.send(src_addr, '/reply', path, prog_str)
    