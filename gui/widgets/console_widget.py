from PyQt6.QtWidgets import QTextEdit, QApplication
from PyQt6.QtCore import pyqtSlot, QDateTime
from PyQt6.QtGui import QTextCursor, QClipboard
import html

class ConsoleWidget(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.setFontFamily("Cascadia Code, Fira Code, Courier New, monospace")
        self.setFontPointSize(9)

    @pyqtSlot(str, str)
    def append_log(self, level, message):
        """
        Ajoute un message formaté HTML dans la console.
        
        Args:
            level (str): Niveau de log (INFO, OK, WARN, ERROR, TIMING, BIT).
            message (str): Le message à afficher.
        """
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss.zzz")
        escaped_message = html.escape(message)
        
        color_map = {
            "INFO": "#D5D8DC",  # Gris clair
            "OK": "#27AE60",    # Vert
            "WARN": "#D4770A",  # Ambre
            "ERROR": "#C0392B", # Rouge
            "TIMING": "#17A589", # Cyan
            "BIT": "#8E44AD",    # Magenta (violet)
        }
        
        color = color_map.get(level, "#FFFFFF")
        
        html_line = (
            f'<span style="color:#7F8C8D;">[{timestamp}]</span> '
            f'<span style="color:{color}; font-weight:bold;">[{level}]</span> '
            f'<span style="color:#EAECEE;">{escaped_message}</span><br>'
        )
        
        # Ajouter le HTML à la fin du document
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.insertHtml(html_line)
        # Assurer le défilement automatique vers le bas
        self.ensureCursorVisible()

    def copy_all(self):
        """Copie tout le contenu de la console dans le presse-papier."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.toPlainText(), QClipboard.Mode.Clipboard)
        self.append_log("INFO", "Contenu de la console copié dans le presse-papier.")
        
    # save_to_file à implémenter plus tard