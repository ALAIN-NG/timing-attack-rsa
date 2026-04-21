# main.py
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QFile, QTextStream
from gui.main_window import MainWindow

def load_stylesheet(app, theme_name="dark"):
    """Charge et applique la feuille de style QSS."""
    try:
        file = QFile(f"gui/styles/{theme_name}_theme.qss")
        if file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
            stream = QTextStream(file)
            app.setStyleSheet(stream.readAll())
            file.close()
            return True
    except Exception as e:
        print(f"Erreur lors du chargement du thème {theme_name}: {e}")
    return False

def main():
    # Configuration High DPI - version corrigée pour PyQt6
    # Note: Dans PyQt6, la gestion High DPI est automatique par défaut
    # Nous n'avons plus besoin de définir AA_EnableHighDpiScaling
    
    app = QApplication(sys.argv)
    app.setApplicationName("RSA Timing Attack Lab")
    app.setOrganizationName("INF4268")

    # Charger le thème sombre par défaut
    load_stylesheet(app, "dark")

    # Créer et afficher la fenêtre principale
    window = MainWindow()
    window.show()

    # Lancer la boucle d'événements
    sys.exit(app.exec())

if __name__ == "__main__":
    main()