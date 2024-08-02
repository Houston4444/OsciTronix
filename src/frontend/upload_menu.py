from typing import TYPE_CHECKING, Optional
from qtpy.QtWidgets import QApplication, QMenu

if TYPE_CHECKING:
    from frontend.main_window import MainWindow

_translate = QApplication.translate


class UploadMenu(QMenu):
    def __init__(self, main_win: 'MainWindow'):
        super().__init__()
        self.main_win = main_win
        self.build()
        
    def build(self, bank_num: Optional[int] =None):
        self.clear()
        
        banks_menu = QMenu(
            _translate('main_win',
                       '>> User Bank'),
            self)
        presets_menu = QMenu(
            _translate('main_win',
                       '>> User AmpFX'),
            self)
        
        for i in range(4):
            act = banks_menu.addAction(
                self.main_win.bank_icon.green, f'A{i+1}')
            act.setData(i)
            if bank_num == i:
                act.setIcon(self.main_win.bank_icon.green_sel)
            
            act.triggered.connect(self.main_win.upload_to_user_program)

        banks_menu.addSeparator()

        for i in range(4):
            act = banks_menu.addAction(
                self.main_win.bank_icon.red, f'B{i+1}')
            act.setData(i+4)
            if bank_num == i + 4:
                act.setIcon(self.main_win.bank_icon.red_sel)

            act.triggered.connect(self.main_win.upload_to_user_program)

        i = 0
        for letter in ('A', 'B', 'C'):
            act = presets_menu.addAction(f'USER {letter}')
            act.setData(i)
            act.triggered.connect(self.main_win.upload_to_user_ampfx)
            i += 1

        self.addMenu(banks_menu)
        self.addMenu(presets_menu)