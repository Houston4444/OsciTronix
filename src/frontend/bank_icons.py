
from qtpy.QtGui import QIcon, QPixmap

class BankIcon:
    def __init__(self):
        self.green = QIcon()
        self.green.addPixmap(QPixmap(':green.png'))
        self.red = QIcon()
        self.red.addPixmap(QPixmap(':red.png'))
        self.green_sel = QIcon()
        self.green_sel.addPixmap(QPixmap(':green_sel.png'))
        self.red_sel = QIcon()
        self.red_sel.addPixmap(QPixmap(':red_sel.png'))