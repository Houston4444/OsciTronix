
from qtpy.QtCore import Slot
from qtpy.QtWidgets import QDialog, QMainWindow

from unidecode import unidecode

from frontend.ui.local_program import Ui_DialogLocalProgram


class LocalProgramDialog(QDialog):
    def __init__(self, parent: QMainWindow):
        super().__init__(parent)
        self.ui = Ui_DialogLocalProgram()
        self.ui.setupUi(self)
        
        self._program_names = set[str]()

        self.ui.labelOverwrite.setVisible(False)
        self.ui.lineEdit.textEdited.connect(self._program_name_changed)
    
    def set_program_list(self, names: set[str]):
        self._program_names = names

    def set_default_program_name(self, program_name: str):
        self.ui.lineEdit.setText(program_name)
        
        if program_name in self._program_names:
            self.ui.labelOverwrite.setVisible(True)
        
    def get_program_name(self) -> str:
        return self.ui.lineEdit.text()
    
    @Slot(str)
    def _program_name_changed(self, new_name: str):
        cursor_pos = self.ui.lineEdit.cursorPosition()
        self.ui.lineEdit.setText(unidecode(new_name))
        self.ui.lineEdit.setCursorPosition(cursor_pos)
        
        self.ui.labelOverwrite.setVisible(new_name in self._program_names)