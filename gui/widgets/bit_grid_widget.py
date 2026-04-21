"""
Widget personnalisé pour afficher les bits sous forme de grille animée.
Utilisé pour visualiser l'exposant privé d et les bits extraits pendant l'attaque.
"""

from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QRect, QPropertyAnimation, pyqtProperty, pyqtSlot
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QFontMetrics


class BitGridWidget(QWidget):
    """
    Widget affichant une grille de bits avec animations.
    
    États visuels :
        - Inconnu : gris, "?"
        - En cours : bleu pulsé, "..."
        - Extrait = 0 : rouge, "0"
        - Extrait = 1 : vert, "1"
        - Correct : vert clair, "1 ✓"
        - Incorrect : rouge clair, "0 ✗"
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuration
        self.cell_size = 40
        self.spacing = 4
        self.columns = 16  # Nombre de colonnes par défaut
        
        # Données
        self.bits = []  # Liste des valeurs de bits
        self.states = []  # États : 'unknown', 'analyzing', 'extracted_0', 'extracted_1', 'correct', 'incorrect'
        self.current_analyzing = -1  # Index du bit en cours d'analyse
        
        # Animation
        self._pulse_value = 1.0
        self.pulse_animation = QPropertyAnimation(self, b"pulse_value")
        self.pulse_animation.setDuration(800)
        self.pulse_animation.setStartValue(0.3)
        self.pulse_animation.setEndValue(1.0)
        self.pulse_animation.setLoopCount(-1)  # Infini
        
        # Couleurs
        self.colors = {
            'unknown': QColor('#5D6D7E'),
            'unknown_border': QColor('#3D4D5E'),
            'analyzing': QColor('#2E75B6'),
            'extracted_0': QColor('#C0392B'),
            'extracted_1': QColor('#27AE60'),
            'correct': QColor('#D5F0DC'),
            'correct_text': QColor('#1E8449'),
            'incorrect': QColor('#FADBD8'),
            'incorrect_text': QColor('#922B21'),
            'text': QColor('#FFFFFF'),
            'border': QColor('#2C3E50'),
        }
        
        # Police
        self.font = QFont('Segoe UI', 12, QFont.Weight.Bold)
        
        # Taille minimale
        self.setMinimumSize(400, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    
    def set_bits(self, bits: list, states: list = None):
        """
        Définit la liste des bits à afficher.
        
        Args:
            bits: Liste des valeurs de bits (0 ou 1)
            states: Liste optionnelle des états ('unknown' par défaut)
        """
        self.bits = bits.copy()
        if states:
            self.states = states.copy()
        else:
            self.states = ['unknown'] * len(bits)
        
        self.current_analyzing = -1
        self.update()
    
    def set_bit_count(self, count: int):
        """
        Initialise une grille vide avec 'count' bits inconnus.
        
        Args:
            count: Nombre de bits
        """
        self.bits = [0] * count
        self.states = ['unknown'] * count
        self.current_analyzing = -1
        self.update()
    
    @pyqtSlot(int, int)
    def update_bit(self, position: int, value: int, state: str = None):
        """
        Met à jour un bit spécifique.
        
        Args:
            position: Index du bit (0 = MSB)
            value: Valeur du bit (0 ou 1)
            state: État optionnel (défaut: 'extracted_0' ou 'extracted_1')
        """
        if 0 <= position < len(self.bits):
            self.bits[position] = value
            
            if state:
                self.states[position] = state
            else:
                self.states[position] = f'extracted_{value}'
            
            self.update()
    
    @pyqtSlot(int)
    def set_analyzing(self, position: int):
        """
        Définit le bit en cours d'analyse.
        
        Args:
            position: Index du bit à analyser
        """
        if 0 <= position < len(self.states):
            # Réinitialiser l'état précédent si c'était 'analyzing'
            if self.current_analyzing >= 0 and self.current_analyzing < len(self.states):
                if self.states[self.current_analyzing] == 'analyzing':
                    self.states[self.current_analyzing] = 'unknown'
            
            self.current_analyzing = position
            self.states[position] = 'analyzing'
            self.pulse_animation.start()
            self.update()
    
    @pyqtSlot()
    def stop_analyzing(self):
        """Arrête l'animation d'analyse."""
        self.pulse_animation.stop()
        if self.current_analyzing >= 0 and self.current_analyzing < len(self.states):
            if self.states[self.current_analyzing] == 'analyzing':
                self.states[self.current_analyzing] = 'unknown'
        self.current_analyzing = -1
        self._pulse_value = 1.0
        self.update()
    
    def compare_with_real(self, real_bits: list):
        """
        Compare les bits extraits avec les bits réels et met à jour les états.
        
        Args:
            real_bits: Liste des bits réels de la clé privée
        """
        for i, (extracted, real) in enumerate(zip(self.bits, real_bits)):
            if self.states[i] in ['extracted_0', 'extracted_1']:
                if extracted == real:
                    self.states[i] = 'correct'
                else:
                    self.states[i] = 'incorrect'
        self.update()
    
    def reset(self):
        """Réinitialise tous les bits à l'état inconnu."""
        self.states = ['unknown'] * len(self.bits)
        self.current_analyzing = -1
        self.pulse_animation.stop()
        self._pulse_value = 1.0
        self.update()
    
    # Propriété pour l'animation de pulsation
    def get_pulse_value(self):
        return self._pulse_value
    
    def set_pulse_value(self, value):
        self._pulse_value = value
        self.update()
    
    pulse_value = pyqtProperty(float, get_pulse_value, set_pulse_value)
    
    def paintEvent(self, event):
        """Dessine la grille de bits."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self.font)
        
        if not self.bits:
            # Afficher un message si pas de bits
            painter.setPen(QColor('#7F8C8D'))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Aucune clé générée")
            return
        
        # Calculer la disposition
        rows = (len(self.bits) + self.columns - 1) // self.columns
        
        # Calculer la largeur totale pour centrer
        total_width = self.columns * (self.cell_size + self.spacing) - self.spacing
        total_height = rows * (self.cell_size + self.spacing) - self.spacing
        
        start_x = (self.width() - total_width) // 2
        start_y = (self.height() - total_height) // 2
        
        # Dessiner chaque bit
        for i, (bit, state) in enumerate(zip(self.bits, self.states)):
            row = i // self.columns
            col = i % self.columns
            
            x = start_x + col * (self.cell_size + self.spacing)
            y = start_y + row * (self.cell_size + self.spacing)
            
            self._draw_cell(painter, x, y, bit, state, i == self.current_analyzing)
    
    def _draw_cell(self, painter: QPainter, x: int, y: int, bit: int, state: str, is_analyzing: bool):
        """Dessine une cellule individuelle."""
        rect = QRect(x, y, self.cell_size, self.cell_size)
        
        # Déterminer les couleurs selon l'état
        if state == 'unknown':
            bg_color = self.colors['unknown']
            border_color = self.colors['unknown_border']
            text = "?"
            text_color = self.colors['text']
        elif state == 'analyzing':
            # Pulsation pour l'état "en cours"
            base_color = self.colors['analyzing']
            bg_color = QColor(
                base_color.red(),
                base_color.green(),
                base_color.blue(),
                int(150 * self._pulse_value)
            )
            border_color = QColor('#3498DB')
            text = "..."
            text_color = self.colors['text']
        elif state == 'extracted_0':
            bg_color = self.colors['extracted_0']
            border_color = QColor('#922B21')
            text = "0"
            text_color = self.colors['text']
        elif state == 'extracted_1':
            bg_color = self.colors['extracted_1']
            border_color = QColor('#1E8449')
            text = "1"
            text_color = self.colors['text']
        elif state == 'correct':
            bg_color = self.colors['correct']
            border_color = QColor('#27AE60')
            text = f"{bit} ✓"
            text_color = self.colors['correct_text']
        elif state == 'incorrect':
            bg_color = self.colors['incorrect']
            border_color = QColor('#E74C3C')
            text = f"{bit} ✗"
            text_color = self.colors['incorrect_text']
        else:
            bg_color = self.colors['unknown']
            border_color = self.colors['unknown_border']
            text = "?"
            text_color = self.colors['text']
        
        # Bordure plus épaisse pour le bit en cours
        if is_analyzing:
            pen = QPen(border_color, 3)
        else:
            pen = QPen(border_color, 2)
        
        # Dessiner le fond
        painter.setBrush(QBrush(bg_color))
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 6, 6)
        
        # Dessiner le texte
        painter.setPen(text_color)
        
        # Ajuster la taille du texte pour qu'il tienne
        fm = QFontMetrics(painter.font())
        text_rect = fm.boundingRect(text)
        
        text_x = x + (self.cell_size - text_rect.width()) // 2
        text_y = y + (self.cell_size + fm.height()) // 2 - 2
        
        painter.drawText(text_x, text_y, text)
    
    def sizeHint(self):
        """Taille suggérée pour le widget."""
        if not self.bits:
            return super().sizeHint()
        
        rows = (len(self.bits) + self.columns - 1) // self.columns
        width = self.columns * (self.cell_size + self.spacing) + 20
        height = rows * (self.cell_size + self.spacing) + 20
        
        return self.sizeHint().expandedTo(self.minimumSizeHint())