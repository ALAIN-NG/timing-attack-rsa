# gui/main_window.py
import os
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QMenuBar, QMenu, QToolBar, QStatusBar,
    QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QMessageBox,
    QApplication  # Ajout de cet import
)
from PyQt6.QtCore import Qt, QFile, QTextStream, QSize, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QIcon, QKeySequence

# Importer les futurs onglets
from gui.tab_rsa import RsaTab
from gui.tab_timing import TimingTab
from gui.tab_attack import AttackTab
from gui.tab_defense import DefenseTab
from gui.widgets.console_widget import ConsoleWidget

class MainWindow(QMainWindow):
    # Signal pour demander un changement de thème
    theme_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.current_theme = "dark"
        self.setWindowTitle("INF4268 - Attaque Temporelle sur RSA")
        self.setMinimumSize(1780, 1000)

        self._create_actions()
        self._create_menu_bar()
        self._create_tool_bar()
        self._create_central_widget()
        self._create_status_bar()

        # Connecter les signaux
        self.theme_changed.connect(self._apply_theme)

    def _create_actions(self):
        """Crée toutes les QAction utilisées dans les menus et barres d'outils."""
        # Menu Fichier
        self.new_exp_action = QAction("&Nouvelle expérience", self)
        self.new_exp_action.setShortcut(QKeySequence.StandardKey.New)
        self.new_exp_action.setStatusTip("Réinitialiser tous les paramètres")
        
        self.export_csv_action = QAction("Exporter données brutes &CSV", self)
        self.export_csv_action.setShortcut(QKeySequence("Ctrl+E"))
        self.export_csv_action.setStatusTip("Exporter les mesures de timing au format CSV")
        
        self.export_png_action = QAction("Exporter graphiques &PNG", self)
        self.export_png_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        self.export_png_action.setStatusTip("Exporter tous les graphiques en PNG 300 DPI")
        
        self.quit_action = QAction("&Quitter", self)
        self.quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.quit_action.setStatusTip("Quitter l'application")
        self.quit_action.triggered.connect(self.close)

        # Menu Expériences
        self.gen_keys_action = QAction("&Générer clés RSA", self)
        self.gen_keys_action.setShortcut(QKeySequence("F5"))
        self.gen_keys_action.setStatusTip("Lancer la génération de clés (Onglet 1)")
        
        self.measure_timing_action = QAction("&Lancer mesures de timing", self)
        self.measure_timing_action.setShortcut(QKeySequence("F6"))
        self.measure_timing_action.setStatusTip("Collecter les mesures temporelles (Onglet 2)")
        
        self.launch_attack_action = QAction("&Lancer attaque", self)
        self.launch_attack_action.setShortcut(QKeySequence("F7"))
        self.launch_attack_action.setStatusTip("Démarrer l'attaque par timing (Onglet 3)")
        
        self.eval_defense_action = QAction("É&valuer contre-mesures", self)
        self.eval_defense_action.setShortcut(QKeySequence("F8"))
        self.eval_defense_action.setStatusTip("Évaluer les contre-mesures (Onglet 4)")

        # Menu Affichage
        self.toggle_theme_action = QAction("Basculer mode &Sombre/Clair", self)
        self.toggle_theme_action.setShortcut(QKeySequence("Ctrl+T"))
        self.toggle_theme_action.setStatusTip("Basculer entre le thème sombre et clair")
        self.toggle_theme_action.triggered.connect(self._toggle_theme)
        
        self.popout_graph_action = QAction("Agrandir graphique actif", self)
        self.popout_graph_action.setShortcut(QKeySequence("Ctrl+G"))
        self.popout_graph_action.setStatusTip("Ouvrir le graphique actif dans une fenêtre séparée")

        # Menu Aide
        self.documentation_action = QAction("&Documentation", self)
        self.documentation_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        self.documentation_action.setStatusTip("Ouvrir le fichier README.md")
        
        self.about_action = QAction("À &propos", self)
        self.about_action.setShortcut(QKeySequence("Ctrl+I"))
        self.about_action.setStatusTip("À propos de cette application")
        self.about_action.triggered.connect(self._show_about_dialog)

    def _create_menu_bar(self):
        """Crée la barre de menu."""
        menu_bar = self.menuBar()

        # Menu Fichier
        file_menu = menu_bar.addMenu("&Fichier")
        file_menu.addAction(self.new_exp_action)
        file_menu.addSeparator()
        file_menu.addAction(self.export_csv_action)
        file_menu.addAction(self.export_png_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)

        # Menu Expériences
        exp_menu = menu_bar.addMenu("&Expériences")
        exp_menu.addAction(self.gen_keys_action)
        exp_menu.addAction(self.measure_timing_action)
        exp_menu.addAction(self.launch_attack_action)
        exp_menu.addAction(self.eval_defense_action)

        # Menu Affichage
        view_menu = menu_bar.addMenu("&Affichage")
        view_menu.addAction(self.toggle_theme_action)
        view_menu.addAction(self.popout_graph_action)

        # Menu Aide
        help_menu = menu_bar.addMenu("&Aide")
        help_menu.addAction(self.documentation_action)
        help_menu.addAction(self.about_action)

    def _create_tool_bar(self):
        """Crée la barre d'outils."""
        tool_bar = QToolBar("Barre d'outils principale")
        self.addToolBar(tool_bar)
        tool_bar.setIconSize(QSize(24, 24))

        tool_bar.addAction(self.new_exp_action)
        tool_bar.addSeparator()
        tool_bar.addAction(self.gen_keys_action)
        tool_bar.addAction(self.measure_timing_action)
        tool_bar.addAction(self.launch_attack_action)
        tool_bar.addAction(self.eval_defense_action)
        tool_bar.addSeparator()
        tool_bar.addAction(self.toggle_theme_action)

    def _create_central_widget(self):
        """Crée le widget central avec le QTabWidget et la console."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Onglets principaux
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setMovable(False)
        
        # Ajouter les 4 onglets
        self.rsa_tab = RsaTab()
        self.timing_tab = TimingTab()
        self.attack_tab = AttackTab()
        self.defense_tab = DefenseTab()
        
        self.tab_widget.addTab(self.rsa_tab, "Phase 1: RSA Naïf")
        self.tab_widget.addTab(self.timing_tab, "Phase 2: Mesures de Timing")
        self.tab_widget.addTab(self.attack_tab, "Phase 3: Attaque")
        self.tab_widget.addTab(self.defense_tab, "Phase 4: Contre-mesures")
        self.rsa_tab.log_message.connect(self.append_console_log)
        self.timing_tab.log_message.connect(self.append_console_log)
        # self.attack_tab.log_message.connect(self.append_console_log)
        # self.defense_tab.log_message.connect(self.append_console_log)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        main_layout.addWidget(self.tab_widget)
        self.timing_tab.session_loaded.connect(self._on_session_loaded)

        # Console de log
        console_container = QWidget()
        console_layout = QHBoxLayout(console_container)
        console_layout.setContentsMargins(4, 4, 4, 4)
        
        self.console = ConsoleWidget()
        # self.console.setMinimumWidth(620)
        self.console.setMaximumWidth(820)
        self.console.setMinimumHeight(100)
        console_layout.addWidget(self.console)
        
        # Boutons de la console
        btn_layout = QHBoxLayout()
        clear_btn = QPushButton("Effacer")
        clear_btn.clicked.connect(self.console.clear)
        copy_btn = QPushButton("Copier tout")
        copy_btn.clicked.connect(self.console.copy_all)
        save_btn = QPushButton("Sauvegarder (.txt)")
        # save_btn.clicked.connect(self.console.save_to_file) # A implémenter
        
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(copy_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        
        console_layout.addLayout(btn_layout)
        
        main_layout.addWidget(console_container)

    def _on_tab_changed(self, index):
        """Appelé quand l'utilisateur change d'onglet."""
        # Transmettre l'instance RSA à l'onglet 2
        if index == 1 and self.rsa_tab.rsa_instance:
            self.timing_tab.set_rsa_instance(self.rsa_tab.rsa_instance)
            
    def _create_status_bar(self):
        """Crée la barre de statut."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Prêt. Sélectionnez une action dans le menu.")

    def _toggle_theme(self):
        """Bascule entre le thème sombre et clair."""
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.theme_changed.emit(self.current_theme)

    def _apply_theme(self, theme_name):
        """Applique la feuille de style correspondant au thème."""
        file = QFile(f"gui/styles/{theme_name}_theme.qss")
        if file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
            stream = QTextStream(file)
            QApplication.instance().setStyleSheet(stream.readAll())
            file.close()
            self.status_bar.showMessage(f"Thème {theme_name} appliqué.", 2000)
        else:
            self.console.append_log("ERROR", f"Impossible de charger le thème {theme_name}.")

    def _show_about_dialog(self):
        """Affiche la boîte de dialogue 'À propos'."""
        QMessageBox.about(
            self,
            "À propos de RSA Timing Attack Lab",
            "<h3>INF4268 - Cryptographie Asymétrique</h3>"
            "<p><b>Projet 3: Attaque par Canal Auxiliaire (Timing) sur RSA</b></p>"
            "<p>Interface PyQt6 développée dans le cadre du Master 1 Sécurité Informatique.</p>"
            "<p>Enseignant: Dr. Ekodeck Stéphane Gaël R.</p>"
            "<p>Version 1.0</p>"
        )
    
    def _connect_tab_logs(self):
        """Connecte les signaux de log des onglets à la console."""
        # Onglet 1
        if hasattr(self.rsa_tab, 'worker'):
            # Sera connecté dynamiquement quand le worker est créé
            pass

    @pyqtSlot(str, str)
    def append_console_log(self, level: str, message: str):
        """Ajoute un message à la console."""
        self.console.append_log(level, message)

    def _on_tab_changed(self, index):
        """Appelé quand l'utilisateur change d'onglet."""
        # Transmettre l'instance RSA à l'onglet 2
        if index == 1 and self.rsa_tab.rsa_instance:
            self.timing_tab.set_rsa_instance(self.rsa_tab.rsa_instance)
        
        # Si on revient à l'onglet 1 après avoir chargé une session dans l'onglet 2
        if index == 0 and self.timing_tab.rsa_instance:
            # Synchroniser l'instance RSA
            if not self.rsa_tab.rsa_instance:
                self.rsa_tab.rsa_instance = self.timing_tab.rsa_instance
                self.rsa_tab._on_keygen_finished(self.timing_tab.rsa_instance)
    
    def _on_session_loaded(self, rsa_instance):
        """Appelé quand une session est chargée dans l'onglet 2."""
        self.rsa_tab.rsa_instance = rsa_instance
        self.rsa_tab._on_keygen_finished(rsa_instance)
        self.append_console_log("INFO", "Instance RSA synchronisée avec l'onglet 1")