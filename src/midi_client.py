import logging
import time

from pyalsa import alsaseq
from pyalsa.alsaseq import SEQ_EVENT_SYSEX
from voxou import Voxou

_logger = logging.getLogger(__name__)


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
        self._midi_drain_pending = False
        self._pending_send = False

    def set_voxou(self, voxou: Voxou):
        self.voxou = voxou
        self.voxou.set_midi_out_func(self.send_to_vox)

    def read_events(self):
        midi_events = self.server.receive_events()
        for event in midi_events:
            if event.type is not SEQ_EVENT_SYSEX:
                continue

            int_list: list[int] = event.get_data()['ext']
            if self.voxou is not None:
                self.voxou.rototo(int_list)

    def send_to_vox(self, args: list[int]):
        event = alsaseq.SeqEvent(SEQ_EVENT_SYSEX)
        event.set_data({'ext': args})
        event.source = (self.server.client_id, self.port_id)
        self.server.output_event(event)

        try:
            self.server.drain_output()
        except:
            self._midi_drain_pending = True
            _logger.warning('midi pool unnavailable, trying again')

        self._pending_send = True

    def flush(self):
        if not self._pending_send:
            return

        if self._midi_drain_pending:
            try:
                self.server.drain_output()
                self.server._midi_drain_pending = False
            except:
                _logger.warning('midi pool unnavailable, trying again')

        self.server.sync_output_queue()
        self._pending_send = False


midi_client = MidiClient()


def init(voxou: Voxou):
    midi_client.set_voxou(voxou)

def stop():
    midi_client.stopping = True

def run_loop():
    if midi_client.voxou is None:
        _logger.error('voxou must be set before to run midi main loop')
        return

    while True:
        midi_client.read_events()
        if midi_client.stopping:
            break
        
        midi_client.flush()
        time.sleep(0.001)