from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout

class TimingTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Onglet 2: Mesures de Timing (en construction)"))
        self.setLayout(layout)