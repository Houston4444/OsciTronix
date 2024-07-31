#!/usr/bin/env python3

import os
import sys
from pathlib import Path

PREFIX = 'X-PREFIX-X'
QT_API = 'X-QT_API-X'

osci_path = Path(PREFIX) / 'share' / 'OsciTronix' / 'src'
sys.path.insert(1, str(osci_path))

if os.environ.get('QT_API') is None:
    os.environ['QT_API'] = QT_API

import oscitronix
oscitronix.main()