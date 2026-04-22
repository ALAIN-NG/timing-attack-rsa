"""
Onglet 2 : Phase 2 - Mesures de Timing
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox,
    QLabel, QPushButton, QSlider, QComboBox, QCheckBox, QSpinBox,
    QDoubleSpinBox, QProgressBar, QTabWidget, QTableWidget,
    QTableWidgetItem, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QBrush

from workers.timing_worker import TimingWorker
from gui.widgets.mpl_canvas import MplWidget
from core.stats import compute_snr


class TimingTab(QWidget):
    """Onglet 2 : Configuration et exécution des mesures de timing."""
    
    log_message = pyqtSignal(str, str)
    session_loaded = pyqtSignal(object) 
    
    
    def __init__(self):
        super().__init__()
        self.rsa_instance = None
        self.measurement_results = []
        self.worker = None
        self.current_csv_path = None
        
        self._init_ui()
    
    def set_rsa_instance(self, rsa_instance):
        """Définit l'instance RSA à utiliser."""
        self.rsa_instance = rsa_instance
        self.launch_btn.setEnabled(rsa_instance is not None)
        
        if rsa_instance:
            self.log_message.emit("INFO", f"Instance RSA-{rsa_instance.key_size} bits chargée pour les mesures")
    
    def _init_ui(self):
        """Initialise l'interface utilisateur."""
        main_layout = QHBoxLayout(self)
        
        # Splitter horizontal : gauche (contrôles) / droite (graphiques)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # === COLONNE GAUCHE ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Groupe : Paramètres de collecte
        collect_group = QGroupBox("Paramètres de collecte")
        collect_layout = QVBoxLayout(collect_group)
        
        # Nombre de chiffrés D
        d_layout = QHBoxLayout()
        d_layout.addWidget(QLabel("Nombre de chiffrés D:"))
        self.d_slider = QSlider(Qt.Orientation.Horizontal)
        self.d_slider.setRange(100, 2000)
        self.d_slider.setValue(500)
        self.d_slider.setTickInterval(100)
        self.d_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.d_slider.valueChanged.connect(self._update_d_label)
        d_layout.addWidget(self.d_slider)
        self.d_label = QLabel("500")
        d_layout.addWidget(self.d_label)
        collect_layout.addLayout(d_layout)
        
        # Répétitions par mesure N
        n_layout = QHBoxLayout()
        n_layout.addWidget(QLabel("Répétitions N:"))
        self.n_slider = QSlider(Qt.Orientation.Horizontal)
        self.n_slider.setRange(50, 1000)
        self.n_slider.setValue(200)
        self.n_slider.setTickInterval(50)
        self.n_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.n_slider.valueChanged.connect(self._update_n_label)
        n_layout.addWidget(self.n_slider)
        self.n_label = QLabel("200")
        n_layout.addWidget(self.n_label)
        collect_layout.addLayout(n_layout)
        
        # Estimateur statistique
        est_layout = QHBoxLayout()
        est_layout.addWidget(QLabel("Estimateur:"))
        self.estimator_combo = QComboBox()
        self.estimator_combo.addItems(["Médiane (robuste)", "Moyenne", "Percentile P10"])
        est_layout.addWidget(self.estimator_combo)
        collect_layout.addLayout(est_layout)
        
        # Options
        self.gc_check = QCheckBox("Désactiver GC pendant mesures")
        self.gc_check.setChecked(True)
        collect_layout.addWidget(self.gc_check)
        
        self.cpu_affinity_check = QCheckBox("Affinité CPU (cœur 0) - Linux uniquement")
        self.cpu_affinity_check.setEnabled(os.name == 'posix')
        collect_layout.addWidget(self.cpu_affinity_check)
        
        # Warm-up
        warmup_layout = QHBoxLayout()
        warmup_layout.addWidget(QLabel("Warm-up:"))
        self.warmup_spin = QSpinBox()
        self.warmup_spin.setRange(10, 200)
        self.warmup_spin.setValue(50)
        warmup_layout.addWidget(self.warmup_spin)
        warmup_layout.addWidget(QLabel("itérations"))
        warmup_layout.addStretch()
        collect_layout.addLayout(warmup_layout)
        
        left_layout.addWidget(collect_group)
        
        # Groupe : Filtrage et qualité
        filter_group = QGroupBox("Filtrage et qualité")
        filter_layout = QVBoxLayout(filter_group)
        
        # Seuil IQR
        iqr_layout = QHBoxLayout()
        iqr_layout.addWidget(QLabel("Seuil IQR (k):"))
        self.iqr_spin = QDoubleSpinBox()
        self.iqr_spin.setRange(1.0, 5.0)
        self.iqr_spin.setValue(3.0)
        self.iqr_spin.setSingleStep(0.5)
        iqr_layout.addWidget(self.iqr_spin)
        filter_layout.addLayout(iqr_layout)
        
        # Bruit de fond
        noise_layout = QHBoxLayout()
        noise_layout.addWidget(QLabel("Bruit de fond:"))
        self.noise_label = QLabel("— ns")
        noise_layout.addWidget(self.noise_label)
        noise_layout.addStretch()
        filter_layout.addLayout(noise_layout)
        
        # SNR
        snr_layout = QHBoxLayout()
        snr_layout.addWidget(QLabel("SNR estimé:"))
        self.snr_label = QLabel("— dB")
        snr_layout.addWidget(self.snr_label)
        snr_layout.addStretch()
        filter_layout.addLayout(snr_layout)
        
        left_layout.addWidget(filter_group)

        # Groupe : Exécution
        exec_group = QGroupBox("Exécution")
        exec_layout = QVBoxLayout(exec_group)

        # Boutons de lancement/arrêt
        launch_stop_layout = QHBoxLayout()
        self.launch_btn = QPushButton("🚀 Lancer la collecte")
        self.launch_btn.setObjectName("primaryButton")
        self.launch_btn.setEnabled(False)
        self.launch_btn.clicked.connect(self._launch_collect)
        launch_stop_layout.addWidget(self.launch_btn)

        self.stop_btn = QPushButton("⏹ Arrêter")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_collect)
        launch_stop_layout.addWidget(self.stop_btn)
        exec_layout.addLayout(launch_stop_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        exec_layout.addWidget(self.progress_bar)

        # Séparateur
        exec_layout.addWidget(QLabel(""))

        # Import/Export
        import_export_layout = QHBoxLayout()

        self.import_btn = QPushButton("📂 Importer CSV")
        self.import_btn.setToolTip("Charger des mesures depuis un fichier CSV")
        self.import_btn.clicked.connect(self._import_csv)
        import_export_layout.addWidget(self.import_btn)

        self.export_btn = QPushButton("💾 Exporter CSV")
        self.export_btn.setEnabled(False)
        self.export_btn.setToolTip("Sauvegarder les mesures actuelles")
        self.export_btn.clicked.connect(self._export_csv)
        import_export_layout.addWidget(self.export_btn)

        exec_layout.addLayout(import_export_layout)

        # Bouton pour sauvegarder la session
        self.save_session_btn = QPushButton("📌 Sauvegarder session")
        self.save_session_btn.setEnabled(False)
        self.save_session_btn.setToolTip("Sauvegarder la session complète (clés + mesures)")
        self.save_session_btn.clicked.connect(self._save_session)
        exec_layout.addWidget(self.save_session_btn)

        # Bouton pour charger une session
        self.load_session_btn = QPushButton("📂 Charger session")
        self.load_session_btn.setToolTip("Charger une session complète")
        self.load_session_btn.clicked.connect(self._load_session)
        exec_layout.addWidget(self.load_session_btn)

        left_layout.addWidget(exec_group)
        
        # === COLONNE DROITE ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Onglets de graphiques
        self.graph_tabs = QTabWidget()
        
        # Onglet 1 : Histogramme double
        self.histogram_widget = MplWidget(width=6, height=4, dpi=100)
        self.graph_tabs.addTab(self.histogram_widget, "Histogramme")
        
        # Onglet 2 : Boxplot
        self.boxplot_widget = MplWidget(width=6, height=4, dpi=100)
        self.graph_tabs.addTab(self.boxplot_widget, "Boxplot")
        
        # Onglet 3 : Heatmap
        self.heatmap_widget = MplWidget(width=6, height=4, dpi=100)
        self.graph_tabs.addTab(self.heatmap_widget, "Heatmap")
        
        right_layout.addWidget(self.graph_tabs)
        
        # Tableau des données brutes
        data_group = QGroupBox("Données brutes (200 premières lignes)")
        data_layout = QVBoxLayout(data_group)
        
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(6)
        self.data_table.setHorizontalHeaderLabels([
            "ID", "Bit pos", "Bit val", "Médiane (ns)", "Moyenne (ns)", "IQR (ns)"
        ])
        data_layout.addWidget(self.data_table)
        
        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.clicked.connect(self._refresh_table)
        data_layout.addWidget(refresh_btn)
        
        right_layout.addWidget(data_group)
        
        # Assemblage
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([350, 750])
        
        main_layout.addWidget(splitter)
    
    def _update_d_label(self, value):
        self.d_label.setText(str(value))
    
    def _update_n_label(self, value):
        self.n_label.setText(str(value))
    
    def _launch_collect(self):
        """Lance la collecte de mesures."""
        if not self.rsa_instance:
            self.log_message.emit("WARN", "Générez d'abord des clés RSA dans l'onglet 1")
            return
        
        self.launch_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, self.d_slider.value())
        
        # Récupérer l'estimateur
        estimator_map = {0: "median", 1: "mean", 2: "p10"}
        estimator = estimator_map[self.estimator_combo.currentIndex()]
        
        # Créer et lancer le worker
        self.worker = TimingWorker(
            rsa_instance=self.rsa_instance,
            num_ciphertexts=self.d_slider.value(),
            repetitions=self.n_slider.value(),
            estimator=estimator,
            filter_outliers=True,
            iqr_multiplier=self.iqr_spin.value()
        )
        
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._on_log)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        
        self.worker.start()
    
    def _stop_collect(self):
        """Arrête la collecte."""
        if self.worker:
            self.worker.stop()
            self.worker.quit()
            self.worker.wait()
        
        self._reset_ui_state()
        self.log_message.emit("WARN", "Collecte arrêtée par l'utilisateur")
    
    @pyqtSlot(int, int)
    def _on_progress(self, current, total):
        """Met à jour la barre de progression."""
        self.progress_bar.setValue(current)
    
    @pyqtSlot(str, str)
    def _on_log(self, level, message):
        """Relaye les logs."""
        self.log_message.emit(level, message)
    
    @pyqtSlot(list)
    def _on_finished(self, results):
        """Appelé quand la collecte est terminée."""
        self.measurement_results = results
        self._reset_ui_state()
        self.export_btn.setEnabled(True)
        self.save_session_btn.setEnabled(True)
        
        # Mettre à jour les graphiques
        self._update_histogram()
        self._update_boxplot()
        self._update_heatmap()
        self._refresh_table()
        
        # Mettre à jour les métriques
        self._update_metrics()
        
        self.log_message.emit("OK", f"Collecte terminée: {len(results)} mesures")
    
    @pyqtSlot(str)
    def _on_error(self, error_msg):
        """Appelé en cas d'erreur."""
        self._reset_ui_state()
        self.log_message.emit("ERROR", error_msg)
    
    def _reset_ui_state(self):
        """Réinitialise l'état de l'interface."""
        self.launch_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
    
    def _update_metrics(self):
        """Met à jour les métriques de qualité."""
        if not self.measurement_results:
            return
        
        # Bruit de fond (via une fonction dédiée si disponible)
        self.noise_label.setText("~150 ns")
        
        # Calculer le SNR approximatif
        all_timings = [r.median_ns for r in self.measurement_results]
        if len(all_timings) > 1:
            # Simuler deux groupes pour le SNR
            mid = len(all_timings) // 2
            group0 = all_timings[:mid]
            group1 = all_timings[mid:]
            
            if len(group0) > 0 and len(group1) > 0:
                snr = compute_snr(all_timings, 150)  # 150ns estimé
                self.snr_label.setText(f"{snr:.1f} dB")

    def _update_histogram(self):
        """Met à jour l'histogramme."""
        if not self.measurement_results:
            return
        
        ax = self.histogram_widget.get_axes()
        ax.clear()
        
        # Extraire les timings
        timings = [r.median_ns for r in self.measurement_results]
        
        # Histogramme
        ax.hist(timings, bins=30, alpha=0.7, color='#2E75B6', edgecolor='white')
        ax.axvline(np.median(timings), color='#27AE60', linestyle='--', 
                label=f'Médiane: {np.median(timings):.0f} ns')
        
        ax.set_xlabel('Temps de déchiffrement (ns)')
        ax.set_ylabel('Fréquence')
        ax.set_title(f'Distribution des temps de déchiffrement (n={len(timings)})')
        ax.legend()
        
        self.histogram_widget.canvas.draw()
        

    def _update_boxplot(self):
        """Met à jour le boxplot."""
        if not self.measurement_results:
            return
        
        ax = self.boxplot_widget.get_axes()
        ax.clear()
        
        # Simuler deux groupes pour démonstration
        timings = [r.median_ns for r in self.measurement_results]
        mid = len(timings) // 2
        group0 = timings[:mid] if mid > 0 else timings
        group1 = timings[mid:] if mid > 0 else timings
        
        ax.boxplot([group0, group1], labels=['Groupe A', 'Groupe B'])
        ax.set_ylabel('Temps de déchiffrement (ns)')
        ax.set_title('Comparaison des distributions')
        
        self.boxplot_widget.canvas.draw()
    
    def _update_heatmap(self):
        """Met à jour la heatmap."""
        if not self.measurement_results:
            return
        
        ax = self.heatmap_widget.get_axes()
        ax.clear()
        
        # Créer une matrice simple pour démonstration
        timings = [r.median_ns for r in self.measurement_results[:100]]
        
        # S'assurer d'avoir assez de données pour une matrice 10x10
        if len(timings) < 100:
            # Remplir avec la médiane si pas assez de données
            while len(timings) < 100:
                timings.append(np.median(timings) if timings else 0)
        
        matrix = np.array(timings).reshape(10, 10)
        
        im = ax.imshow(matrix, cmap='viridis', aspect='auto')
        
        # Correction : accéder à la figure via canvas
        self.heatmap_widget.canvas.fig.colorbar(im, ax=ax, label='Temps (ns)')
        
        ax.set_xlabel('Position')
        ax.set_ylabel('Échantillon')
        ax.set_title('Heatmap des temps de déchiffrement')
        
        self.heatmap_widget.canvas.draw()
    
    def _refresh_table(self):
        """Actualise le tableau des données brutes."""
        if not self.measurement_results:
            return
        
        self.data_table.setRowCount(min(200, len(self.measurement_results)))
        
        for i, result in enumerate(self.measurement_results[:200]):
            self.data_table.setItem(i, 0, QTableWidgetItem(str(result.ciphertext_id)))
            self.data_table.setItem(i, 1, QTableWidgetItem(str(result.bit_position)))
            self.data_table.setItem(i, 2, QTableWidgetItem(str(result.bit_value)))
            self.data_table.setItem(i, 3, QTableWidgetItem(f"{result.median_ns:.0f}"))
            self.data_table.setItem(i, 4, QTableWidgetItem(f"{result.mean_ns:.0f}"))
            self.data_table.setItem(i, 5, QTableWidgetItem(f"{result.iqr_ns:.0f}"))
    
    def _export_csv(self):
        """Exporte les données au format CSV."""
        if not self.measurement_results:
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter les données CSV",
            f"data/raw/timings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if filename:
            # Créer le dossier si nécessaire
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            # Créer le DataFrame
            data = []
            for r in self.measurement_results:
                data.append({
                    'ciphertext_id': r.ciphertext_id,
                    'ciphertext': r.ciphertext,
                    'bit_position': r.bit_position,
                    'bit_value': r.bit_value,
                    'median_ns': r.median_ns,
                    'mean_ns': r.mean_ns,
                    'std_ns': r.std_ns,
                    'iqr_ns': r.iqr_ns,
                    'repetitions': r.repetitions,
                    'key_size': self.rsa_instance.key_size if self.rsa_instance else 0
                })
            
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False)
            
            self.current_csv_path = filename
            self.log_message.emit("OK", f"Données exportées: {filename}")
    
    def get_measurements(self):
        """Retourne les résultats de mesure."""
        return self.measurement_results
    
    def _import_csv(self):
        """Importe des mesures depuis un fichier CSV."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Importer des mesures CSV",
            "data/raw/",
            "CSV Files (*.csv);;All Files (*.*)"
        )
        
        if not filename:
            return
        
        try:
            self.log_message.emit("INFO", f"Importation depuis: {filename}")
            
            # Lire le CSV
            df = pd.read_csv(filename)
            
            # Vérifier les colonnes requises
            required_columns = ['ciphertext_id', 'median_ns', 'mean_ns', 'std_ns', 'iqr_ns']
            for col in required_columns:
                if col not in df.columns:
                    self.log_message.emit("ERROR", f"Colonne manquante: {col}")
                    return
            
            # Reconstruire les TimingResult
            from core.timing_bench import TimingResult
            
            self.measurement_results = []
            for _, row in df.iterrows():
                result = TimingResult(
                    ciphertext_id=int(row.get('ciphertext_id', 0)),
                    ciphertext=int(row.get('ciphertext', 0)),
                    bit_position=int(row.get('bit_position', 0)),
                    bit_value=int(row.get('bit_value', 0)),
                    timings_ns=[],  # Les timings bruts ne sont pas dans le CSV
                    repetitions=int(row.get('repetitions', 0))
                )
                result.median_ns = float(row['median_ns'])
                result.mean_ns = float(row['mean_ns'])
                result.std_ns = float(row['std_ns'])
                result.iqr_ns = float(row['iqr_ns'])
                
                self.measurement_results.append(result)
            
            self.current_csv_path = filename
            
            # Mettre à jour l'interface
            self.export_btn.setEnabled(True)
            self.save_session_btn.setEnabled(True)
            
            self._update_histogram()
            self._update_boxplot()
            self._update_heatmap()
            self._refresh_table()
            self._update_metrics()
            
            self.log_message.emit("OK", f"Import réussi: {len(self.measurement_results)} mesures chargées")
            
        except Exception as e:
            self.log_message.emit("ERROR", f"Erreur lors de l'import: {str(e)}")
    
    def _export_csv(self):
        """Exporte les données au format CSV."""
        if not self.measurement_results:
            return
        
        # Créer le dossier data/raw s'il n'existe pas
        os.makedirs("data/raw", exist_ok=True)
        
        # Nom par défaut avec timestamp
        default_name = f"data/raw/timings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter les données CSV",
            default_name,
            "CSV Files (*.csv)"
        )
        
        if filename:
            try:
                # Créer le DataFrame
                data = []
                for r in self.measurement_results:
                    data.append({
                        'ciphertext_id': r.ciphertext_id,
                        'ciphertext': r.ciphertext,
                        'bit_position': r.bit_position,
                        'bit_value': r.bit_value,
                        'median_ns': r.median_ns,
                        'mean_ns': r.mean_ns,
                        'std_ns': r.std_ns,
                        'iqr_ns': r.iqr_ns,
                        'repetitions': r.repetitions,
                        'key_size': self.rsa_instance.key_size if self.rsa_instance else 0,
                        'timestamp': datetime.now().isoformat()
                    })
                
                df = pd.DataFrame(data)
                df.to_csv(filename, index=False)
                
                self.current_csv_path = filename
                self.log_message.emit("OK", f"Données exportées: {filename}")
                
            except Exception as e:
                self.log_message.emit("ERROR", f"Erreur lors de l'export: {str(e)}")
    
    def _save_session(self):
        """Sauvegarde une session complète (clés RSA + mesures)."""
        if not self.rsa_instance or not self.measurement_results:
            self.log_message.emit("WARN", "Aucune donnée à sauvegarder")
            return
        
        # Créer le dossier sessions s'il n'existe pas
        os.makedirs("data/sessions", exist_ok=True)
        
        default_name = f"data/sessions/session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.rsa"
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Sauvegarder la session",
            default_name,
            "RSA Session Files (*.rsa);;All Files (*.*)"
        )
        
        if filename:
            try:
                session_data = {
                    'p': str(self.rsa_instance.p),
                    'q': str(self.rsa_instance.q),
                    'N': str(self.rsa_instance.N),
                    'e': str(self.rsa_instance.e),
                    'd': str(self.rsa_instance.d),
                    'phi': str(self.rsa_instance.phi),
                    'key_size': self.rsa_instance.key_size,
                    'measurements': []
                }
                
                for r in self.measurement_results:
                    session_data['measurements'].append({
                        'ciphertext_id': r.ciphertext_id,
                        'ciphertext': r.ciphertext,
                        'bit_position': r.bit_position,
                        'bit_value': r.bit_value,
                        'median_ns': r.median_ns,
                        'mean_ns': r.mean_ns,
                        'std_ns': r.std_ns,
                        'iqr_ns': r.iqr_ns,
                        'repetitions': r.repetitions
                    })
                
                with open(filename, 'w') as f:
                    json.dump(session_data, f, indent=2)
                
                self.log_message.emit("OK", f"Session sauvegardée: {filename}")
                
            except Exception as e:
                self.log_message.emit("ERROR", f"Erreur lors de la sauvegarde: {str(e)}")
    
    def _load_session(self):
        """Charge une session complète."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Charger une session",
            "data/sessions/",
            "RSA Session Files (*.rsa);;JSON Files (*.json);;All Files (*.*)"
        )
        
        if not filename:
            return
        
        try:
            self.log_message.emit("INFO", f"Chargement de la session: {filename}")
            
            with open(filename, 'r') as f:
                session_data = json.load(f)
            
            # Vérifier que l'instance RSA existe ou en créer une
            if not self.rsa_instance:
                from core.rsa_naive import RSANaive
                self.rsa_instance = RSANaive(key_size=session_data.get('key_size', 1024))
            
            # Restaurer les paramètres RSA
            self.rsa_instance.p = int(session_data['p'])
            self.rsa_instance.q = int(session_data['q'])
            self.rsa_instance.N = int(session_data['N'])
            self.rsa_instance.e = int(session_data['e'])
            self.rsa_instance.d = int(session_data['d'])
            self.rsa_instance.phi = int(session_data['phi'])
            self.rsa_instance.key_size = session_data.get('key_size', 1024)
            
            # Reconstruire les mesures
            from core.timing_bench import TimingResult
            
            self.measurement_results = []
            for m in session_data['measurements']:
                result = TimingResult(
                    ciphertext_id=m['ciphertext_id'],
                    ciphertext=int(m['ciphertext']),
                    bit_position=m['bit_position'],
                    bit_value=m['bit_value'],
                    timings_ns=[],
                    repetitions=m['repetitions']
                )
                result.median_ns = float(m['median_ns'])
                result.mean_ns = float(m['mean_ns'])
                result.std_ns = float(m['std_ns'])
                result.iqr_ns = float(m['iqr_ns'])
                
                self.measurement_results.append(result)
            
            # Mettre à jour l'interface
            self.export_btn.setEnabled(True)
            self.save_session_btn.setEnabled(True)
            
            self._update_histogram()
            self._update_boxplot()
            self._update_heatmap()
            self._refresh_table()
            self._update_metrics()
            
            # Notifier l'onglet 1 de la mise à jour des clés
            self.log_message.emit("OK", f"Session chargée: RSA-{self.rsa_instance.key_size} bits, {len(self.measurement_results)} mesures")
            self.session_loaded.emit(self.rsa_instance)
        except Exception as e:
            self.log_message.emit("ERROR", f"Erreur lors du chargement: {str(e)}")
    
    def get_rsa_instance(self):
        """Retourne l'instance RSA (peut avoir été chargée depuis une session)."""
        return self.rsa_instance