import logging
import os
from pathlib import Path
import json

from qtpy.QtCore import Slot
from qtpy.QtWidgets import (
    QDialog, QApplication, QDialogButtonBox,
    QFileDialog)   
from effects import BankName, EffectOnOff

import xdg
from version import APP_NAME
from vox_program import VoxProgram
from voxou import Voxou

import ui.full_amp_import


_logger = logging.getLogger(__name__)
_translate = QApplication.translate


class FullAmpConf:
    def __init__(self):
        self.programs = [VoxProgram() for i in range(8)]
        self.user_ampfxs = [VoxProgram() for i in range(4)]
        self.current_program = VoxProgram()


class FullAmpImportDialog(QDialog):
    def __init__(self, parent, voxou: Voxou):
        super().__init__(parent)
        self.ui = ui.full_amp_import.Ui_DialogFullAmpImport()
        self.ui.setupUi(self)
        
        self.voxou = voxou

        # fill combobox with amp configs found

        self.full_amps_dir = xdg.xdg_data_home() / APP_NAME / 'full_amps'
        full_amps = dict[str, Path]()
        
        for root, dirs, files in os.walk(self.full_amps_dir):
            for file in files:
                if file.endswith('.json'):                    
                    full_amps[file.rpartition('.')[0]] = Path(root) / file

        for amp_name, amp_path in full_amps.items():
            self.ui.comboBoxAmpConfig.addItem(amp_name, amp_path)
        
        self.ui.comboBoxAmpConfig.insertSeparator(
            self.ui.comboBoxAmpConfig.count())
        self.ui.comboBoxAmpConfig.addItem(
            _translate('amp_import', 'Choose another file...'), None)
        
        if full_amps:
            self.ui.groupBoxMainAction.setEnabled(True)
        self.ui.comboBoxAmpConfig.setCurrentIndex(0)
        
        if self.ui.comboBoxAmpConfig.currentData() is None:
            self.ui.framePathSelector.setEnabled(True)

        self.ui.labelInvalidFile.setVisible(False)

        # fill main choice combobox

        self.ui.comboBoxMainChoice.addItem(
            _translate('amp_import', 'Import full amp config'))
        self.ui.comboBoxMainChoice.addItem(
            _translate('amp_import', 'Import an AmpFx'))
        self.ui.comboBoxMainChoice.addItem(
            _translate('amp_import', 'Import a single program'))

        self.ui.comboBoxMainChoice.activated.connect(
            self.ui.stackedWidget.setCurrentIndex)
        
        # fill ampfx comboboxes
        
        for ampfx_str in ('USER A', 'USER B', 'USER C', 'USER D'):
            self.ui.comboBoxAmpFxFrom.addItem(ampfx_str)
            self.ui.comboBoxAmpFxTo.addItem(ampfx_str)
            
        # fill user bank comboboxes
        
        for bank_name in BankName:
            self.ui.comboBoxSingleFrom.addItem(
                bank_name.name, bank_name.value)
            self.ui.comboBoxSingleTo.addItem(
                bank_name.name, bank_name.value)
        current_str = _translate('amp_import', 'Current program')
        self.ui.comboBoxSingleFrom.addItem(current_str, -1)
        self.ui.comboBoxSingleTo.addItem(current_str, -1)
        
        self.ui.comboBoxSingleFrom.insertSeparator(4)
        self.ui.comboBoxSingleFrom.insertSeparator(9)
        self.ui.comboBoxSingleTo.insertSeparator(4)
        self.ui.comboBoxSingleTo.insertSeparator(9)
        
            
        self._full_amp_conf = FullAmpConf()
        
        self.ui.toolButtonBrowse.clicked.connect(self._browse)
        self.ui.comboBoxAmpConfig.activated.connect(
            self._amp_config_changed)
        self.ui.comboBoxAmpConfig.activated.emit(0)
        self.ui.comboBoxAmpFxFrom.activated.connect(
            self._ampfx_index_changed)
        self.ui.comboBoxAmpFxFrom.activated.emit(0)
        self.ui.comboBoxSingleFrom.activated.connect(
            self._single_bank_index_changed)
        self.ui.comboBoxSingleFrom.activated.emit(0)

        self.ui.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(
            self._apply_import)

    def _set_amp_file_valid(self, valid: bool):
        self.ui.labelInvalidFile.setVisible(not valid)
        self.ui.groupBoxMainAction.setEnabled(valid)

    def _set_full_amp_conf(self, file_path: Path):
        self._set_amp_file_valid(True)
        
        try:
            with open(file_path, 'r') as f:
                amp_dict: dict = json.load(f)
        except:
            _logger.warning(f'Failed to load {file_path} with json')
            self._set_amp_file_valid(False)
            return
        
        # Write the full amp conf
        
        self._full_amp_conf = FullAmpConf()

        banks_dict = amp_dict.get('banks')
        if banks_dict is not None:
            if not isinstance(banks_dict, list):
                self._set_amp_file_valid(False)
                return
            
            for bank_num in range(len(banks_dict)):
                if bank_num > 7:
                    break
                
                self._full_amp_conf.programs[bank_num] = \
                    VoxProgram.from_json_dict(banks_dict[bank_num])
        
        ampfxs_dict = amp_dict.get('ampfxs')
        if ampfxs_dict is not None:
            if not isinstance(ampfxs_dict, list):
                self._set_amp_file_valid(False)
                return
            
            for ampfx_num in range(len(ampfxs_dict)):
                if ampfx_num > 3:
                    break
                
                self._full_amp_conf.user_ampfxs[ampfx_num] = \
                    VoxProgram.from_json_dict(banks_dict[ampfx_num])
                    
        cur_prog_dict = amp_dict.get('current_program')
        if cur_prog_dict is not None:
            if not isinstance(cur_prog_dict, dict):
                self._set_amp_file_valid(False)
                return
            
            self._full_amp_conf.current_program = \
                VoxProgram.from_json_dict(cur_prog_dict)

        self.ui.labelAmpFxAmp.setText(
            self._full_amp_conf.user_ampfxs[
                self.ui.comboBoxAmpFxFrom.currentIndex()].amp_model.name)
        
        self.ui.labelSingleAmp.setText(
            self._full_amp_conf.programs[
                self.ui.comboBoxSingleFrom.currentIndex()].amp_model.name)

    @Slot(int)
    def _amp_config_changed(self, index: int):
        file_path = self.ui.comboBoxAmpConfig.currentData()
        if file_path is None:
            self.ui.framePathSelector.setEnabled(True)
            self.ui.toolButtonBrowse.clicked.emit()
            return
        
        self.ui.lineEditPath.setText('')
        self.ui.framePathSelector.setEnabled(False)
        self._set_full_amp_conf(file_path)
    
    @Slot()
    def _browse(self):
        filepath, filter = QFileDialog.getOpenFileName(
            self,
            "Select a full amp config file...",
            str(self.full_amps_dir),
            _translate('main_win', 'JSON files (*.json)'))

        if not filepath:
            return

        self.ui.lineEditPath.setText(filepath)
        self._set_full_amp_conf(Path(filepath))        
    
    @Slot(int)
    def _ampfx_index_changed(self, index: int):
        p = self._full_amp_conf.user_ampfxs[index]
        self.ui.labelAmpFxAmp.setText(p.amp_model.name)
        self.ui.labelAmpFxPedal1.setText(p.pedal1_type.name)
        self.ui.labelAmpFxPedal2.setText(p.pedal2_type.name)
        self.ui.labelAmpFxReverb.setText(p.reverb_type.name)
        
    @Slot(int)
    def _single_bank_index_changed(self, index: int):
        bank_index: int = self.ui.comboBoxSingleFrom.currentData()
        if 0 <= bank_index <= 7:
            p = self._full_amp_conf.programs[bank_index]
        else:
            p = self._full_amp_conf.current_program        
        
        self.ui.lineEditSingleProgramName.setText(p.program_name)
        self.ui.labelSingleAmp.setText(p.amp_model.name)
        self.ui.labelSinglePedal1.setText(p.pedal1_type.name)
        self.ui.labelSinglePedal2.setText(p.pedal2_type.name)
        self.ui.labelSingleReverb.setText(p.reverb_type.name)
        self.ui.labelSinglePedal1.setEnabled(
            bool(p.active_effects[EffectOnOff.PEDAL1]))
        self.ui.labelSinglePedal2.setEnabled(
            bool(p.active_effects[EffectOnOff.PEDAL2]))
        self.ui.labelSingleReverb.setEnabled(
            bool(p.active_effects[EffectOnOff.REVERB]))
    
    @Slot()
    def _apply_import(self):
        if not self.voxou.communication_state:
            return
        
        main_index = self.ui.comboBoxMainChoice.currentIndex()
        
        if main_index == 0:
            # global import
            
            if self.ui.checkBoxUserBanks.isChecked():
                for i in range(8):
                    self.voxou.load_bank(
                        self._full_amp_conf.programs[i], i)
                    
            if self.ui.checkBoxAmpFx.isChecked():
                for i in range(4):
                    self.voxou.load_ampfx(
                        self._full_amp_conf.user_ampfxs[i], i)
                    
            if self.ui.checkBoxCurrentProgram.isChecked():
                self.voxou.load_program(
                    self._full_amp_conf.current_program)
                    
        elif main_index == 1:
            # AmpFX import

            self.voxou.load_ampfx(
                self._full_amp_conf.user_ampfxs[
                    self.ui.comboBoxAmpFxFrom.currentIndex()],
                self.ui.comboBoxAmpFxTo.currentIndex())
            
        elif main_index == 2:
            # Single program import
            
            bank_in_num = self.ui.comboBoxSingleFrom.currentData()
            bank_out_num = self.ui.comboBoxSingleTo.currentData()
            
            if bank_in_num < 0 and bank_out_num < 0:
                # load current program to current program
                self.voxou.load_program(
                        self._full_amp_conf.current_program)
                return
            
            if bank_in_num < 0:
                # load current program to bank
                self.voxou.load_bank(
                    self._full_amp_conf.current_program, bank_out_num)
                return
            
            if bank_out_num < 0:
                # load bank to current program
                self.voxou.load_program(
                    self._full_amp_conf.programs[bank_in_num])
                return
                
            # load bank to bank
            self.voxou.load_bank(
                self._full_amp_conf.programs[bank_in_num], bank_out_num)
            return
            