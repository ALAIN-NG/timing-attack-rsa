from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import pyqtSignal

class TimingTab(QWidget):
    log_message = pyqtSignal(str, str)
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Onglet 2: Mesures de Timing (en construction)"))
        self.setLayout(layout)