from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from qtpy.QtWidgets import (
    QApplication, QMainWindow, QFileDialog,
    QCheckBox, QComboBox, QGroupBox, QMenu,
    QMessageBox, QAction)
from qtpy.QtCore import QTimer, Slot, Signal, QSettings

from app_infos import APP_NAME
from config import NsmMode
from frontend.local_program_dialog import LocalProgramDialog
import xdg
from midi_enums import MidiConnectState
from effects import (
    AmpModel, AmpParam, BankName, DummyParam, EffParam,
    EffectOnOff, Pedal1Type, Pedal2Type,
    ReverbParam, ReverbType, VoxIndex, VoxMode)
from engine import (CommunicationState, FunctionCode, EngineCallback,
                    VoxProgram, Engine)
from frontend.progress import ParamProgressBar
from frontend.amp_import_dialog import FullAmpImportDialog
from frontend.about_dialog import AboutDialog

from frontend.ui.main_win import Ui_MainWindow


_translate = QApplication.translate


class MainWindow(QMainWindow):
    callback_sig = Signal(Enum, object)
    nsm_show = Signal()
    nsm_hide = Signal()
    apply_under_nsm = Signal()
    config_changed = Signal()
    local_programs_changed = Signal()
    
    def __init__(self, engine: Engine):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.engine = engine
        self.engine.add_callback(self.engine_callback)

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

        self.ui.toolButtonSave.clicked.connect(self._save_to_local_program)
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
        
        self.ui.comboBoxLocalPrograms.activated.connect(
            self._load_local_program)
        self.ui.actionAutoConnectMidi.triggered.connect(
            self._auto_connect_device_change)
        self.ui.actionNsmFree.triggered.connect(
            self._nsm_mode_change)
        self.ui.actionLoadSavedProgram.triggered.connect(
            self._nsm_mode_change)
        self.ui.actionAboutOsciTronix.triggered.connect(
            self._about_oscitronix)
        self.ui.actionAboutQt.triggered.connect(QApplication.aboutQt)

        # manage saving paths
        self.data_path = xdg.xdg_data_home() / APP_NAME
        self.ui.actionSaveCurrentProgram.triggered.connect(
            self._save_current_program_to_disk)
        self.ui.actionLoadProgram.triggered.connect(
            self._load_program_from_disk)
        self.ui.actionSaveCompleteAmp.triggered.connect(
            self._save_full_amp)
        self.ui.actionLoadCompleteAmp.triggered.connect(
            self._load_full_amp)
        self.ui.actionQuit.triggered.connect(QApplication.quit)
        self.ui.actionHide.triggered.connect(self.hide)
        
        # visible only under NSM
        self.ui.actionHide.setVisible(False)
        self.ui.menuOptions.clear()
        self.ui.menuOptions.addAction(self.ui.actionAutoConnectMidi)
        
        self.comm_state_timer = QTimer()
        self.comm_state_timer.setInterval(100)
        self.comm_state_timer.setSingleShot(True)
        self.comm_state_timer.timeout.connect(self._comm_timer_timeout)
        
        self.connection_timer = QTimer()
        self.connection_timer.setInterval(200)
        self.connection_timer.timeout.connect(self._start_communication)
        self.connection_timer.start()
        
        # for NSM show/hide optional gui
        self._nsm_visible_cb: Optional[Callable[[bool], None]] = None
        self.nsm_show.connect(self.show)
        self.nsm_hide.connect(self.hide)
        self.apply_under_nsm.connect(self._under_nsm)
        self.config_changed.connect(self._config_changed)
        self.local_programs_changed.connect(self._local_programs_changed)
        
        geom = QSettings().value('MainWindow/geometry')
        if geom:
            self.restoreGeometry(geom)

    def set_nsm_visible_callback(self, nsm_cb: Callable[[bool], None]):
        self._nsm_visible_cb = nsm_cb
        self.apply_under_nsm.emit()

    @Slot()
    def _under_nsm(self):
        self.ui.actionQuit.setVisible(False)
        self.ui.actionHide.setVisible(True)
        self.ui.menuOptions.addMenu(self.ui.menuNsmMode)
    
    @Slot()
    def _config_changed(self):
        self.ui.actionAutoConnectMidi.setChecked(
            self.engine.config.auto_connect_device)
        self.ui.actionNsmFree.setChecked(
            self.engine.config.nsm_mode is NsmMode.FREE)
        self.ui.actionLoadSavedProgram.setChecked(
            self.engine.config.nsm_mode is NsmMode.LOAD_SAVED_PROGRAM)
    
    @Slot()
    def _local_programs_changed(self):
        self.ui.comboBoxLocalPrograms.clear()

        i, index = 0, 0
        for pname in self.engine.local_programs.keys():
            self.ui.comboBoxLocalPrograms.addItem(str(pname))
            if str(pname) == self.engine.current_local_pg_name:
                index = i
            i += 1

        if self.engine.current_local_pg_name:
            self.ui.comboBoxLocalPrograms.setCurrentIndex(index)
        else:
            self.ui.comboBoxLocalPrograms.setCurrentIndex(-1)
    
    @Slot(int)
    def _load_local_program(self, index: int):
        self.engine.load_local_program(
            self.ui.comboBoxLocalPrograms.currentText())
    
    @Slot()
    def _save_to_local_program(self):
        dialog = LocalProgramDialog(self)
        dialog.set_program_list(set(self.engine.local_programs.keys()))
        dialog.set_default_program_name(
            self.engine.current_program.program_name)
        
        if not dialog.exec():
            return

        self.engine.save_to_local_program(dialog.get_program_name())
    
    def set_communication_state(self, comm_state: CommunicationState):
        if comm_state.is_ok():
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
                    self.engine.prog_num)
            self.ui.comboBoxBanksAndPresets.setCurrentIndex(
                self.engine.prog_num)
            return
        
        # vox_mode is VoxMode.PRESET
        self.ui.labelBankPreset.setText(
            _translate('main_win', 'Preset'))

        for i in range(len(self.engine.factory_programs)):
            program = self.engine.factory_programs[i]
            self.ui.comboBoxBanksAndPresets.addItem(
                program.program_name, i)
        self.ui.comboBoxBanksAndPresets.setCurrentIndex(
            self.engine.prog_num)

    def engine_callback(self, *args):
        self.callback_sig.emit(*args)
    
    @Slot(EngineCallback, object)
    def apply_callback(self, cb: EngineCallback, arg: Any):
        if cb is EngineCallback.COMMUNICATION_STATE:
            comm_state: CommunicationState = arg
            self.set_communication_state(comm_state)
            if comm_state.is_ok():
                self.comm_state_timer.stop()
            else:
                if not self.comm_state_timer.isActive():
                    self.comm_state_timer.start()
                
        elif cb is EngineCallback.MIDI_CONNECT_STATE:
            self.set_midi_connect_state(arg)

        elif cb is EngineCallback.DATA_ERROR:
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

        elif cb is EngineCallback.MODE_CHANGED:
            vox_mode: VoxMode = arg
            self.set_vox_mode(vox_mode)

        elif cb is EngineCallback.USER_BANKS_READ:
            if self.ui.comboBoxMode.currentData() is VoxMode.USER:
                # update the banks combobox
                self.set_vox_mode(VoxMode.USER)

        elif cb is EngineCallback.FACTORY_BANKS_READ:
            if self.ui.comboBoxMode.currentData() is VoxMode.PRESET:
                # update the presets combobox
                self.set_vox_mode(VoxMode.PRESET)

        elif cb is EngineCallback.CURRENT_CHANGED:
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
        
        elif cb is EngineCallback.PARAM_CHANGED:
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
        
        elif cb is EngineCallback.PROGRAM_NAME_CHANGED:
            cursor_pos = -1
            if self.ui.lineEditProgramName.hasFocus():
                cursor_pos = self.ui.lineEditProgramName.cursorPosition()

            self.ui.lineEditProgramName.setText(arg)
            
            if cursor_pos != -1:
                self.ui.lineEditProgramName.setCursorPosition(cursor_pos)
                
        elif cb is EngineCallback.LOCAL_PROGRAMS_CHANGED:
            self._local_programs_changed()
    
    @Slot(float)
    def _noise_gate_changed(self, value: float):
        self.engine.set_param_value(
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
        
        self.engine.set_param_value(
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

        self.engine.set_param_value(
            VoxIndex.EFFECT_STATUS, param, int(yesno))
    
    @Slot(bool)
    def _amp_param_bool_changed(self, state: bool):
        checkbox: QCheckBox = self.sender()
        for param, cbox in self.amp_params_widgets.items():
            if cbox is checkbox:
                self.engine.set_param_value(VoxIndex.AMP, param, int(state))
                break
    
    @Slot(float)
    def _amp_param_moved(self, value: float):
        param_wg: ParamProgressBar = self.sender()
        self.engine.set_param_value(VoxIndex.AMP, param_wg.param, int(value))
    
    @Slot(float)
    def _pedal1_param_moved(self, value: float):
        param_wg: ParamProgressBar = self.sender()
        self.engine.set_param_value(VoxIndex.PEDAL1, param_wg.param, int(value))
    
    @Slot(float)
    def _pedal2_param_moved(self, value: float):
        param_wg: ParamProgressBar = self.sender()
        self.engine.set_param_value(VoxIndex.PEDAL2, param_wg.param, int(value))
            
    @Slot(float)
    def _reverb_param_moved(self, value: float):
        param_wg: ParamProgressBar = self.sender()
        self.engine.set_param_value(VoxIndex.REVERB, param_wg.param, int(value))
    
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
        self.set_communication_state(CommunicationState.LOSED)
        if not self.connection_timer.isActive():
            self.connection_timer.start()

    @Slot()
    def _start_communication(self):
        if self.engine.communication_state.is_ok():
            self.connection_timer.stop()
            self.ui.labelConnected.setText(
                _translate('main_win', 'Communication OK'))
            return
        
        self.engine.start_communication()
            
    @Slot()
    def _refresh_all(self):
        self.engine.start_communication()
            
    @Slot(str)
    def _set_program_name(self, text: str):
        self.engine.set_program_name(text)
            
    @Slot(int)
    def _change_mode(self, index: int):
        new_mode: VoxMode = self.ui.comboBoxMode.currentData()
        self.engine.set_mode(new_mode)
        self.set_vox_mode(new_mode)
    
    @Slot(int)
    def _change_program_number(self, index: int):
        vox_mode = self.ui.comboBoxMode.currentData()
        if vox_mode is VoxMode.PRESET:
            self.engine.set_preset_num(index)
        elif vox_mode is VoxMode.USER:
            self.engine.set_user_bank_num(index)
    
    @Slot()
    def _save_current_program_to_disk(self):
        default_path = self.data_path / 'programs'
        default_path.mkdir(parents=True, exist_ok=True)
        
        base = self.engine.current_program.program_name
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
            if not filepath.endswith('.json'):
                filepath += '.json'
            self.engine.save_current_program_to_disk(Path(filepath))
    
    @Slot()
    def _load_program_from_disk(self):
        default_path = self.data_path / 'programs'
        default_path.mkdir(parents=True, exist_ok=True)
        
        filepath, filter = QFileDialog.getOpenFileName(
            self, _translate('main_win', 'Save your program...'),
            str(default_path),
            _translate('main_win', 'JSON files (*.json)'))
        
        if filepath:
            self.engine.load_program_from_disk(filepath)
    
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
            self.engine.save_all_amp(filepath)
    
    @Slot()
    def _load_full_amp(self):
        dialog = FullAmpImportDialog(self, self.engine)
        dialog.exec()
    
    @Slot()
    def _upload_to_user_program(self):
        bank_num: int = self.sender().data()
        self.engine.upload_current_to_user_program(bank_num)
            
    @Slot()
    def _upload_to_user_ampfx(self):
        user_num: int = self.sender().data()
        self.engine.upload_current_to_user_ampfx(user_num)

    @Slot(bool)
    def _auto_connect_device_change(self, checked: bool):
        self.engine.config.auto_connect_device = checked

    @Slot(bool)
    def _nsm_mode_change(self, checked: bool):
        sender: QAction = self.sender()
        
        load_prog = bool(sender is self.ui.actionLoadSavedProgram)

        if load_prog:
            self.engine.config.nsm_mode = NsmMode.LOAD_SAVED_PROGRAM
        else:
            self.engine.config.nsm_mode = NsmMode.FREE

        self.ui.actionNsmFree.setChecked(not load_prog)
        self.ui.actionLoadSavedProgram.setChecked(load_prog)

    @Slot()
    def _about_oscitronix(self):
        dialog = AboutDialog(self)
        dialog.show()

    # reimplemented functions
    def showEvent(self, event):
        super().showEvent(event)
        if self._nsm_visible_cb is not None:
            self._nsm_visible_cb(True)
            
    def hideEvent(self, event):
        QSettings().setValue('MainWindow/geometry', self.saveGeometry())
        
        super().hideEvent(event)
        if self._nsm_visible_cb is not None:
            self._nsm_visible_cb(False)