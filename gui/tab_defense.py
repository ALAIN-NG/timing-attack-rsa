"""
Onglet 4 : Phase 4 - Contre-mesures
"""

import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox,
    QLabel, QPushButton, QTabWidget, QTextEdit, QProgressBar,
    QTableWidget, QTableWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont

from workers.defense_worker import DefenseWorker
from gui.widgets.mpl_canvas import MplWidget


class DefenseTab(QWidget):
    """Onglet 4 : Évaluation des contre-mesures."""
    
    log_message = pyqtSignal(str, str)
    
    def __init__(self):
        super().__init__()
        self.rsa_instance = None
        self.defense_results = {}
        self.worker = None
        
        self._init_ui()
    
    def set_rsa_instance(self, rsa_instance):
        """Définit l'instance RSA à utiliser."""
        self.rsa_instance = rsa_instance
        self._update_ui_state()
    
    def _update_ui_state(self):
        """Met à jour l'état de l'interface."""
        has_rsa = self.rsa_instance is not None
        self.eval_btn.setEnabled(has_rsa)
    
    def _init_ui(self):
        """Initialise l'interface utilisateur."""
        main_layout = QVBoxLayout(self)
        
        # Zone haute : graphiques comparatifs
        self.graph_tabs = QTabWidget()
        
        # Graphique 1 : Performances comparées
        self.perf_widget = MplWidget(width=8, height=5, dpi=100)
        self.graph_tabs.addTab(self.perf_widget, "Performances comparées")
        
        # Graphique 2 : Distributions
        self.dist_widget = MplWidget(width=8, height=5, dpi=100)
        self.graph_tabs.addTab(self.dist_widget, "Distributions")
        
        # Graphique 3 : Tableau de bord
        self.dashboard_widget = MplWidget(width=8, height=4, dpi=100)
        self.graph_tabs.addTab(self.dashboard_widget, "Tableau de bord")
        
        main_layout.addWidget(self.graph_tabs)
        
        # Zone basse : contrôles et sous-onglets
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Panneau gauche : contrôles
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Groupe : Configuration
        config_group = QGroupBox("Évaluation des contre-mesures")
        config_layout = QVBoxLayout(config_group)
        
        self.eval_btn = QPushButton("🚀 Évaluer les contre-mesures")
        self.eval_btn.setObjectName("primaryButton")
        self.eval_btn.setEnabled(False)
        self.eval_btn.clicked.connect(self._launch_evaluation)
        config_layout.addWidget(self.eval_btn)
        
        self.stop_btn = QPushButton("⏹ Arrêter")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_evaluation)
        config_layout.addWidget(self.stop_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        config_layout.addWidget(self.progress_bar)
        
        left_layout.addWidget(config_group)
        
        # Groupe : Résultats
        results_group = QGroupBox("Résultats")
        results_layout = QVBoxLayout(results_group)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Contre-mesure", "Médiane (ms)", "Moyenne (ms)", "Écart-type (ms)", "Surcoût (%)"
        ])
        self.results_table.setRowCount(3)
        self.results_table.setItem(0, 0, QTableWidgetItem("RSA Naïf"))
        self.results_table.setItem(1, 0, QTableWidgetItem("RSA Blinding"))
        self.results_table.setItem(2, 0, QTableWidgetItem("Montgomery Ladder"))
        
        for i in range(3):
            for j in range(1, 5):
                self.results_table.setItem(i, j, QTableWidgetItem("—"))
        
        results_layout.addWidget(self.results_table)
        
        left_layout.addWidget(results_group)
        left_layout.addStretch()
        
        # Panneau droit : code des contre-mesures
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.code_tabs = QTabWidget()
        
        # Sous-onglet Blinding
        blinding_widget = QWidget()
        blinding_layout = QVBoxLayout(blinding_widget)
        
        self.blinding_code = QTextEdit()
        self.blinding_code.setReadOnly(True)
        self.blinding_code.setFont(QFont("Cascadia Code, Fira Code, monospace", 9))
        self.blinding_code.setPlainText('''
# RSA Blinding - Algorithme

def decrypt_blinded(ciphertext):
    # 1. Générer r aléatoire
    r = random(2, N-1)  avec gcd(r, N) = 1
    
    # 2. Calculer r^e mod N
    r_e = pow(r, e, N)
    
    # 3. Aveugler le chiffré
    c_blind = (c * r_e) mod N
    
    # 4. Déchiffrer l'aveuglé
    m_blind = c_blind^d mod N
    
    # 5. Désaveugler
    r_inv = r^(-1) mod N
    m = (m_blind * r_inv) mod N
    
    return m

# Protection : le temps de déchiffrement
# n'est plus corrélé aux bits de d
        ''')
        blinding_layout.addWidget(self.blinding_code)
        
        self.code_tabs.addTab(blinding_widget, "RSA Blinding")
        
        # Sous-onglet Montgomery Ladder
        mladder_widget = QWidget()
        mladder_layout = QVBoxLayout(mladder_widget)
        
        self.mladder_code = QTextEdit()
        self.mladder_code.setReadOnly(True)
        self.mladder_code.setFont(QFont("Cascadia Code, Fira Code, monospace", 9))
        self.mladder_code.setPlainText('''
# Montgomery Ladder - Algorithme

def montgomery_ladder(base, exp, modulus):
    r0, r1 = 1, base
    
    for bit in bits_msb_first(exp):
        if bit == 0:
            r1 = (r0 * r1) % modulus
            r0 = (r0 * r0) % modulus
        else:
            r0 = (r0 * r1) % modulus
            r1 = (r1 * r1) % modulus
    
    return r0

# Protection : exactement 2 multiplications
# par bit, quelle que soit sa valeur.
# Note : en Python, le if/else crée une
# légère différence de timing CPU.
        ''')
        mladder_layout.addWidget(self.mladder_code)
        
        self.code_tabs.addTab(mladder_widget, "Montgomery Ladder")
        
        right_layout.addWidget(self.code_tabs)
        
        # Assemblage
        bottom_splitter.addWidget(left_widget)
        bottom_splitter.addWidget(right_widget)
        bottom_splitter.setSizes([400, 600])
        
        main_layout.addWidget(bottom_splitter)
    
    def _launch_evaluation(self):
        """Lance l'évaluation des contre-mesures."""
        if not self.rsa_instance:
            self.log_message.emit("WARN", "Générez d'abord des clés RSA")
            return
        
        self.eval_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        
        self.defense_results = {}
        
        self.worker = DefenseWorker(
            rsa_naive=self.rsa_instance,
            num_tests=100,
            repetitions=200
        )
        
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._on_log)
        self.worker.result_ready.connect(self._on_result_ready)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        
        self.worker.start()
    
    def _stop_evaluation(self):
        """Arrête l'évaluation."""
        if self.worker:
            self.worker.stop()
            self.worker.quit()
            self.worker.wait()
        
        self._reset_ui_state()
        self.log_message.emit("WARN", "Évaluation arrêtée")
    
    def _reset_ui_state(self):
        """Réinitialise l'état de l'interface."""
        self.eval_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
    
    @pyqtSlot(int, int)
    def _on_progress(self, current, total):
        self.progress_bar.setValue(current)
    
    @pyqtSlot(str, str)
    def _on_log(self, level, message):
        self.log_message.emit(level, message)
    
    @pyqtSlot(str, dict)
    def _on_result_ready(self, name, stats):
        """Appelé quand une contre-mesure est évaluée."""
        self.defense_results[name] = stats
        
        # Mettre à jour le tableau
        row_map = {'naive': 0, 'blinding': 1, 'montgomery': 2}
        if name in row_map:
            row = row_map[name]
            self.results_table.setItem(row, 1, QTableWidgetItem(f"{stats['median_ns']/1e6:.2f}"))
            self.results_table.setItem(row, 2, QTableWidgetItem(f"{stats['mean_ns']/1e6:.2f}"))
            self.results_table.setItem(row, 3, QTableWidgetItem(f"{stats['std_ns']/1e6:.2f}"))
            
            if 'overhead_pct' in stats:
                self.results_table.setItem(row, 4, QTableWidgetItem(f"{stats['overhead_pct']:.1f}%"))
        
        self.log_message.emit("OK", f"{name}: médiane={stats['median_ns']/1e6:.2f} ms")
    
    @pyqtSlot(dict)
    def _on_finished(self, all_results):
        """Appelé quand toutes les évaluations sont terminées."""
        self.defense_results = all_results
        self._reset_ui_state()
        
        # Mettre à jour les graphiques
        self._update_perf_chart()
        self._update_dist_chart()
        self._update_dashboard()
        
        self.log_message.emit("OK", "Évaluation terminée")
    
    @pyqtSlot(str)
    def _on_error(self, error_msg):
        self._reset_ui_state()
        self.log_message.emit("ERROR", error_msg)
    
    def _update_perf_chart(self):
        """Graphique des performances comparées."""
        ax = self.perf_widget.get_axes()
        ax.clear()
        
        if self.defense_results:
            names = []
            medians = []
            colors = ['#C0392B', '#2E75B6', '#27AE60']
            
            for i, (name, label) in enumerate([('naive', 'RSA Naïf'), 
                                                ('blinding', 'Blinding'), 
                                                ('montgomery', 'Montgomery')]):
                if name in self.defense_results:
                    names.append(label)
                    medians.append(self.defense_results[name]['median_ns'] / 1e6)
            
            bars = ax.bar(names, medians, color=colors[:len(names)], alpha=0.8)
            ax.set_ylabel('Temps médian (ms)')
            ax.set_title('Performances comparées des implémentations RSA')
            
            # Ajouter les valeurs sur les barres
            for bar, val in zip(bars, medians):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                       f'{val:.2f}', ha='center', va='bottom')
        
        self.perf_widget.canvas.draw()
    
    def _update_dist_chart(self):
        """Graphique des distributions."""
        ax = self.dist_widget.get_axes()
        ax.clear()
        
        if self.defense_results:
            # Boîte à moustaches pour chaque implémentation
            data = []
            labels = []
            
            for name, label in [('naive', 'Naïf'), ('blinding', 'Blinding'), ('montgomery', 'Montgomery')]:
                if name in self.defense_results:
                    # Simuler une distribution autour de la médiane
                    median = self.defense_results[name]['median_ns']
                    std = self.defense_results[name]['std_ns']
                    distribution = np.random.normal(median, std, 100)
                    data.append(distribution / 1e6)
                    labels.append(label)
            
            if data:
                bp = ax.boxplot(data, labels=labels, patch_artist=True)
                colors = ['#C0392B', '#2E75B6', '#27AE60']
                for patch, color in zip(bp['boxes'], colors[:len(data)]):
                    patch.set_facecolor(color)
                    patch.set_alpha(0.6)
                
                ax.set_ylabel('Temps (ms)')
                ax.set_title('Distribution des temps de déchiffrement')
        
        self.dist_widget.canvas.draw()
    
    def _update_dashboard(self):
        """Tableau de bord synthétique."""
        ax = self.dashboard_widget.get_axes()
        ax.clear()
        
        if self.defense_results:
            metrics = ['Médiane (ms)', 'Surcoût (%)', 'Écart-type (ms)']
            implementations = ['Naïf', 'Blinding', 'Montgomery']
            
            data = []
            for name in ['naive', 'blinding', 'montgomery']:
                if name in self.defense_results:
                    stats = self.defense_results[name]
                    data.append([
                        stats['median_ns'] / 1e6,
                        stats.get('overhead_pct', 0),
                        stats['std_ns'] / 1e6
                    ])
                else:
                    data.append([0, 0, 0])
            
            data = np.array(data).T
            
            im = ax.imshow(data, cmap='YlOrRd', aspect='auto')
            
            # Ajouter les valeurs
            for i in range(len(metrics)):
                for j in range(len(implementations)):
                    ax.text(j, i, f'{data[i, j]:.1f}', ha='center', va='center',
                           color='white' if data[i, j] > np.mean(data) else 'black')
            
            ax.set_xticks(range(len(implementations)))
            ax.set_xticklabels(implementations)
            ax.set_yticks(range(len(metrics)))
            ax.set_yticklabels(metrics)
            ax.set_title('Tableau de bord synthétique')
            
            self.dashboard_widget.canvas.fig.colorbar(im, ax=ax)
        
        self.dashboard_widget.canvas.draw()