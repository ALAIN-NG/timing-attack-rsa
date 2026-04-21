"""
Wrapper Matplotlib pour intégration dans PyQt6.
"""

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt


class MplCanvas(FigureCanvasQTAgg):
    """
    Canvas Matplotlib pour intégration PyQt6.
    Supporte le thème dark/light automatiquement.
    """
    
    def __init__(self, parent=None, width=5, height=4, dpi=100, dark_theme=True):
        self.dark_theme = dark_theme
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        
        # Configuration du thème
        self._apply_theme()
        
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Politique de taille
        self.setSizePolicy(
            self.sizePolicy().horizontalPolicy(),
            self.sizePolicy().verticalPolicy()
        )
        
    def _apply_theme(self):
        """Applique le thème à la figure."""
        if self.dark_theme:
            self.fig.patch.set_facecolor('#1E2333')
            self.default_text_color = '#EAECEE'
            self.default_grid_color = '#2C3E50'
        else:
            self.fig.patch.set_facecolor('#F4F6F9')
            self.default_text_color = '#2C3E50'
            self.default_grid_color = '#BDC3C7'
    
    def set_theme(self, dark_theme: bool):
        """Change le thème de la figure."""
        self.dark_theme = dark_theme
        self._apply_theme()
        self.draw()
    
    def get_axes(self):
        """Retourne les axes de la figure (en crée un si nécessaire)."""
        if not self.fig.axes:
            return self.fig.add_subplot(111)
        return self.fig.axes[0]
    
    def clear(self):
        """Efface tous les axes de la figure."""
        self.fig.clear()
    
    def set_labels(self, xlabel: str = None, ylabel: str = None, title: str = None):
        """Définit les labels des axes."""
        ax = self.get_axes()
        if xlabel:
            ax.set_xlabel(xlabel, color=self.default_text_color)
        if ylabel:
            ax.set_ylabel(ylabel, color=self.default_text_color)
        if title:
            ax.set_title(title, color=self.default_text_color)
        
        # Configurer les couleurs des ticks
        ax.tick_params(colors=self.default_text_color)
        
        # Configurer la grille
        ax.grid(True, alpha=0.3, color=self.default_grid_color)
        
        # Configurer les spines
        for spine in ax.spines.values():
            spine.set_color(self.default_text_color)


class MplWidget(QWidget):
    """
    Widget complet contenant un canvas Matplotlib et une barre d'outils.
    """
    
    def __init__(self, parent=None, width=5, height=4, dpi=100, dark_theme=True, with_toolbar=True):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Canvas
        self.canvas = MplCanvas(self, width, height, dpi, dark_theme)
        
        # Barre d'outils (optionnelle)
        if with_toolbar:
            self.toolbar = NavigationToolbar2QT(self.canvas, self)
            layout.addWidget(self.toolbar)
        
        layout.addWidget(self.canvas)
    
    def set_theme(self, dark_theme: bool):
        """Change le thème du canvas."""
        self.canvas.set_theme(dark_theme)
    
    def get_axes(self):
        """Retourne les axes du canvas."""
        return self.canvas.get_axes()
    
    def draw(self):
        """Redessine le canvas."""
        self.canvas.draw()
    
    def clear(self):
        """Efface le canvas."""
        self.canvas.clear()