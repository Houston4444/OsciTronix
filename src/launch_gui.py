import signal
import sys
from typing import TYPE_CHECKING
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QSpacerItem, QSizePolicy, QCheckBox, QComboBox
from PyQt5.QtCore import pyqtSlot, QTimer, pyqtSignal
import threading

from effects import AmpModel, AmpParam, EffParam, EffectOnOff, Pedal1Type, Pedal2Type, ReverbParam, ReverbType, VoxIndex
from mentatronix import start_mentat, stop_mentat

from ui.main_win import Ui_MainWindow
from ui.progress import ParamProgressBar

if TYPE_CHECKING:
    from voxou import VoxProgram, Voxou


voxou_dict = {'voxou': None}

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

        # self._pedal1_widgets = dict[int, tuple[QLabel, ParamProgressBar]]()
        

        for pedal1_type in Pedal1Type:
            self.ui.comboBoxPedal1.addItem(
                pedal1_type.name.replace('_', ' ').capitalize(), pedal1_type)
            
        for i in (6, 2, 1):
            self.ui.comboBoxPedal1.insertSeparator(i)
        
        self._pedal1_widgets = (
            (self.ui.labelPedal1Param0, self.ui.progressBarPedal1Param0),
            (self.ui.labelPedal1Param1, self.ui.progressBarPedal1Param1),
            (self.ui.labelPedal1Param2, self.ui.progressBarPedal1Param2),
            (self.ui.labelPedal1Param3, self.ui.progressBarPedal1Param3),
            (self.ui.labelPedal1Param4, self.ui.progressBarPedal1Param4),
            (self.ui.labelPedal1Param5, self.ui.progressBarPedal1Param5),
        )
        
        self._pedal2_widgets = (
            (self.ui.labelPedal2Param0, self.ui.progressBarPedal2Param0),
            (self.ui.labelPedal2Param1, self.ui.progressBarPedal2Param1),
            (self.ui.labelPedal2Param2, self.ui.progressBarPedal2Param2),
            (self.ui.labelPedal2Param3, self.ui.progressBarPedal2Param3),
            (self.ui.labelPedal2Param4, self.ui.progressBarPedal2Param4),
            (self.ui.labelPedal2Param5, self.ui.progressBarPedal2Param5),
        )
        
        self._reverb_sliders = (
            self.ui.progressBarReverbMix,
            self.ui.progressBarReverbTime,
            self.ui.progressBarReverbPreDelay,
            self.ui.progressBarReverbLowDamp,
            self.ui.progressBarReverbHighDump
        )
        
        for combobox in (self.ui.comboBoxAmpModel,
                         self.ui.comboBoxPedal1,
                         self.ui.comboBoxPedal2,
                         self.ui.comboBoxReverb):
            combobox.activated.connect(self._effect_model_changed)

        for amp_param, param_wg in self.amp_params_widgets.items():
            if isinstance(param_wg, ParamProgressBar):
                param_wg.valueChanged.connect(self._amp_param_moved)
        for label, param_wg in self._pedal1_widgets:
            param_wg.valueChanged.connect(self._pedal1_param_moved)
        for label, param_wg in self._pedal2_widgets:
            param_wg.valueChanged.connect(self._pedal2_param_moved)
        for param_wg in self._reverb_sliders:
            param_wg.valueChanged.connect(self._reverb_param_moved)
        # for param_wg in ([w[1] for w in self._pedal1_widgets]
        #                  + [w[1] for w in self._pedal2_widgets]
        #                  + [w for w in self._reverb_sliders]):
        #     param_wg.valueChanged.connect(self.slider_value_changed)

        self._fill_pedal1(Pedal1Type.COMP)
        self._fill_pedal2(Pedal2Type.FLANGER)
        for rev_param in ReverbParam:
            self._reverb_sliders[rev_param.value].set_param(rev_param)
        
        for pedal2_type in Pedal2Type:
            self.ui.comboBoxPedal2.addItem(
                pedal2_type.name.replace('_', ' ').capitalize(), pedal2_type)
            
        for i in (5, 4, 1):
            self.ui.comboBoxPedal2.insertSeparator(i)
            
        for reverb_type in ReverbType:
            self.ui.comboBoxReverb.addItem(
                reverb_type.name.replace('_', ' ').capitalize(), reverb_type)
        
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
            for eff_param, value in program.pedal1_params.items():
                self._pedal1_widgets[eff_param.value][1].setValue(value)
                            
            self.ui.comboBoxPedal2.setCurrentIndex(
                self.ui.comboBoxPedal2.findData(program.pedal2_type))
            for eff_param, value in program.pedal2_params.items():
                self._pedal2_widgets[eff_param.value][1].setValue(value)
                            
            self.ui.comboBoxReverb.setCurrentIndex(
                self.ui.comboBoxReverb.findData(program.reverb_type))
            for eff_param, value in program.reverb_params.items():
                self._reverb_sliders[eff_param.value].setValue(value)

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
                for label, widget in self._pedal1_widgets:
                    widget.setValue(program.pedal1_params[widget.param])
                return
            
            if vox_index is VoxIndex.PEDAL2:
                for label, widget in self._pedal2_widgets:
                    widget.setValue(program.pedal2_params[widget.param])
                return
            
            if vox_index is VoxIndex.REVERB:
                for widget in self._reverb_sliders:
                    widget.setValue(program.reverb_params[widget.param])
                return
    
    @pyqtSlot(int)
    def _effect_model_changed(self, index: int):
        print('choupinai')
        voxou: 'Voxou' = voxou_dict['voxou']
        if voxou is not None:
            sender: QComboBox = self.sender()
            print('choupizef', sender)
            if sender is self.ui.comboBoxAmpModel:
                effect_on_off = EffectOnOff.AMP
            elif sender is self.ui.comboBoxPedal1:
                effect_on_off = EffectOnOff.PEDAL1
            elif sender is self.ui.comboBoxPedal2:
                effect_on_off = EffectOnOff.PEDAL2
            elif sender is self.ui.comboBoxReverb:
                effect_on_off = EffectOnOff.REVERB
            else:
                return
            print('choupzessss', effect_on_off)
            voxou.set_param_value(
                VoxIndex.EFFECT_MODEL, effect_on_off, index)
    
    @pyqtSlot(float)
    def _amp_param_moved(self, value: float):
        param_wg: ParamProgressBar = self.sender()
        voxou: 'Voxou' = voxou_dict['voxou']
        if voxou is not None:
            voxou.set_param_value(VoxIndex.AMP, param_wg.param, int(value))
    
    @pyqtSlot(float)
    def _pedal1_param_moved(self, value: float):
        param_wg: ParamProgressBar = self.sender()
        voxou: 'Voxou' = voxou_dict['voxou']
        if voxou is not None:
            voxou.set_param_value(VoxIndex.PEDAL1, param_wg.param, int(value))
    
    @pyqtSlot(float)
    def _pedal2_param_moved(self, value: float):
        param_wg: ParamProgressBar = self.sender()
        voxou: 'Voxou' = voxou_dict['voxou']
        if voxou is not None:
            voxou.set_param_value(VoxIndex.PEDAL2, param_wg.param, int(value))
            
    @pyqtSlot(float)
    def _reverb_param_moved(self, value: float):
        param_wg: ParamProgressBar = self.sender()
        voxou: 'Voxou' = voxou_dict['voxou']
        if voxou is not None:
            voxou.set_param_value(VoxIndex.REVERB, param_wg.param, int(value))
    
    def _fill_pedal1(self, pedal1_type: Pedal1Type):
        pedal1_param: EffParam
        for pedal1_param in pedal1_type.param_type():
            label, param_wg = self._pedal1_widgets[pedal1_param.value]            
            label.setText(pedal1_param.display_name())
            
            param_wg.set_param(pedal1_param)
            param_wg.setVisible(bool(pedal1_param.display_name()))
        
    def _fill_pedal2(self, pedal2_type: Pedal2Type):
        pedal1_param: EffParam
        for pedal1_param in pedal2_type.param_type():
            label, param_wg = self._pedal2_widgets[pedal1_param.value]            
            label.setText(pedal1_param.display_name())
            
            param_wg.set_param(pedal1_param)
            param_wg.setVisible(bool(pedal1_param.display_name()))
            
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
        target=start_mentat, args=(main_win.engine_callback, voxou_dict))
    mentat_thread.start()
    
    main_win.show()
    app.exec()
    stop_mentat()