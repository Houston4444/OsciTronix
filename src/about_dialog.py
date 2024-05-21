
from qtpy.QtWidgets import QDialog

from app_infos import VERSION

from ui.about_oscitronix import Ui_DialogAboutOscitronix


class AboutDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.ui = Ui_DialogAboutOscitronix()
        self.ui.setupUi(self)
        
        self.ui.labelOsciAndVersion.setText(
            self.ui.labelOsciAndVersion.text()
            % VERSION)