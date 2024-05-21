from enum import Enum
from typing import Any

from qtpy.QtWidgets import (
    QApplication, QMainWindow, QFileDialog,
    QCheckBox, QComboBox, QGroupBox, QMenu,
    QMessageBox)
from qtpy.QtCore import QTimer, Slot, Signal
from amp_import_dialog import FullAmpImportDialog

import xdg
from midi_enums import MidiConnectState
from effects import (
    AmpModel, AmpParam, BankName, DummyParam, EffParam,
    EffectOnOff, Pedal1Type, Pedal2Type,
    ReverbParam, ReverbType, VoxIndex, VoxMode)
from voxou import FunctionCode, GuiCallback, VoxProgram, Voxou
from progress import ParamProgressBar
from about_dialog import AboutDialog

from ui.main_win import Ui_MainWindow


_translate = QApplication.translate


class MainWindow(QMainWindow):
    callback_sig = Signal(Enum, object)
    
    def __init__(self, voxou: Voxou):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.voxou = voxou
        self.voxou.set_gui_cb(self.engine_callback)

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
            AmpParam.BIAS_SHIFT: self.ui.progressBarBiasShift,
            AmpParam.CLASS: self.ui.progressBarClassAAB
        }
        
        for param, widget in self.amp_params_widgets.items():
            if isinstance(widget, ParamProgressBar):
                widget.set_param(param)
        
        for amp_model in AmpModel:
            self.ui.comboBoxAmpModel.addItem(
                amp_model.name.replace('_', ' '), amp_model)        

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

        for vox_mode in VoxMode:
            if vox_mode is VoxMode.PRESET:
                mode_name = _translate('main_win', 'Factory presets')
            elif vox_mode is VoxMode.USER:
                mode_name = _translate('main_win', 'User Banks')
            else:
                mode_name = _translate('main_win', 'Manual')

            self.ui.comboBoxMode.addItem(mode_name, vox_mode)

        self.ui.comboBoxMode.activated.connect(self._change_mode)
        self.ui.comboBoxBanksAndPresets.activated.connect(
            self._change_program_number)
        self.ui.lineEditProgramName.textEdited.connect(
            self._set_program_name)
        
        self.upload_menu = QMenu()
        banks_menu = QMenu(
            _translate('main_win',
                       '>> User Bank'),
            self.upload_menu)
        presets_menu = QMenu(
            _translate('main_win',
                       '>> User AmpFX'),
            self.upload_menu)
        
        for i in range(4):
            act = banks_menu.addAction(f'A{i+1}')
            act.setData(i)
            act.triggered.connect(self._upload_to_user_program)

        banks_menu.addSeparator()

        for i in range(4):
            act = banks_menu.addAction(f'B{i+1}')
            act.setData(i+4)
            act.triggered.connect(self._upload_to_user_program)

        i = 0
        for letter in ('A', 'B', 'C'):
            act = presets_menu.addAction(f'USER {letter}')
            act.setData(i)
            act.triggered.connect(self._upload_to_user_ampfx)
            i += 1

        self.upload_menu.addMenu(banks_menu)
        self.upload_menu.addMenu(presets_menu)
        self.ui.toolButtonUpload.setMenu(self.upload_menu)

        self.ui.progressBarNoiseGate.valueChanged.connect(
            self._noise_gate_changed)
        
        for combobox in (self.ui.comboBoxAmpModel,
                         self.ui.comboBoxPedal1,
                         self.ui.comboBoxPedal2,
                         self.ui.comboBoxReverb):
            combobox.activated.connect(self._effect_model_changed)

        for group_box in (self.ui.groupBoxPedal1,
                          self.ui.groupBoxPedal2,
                          self.ui.groupBoxReverb):
            group_box.clicked.connect(self._effect_checked)

        for amp_param, param_wg in self.amp_params_widgets.items():
            if isinstance(param_wg, ParamProgressBar):
                param_wg.valueChanged.connect(self._amp_param_moved)
            elif isinstance(param_wg, QCheckBox):
                param_wg.clicked.connect(self._amp_param_bool_changed)
        for label, param_wg in self._pedal1_widgets:
            param_wg.valueChanged.connect(self._pedal1_param_moved)
        for label, param_wg in self._pedal2_widgets:
            param_wg.valueChanged.connect(self._pedal2_param_moved)
        for param_wg in self._reverb_sliders:
            param_wg.valueChanged.connect(self._reverb_param_moved)

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
        
        self.ui.toolButtonRefresh.clicked.connect(self._refresh_all)
        
        self.ui.actionAboutOsciTronix.triggered.connect(
            self._about_oscitronix)
        self.ui.actionAboutQt.triggered.connect(QApplication.aboutQt)
        
        # manage saving paths
        self.data_path = xdg.xdg_data_home() / 'OsciTronix'
        self.ui.actionSaveCurrentProgram.triggered.connect(
            self._save_current_program_to_disk)
        self.ui.actionLoadProgram.triggered.connect(
            self._load_program_from_disk)
        self.ui.actionSaveCompleteAmp.triggered.connect(
            self._save_full_amp)
        self.ui.actionLoadCompleteAmp.triggered.connect(
            self._load_full_amp)
        
        self.comm_state_timer = QTimer()
        self.comm_state_timer.setInterval(100)
        self.comm_state_timer.setSingleShot(True)
        self.comm_state_timer.timeout.connect(self._comm_timer_timeout)
        
        self.connection_timer = QTimer()
        self.connection_timer.setInterval(200)
        self.connection_timer.timeout.connect(self._start_communication)
        self.connection_timer.start()
    
    def set_communication_state(self, state: bool):
        if state:
            text = _translate('main_win', 'Communication OK')
            style_sheet = 'QLabel{color: green}'
        else:
            text = _translate('main_win', 'Communication failure')
            style_sheet = 'QLabel{color: red}'

        self.ui.labelConnected.setStyleSheet(style_sheet)
        self.ui.labelConnected.setText(text)
    
    def set_midi_connect_state(self, connect_state: MidiConnectState):
        self.ui.labelMidiConnectState.setVisible(True)
        
        text = _translate('main_win', 'Absent device')
        if connect_state is MidiConnectState.DISCONNECTED:
            text = _translate('main_win', 'Not connected')
        elif connect_state is MidiConnectState.INPUT_ONLY:
            text = _translate('main_win', 'Output not connected')
        elif connect_state is MidiConnectState.OUTPUT_ONLY:
            text = _translate('main_win', 'Input not connected')
        elif connect_state is MidiConnectState.CONNECTED:
            text = ''
            self.ui.labelMidiConnectState.setVisible(False)
        
        self.ui.labelMidiConnectState.setText(text)

    def set_vox_mode(self, vox_mode: VoxMode):
        self.ui.comboBoxMode.setCurrentIndex(vox_mode.value)
        self.ui.comboBoxBanksAndPresets.clear()
        
        if vox_mode is VoxMode.MANUAL:
            self.ui.comboBoxBanksAndPresets.setEnabled(False)
            self.ui.labelBankPreset.setText('')
            return

        self.ui.comboBoxBanksAndPresets.setEnabled(True)

        if vox_mode is VoxMode.USER:
            self.ui.labelBankPreset.setText(
                _translate('main_win', 'Bank'))

            for bank_name in BankName:
                self.ui.comboBoxBanksAndPresets.addItem(
                    bank_name.name, bank_name.value)
                self.ui.comboBoxBanksAndPresets.setCurrentIndex(
                    self.voxou.prog_num)
            self.ui.comboBoxBanksAndPresets.setCurrentIndex(
                self.voxou.prog_num)
            return
        
        # vox_mode is VoxMode.PRESET
        self.ui.labelBankPreset.setText(
            _translate('main_win', 'Preset'))

        for i in range(len(self.voxou.factory_programs)):
            program = self.voxou.factory_programs[i]
            self.ui.comboBoxBanksAndPresets.addItem(
                program.program_name, i)
        self.ui.comboBoxBanksAndPresets.setCurrentIndex(
            self.voxou.prog_num)

    def engine_callback(self, *args):
        self.callback_sig.emit(*args)
    
    @Slot(GuiCallback, object)
    def apply_callback(self, cb: GuiCallback, arg: Any):
        if cb is GuiCallback.COMMUNICATION_STATE:
            if arg is True:
                self.set_communication_state(True)
                self.comm_state_timer.stop()
            else:
                if not self.comm_state_timer.isActive():
                    self.comm_state_timer.start()
                
        elif cb is GuiCallback.MIDI_CONNECT_STATE:
            self.set_midi_connect_state(arg)

        elif cb is GuiCallback.DATA_ERROR:
            function_code: FunctionCode = arg
            QMessageBox.critical(
                self,
                _translate('main_win', 'Data Error'),
                _translate('main_win',
                           "Amp sent an error message, "
                           "probably because the last %s was incorrect.\n"
                           "Try to restart the amp.")
                % function_code.name
            )            

        elif cb is GuiCallback.MODE_CHANGED:
            vox_mode: VoxMode = arg
            self.set_vox_mode(vox_mode)

        elif cb is GuiCallback.USER_BANKS_READ:
            if self.ui.comboBoxMode.currentData() is VoxMode.USER:
                # update the banks combobox
                self.set_vox_mode(VoxMode.USER)

        elif cb is GuiCallback.FACTORY_BANKS_READ:
            if self.ui.comboBoxMode.currentData() is VoxMode.PRESET:
                # update the presets combobox
                self.set_vox_mode(VoxMode.PRESET)

        elif cb is GuiCallback.CURRENT_CHANGED:
            program: 'VoxProgram' = arg
            
            self.ui.lineEditProgramName.setText(program.program_name.strip())
            self.ui.progressBarNoiseGate.setValue(program.nr_sens)
            
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
            
            eff_param: EffParam

            self.ui.comboBoxPedal1.setCurrentIndex(
                self.ui.comboBoxPedal1.findData(program.pedal1_type))
            for eff_param in program.pedal1_type.param_type():
                self._pedal1_widgets[eff_param.value][1].setValue(
                    program.pedal1_values[eff_param.value])
                            
            self.ui.comboBoxPedal2.setCurrentIndex(
                self.ui.comboBoxPedal2.findData(program.pedal2_type))
            for eff_param in program.pedal2_type.param_type():
                self._pedal2_widgets[eff_param.value][1].setValue(
                    program.pedal2_values[eff_param.value])
                            
            self.ui.comboBoxReverb.setCurrentIndex(
                self.ui.comboBoxReverb.findData(program.reverb_type))
            for rev_param in ReverbType:
                self._reverb_sliders[rev_param.value].setValue(
                    program.reverb_values[rev_param.value])

            return
        
        elif cb is GuiCallback.PARAM_CHANGED:
            program, vox_index, param_index = arg

            if vox_index is VoxIndex.NR_SENS:
                self.ui.progressBarNoiseGate.setValue(program.nr_sens)

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
                    widget.setValue(program.pedal1_values[widget.param.value])
                return
            
            if vox_index is VoxIndex.PEDAL2:
                for label, widget in self._pedal2_widgets:
                    widget.setValue(program.pedal2_values[widget.param.value])
                return
            
            if vox_index is VoxIndex.REVERB:
                for widget in self._reverb_sliders:
                    widget.setValue(program.reverb_values[widget.param.value])
                return
    
    @Slot(float)
    def _noise_gate_changed(self, value: float):
        self.voxou.set_param_value(
                VoxIndex.NR_SENS, DummyParam.DUMMY, int(value))

    @Slot(int)
    def _effect_model_changed(self, index: int):
        sender: QComboBox = self.sender()
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
        
        model: EffParam = sender.itemData(index)
        
        self.voxou.set_param_value(
            VoxIndex.EFFECT_MODEL, effect_on_off, model.value)
    
    @Slot(bool)
    def _effect_checked(self, yesno: bool):
        sender: QGroupBox = self.sender()
        if sender is self.ui.groupBoxPedal1:
            param = EffectOnOff.PEDAL1
        elif sender is self.ui.groupBoxPedal2:
            param = EffectOnOff.PEDAL2
        elif sender is self.ui.groupBoxReverb:
            param = EffectOnOff.REVERB
        else:
            return

        self.voxou.set_param_value(
            VoxIndex.EFFECT_STATUS, param, int(yesno))
    
    @Slot(bool)
    def _amp_param_bool_changed(self, state: bool):
        checkbox: QCheckBox = self.sender()
        for param, cbox in self.amp_params_widgets.items():
            if cbox is checkbox:
                self.voxou.set_param_value(VoxIndex.AMP, param, int(state))
                break
    
    @Slot(float)
    def _amp_param_moved(self, value: float):
        param_wg: ParamProgressBar = self.sender()
        self.voxou.set_param_value(VoxIndex.AMP, param_wg.param, int(value))
    
    @Slot(float)
    def _pedal1_param_moved(self, value: float):
        param_wg: ParamProgressBar = self.sender()
        self.voxou.set_param_value(VoxIndex.PEDAL1, param_wg.param, int(value))
    
    @Slot(float)
    def _pedal2_param_moved(self, value: float):
        param_wg: ParamProgressBar = self.sender()
        self.voxou.set_param_value(VoxIndex.PEDAL2, param_wg.param, int(value))
            
    @Slot(float)
    def _reverb_param_moved(self, value: float):
        param_wg: ParamProgressBar = self.sender()
        self.voxou.set_param_value(VoxIndex.REVERB, param_wg.param, int(value))
    
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
            
    @Slot(int)
    def amp_model_changed(self, index: int):
        amp_model: AmpModel = self.ui.comboBoxAmpModel.currentData()
        self.ui.checkBoxBrightCap.setVisible(amp_model.has_bright_cap())
        if amp_model.presence_is_tone():
            self.ui.labelPresenceTone.setText('Tone')
        else:
            self.ui.labelPresenceTone.setText('Presence')
    
    @Slot(int)
    def pedal1_effect_changed(self, index: int):
        pedal1_type = self.ui.comboBoxPedal1.currentData()
        if pedal1_type is not None:
            self._fill_pedal1(pedal1_type)
        
    @Slot(int)
    def pedal2_effect_changed(self, index: int):
        pedal2_type = self.ui.comboBoxPedal2.currentData()
        if pedal2_type is not None:
            self._fill_pedal2(pedal2_type)
    
    @Slot()
    def _comm_timer_timeout(self):
        self.set_communication_state(False)
        if not self.connection_timer.isActive():
            self.connection_timer.start()

    @Slot()
    def _start_communication(self):
        if self.voxou.communication_state is True:
            self.connection_timer.stop()
            self.ui.labelConnected.setText(
                _translate('main_win', 'Communication OK'))
            return
        
        self.voxou.start_communication()
            
    @Slot()
    def _refresh_all(self):
        self.voxou.start_communication()
            
    @Slot(str)
    def _set_program_name(self, text: str):
        normed_text = ''.join([chr(ord(c) % 128) for c in text])
        self.ui.lineEditProgramName.setText(normed_text)
        self.voxou.set_program_name(normed_text)
            
    @Slot(int)
    def _change_mode(self, index: int):
        new_mode: VoxMode = self.ui.comboBoxMode.currentData()
        self.voxou.set_mode(new_mode)
        self.set_vox_mode(new_mode)
    
    @Slot(int)
    def _change_program_number(self, index: int):
        vox_mode = self.ui.comboBoxMode.currentData()
        if vox_mode is VoxMode.PRESET:
            self.voxou.set_preset_num(index)
        elif vox_mode is VoxMode.USER:
            self.voxou.set_user_bank_num(index)
    
    @Slot()
    def _save_current_program_to_disk(self):
        default_path = self.data_path / 'programs'
        default_path.mkdir(parents=True, exist_ok=True)
        
        base = self.voxou.current_program.program_name
        default_file_path = default_path / f'{base}.json'
        if default_file_path.exists():
            num = 2
            while default_file_path.exists():
                default_file_path = default_path / f"{base} ({num}).json"
                num += 1
                
        filepath, filter = QFileDialog.getSaveFileName(
            self, _translate('main_win', 'Save your program...'),
            str(default_file_path),
            _translate('main_win', 'JSON files (*.json)'))
        
        if filepath:
            self.voxou.save_current_program_to_disk(filepath)
    
    @Slot()
    def _load_program_from_disk(self):
        default_path = self.data_path / 'programs'
        default_path.mkdir(parents=True, exist_ok=True)
        
        filepath, filter = QFileDialog.getOpenFileName(
            self, _translate('main_win', 'Save your program...'),
            str(default_path),
            _translate('main_win', 'JSON files (*.json)'))
        
        if filepath:
            self.voxou.load_program_from_disk(filepath)
    
    @Slot()
    def _save_full_amp(self):
        default_path = self.data_path / 'full_amps'
        default_path.mkdir(parents=True, exist_ok=True)
        
        base = _translate('main_win', 'my_amp')
        default_file_path = default_path / f'{base}.json'
        if default_file_path.exists():
            num = 2
            while default_file_path.exists():
                default_file_path = default_path / f"{base} ({num}).json"
                num += 1

        filepath, filter = QFileDialog.getSaveFileName(
            self, _translate('main_win', 'full amp destination'),
            str(default_file_path),
            _translate('main_win', 'JSON files (*.json)'))

        if filepath:
            self.voxou.save_all_amp(filepath)
    
    @Slot()
    def _load_full_amp(self):
        dialog = FullAmpImportDialog(self, self.voxou)
        dialog.exec()
        
        # default_path = self.data_path / 'full_amps'
        # default_path.mkdir(parents=True, exist_ok=True)
        
        # filepath, filter = QFileDialog.getOpenFileName(
        #     self, _translate('main_win', 'load full amp'),
        #     str(default_path),
        #     _translate('main_win', 'JSON files (*.json)'))
        
        # if filepath:
        #     self.voxou.load_full_amp(filepath, with_ampfxs=True)
    
    @Slot()
    def _upload_to_user_program(self):
        bank_num: int = self.sender().data()
        self.voxou.upload_current_to_user_program(bank_num)
            
    @Slot()
    def _upload_to_user_ampfx(self):
        user_num: int = self.sender().data()
        self.voxou.upload_current_to_user_ampfx(user_num)

    @Slot()
    def _about_oscitronix(self):
        dialog = AboutDialog(self)
        dialog.show()
