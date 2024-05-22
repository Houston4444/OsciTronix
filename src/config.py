from enum import Enum
import logging
from typing import Any
from pathlib import Path
import json

_logger = logging.getLogger(__name__)


class NsmMode(Enum):
    FREE = 0
    LOAD_SAVED_PROGRAM = 1


class Config:
    auto_connect_device = True
    nsm_mode = NsmMode.LOAD_SAVED_PROGRAM

    def to_dict(self) -> dict[str, Any]:
        return {'auto_connect_device': self.auto_connect_device,
                'nsm_mode': self.nsm_mode.name.lower()}

    def adjust_from_dict(self, conf_dict: dict[str, Any]):
        try:
            self.auto_connect_device = bool(conf_dict['auto_connect_device'])
        except BaseException as e:
            _logger.warning(
                'config file does not contain correct value '
                f'for auto_connect_device. {str(e)}')

        try:
            self.nsm_mode = NsmMode[conf_dict['nsm_mode'].upper()]
        except BaseException as e:
            _logger.warning(
                'config file does not contain correct value '
                f'for nsm_mode. {str(e)}')
    
    def load_from_file(self, config_path: Path):
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    self.adjust_from_dict(json.load(f))
            except BaseException as e:
                _logger.warning(
                    f'Failed to open config file\n{str(e)}')
                
    def save_in_file(self, config_path: Path):
        try:
            with open(config_path, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
        except BaseException as e:
            _logger.warning(f'Failed to save config file\n{str(e)}')