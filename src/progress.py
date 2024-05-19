import logging
from math import isnan
from typing import Callable
from enum import Enum

from qtpy.QtCore import Signal, Qt, QPoint
from qtpy.QtWidgets import QProgressBar, QInputDialog
from qtpy.QtGui import QWheelEvent, QPalette, QColor, QMouseEvent

from effects import EffParam, DummyParam


_logger = logging.getLogger(__name__)


class SpecialParam(Enum):
    NORMAL = 0
    CLASS_AAB = 1
    BIAS_SHIFT = 2


class ParamProgressBar(QProgressBar):
    # signals
    dragStateChanged = Signal(bool)
    valueChanged = Signal(float)

    def __init__(self, parent):
        QProgressBar.__init__(self, parent=parent)

        self.param = DummyParam.DUMMY

        self._left_click_down = False
        self._is_integer = True
        self._is_read_only = False

        self._minimum = 0.0
        self._maximum = 100.0
        self._initiated = False
        self._real_value = 0.0

        self._last_painted_value = None
        self._current_painted_text = ""

        self._name  = ""
        self._label_prefix = ""
        self._label_suffix = ""
        self._text_call = None
        self._value_call = None

        self._special = SpecialParam.NORMAL

        self.setFormat("(none)")

        # Fake internal value, 10'000 precision
        QProgressBar.setMinimum(self, 0)
        QProgressBar.setMaximum(self, 10000)
        QProgressBar.setValue(self, 0)
        
        palette = self.palette()
        palette.setBrush(
            QPalette.ColorRole.Highlight,
            QColor(138, 128, 128, 80))
        self.setPalette(palette)

    def set_param(self, param: 'EffParam'):
        self.param = param
        mini, maxi, unit = param.range_unit()
        self.setMinimum(mini)
        self.setMaximum(maxi)

        if (mini, maxi, unit) == (0, 2, 'Off,COLD,HOT'):
            self._special = SpecialParam.BIAS_SHIFT
        elif (mini, maxi, unit) == (0, 1, 'A,AB'):
            self._special = SpecialParam.CLASS_AAB

        if unit == '%':
            self._label_suffix = ''
        else:
            self._label_suffix = f' {unit}'
        self.update()

    def setMinimum(self, value):
        self._minimum = value

    def setMaximum(self, value):
        self._maximum = value

    def setValue(self, value):
        if (self._real_value == value or isnan(value)) and self._initiated:
            return False

        self._initiated = True
        self._real_value = value
        div = float(self._maximum - self._minimum)

        if self._special is SpecialParam.CLASS_AAB:
            if value == 0:
                self.setStyleSheet(
                    'QProgressBar{background-color: #60dd60;color: #224422}')
            elif value == 1:
                self.setStyleSheet(
                    'QProgressBar{background-color: #ee7070;color: #442222}')

        if self._special is SpecialParam.BIAS_SHIFT:
            if value == 1:
                self.setStyleSheet('QProgressBar{background-color: #60dd60}')
            elif value == 2:
                self.setStyleSheet('QProgressBar{background-color: #dd6060}')
            else:
                self.setStyleSheet('')

        if div == 0.0:
            _logger.warning(
                f"Parameter '{self._name}' division by 0 prevented "
                f"(value:{value}, min:{self._minimum}, max:{self._maximum})")
            vper = 1.0
        elif isnan(value):
            _logger.warning(
                f"Parameter '{self._name}' is NaN "
                f"(value:{value}, min:{self._minimum}, max:{self._maximum})")
            vper = 1.0
        else:
            vper = float(value - self._minimum) / div

            if vper < 0.0:
                vper = 0.0
            elif vper > 1.0:
                vper = 1.0

        if self._value_call is not None:
            self._value_call(value)

        QProgressBar.setValue(self, int(vper * 10000))
        self.update()
        return True

    def set_suffixes(self, prefix: str, suffix: str):
        self._label_prefix = prefix
        self._label_suffix = suffix

        # force refresh of text value
        self._last_painted_value = None

        self.update()

    def set_name(self, name: str):
        self._name = name

    def set_read_only(self, yesno: bool):
        self._is_read_only = yesno

    def set_text_call(self, text_call: Callable):
        self._text_call = text_call

    def set_value_call(self, value_call: Callable):
        self._value_call = value_call

    def _handle_mouse_event_pos(self, pos: QPoint):
        if self._is_read_only:
            return

        xper  = float(pos.x()) / float(self.width())
        value = xper * (self._maximum - self._minimum) + self._minimum

        if self._is_integer:
            value = round(value)

        if value < self._minimum:
            value = self._minimum
        elif value > self._maximum:
            value = self._maximum

        if self.setValue(value):
            self.valueChanged.emit(value)

    def mousePressEvent(self, event: QMouseEvent):
        if self._is_read_only:
            return

        if event.button() == Qt.LeftButton:
            if self._minimum == 0 and self._maximum == 1:
                # toggle if it is a toggle switch, whatever the mouse pos
                if self.setValue(int(not bool(self._real_value))):
                    self.valueChanged.emit(int(bool(self._real_value)))
                return

            self._handle_mouse_event_pos(event.pos())
            self._left_click_down = True
            self.dragStateChanged.emit(True)

        else:
            self._left_click_down = False
            
        if event.button() == Qt.RightButton:
            ret, ok = QInputDialog.getInt(
                self, "set value", self.param.display_name(),
                int(self._real_value),
                min=int(self._minimum), max=int(self._maximum), step=1)
            if ok:
                if self.setValue(ret):
                    self.valueChanged.emit(ret)
            return

        QProgressBar.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self._is_read_only:
            return

        if self._left_click_down:
            self._handle_mouse_event_pos(event.pos())

        QProgressBar.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self._is_read_only:
            return

        self._left_click_down = False
        self.dragStateChanged.emit(False)
        QProgressBar.mouseReleaseEvent(self, event)

    def paintEvent(self, event):
        if self._text_call is not None:
            if self._last_painted_value != self._real_value:
                self._last_painted_value   = self._real_value
                self._current_painted_text = self._text_call()
            self.setFormat(
                f'{self._label_prefix}{self._current_painted_text}{self._label_suffix}')

        elif self._is_integer:
            if self._special is SpecialParam.CLASS_AAB:
                self.setFormat('AB' if int(self._real_value) else 'A')

            elif self._special is SpecialParam.BIAS_SHIFT:
                if self._real_value < 0.5:
                    self.setFormat('Off')
                elif self._real_value < 1.5:
                    self.setFormat('COLD')
                else:
                    self.setFormat('HOT')

            elif self._minimum == 0 and self._maximum == 1:
                self.setFormat('On' if int(self._real_value) else 'Off')

            elif self._label_suffix == ' Hz':
                self.setFormat(
                    f'{self._label_prefix}%.3f{self._label_suffix}'
                    % (self._real_value * 0.001))
            else:
                self.setFormat(
                    f'{self._label_prefix}{int(self._real_value)}'
                    f'{self._label_suffix}')

        else:
            self.setFormat(
                f'{self._label_prefix}{self._real_value}{self._label_suffix}')

        QProgressBar.paintEvent(self, event)
        
    def wheelEvent(self, event: QWheelEvent):
        super().wheelEvent(event)
        angle = event.angleDelta().y()

        delta = 1
        if not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = max(1, int(0.05 * (self._maximum - self._minimum)))
        if angle < 0:
            delta *= -1
        
        value = round(min(self._maximum,
                      max(self._minimum,
                          round(self._real_value + delta))))
        
        if self.setValue(value):
            self.valueChanged.emit(value)

