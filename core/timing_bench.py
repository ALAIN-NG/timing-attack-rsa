"""
Infrastructure de mesure de timing pour RSA.
Fournit des fonctions de collecte de temps d'exécution avec précision nanoseconde.
"""

import time
import gc
import random
import numpy as np
from typing import List, Tuple, Dict, Optional, Callable
from dataclasses import dataclass, field
from core.rsa_naive import RSANaive


@dataclass
class TimingResult:
    """Stocke les résultats d'une mesure de timing."""
    ciphertext_id: int
    ciphertext: int
    bit_position: int
    bit_value: int
    timings_ns: List[int] = field(default_factory=list)
    repetitions: int = 0
    median_ns: float = 0.0
    iqr_ns: float = 0.0
    mean_ns: float = 0.0
    std_ns: float = 0.0
    
    def compute_statistics(self):
        """Calcule les statistiques sur les timings collectés."""
        if not self.timings_ns:
            return
        
        self.repetitions = len(self.timings_ns)
        self.median_ns = float(np.median(self.timings_ns))
        self.mean_ns = float(np.mean(self.timings_ns))
        self.std_ns = float(np.std(self.timings_ns))
        
        q1 = np.percentile(self.timings_ns, 25)
        q3 = np.percentile(self.timings_ns, 75)
        self.iqr_ns = q3 - q1


class TimingBenchmark:
    """
    Banc de mesure pour collecter les temps d'exécution du déchiffrement RSA.
    """
    
    def __init__(self, rsa_instance: RSANaive):
        """
        Initialise le banc de mesure.
        
        Args:
            rsa_instance: Instance RSA avec clés générées
        """
        self.rsa = rsa_instance
        self.warmup_done = False
        
    def warmup(self, iterations: int = 50):
        """
        Effectue un warm-up pour stabiliser le CPU et le cache.
        
        Args:
            iterations: Nombre d'itérations de warm-up
        """
        # Générer un message aléatoire
        m = random.randint(2, self.rsa.N - 1)
        c = self.rsa.encrypt(m)
        
        for _ in range(iterations):
            _ = self.rsa.decrypt(c)
        
        self.warmup_done = True
    
    def measure_single(self, ciphertext: int, repetitions: int = 200) -> List[int]:
        """
        Mesure le temps de déchiffrement d'un seul chiffré.
        
        Args:
            ciphertext: Message chiffré à déchiffrer
            repetitions: Nombre de répétitions pour la mesure
            
        Returns:
            Liste des temps mesurés en nanosecondes
        """
        timings = []
        
        # Désactiver le garbage collector pendant les mesures
        gc.disable()
        
        try:
            for _ in range(repetitions):
                start = time.perf_counter_ns()
                _ = self.rsa.decrypt(ciphertext)
                end = time.perf_counter_ns()
                timings.append(end - start)
        finally:
            gc.enable()
        
        return timings
    
    def collect_measurements(
        self,
        num_ciphertexts: int = 500,
        repetitions: int = 200,
        estimator: str = "median",
        filter_outliers: bool = True,
        iqr_multiplier: float = 3.0,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None
    ) -> List[TimingResult]:
        """
        Collecte les mesures de timing pour plusieurs chiffrés.
        
        Args:
            num_ciphertexts: Nombre de chiffrés différents à tester
            repetitions: Nombre de répétitions par chiffré
            estimator: Estimateur statistique ("median", "mean", "p10")
            filter_outliers: Filtrer les outliers avec IQR
            iqr_multiplier: Multiplicateur pour le seuil IQR
            progress_callback: Fonction appelée pour la progression
            log_callback: Fonction pour les logs
            
        Returns:
            Liste des résultats de timing
        """
        if not self.warmup_done:
            if log_callback:
                log_callback("INFO", "Warm-up automatique (50 itérations)...")
            self.warmup(50)
        
        results = []
        
        # Générer les chiffrés
        if log_callback:
            log_callback("INFO", f"Génération de {num_ciphertexts} messages...")
        
        messages = []
        ciphertexts = []
        for i in range(num_ciphertexts):
            m = random.randint(2, self.rsa.N - 1)
            c = self.rsa.encrypt(m)
            messages.append(m)
            ciphertexts.append(c)
        
        if log_callback:
            log_callback("INFO", f"Collecte des mesures ({num_ciphertexts} chiffrés × {repetitions} répétitions)...")
        
        # Bits de la clé privée
        d_bits = self.rsa.get_bits_msb_first(self.rsa.d)
        
        # Mesurer chaque chiffré
        for i, (c, m) in enumerate(zip(ciphertexts, messages)):
            # Mesurer le temps de déchiffrement
            timings = self.measure_single(c, repetitions)
            
            # Filtrer les outliers si demandé
            if filter_outliers and len(timings) > 0:
                timings = self._filter_outliers(timings, iqr_multiplier)
            
            # Créer le résultat (on associe arbitrairement à un bit pour l'instant)
            # Dans la vraie attaque, on partitionnera selon les hypothèses
            result = TimingResult(
                ciphertext_id=i,
                ciphertext=c,
                bit_position=0,
                bit_value=0,
                timings_ns=timings,
                repetitions=len(timings)
            )
            result.compute_statistics()
            results.append(result)
            
            # Log périodique
            if log_callback and (i + 1) % 50 == 0:
                log_callback("TIMING", f"Progression: {i+1}/{num_ciphertexts} chiffrés mesurés")
            
            # Callback de progression
            if progress_callback:
                progress_callback(i + 1, num_ciphertexts)
        
        if log_callback:
            log_callback("OK", f"Mesures terminées: {len(results)} résultats collectés")
        
        return results
    
    def _filter_outliers(self, timings: List[int], k: float = 3.0) -> List[int]:
        """
        Filtre les outliers en utilisant la méthode IQR.
        
        Args:
            timings: Liste des temps mesurés
            k: Multiplicateur pour le seuil IQR
            
        Returns:
            Liste filtrée
        """
        if len(timings) < 4:
            return timings
        
        q1 = np.percentile(timings, 25)
        q3 = np.percentile(timings, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - k * iqr
        upper_bound = q3 + k * iqr
        
        return [t for t in timings if lower_bound <= t <= upper_bound]
    
    def estimate_noise_floor(self, iterations: int = 1000) -> float:
        """
        Estime le bruit de fond en mesurant une opération nulle.
        
        Args:
            iterations: Nombre d'itérations
            
        Returns:
            Médiane du bruit de fond en nanosecondes
        """
        gc.disable()
        try:
            timings = []
            for _ in range(iterations):
                start = time.perf_counter_ns()
                _ = 1 * 1  # Opération triviale
                end = time.perf_counter_ns()
                timings.append(end - start)
        finally:
            gc.enable()
        
        return float(np.median(timings))