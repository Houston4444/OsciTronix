import time
from typing import Generator, Any

from pyalsa import alsaseq
from pyalsa.alsaseq import SEQ_EVENT_SYSEX
from voxou import Voxou

# midi_server = alsaseq.Sequencer(clientname='OsciTronix')
# port_type = alsaseq.SEQ_PORT_TYPE_MIDI_GENERIC | alsaseq.SEQ_PORT_TYPE_APPLICATION
# port_caps = (alsaseq.SEQ_PORT_CAP_WRITE | alsaseq.SEQ_PORT_CAP_SUBS_WRITE |
#                 alsaseq.SEQ_PORT_CAP_READ | alsaseq.SEQ_PORT_CAP_SUBS_READ)
# port_id = midi_server.create_simple_port("Valvetronix", port_type, port_caps)


class MidiClient:
    def __init__(self):
        self.server = alsaseq.Sequencer(clientname='OsciTronix')
        port_type = (alsaseq.SEQ_PORT_TYPE_MIDI_GENERIC
                     | alsaseq.SEQ_PORT_TYPE_APPLICATION)
        port_caps = (alsaseq.SEQ_PORT_CAP_WRITE
                     | alsaseq.SEQ_PORT_CAP_SUBS_WRITE
                     | alsaseq.SEQ_PORT_CAP_READ
                     | alsaseq.SEQ_PORT_CAP_SUBS_READ)
        self.port_id = self.server.create_simple_port(
            "Valvetronix", port_type, port_caps)

        self.stopping = False
        self.voxou: Voxou = None        

    def read_events(self):
        midi_events = self.server.receive_events()
        for event in midi_events:
            if event.type is not SEQ_EVENT_SYSEX:
                print('receive non sysex')
                continue
            
            int_list: list[int] = event.get_data()['ext']
            if self.voxou is not None:
                self.voxou.rototo(int_list)


midi_client = MidiClient()


def run_loop(voxou_dict: dict[str, Voxou]):
    while midi_client.voxou is None:
        midi_client.voxou = voxou_dict['voxou']
        time.sleep(0.001)

    while True:
        midi_client.read_events()
        if midi_client.stopping:
            break

        time.sleep(0.001)