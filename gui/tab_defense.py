from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout

class DefenseTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Onglet 4: Contre-mesures (en construction)"))
        self.setLayout(layout)