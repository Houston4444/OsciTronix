import signal
import sys
from typing import TYPE_CHECKING
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QSpacerItem, QSizePolicy, QCheckBox
from PyQt5.QtCore import pyqtSlot, QTimer, pyqtSignal
import threading

from effects import AmpModel, AmpParam, EffParam, EffectOnOff, Pedal1Type, Pedal2Type, ReverbType, VoxIndex
from mentatronix import start_mentat, stop_mentat

from ui.main_win import Ui_MainWindow
from ui.progress import ParamProgressBar

if TYPE_CHECKING:
    from voxou import VoxProgram

def signal_handler(sig, frame):
    QApplication.quit()


class MainWindow(QMainWindow):
    callback_sig = pyqtSignal(str, object)
    
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.amp_params_widgets = {
            AmpParam.GAIN: self.ui.progressBarGain,
            AmpParam.TREBLE: self.ui.progressBarTreble,
            AmpParam.MIDDLE: self.ui.progressBarMiddle,
            AmpParam.BASS: self.ui.progressBarBass,
            AmpParam.TONE: self.ui.progressBarTone,
            AmpParam.RESONANCE: self.ui.progressBarResonance,
            AmpParam.VOLUME: self.ui.progressBarVolume,
            AmpParam.BRIGHT_CAP: self.ui.checkBoxBrightCap,
            AmpParam.LOW_CUT: self.ui.checkBoxLowCut,
            AmpParam.MID_BOOST: self.ui.checkBoxMidBoost,
            AmpParam.BIAS_SHIFT: self.ui.checkBoxBiasShift,
            AmpParam.CLASS: self.ui.checkBoxClassAAB
        }
        
        for param, widget in self.amp_params_widgets.items():
            if isinstance(widget, ParamProgressBar):
                widget.set_param(param)
        
        for amp_model in AmpModel:
            self.ui.comboBoxAmpModel.addItem(
                amp_model.name.replace('_', ' '), amp_model)

        self._pedal1_widgets = set[QWidget]()
        self._pedal1_spacer = QSpacerItem(
            0, 0, hPolicy=QSizePolicy.Maximum,
            vPolicy=QSizePolicy.MinimumExpanding)

        for pedal1_type in Pedal1Type:
            self.ui.comboBoxPedal1.addItem(
                pedal1_type.name.replace('_', ' ').capitalize(), pedal1_type)
            
        for i in (6, 2, 1):
            self.ui.comboBoxPedal1.insertSeparator(i)
        
        self._fill_pedal1(Pedal1Type.COMP)

        self._pedal2_widgets = set[QWidget]()
        self._pedal2_spacer = QSpacerItem(
            0, 0, hPolicy=QSizePolicy.Maximum,
            vPolicy=QSizePolicy.MinimumExpanding)
        
        for pedal2_type in Pedal2Type:
            self.ui.comboBoxPedal2.addItem(
                pedal2_type.name.replace('_', ' ').capitalize(), pedal2_type)
            
        for i in (5, 4, 1):
            self.ui.comboBoxPedal2.insertSeparator(i)
            
        self._fill_pedal2(Pedal2Type.FLANGER)
        
        self._reverb_widgets = set[QWidget]()
        for reverb_type in ReverbType:
            self.ui.comboBoxReverb.addItem(
                reverb_type.name.replace('_', ' ').capitalize(), reverb_type)
        
        self._fill_reverb(ReverbType.ROOM)
        
        self.ui.comboBoxAmpModel.currentIndexChanged.connect(
            self.amp_model_changed)
        self.ui.comboBoxPedal1.currentIndexChanged.connect(
            self.pedal1_effect_changed)
        self.ui.comboBoxPedal2.currentIndexChanged.connect(
            self.pedal2_effect_changed)
        self.callback_sig.connect(self.apply_callback)
    
    def engine_callback(self, *args):
        self.callback_sig.emit(*args)
        
    def apply_callback(self, *args):
        print('cbbbb', *args)
        if args[0] == 'ALL_CURRENT':
            program: 'VoxProgram' = args[1]
            
            self.ui.comboBoxAmpModel.setCurrentIndex(
                self.ui.comboBoxAmpModel.findData(program.amp_model))
            
            for amp_param, value in program.amp_params.items():
                widget = self.amp_params_widgets[amp_param]
                if isinstance(widget, ParamProgressBar):
                    widget.setValue(value)
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(value == 1)
            
            self.ui.groupBoxPedal1.setChecked(
                bool(program.active_effects[EffectOnOff.PEDAL1]))
            self.ui.groupBoxPedal2.setChecked(
                bool(program.active_effects[EffectOnOff.PEDAL2]))
            self.ui.groupBoxReverb.setChecked(
                bool(program.active_effects[EffectOnOff.REVERB]))
            
            self.ui.comboBoxPedal1.setCurrentIndex(
                self.ui.comboBoxPedal1.findData(program.pedal1_type))
            for amp_param, value in program.pedal1_params.items():
                for widget in self._pedal1_widgets:
                    if isinstance(widget, ParamProgressBar):
                        if widget.param is amp_param:
                            widget.setValue(value)
                            
            self.ui.comboBoxPedal2.setCurrentIndex(
                self.ui.comboBoxPedal2.findData(program.pedal2_type))
            for amp_param, value in program.pedal2_params.items():
                for widget in self._pedal2_widgets:
                    if isinstance(widget, ParamProgressBar):
                        if widget.param is amp_param:
                            widget.setValue(value)
                            
            self.ui.comboBoxReverb.setCurrentIndex(
                self.ui.comboBoxReverb.findData(program.reverb_type))
            for amp_param, value in program.reverb_params.items():
                for widget in self._reverb_widgets:
                    if isinstance(widget, ParamProgressBar):
                        if widget.param is amp_param:
                            widget.setValue(value)
            return
        
        if args[0] == 'PARAM_CHANGED':
            program, vox_index, param_index = args[1]

            if vox_index is VoxIndex.AMP:
                amp_param = AmpParam(param_index)
                value = program.amp_params[amp_param]
                widget = self.amp_params_widgets[amp_param]
                if isinstance(widget, ParamProgressBar):
                    widget.setValue(value)
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(bool(value))
                return
            
            if vox_index is VoxIndex.EFFECT_MODEL:
                effect = EffectOnOff(param_index)
                if effect is EffectOnOff.AMP:
                    self.ui.comboBoxAmpModel.setCurrentIndex(
                        self.ui.comboBoxAmpModel.findData(program.amp_model))
                elif effect is EffectOnOff.PEDAL1:
                    self.ui.comboBoxPedal1.setCurrentIndex(
                        self.ui.comboBoxPedal1.findData(program.pedal1_type))
                elif effect is EffectOnOff.PEDAL2:
                    self.ui.comboBoxPedal2.setCurrentIndex(
                        self.ui.comboBoxPedal2.findData(program.pedal2_type))
                elif effect is EffectOnOff.REVERB:
                    self.ui.comboBoxReverb.setCurrentIndex(
                        self.ui.comboBoxReverb.findData(program.reverb_type))
                return
            
            if vox_index is VoxIndex.EFFECT_STATUS:
                self.ui.groupBoxPedal1.setChecked(
                    bool(program.active_effects[EffectOnOff.PEDAL1]))
                self.ui.groupBoxPedal2.setChecked(
                    bool(program.active_effects[EffectOnOff.PEDAL2]))
                self.ui.groupBoxReverb.setChecked(
                    bool(program.active_effects[EffectOnOff.REVERB]))
                return
            
            if vox_index is VoxIndex.PEDAL1:
                for widget in self._pedal1_widgets:
                    if isinstance(widget, ParamProgressBar):
                        widget.setValue(program.pedal1_params[widget.param])
                return
            
            if vox_index is VoxIndex.PEDAL2:
                for widget in self._pedal2_widgets:
                    if isinstance(widget, ParamProgressBar):
                        widget.setValue(program.pedal2_params[widget.param])
                return
            
            if vox_index is VoxIndex.REVERB:
                for widget in self._reverb_widgets:
                    if isinstance(widget, ParamProgressBar):
                        widget.setValue(program.reverb_params[widget.param])
                return
    
    def _fill_pedal1(self, pedal1_type: Pedal1Type):
        print('fill peddal1', pedal1_type)
        
        for widget in self._pedal1_widgets:
            self.ui.gridLayout_2.removeWidget(widget)
        self.ui.gridLayout_2.removeItem(self._pedal1_spacer)
        
        self._pedal1_widgets.clear()
        
        pedal1_param: EffParam
        i = 1
        for pedal1_param in pedal1_type.param_type():
            label = QLabel(self.ui.groupBoxPedal1)
            label.setText(pedal1_param.display_name())
            self.ui.gridLayout_2.addWidget(label, i, 0, 1, 1)
            self._pedal1_widgets.add(label)
            
            param_wg = ParamProgressBar(self.ui.groupBoxPedal1)
            param_wg.set_param(pedal1_param)
            if not pedal1_param.display_name():
                param_wg.setVisible(False)
            self.ui.gridLayout_2.addWidget(param_wg, i, 1, 1, 1)
            self._pedal1_widgets.add(param_wg)
            
            i += 1

        self.ui.gridLayout_2.addItem(self._pedal1_spacer, i, 0, 1, 1)
        
    def _fill_pedal2(self, pedal2_type: Pedal2Type):
        for widget in self._pedal2_widgets:
            self.ui.gridLayout_3.removeWidget(widget)
        self.ui.gridLayout_3.removeItem(self._pedal2_spacer)
        
        self._pedal2_widgets.clear()
        
        pedal2_param: EffParam
        i = 1
        for pedal2_param in pedal2_type.param_type():
            label = QLabel(self.ui.groupBoxPedal2)
            label.setText(pedal2_param.display_name())
            self.ui.gridLayout_3.addWidget(label, i, 0, 1, 1)
            self._pedal2_widgets.add(label)
            
            param_wg = ParamProgressBar(self.ui.groupBoxPedal2)
            param_wg.set_param(pedal2_param)
            self.ui.gridLayout_3.addWidget(param_wg, i, 1, 1, 1)
            self._pedal2_widgets.add(param_wg)
            
            i += 1
            
        self.ui.gridLayout_2.addItem(self._pedal2_spacer, i, 0, 1, 1)
    
    def _fill_reverb(self, reverb_type: ReverbType):
        for widget in self._reverb_widgets:
            self.ui.gridLayout_5.removeWidget(widget)
        
        reverb_param: EffParam
        i = 1
        for reverb_param in reverb_type.param_type():
            label = QLabel(self.ui.groupBoxReverb)
            label.setText(reverb_param.display_name())
            self.ui.gridLayout_5.addWidget(label, i, 0, 1, 1)
            self._reverb_widgets.add(label)
            
            param_wg = ParamProgressBar(self.ui.groupBoxReverb)
            param_wg.set_param(reverb_param)
            self.ui.gridLayout_5.addWidget(param_wg, i, 1, 1, 1)
            self._reverb_widgets.add(param_wg)
            
            i += 1
            
    @pyqtSlot(int)
    def amp_model_changed(self, index: int):
        amp_model: AmpModel = self.ui.comboBoxAmpModel.currentData()
        self.ui.checkBoxBrightCap.setVisible(amp_model.has_bright_cap())
        if amp_model.presence_is_tone():
            self.ui.labelPresenceTone.setText('Tone')
        else:
            self.ui.labelPresenceTone.setText('Presence')
    
    @pyqtSlot(int)
    def pedal1_effect_changed(self, index: int):
        pedal1_type = self.ui.comboBoxPedal1.currentData()
        if pedal1_type is not None:
            self._fill_pedal1(pedal1_type)
        
    @pyqtSlot(int)
    def pedal2_effect_changed(self, index: int):
        pedal2_type = self.ui.comboBoxPedal2.currentData()
        if pedal2_type is not None:
            self._fill_pedal2(pedal2_type)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_win = MainWindow()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    timer = QTimer()
    timer.start(200)
    timer.timeout.connect(lambda: None)
    
    mentat_thread = threading.Thread(
        target=start_mentat, args=(main_win.engine_callback,))
    mentat_thread.start()
    
    main_win.show()
    app.exec()
    stop_mentat()