from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout

class AttackTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Onglet 3: Attaque (en construction)"))
        self.setLayout(layout)