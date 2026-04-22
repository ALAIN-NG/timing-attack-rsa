"""
Worker QThread pour la collecte des mesures de timing.
"""

from PyQt6.QtCore import QThread, pyqtSignal
from core.rsa_naive import RSANaive
from core.timing_bench import TimingBenchmark, TimingResult
from typing import List


class TimingWorker(QThread):
    """
    Worker thread pour collecter les mesures de timing sans bloquer l'interface.
    """
    
    # Signaux
    progress = pyqtSignal(int, int)       # (current, total)
    log = pyqtSignal(str, str)            # (level, message)
    measurement_ready = pyqtSignal(object)  # TimingResult
    finished = pyqtSignal(list)           # List[TimingResult]
    error = pyqtSignal(str)               # Message d'erreur
    
    def __init__(
        self,
        rsa_instance: RSANaive,
        num_ciphertexts: int = 500,
        repetitions: int = 200,
        estimator: str = "median",
        filter_outliers: bool = True,
        iqr_multiplier: float = 3.0
    ):
        """
        Initialise le worker.
        
        Args:
            rsa_instance: Instance RSA avec clés générées
            num_ciphertexts: Nombre de chiffrés à tester
            repetitions: Nombre de répétitions par chiffré
            estimator: Estimateur statistique
            filter_outliers: Filtrer les outliers
            iqr_multiplier: Multiplicateur IQR
        """
        super().__init__()
        self.rsa = rsa_instance
        self.num_ciphertexts = num_ciphertexts
        self.repetitions = repetitions
        self.estimator = estimator
        self.filter_outliers = filter_outliers
        self.iqr_multiplier = iqr_multiplier
        self._is_running = True
    
    def run(self):
        """Exécute la collecte dans un thread séparé."""
        try:
            self.log.emit("INFO", "=== Démarrage de la collecte de mesures de timing ===")
            self.log.emit("INFO", f"Configuration: {self.num_ciphertexts} chiffrés × {self.repetitions} répétitions")
            
            # Créer le banc de mesure
            benchmark = TimingBenchmark(self.rsa)
            
            # Estimer le bruit de fond
            noise = benchmark.estimate_noise_floor()
            self.log.emit("INFO", f"Bruit de fond estimé: {noise:.2f} ns")
            
            # Collecter les mesures
            results = benchmark.collect_measurements(
                num_ciphertexts=self.num_ciphertexts,
                repetitions=self.repetitions,
                estimator=self.estimator,
                filter_outliers=self.filter_outliers,
                iqr_multiplier=self.iqr_multiplier,
                progress_callback=self._on_progress,
                log_callback=self._on_log
            )
            
            if self._is_running:
                self.log.emit("OK", f"Collecte terminée: {len(results)} mesures")
                self.finished.emit(results)
            
        except Exception as e:
            self.log.emit("ERROR", f"Erreur lors de la collecte: {str(e)}")
            self.error.emit(str(e))
    
    def _on_progress(self, current: int, total: int):
        """Callback de progression."""
        if self._is_running:
            self.progress.emit(current, total)
    
    def _on_log(self, level: str, message: str):
        """Callback de log."""
        if self._is_running:
            self.log.emit(level, message)
    
    def stop(self):
        """Arrête le worker."""
        self._is_running = False