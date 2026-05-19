"""
Worker QThread pour l'attaque par timing.
"""

from PyQt6.QtCore import QThread, pyqtSignal
from typing import List

from core.rsa_naive import RSANaive
from core.timing_bench import TimingResult
from core.attack_engine import TimingAttackEngine, AttackResult, MetricType


class AttackWorker(QThread):
    """
    Worker thread pour exécuter l'attaque sans bloquer l'interface.
    """
    
    # Signaux
    progress = pyqtSignal(int, int)           # (current_bit, total_bits)
    bit_extracted = pyqtSignal(int, int, bool) # (position, value, is_correct)
    log = pyqtSignal(str, str)                # (level, message)
    finished = pyqtSignal(list, float)        # (results, success_rate)
    error = pyqtSignal(str)                   # Message d'erreur
    
    def __init__(
        self,
        rsa_instance: RSANaive,
        measurements: List[TimingResult],
        start_position: int = 1,
        num_bits: int = 8,
        metric: str = "mean_diff",
        confidence_threshold: float = 0.05
    ):
        """
        Initialise le worker.
        
        Args:
            rsa_instance: Instance RSA avec clés
            measurements: Mesures de timing
            start_position: Position du premier bit à extraire
            num_bits: Nombre de bits à extraire
            metric: Métrique statistique
            confidence_threshold: Seuil de confiance
        """
        super().__init__()
        self.rsa = rsa_instance
        self.measurements = measurements
        self.start_position = start_position
        self.num_bits = num_bits
        self.confidence_threshold = confidence_threshold
        
        # Convertir la métrique
        metric_map = {
            "mean_diff": MetricType.MEAN_DIFFERENCE,
            "t_test": MetricType.T_TEST,
            "pearson": MetricType.PEARSON,
            "spearman": MetricType.SPEARMAN
        }
        self.metric = metric_map.get(metric, MetricType.MEAN_DIFFERENCE)
        
        self._is_running = True
    
    def run(self):
        """Exécute l'attaque dans un thread séparé."""
        try:
            self.log.emit("INFO", "=== Démarrage de l'attaque par timing ===")
            self.log.emit("INFO", f"Configuration: {self.num_bits} bits, métrique: {self.metric.value}")
            
            # Créer le moteur d'attaque
            engine = TimingAttackEngine(self.rsa, self.measurements)
            
            # Bits réels pour information
            real_bits = engine.real_d_bits
            self.log.emit("INFO", f"Bits réels (début): {real_bits[:min(16, len(real_bits))]}")
            
            # Lancer l'attaque
            results = engine.extract_bits_batch(
                start_position=self.start_position,
                num_bits=self.num_bits,
                metric=self.metric,
                progress_callback=self._on_bit_extracted
            )
            
            if self._is_running:
                success_rate = engine.compute_extraction_rate()
                
                self.log.emit("OK", f"Attaque terminée: {success_rate*100:.1f}% de bits corrects")
                self.log.emit("INFO", f"Bits extraits: {[r.extracted_value for r in results]}")
                
                self.finished.emit(results, success_rate)
            
        except Exception as e:
            self.log.emit("ERROR", f"Erreur lors de l'attaque: {str(e)}")
            self.error.emit(str(e))
    
    def _on_bit_extracted(self, position: int, total_bits: int, result: AttackResult):
        """Callback appelé après chaque bit extrait."""
        if not self._is_running:
            return
        
        self.progress.emit(position, total_bits)
        self.bit_extracted.emit(position, result.extracted_value, result.is_correct)
        
        status = "✓" if result.is_correct else "✗"
        self.log.emit(
            "BIT",
            f"Bit {position}: extrait={result.extracted_value}, réel={result.actual_value} {status} "
            f"(confiance={result.confidence:.4f})"
        )
    
    def stop(self):
        """Arrête le worker."""
        self._is_running = False