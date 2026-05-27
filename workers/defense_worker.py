"""
Worker QThread pour l'évaluation des contre-mesures.
"""

from PyQt6.QtCore import QThread, pyqtSignal
from typing import List
import time
import numpy as np

from core.rsa_naive import RSANaive
from core.rsa_secure import RSABlinding, RSAMontgomeryLadder
from core.timing_bench import TimingResult
import random


class DefenseWorker(QThread):
    """
    Worker thread pour évaluer les contre-mesures sans bloquer l'interface.
    """
    
    # Signaux
    progress = pyqtSignal(int, int)       # (current, total)
    log = pyqtSignal(str, str)            # (level, message)
    result_ready = pyqtSignal(str, dict)  # (defense_name, stats)
    finished = pyqtSignal(dict)           # Tous les résultats
    error = pyqtSignal(str)
    
    def __init__(
        self,
        rsa_naive: RSANaive,
        num_tests: int = 100,
        repetitions: int = 200
    ):
        super().__init__()
        self.rsa_naive = rsa_naive
        self.num_tests = num_tests
        self.repetitions = repetitions
        self._is_running = True
    
    def run(self):
        """Exécute l'évaluation des contre-mesures."""
        try:
            self.log.emit("INFO", "=== Évaluation des contre-mesures ===")
            
            all_results = {}
            
            # 1. Mesurer le RSA naïf (référence)
            self.log.emit("INFO", "Mesure du RSA naïf (référence)...")
            naive_stats = self._benchmark_naive()
            all_results['naive'] = naive_stats
            self.result_ready.emit('naive', naive_stats)
            self.progress.emit(33, 100)
            
            if not self._is_running:
                return
            
            # 2. Mesurer le RSA Blinding
            self.log.emit("INFO", "Mesure du RSA Blinding...")
            blinding_stats = self._benchmark_blinding()
            all_results['blinding'] = blinding_stats
            self.result_ready.emit('blinding', blinding_stats)
            self.progress.emit(66, 100)
            
            if not self._is_running:
                return
            
            # 3. Mesurer le Montgomery Ladder
            self.log.emit("INFO", "Mesure du Montgomery Ladder...")
            mladder_stats = self._benchmark_montgomery()
            all_results['montgomery'] = mladder_stats
            self.result_ready.emit('montgomery', mladder_stats)
            self.progress.emit(100, 100)
            
            # Calculer les surcoûts
            naive_median = naive_stats['median_ns']
            
            for name, stats in all_results.items():
                if name != 'naive' and naive_median > 0:
                    stats['overhead_pct'] = (stats['median_ns'] / naive_median - 1) * 100
                else:
                    stats['overhead_pct'] = 0.0
            
            self.log.emit("OK", "Évaluation des contre-mesures terminée")
            self.finished.emit(all_results)
            
        except Exception as e:
            self.log.emit("ERROR", f"Erreur: {str(e)}")
            self.error.emit(str(e))
    
    def _benchmark_naive(self) -> dict:
        """Mesure les performances du RSA naïf."""
        import gc
        gc.disable()
        
        try:
            timings = []
            
            # Warm-up
            m = random.randint(2, self.rsa_naive.N - 1)
            c = self.rsa_naive.encrypt(m)
            for _ in range(50):
                _ = self.rsa_naive.decrypt(c)
            
            # Mesures
            for _ in range(self.num_tests):
                m = random.randint(2, self.rsa_naive.N - 1)
                c = self.rsa_naive.encrypt(m)
                
                rep_timings = []
                for _ in range(min(self.repetitions, 50)):  # Limiter pour la vitesse
                    start = time.perf_counter_ns()
                    _ = self.rsa_naive.decrypt(c)
                    end = time.perf_counter_ns()
                    rep_timings.append(end - start)
                
                timings.append(np.median(rep_timings))
            
            return {
                'median_ns': float(np.median(timings)),
                'mean_ns': float(np.mean(timings)),
                'std_ns': float(np.std(timings)),
                'min_ns': float(np.min(timings)),
                'max_ns': float(np.max(timings))
            }
        finally:
            gc.enable()
    
    def _benchmark_blinding(self) -> dict:
        """Mesure les performances du RSA Blinding."""
        import gc
        gc.disable()
        
        try:
            # Créer l'instance RSA Blinding avec les mêmes clés
            blind_rsa = RSABlinding()
            blind_rsa.p = self.rsa_naive.p
            blind_rsa.q = self.rsa_naive.q
            blind_rsa.N = self.rsa_naive.N
            blind_rsa.phi = self.rsa_naive.phi
            blind_rsa.e = self.rsa_naive.e
            blind_rsa.d = self.rsa_naive.d
            blind_rsa.key_size = self.rsa_naive.key_size
            
            timings = []
            
            # Warm-up
            m = random.randint(2, blind_rsa.N - 1)
            c = blind_rsa.encrypt(m)
            for _ in range(10):
                _, _ = blind_rsa.decrypt_blinded(c)
            
            # Mesures
            for _ in range(self.num_tests):
                m = random.randint(2, blind_rsa.N - 1)
                c = blind_rsa.encrypt(m)
                
                rep_timings = []
                for _ in range(min(self.repetitions, 30)):
                    _, t = blind_rsa.decrypt_blinded(c)
                    rep_timings.append(t)
                
                timings.append(np.median(rep_timings))
            
            return {
                'median_ns': float(np.median(timings)),
                'mean_ns': float(np.mean(timings)),
                'std_ns': float(np.std(timings)),
                'min_ns': float(np.min(timings)),
                'max_ns': float(np.max(timings))
            }
        finally:
            gc.enable()
    
    def _benchmark_montgomery(self) -> dict:
        """Mesure les performances du Montgomery Ladder."""
        import gc
        gc.disable()
        
        try:
            # Créer l'instance RSA Montgomery avec les mêmes clés
            ml_rsa = RSAMontgomeryLadder()
            ml_rsa.p = self.rsa_naive.p
            ml_rsa.q = self.rsa_naive.q
            ml_rsa.N = self.rsa_naive.N
            ml_rsa.phi = self.rsa_naive.phi
            ml_rsa.e = self.rsa_naive.e
            ml_rsa.d = self.rsa_naive.d
            ml_rsa.key_size = self.rsa_naive.key_size
            
            timings = []
            
            # Warm-up
            m = random.randint(2, ml_rsa.N - 1)
            c = ml_rsa.encrypt(m)
            for _ in range(50):
                _ = ml_rsa.decrypt_secure(c)
            
            # Mesures
            for _ in range(self.num_tests):
                m = random.randint(2, ml_rsa.N - 1)
                c = ml_rsa.encrypt(m)
                
                rep_timings = []
                for _ in range(min(self.repetitions, 50)):
                    start = time.perf_counter_ns()
                    _ = ml_rsa.decrypt_secure(c)
                    end = time.perf_counter_ns()
                    rep_timings.append(end - start)
                
                timings.append(np.median(rep_timings))
            
            return {
                'median_ns': float(np.median(timings)),
                'mean_ns': float(np.mean(timings)),
                'std_ns': float(np.std(timings)),
                'min_ns': float(np.min(timings)),
                'max_ns': float(np.max(timings))
            }
        finally:
            gc.enable()
    
    def stop(self):
        """Arrête le worker."""
        self._is_running = False