from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import pyqtSignal

class DefenseTab(QWidget):
    log_message = pyqtSignal(str, str)
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Onglet 4: Contre-mesures (en construction)"))
        self.setLayout(layout)