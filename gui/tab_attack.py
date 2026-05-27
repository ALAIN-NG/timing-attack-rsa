"""
Onglet 3 : Phase 3 - Attaque par Timing
"""

import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox,
    QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QProgressBar, QLCDNumber, QTableWidget, QTableWidgetItem,
    QMessageBox, QTabWidget, QFileDialog, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
import pandas as pd
import os

from workers.attack_worker import AttackWorker
from gui.widgets.bit_grid_widget import BitGridWidget
from gui.widgets.mpl_canvas import MplWidget
from core.stats import compute_roc_curve, confusion_matrix
from core.timing_bench import TimingResult


def _get_attr(r, attr, default=None):
    """Accède à un attribut d'un résultat, qu'il soit un objet ou un dictionnaire."""
    if isinstance(r, dict):
        return r.get(attr, default)
    return getattr(r, attr, default)


class AttackTab(QWidget):
    """Onglet 3 : Configuration et exécution de l'attaque."""
    
    log_message = pyqtSignal(str, str)
    request_measurements = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.rsa_instance = None
        self.measurements = []
        self.attack_results = []
        self.worker = None
        self.chrono_timer = QTimer()
        self.chrono_timer.timeout.connect(self._update_chrono)
        self.chrono_seconds = 0
        
        self._init_ui()
    
    def set_rsa_instance(self, rsa_instance):
        self.rsa_instance = rsa_instance
        self._update_ui_state()
    
    def set_measurements(self, measurements):
        self.measurements = measurements if measurements else []
        self._update_ui_state()
        if measurements:
            self.log_message.emit("INFO", f"{len(measurements)} mesures chargées pour l'attaque")
    
    def _update_ui_state(self):
        has_rsa = self.rsa_instance is not None
        has_measurements = len(self.measurements) > 0
        
        if has_measurements:
            self.data_status_label.setText(f"✅ {len(self.measurements)} mesures disponibles")
            self.data_status_label.setStyleSheet("color: #27AE60; font-weight: bold;")
        elif has_rsa:
            self.data_status_label.setText("⚠️ Instance RSA chargée, mais pas de mesures")
            self.data_status_label.setStyleSheet("color: #D4770A; font-weight: bold;")
        else:
            self.data_status_label.setText("❌ Aucune donnée chargée")
            self.data_status_label.setStyleSheet("color: #C0392B; font-weight: bold;")
        
        self.launch_btn.setEnabled(has_rsa and has_measurements)
        
        if has_rsa:
            d_bits = self.rsa_instance.get_bits_msb_first(self.rsa_instance.d)
            self.bit_grid.set_bit_count(len(d_bits))
            self.bit_grid.set_bits(d_bits, ['unknown'] * len(d_bits))
            self._update_grid_size()
            self.total_bits_label.setText(f"/ {len(d_bits)} bits")
            self.bits_extracted_lcd.display(0)
            self.success_label.setText("—")
            self.success_label.setStyleSheet("font-weight: bold;")
            self.d_partial_label.setText("—")
            self.delta_label.setText("— ns")
    
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # ==================== PANNEAU GAUCHE ====================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Scénario
        scenario_group = QGroupBox("Scénario d'expérimentation")
        scenario_layout = QVBoxLayout(scenario_group)
        self.scenario_combo = QComboBox()
        self.scenario_combo.addItem("S1 - Baseline (RSA-512, D=1000)", "S1")
        self.scenario_combo.addItem("S2 - Principal (RSA-1024, D=2000)", "S2")
        self.scenario_combo.addItem("S3 - Bruit faible (Docker isolé)", "S3")
        self.scenario_combo.addItem("S4 - Bruit fort (Charge CPU)", "S4")
        self.scenario_combo.addItem("S5 - Seuil minimal", "S5")
        self.scenario_combo.currentIndexChanged.connect(self._on_scenario_changed)
        scenario_layout.addWidget(self.scenario_combo)
        left_layout.addWidget(scenario_group)
        
        # Configuration
        config_group = QGroupBox("Configuration de l'attaque")
        config_layout = QVBoxLayout(config_group)
        
        metric_layout = QHBoxLayout()
        metric_layout.addWidget(QLabel("Métrique :"))
        self.metric_combo = QComboBox()
        self.metric_combo.addItem("Différence de moyenne", "mean_diff")
        self.metric_combo.addItem("T-test de Student", "t_test")
        self.metric_combo.addItem("Corrélation de Pearson", "pearson")
        self.metric_combo.addItem("Corrélation de Spearman", "spearman")
        metric_layout.addWidget(self.metric_combo)
        config_layout.addLayout(metric_layout)
        
        bits_layout = QHBoxLayout()
        bits_layout.addWidget(QLabel("Bits à extraire :"))
        self.bits_spin = QSpinBox()
        self.bits_spin.setRange(4, 1022)
        self.bits_spin.setValue(8)
        bits_layout.addWidget(self.bits_spin)
        config_layout.addLayout(bits_layout)
        
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Position départ :"))
        self.start_spin = QSpinBox()
        self.start_spin.setRange(1, 100)
        self.start_spin.setValue(1)
        start_layout.addWidget(self.start_spin)
        config_layout.addLayout(start_layout)
        
        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("Seuil p-value :"))
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.01, 0.5)
        self.confidence_spin.setValue(0.05)
        self.confidence_spin.setSingleStep(0.01)
        conf_layout.addWidget(self.confidence_spin)
        config_layout.addLayout(conf_layout)
        
        left_layout.addWidget(config_group)
        
        # Contrôles
        control_group = QGroupBox("Exécution")
        control_layout = QVBoxLayout(control_group)
        
        self.launch_btn = QPushButton("🚀 Lancer l'attaque")
        self.launch_btn.setObjectName("dangerButton")
        self.launch_btn.setEnabled(False)
        self.launch_btn.clicked.connect(self._launch_attack)
        control_layout.addWidget(self.launch_btn)
        
        pause_layout = QHBoxLayout()
        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._pause_attack)
        pause_layout.addWidget(self.pause_btn)
        self.stop_btn = QPushButton("⏹ Arrêter")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_attack)
        pause_layout.addWidget(self.stop_btn)
        control_layout.addLayout(pause_layout)
        
        self.reset_btn = QPushButton("🔄 Réinitialiser")
        self.reset_btn.clicked.connect(self._reset_attack)
        control_layout.addWidget(self.reset_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)
        
        left_layout.addWidget(control_group)
        
        # Source des données
        data_group = QGroupBox("Source des données")
        data_layout = QVBoxLayout(data_group)
        self.data_status_label = QLabel("Aucune donnée chargée")
        self.data_status_label.setStyleSheet("color: #C0392B; font-weight: bold;")
        data_layout.addWidget(self.data_status_label)
        
        self.load_measures_btn = QPushButton("📂 Charger des mesures depuis un fichier")
        self.load_measures_btn.clicked.connect(self._load_measurements_from_file)
        data_layout.addWidget(self.load_measures_btn)
        
        self.use_tab2_btn = QPushButton("📊 Utiliser les mesures de l'onglet 2")
        self.use_tab2_btn.clicked.connect(self._use_measurements_from_tab2)
        data_layout.addWidget(self.use_tab2_btn)
        left_layout.addWidget(data_group)
        
        # Métriques en temps réel
        metrics_group = QGroupBox("Métriques en temps réel")
        metrics_layout = QVBoxLayout(metrics_group)
        
        bits_extracted_layout = QHBoxLayout()
        bits_extracted_layout.addWidget(QLabel("Bits extraits :"))
        self.bits_extracted_lcd = QLCDNumber()
        self.bits_extracted_lcd.setDigitCount(3)
        self.bits_extracted_lcd.display(0)
        bits_extracted_layout.addWidget(self.bits_extracted_lcd)
        self.total_bits_label = QLabel("/ 0 bits")
        bits_extracted_layout.addWidget(self.total_bits_label)
        bits_extracted_layout.addStretch()
        metrics_layout.addLayout(bits_extracted_layout)
        
        success_layout = QHBoxLayout()
        success_layout.addWidget(QLabel("Taux de succès :"))
        self.success_label = QLabel("—")
        self.success_label.setStyleSheet("font-weight: bold;")
        success_layout.addWidget(self.success_label)
        success_layout.addStretch()
        metrics_layout.addLayout(success_layout)
        
        measures_layout = QHBoxLayout()
        measures_layout.addWidget(QLabel("Mesures utilisées :"))
        self.measures_label = QLabel("0")
        measures_layout.addWidget(self.measures_label)
        measures_layout.addStretch()
        metrics_layout.addLayout(measures_layout)
        
        chrono_layout = QHBoxLayout()
        chrono_layout.addWidget(QLabel("Temps d'exécution :"))
        self.chrono_label = QLabel("00:00")
        self.chrono_label.setStyleSheet("font-family: monospace; font-size: 14pt;")
        chrono_layout.addWidget(self.chrono_label)
        chrono_layout.addStretch()
        metrics_layout.addLayout(chrono_layout)
        
        delta_layout = QHBoxLayout()
        delta_layout.addWidget(QLabel("Δ timing moyen :"))
        self.delta_label = QLabel("— ns")
        delta_layout.addWidget(self.delta_label)
        delta_layout.addStretch()
        metrics_layout.addLayout(delta_layout)
        
        d_partial_layout = QHBoxLayout()
        d_partial_layout.addWidget(QLabel("d partiel :"))
        self.d_partial_label = QLabel("—")
        self.d_partial_label.setStyleSheet("font-family: monospace;")
        d_partial_layout.addWidget(self.d_partial_label)
        metrics_layout.addLayout(d_partial_layout)
        
        left_layout.addWidget(metrics_group)
        left_layout.addStretch()
        
        # ==================== PANNEAU DROIT ====================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # BitGridWidget avec barre de défilement et zoom
        grid_group = QGroupBox("Bits extraits (animé)")
        grid_layout = QVBoxLayout(grid_group)
        
        # ScrollArea pour le défilement
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.bit_grid = BitGridWidget()
        self.bit_grid.setMinimumSize(900, 350)
        self.scroll_area.setWidget(self.bit_grid)
        grid_layout.addWidget(self.scroll_area)
        
        # Contrôles de zoom
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("Zoom :"))
        
        zoom_out_btn = QPushButton("🔍-")
        zoom_out_btn.setMaximumWidth(50)
        zoom_out_btn.setToolTip("Réduire la taille des cellules")
        zoom_out_btn.clicked.connect(lambda: self._zoom_grid(-5))
        zoom_layout.addWidget(zoom_out_btn)
        
        zoom_in_btn = QPushButton("🔍+")
        zoom_in_btn.setMaximumWidth(50)
        zoom_in_btn.setToolTip("Agrandir la taille des cellules")
        zoom_in_btn.clicked.connect(lambda: self._zoom_grid(5))
        zoom_layout.addWidget(zoom_in_btn)
        
        zoom_reset_btn = QPushButton("↺")
        zoom_reset_btn.setMaximumWidth(50)
        zoom_reset_btn.setToolTip("Réinitialiser le zoom")
        zoom_reset_btn.clicked.connect(lambda: self._zoom_grid(0))
        zoom_layout.addWidget(zoom_reset_btn)
        
        zoom_layout.addStretch()
        grid_layout.addLayout(zoom_layout)
        
        right_layout.addWidget(grid_group)
        
        # Graphiques
        graphs_tabs = QTabWidget()
        self.diff_widget = MplWidget(width=6, height=3, dpi=100)
        graphs_tabs.addTab(self.diff_widget, "Différences de timing")
        self.roc_widget = MplWidget(width=6, height=3, dpi=100)
        graphs_tabs.addTab(self.roc_widget, "Courbe ROC")
        self.confusion_widget = MplWidget(width=6, height=3, dpi=100)
        graphs_tabs.addTab(self.confusion_widget, "Matrice de confusion")
        right_layout.addWidget(graphs_tabs)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 700])
        main_layout.addWidget(splitter)
    
    def _zoom_grid(self, delta):
        """Ajuste la taille des cellules du BitGridWidget."""
        if delta == 0:
            self.bit_grid.cell_size = 40
        else:
            self.bit_grid.cell_size = max(20, min(80, self.bit_grid.cell_size + delta))
        self._update_grid_size()
        self.log_message.emit("INFO", f"Zoom: cellules = {self.bit_grid.cell_size}px")
    
    def _update_grid_size(self):
        """Recalcule la taille minimale du BitGridWidget selon le nombre de bits."""
        if self.rsa_instance:
            d_bits = self.rsa_instance.get_bits_msb_first(self.rsa_instance.d)
            rows = (len(d_bits) + self.bit_grid.columns - 1) // self.bit_grid.columns
            w = self.bit_grid.columns * (self.bit_grid.cell_size + self.bit_grid.spacing) + 20
            h = rows * (self.bit_grid.cell_size + self.bit_grid.spacing) + 20
            self.bit_grid.setMinimumSize(w, h)
            self.bit_grid.update()
    
    def _on_scenario_changed(self, index):
        scenario = self.scenario_combo.currentData()
        scenarios_config = {
            "S1": {"bits": 8, "metric": "t_test"},
            "S2": {"bits": 12, "metric": "t_test"},
            "S3": {"bits": 10, "metric": "pearson"},
            "S4": {"bits": 8, "metric": "spearman"},
            "S5": {"bits": 4, "metric": "mean_diff"}
        }
        if scenario in scenarios_config:
            config = scenarios_config[scenario]
            self.bits_spin.setValue(config["bits"])
            for i in range(self.metric_combo.count()):
                if self.metric_combo.itemData(i) == config["metric"]:
                    self.metric_combo.setCurrentIndex(i)
                    break
        self.log_message.emit("INFO", f"Scénario {scenario} sélectionné")
    
    def _launch_attack(self):
        if not self.rsa_instance or not self.measurements:
            self.log_message.emit("WARN", "Données insuffisantes pour l'attaque")
            return
        
        self.launch_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.reset_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, self.bits_spin.value())
        
        d_bits = self.rsa_instance.get_bits_msb_first(self.rsa_instance.d)
        self.bit_grid.set_bit_count(len(d_bits))
        self.bit_grid.set_bits(d_bits, ['unknown'] * len(d_bits))
        self._update_grid_size()
        
        start_pos = self.start_spin.value()
        self.bit_grid.set_analyzing(start_pos)
        
        self.chrono_seconds = 0
        self.chrono_timer.start(1000)
        self.bits_extracted_lcd.display(0)
        self.measures_label.setText(str(len(self.measurements)))
        self.attack_results = []
        
        self.worker = AttackWorker(
            rsa_instance=self.rsa_instance,
            measurements=self.measurements,
            start_position=self.start_spin.value(),
            num_bits=self.bits_spin.value(),
            metric=self.metric_combo.currentData(),
            confidence_threshold=self.confidence_spin.value()
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.bit_extracted.connect(self._on_bit_extracted)
        self.worker.log.connect(self._on_log)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()
        self.log_message.emit("INFO", f"Attaque lancée : {self.bits_spin.value()} bits à extraire")
    
    def _pause_attack(self):
        if self.worker:
            if self.pause_btn.text() == "⏸ Pause":
                self.pause_btn.setText("▶ Reprendre")
                self.chrono_timer.stop()
                self.log_message.emit("INFO", "Attaque en pause")
            else:
                self.pause_btn.setText("⏸ Pause")
                self.chrono_timer.start(1000)
                self.log_message.emit("INFO", "Attaque reprise")
    
    def _stop_attack(self):
        if self.worker:
            self.worker.stop()
            self.worker.quit()
            self.worker.wait()
        self._reset_ui_state()
        self.log_message.emit("WARN", "Attaque arrêtée par l'utilisateur")
    
    def _reset_attack(self):
        if self.rsa_instance:
            d_bits = self.rsa_instance.get_bits_msb_first(self.rsa_instance.d)
            self.bit_grid.reset()
            self.bit_grid.set_bits(d_bits, ['unknown'] * len(d_bits))
        self.attack_results = []
        self.bits_extracted_lcd.display(0)
        self.success_label.setText("—")
        self.delta_label.setText("— ns")
        self.d_partial_label.setText("—")
        self.chrono_seconds = 0
        self.chrono_label.setText("00:00")
        self.log_message.emit("INFO", "Attaque réinitialisée")
    
    def _reset_ui_state(self):
        self.launch_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸ Pause")
        self.stop_btn.setEnabled(False)
        self.reset_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.chrono_timer.stop()
    
    def _update_chrono(self):
        self.chrono_seconds += 1
        minutes = self.chrono_seconds // 60
        seconds = self.chrono_seconds % 60
        self.chrono_label.setText(f"{minutes:02d}:{seconds:02d}")
    
    @pyqtSlot(int, int)
    def _on_progress(self, current, total):
        self.progress_bar.setValue(current)
    
    @pyqtSlot(int, int, bool)
    def _on_bit_extracted(self, position, value, is_correct):
        result_dict = {
            'position': position,
            'extracted_value': value,
            'is_correct': is_correct,
            'actual_value': -1,
            'metric_value': 0.0,
            'confidence': 0.0
        }
        self.attack_results.append(result_dict)
        
        state = 'correct' if is_correct else 'incorrect'
        self.bit_grid.update_bit(position, value, state)
        self.bits_extracted_lcd.display(len(self.attack_results))
        
        if self.attack_results:
            correct = sum(1 for r in self.attack_results if r['is_correct'])
            rate = (correct / len(self.attack_results)) * 100
            self.success_label.setText(f"{rate:.1f}%")
            if rate >= 70:
                self.success_label.setStyleSheet("color: #27AE60; font-weight: bold;")
            elif rate >= 50:
                self.success_label.setStyleSheet("color: #D4770A; font-weight: bold;")
            else:
                self.success_label.setStyleSheet("color: #C0392B; font-weight: bold;")
        
        extracted_bits = {r['position']: r['extracted_value'] for r in self.attack_results}
        d_partial = 1
        for pos in sorted(extracted_bits.keys()):
            d_partial = (d_partial << 1) | extracted_bits[pos]
        d_hex = hex(d_partial)
        if len(d_hex) > 30:
            d_hex = d_hex[:25] + "..." + d_hex[-5:]
        self.d_partial_label.setText(d_hex)
        
        next_position = position + 1
        d_bits = self.rsa_instance.get_bits_msb_first(self.rsa_instance.d)
        end_position = self.start_spin.value() + self.bits_spin.value()
        if next_position < end_position and next_position < len(d_bits):
            self.bit_grid.set_analyzing(next_position)
    
    @pyqtSlot(str, str)
    def _on_log(self, level, message):
        self.log_message.emit(level, message)
    
    @pyqtSlot(list, float)
    def _on_finished(self, results, success_rate):
        self.attack_results = []
        for r in results:
            self.attack_results.append({
                'position': _get_attr(r, 'position'),
                'extracted_value': _get_attr(r, 'extracted_value'),
                'is_correct': _get_attr(r, 'is_correct'),
                'actual_value': _get_attr(r, 'actual_value'),
                'metric_value': _get_attr(r, 'metric_value'),
                'confidence': _get_attr(r, 'confidence')
            })
        
        self._reset_ui_state()
        self.bit_grid.stop_analyzing()
        
        if self.rsa_instance:
            real_bits = self.rsa_instance.get_bits_msb_first(self.rsa_instance.d)
            for r in self.attack_results:
                pos = r['position']
                val = r['extracted_value']
                state = 'correct' if r['is_correct'] else 'incorrect'
                self.bit_grid.update_bit(pos, val, state)
            self.bit_grid.compare_with_real(real_bits)
        
        self.bits_extracted_lcd.display(len(self.attack_results))
        self.success_label.setText(f"{success_rate*100:.1f}%")
        if success_rate >= 0.7:
            self.success_label.setStyleSheet("color: #27AE60; font-weight: bold;")
        elif success_rate >= 0.5:
            self.success_label.setStyleSheet("color: #D4770A; font-weight: bold;")
        else:
            self.success_label.setStyleSheet("color: #C0392B; font-weight: bold;")
        
        self.measures_label.setText(str(len(self.measurements)))
        
        if self.rsa_instance and self.attack_results:
            extracted_bits = {r['position']: r['extracted_value'] for r in self.attack_results}
            d_extracted = 1
            for pos in sorted(extracted_bits.keys()):
                d_extracted = (d_extracted << 1) | extracted_bits[pos]
            d_hex = hex(d_extracted)
            if len(d_hex) > 40:
                d_hex = d_hex[:35] + "..." + d_hex[-5:]
            self.d_partial_label.setText(d_hex)
        
        self._update_diff_chart(self.attack_results)
        self._update_roc_curve(self.attack_results)
        self._update_confusion_matrix(self.attack_results)
        
        correct = sum(1 for r in self.attack_results if r['is_correct'])
        self.log_message.emit("OK", f"Attaque terminée : {correct}/{len(self.attack_results)} bits corrects ({success_rate*100:.1f}%)")
    
    @pyqtSlot(str)
    def _on_error(self, error_msg):
        self._reset_ui_state()
        self.log_message.emit("ERROR", error_msg)
    
    def _update_diff_chart(self, results):
        ax = self.diff_widget.get_axes()
        ax.clear()
        if results:
            positions = [_get_attr(r, 'position') for r in results]
            values = [_get_attr(r, 'metric_value', 0.0) for r in results]
            colors = ['#27AE60' if _get_attr(r, 'is_correct') else '#C0392B' for r in results]
            ax.bar(positions, values, color=colors, alpha=0.7)
            ax.axhline(y=0, color='white', linestyle='-', linewidth=0.5)
            ax.set_xlabel('Position du bit')
            ax.set_ylabel('Valeur de la métrique')
            ax.set_title('Différence de timing par position')
        self.diff_widget.canvas.draw()
    
    def _update_roc_curve(self, results):
        ax = self.roc_widget.get_axes()
        ax.clear()
        if results and len(results) >= 4:
            try:
                scores = [float(_get_attr(r, 'metric_value', 0.0)) for r in results]
                labels = [int(_get_attr(r, 'actual_value', 0)) for r in results if _get_attr(r, 'actual_value', 0) >= 0]
                if len(labels) >= 4:
                    fpr, tpr, auc = compute_roc_curve(scores[:len(labels)], labels)
                    ax.plot(fpr, tpr, 'b-', linewidth=2, label=f'ROC (AUC = {auc:.3f})')
                    ax.plot([0, 1], [0, 1], 'w--', linewidth=1, label='Aléatoire')
                    ax.set_xlabel('Taux de faux positifs')
                    ax.set_ylabel('Taux de vrais positifs')
                    ax.set_title('Courbe ROC')
                    ax.legend()
            except Exception as e:
                ax.text(0.5, 0.5, f"Erreur ROC:\n{e}", ha='center', va='center', transform=ax.transAxes)
        self.roc_widget.canvas.draw()
    
    def _update_confusion_matrix(self, results):
        ax = self.confusion_widget.get_axes()
        ax.clear()
        if results:
            predicted = [_get_attr(r, 'extracted_value') for r in results]
            actual = [_get_attr(r, 'actual_value') for r in results]
            valid = [(p, a) for p, a in zip(predicted, actual) if a >= 0]
            if valid:
                pred_list, act_list = zip(*valid)
                tp, fp, tn, fn = confusion_matrix(list(pred_list), list(act_list))
                matrix = np.array([[tn, fp], [fn, tp]])
                im = ax.imshow(matrix, cmap='RdYlGn', vmin=0, vmax=max(1, len(results)))
                for i in range(2):
                    for j in range(2):
                        ax.text(j, i, str(matrix[i, j]), ha='center', va='center',
                               color='white', fontweight='bold', fontsize=14)
                ax.set_xticks([0, 1])
                ax.set_xticklabels(['Prédit 0', 'Prédit 1'])
                ax.set_yticks([0, 1])
                ax.set_yticklabels(['Réel 0', 'Réel 1'])
                ax.set_title('Matrice de confusion')
        self.confusion_widget.canvas.draw()
    
    def get_attack_results(self):
        return self.attack_results
    
    def _load_measurements_from_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Charger des mesures", "data/raw/",
            "CSV Files (*.csv);;All Files (*.*)"
        )
        if not filename:
            return
        try:
            self.log_message.emit("INFO", f"Chargement des mesures depuis: {filename}")
            df = pd.read_csv(filename)
            required = ['ciphertext_id', 'median_ns', 'mean_ns', 'std_ns', 'iqr_ns']
            for col in required:
                if col not in df.columns:
                    self.log_message.emit("ERROR", f"Colonne manquante: {col}")
                    return
            self.measurements = []
            for _, row in df.iterrows():
                result = TimingResult(
                    ciphertext_id=int(row.get('ciphertext_id', 0)),
                    ciphertext=int(row.get('ciphertext', 0)),
                    bit_position=int(row.get('bit_position', 0)),
                    bit_value=int(row.get('bit_value', 0)),
                    timings_ns=[],
                    repetitions=int(row.get('repetitions', 0))
                )
                result.median_ns = float(row['median_ns'])
                result.mean_ns = float(row['mean_ns'])
                result.std_ns = float(row['std_ns'])
                result.iqr_ns = float(row['iqr_ns'])
                self.measurements.append(result)
            self._update_ui_state()
            self.data_status_label.setText(f"✅ {len(self.measurements)} mesures chargées")
            self.data_status_label.setStyleSheet("color: #27AE60; font-weight: bold;")
            self.log_message.emit("OK", f"{len(self.measurements)} mesures chargées")
        except Exception as e:
            self.log_message.emit("ERROR", f"Erreur: {str(e)}")
    
    def _use_measurements_from_tab2(self):
        self.log_message.emit("INFO", "Tentative de récupération des mesures depuis l'onglet 2...")
        self.request_measurements.emit()