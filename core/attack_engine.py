"""
Moteur d'attaque par timing selon l'algorithme de Kocher (1996).
"""

import numpy as np
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from core.rsa_naive import RSANaive
from core.timing_bench import TimingResult
from core.stats import welch_ttest, pearson_correlation, spearman_correlation


class MetricType(Enum):
    """Types de métriques statistiques pour l'attaque."""
    MEAN_DIFFERENCE = "mean_diff"
    T_TEST = "t_test"
    PEARSON = "pearson"
    SPEARMAN = "spearman"


@dataclass
class AttackResult:
    """Résultat d'une attaque sur un bit."""
    position: int           # Position du bit dans d
    extracted_value: int    # Valeur extraite (0 ou 1)
    actual_value: int       # Valeur réelle (si connue)
    confidence: float       # Confiance (p-value ou score)
    metric_value: float     # Valeur de la métrique utilisée
    is_correct: bool        # Extraction correcte ?


class TimingAttackEngine:
    """
    Moteur d'attaque par timing sur RSA.
    Implémente l'algorithme de Kocher (1996).
    """
    
    def __init__(self, rsa_instance: RSANaive, measurements: List[TimingResult]):
        """
        Initialise le moteur d'attaque.
        
        Args:
            rsa_instance: Instance RSA avec clés générées
            measurements: Mesures de timing collectées
        """
        self.rsa = rsa_instance
        self.measurements = measurements
        
        # Bits de la clé privée réelle (pour validation)
        self.real_d_bits = self.rsa.get_bits_msb_first(self.rsa.d)
        
        # État de l'attaque
        self.extracted_bits = {}  # position -> valeur
        self.current_d_partial = 1  # d partiel (commence à 1 car MSB est toujours 1)
        
    def get_measurements_for_bit(self, bit_position: int) -> List[Tuple[int, float]]:
        """
        Retourne les mesures associées à une position de bit.
        
        Args:
            bit_position: Position du bit dans d
            
        Returns:
            Liste de tuples (ciphertext, median_timing)
        """
        # Dans une vraie attaque, on devrait partitionner selon les hypothèses
        # Pour l'instant, on retourne toutes les mesures
        return [(m.ciphertext, m.median_ns) for m in self.measurements]
    
    def partition_ciphertexts(
        self,
        ciphertexts: List[int],
        bit_position: int,
        hypothesis_0: bool = True
    ) -> List[float]:
        """
        Partitionne les chiffrés selon une hypothèse sur le bit.
        
        Pour l'hypothèse bit=0 : on calcule c^(d_partial * 2) mod N
        Pour l'hypothèse bit=1 : on calcule c^(d_partial * 2 + 1) mod N
        
        Args:
            ciphertexts: Liste des chiffrés
            bit_position: Position du bit testé
            hypothesis_0: True pour bit=0, False pour bit=1
            
        Returns:
            Liste des valeurs v_i = f(c_i) pour la partition
        """
        d_partial = self._get_current_d_partial()
        
        # L'exposant pour l'hypothèse
        if hypothesis_0:
            exp = d_partial * 2
        else:
            exp = d_partial * 2 + 1
        
        values = []
        for c in ciphertexts:
            # v_i = c^exp mod N
            v = pow(c, exp, self.rsa.N)
            values.append(v)
        
        return values
    
    def _get_current_d_partial(self) -> int:
        """Reconstruit l'exposant partiel d à partir des bits extraits."""
        d_partial = 1  # MSB est toujours 1
        sorted_positions = sorted(self.extracted_bits.keys())
        
        for pos in sorted_positions:
            d_partial = (d_partial << 1) | self.extracted_bits[pos]
        
        return d_partial
    
    def _get_d_partial_bits(self) -> List[int]:
        """Retourne les bits de d_partial sous forme de liste."""
        sorted_positions = sorted(self.extracted_bits.keys())
        bits = [1]  # MSB
        for pos in sorted_positions:
            bits.append(self.extracted_bits[pos])
        return bits
    
    def compute_timing_difference(
        self,
        timings: List[float],
        ciphertexts: List[int],
        bit_position: int
    ) -> Tuple[float, float, float]:
        """
        Calcule la différence de timing entre les hypothèses bit=0 et bit=1.
        
        Args:
            timings: Temps médians pour chaque chiffré
            ciphertexts: Chiffrés correspondants
            bit_position: Position du bit testé
            
        Returns:
            Tuple (mean_0, mean_1, difference)
        """
        # Obtenir les valeurs de partition
        values_0 = self.partition_ciphertexts(ciphertexts, bit_position, True)
        values_1 = self.partition_ciphertexts(ciphertexts, bit_position, False)
        
        # Partitionner les timings selon une heuristique simple
        # (dans une vraie attaque, on utilise la valeur médiane ou un seuil)
        threshold = np.median(values_0 + values_1)
        
        timings_0 = []
        timings_1 = []
        
        for t, v0, v1 in zip(timings, values_0, values_1):
            # Utiliser la moyenne des deux valeurs comme critère
            avg_v = (v0 + v1) / 2
            if avg_v < threshold:
                timings_0.append(t)
            else:
                timings_1.append(t)
        
        mean_0 = np.mean(timings_0) if timings_0 else 0
        mean_1 = np.mean(timings_1) if timings_1 else 0
        
        return mean_0, mean_1, mean_1 - mean_0
    
    def extract_bit_kocher(
        self,
        bit_position: int,
        metric: MetricType = MetricType.MEAN_DIFFERENCE,
        confidence_threshold: float = 0.05
    ) -> AttackResult:
        """
        Extrait un bit en utilisant l'algorithme de Kocher.
        """
        # Récupérer les mesures
        measurements = self.get_measurements_for_bit(bit_position)
        ciphertexts = [m[0] for m in measurements]
        timings = [m[1] for m in measurements]
        
        if len(timings) < 10:
            return AttackResult(
                position=bit_position,
                extracted_value=0,
                actual_value=self.real_d_bits[bit_position] if bit_position < len(self.real_d_bits) else -1,
                confidence=1.0,
                metric_value=0.0,
                is_correct=False
            )
        
        # S'assurer que les timings sont des floats
        timings = [float(t) for t in timings]
        
        # Calculer les partitions pour les deux hypothèses
        values_0 = self.partition_ciphertexts(ciphertexts, bit_position, True)
        values_1 = self.partition_ciphertexts(ciphertexts, bit_position, False)
        
        # Convertir en tableaux numpy
        values_0 = np.array([float(v) for v in values_0], dtype=np.float64)
        values_1 = np.array([float(v) for v in values_1], dtype=np.float64)
        
        # Diviser les timings en deux groupes selon la différence v1 - v0
        differences = values_1 - values_0
        median_diff = np.median(differences)
        
        group_0 = [timings[i] for i in range(len(timings)) if differences[i] <= median_diff]
        group_1 = [timings[i] for i in range(len(timings)) if differences[i] > median_diff]
        
        # S'assurer d'avoir assez de données dans chaque groupe
        if len(group_0) < 2 or len(group_1) < 2:
            return AttackResult(
                position=bit_position,
                extracted_value=0,
                actual_value=self.real_d_bits[bit_position] if bit_position < len(self.real_d_bits) else -1,
                confidence=1.0,
                metric_value=0.0,
                is_correct=False
            )
        
        # Calculer la métrique choisie
        if metric == MetricType.MEAN_DIFFERENCE:
            mean_0 = np.mean(group_0)
            mean_1 = np.mean(group_1)
            metric_value = mean_1 - mean_0
            confidence = 1.0 / (1.0 + abs(metric_value))
            extracted_bit = 1 if metric_value > 0 else 0
            
        elif metric == MetricType.T_TEST:
            t_stat, p_value = welch_ttest(group_0, group_1)
            metric_value = t_stat
            confidence = p_value
            extracted_bit = 1 if t_stat > 0 else 0
            
        elif metric == MetricType.PEARSON:
            corr, p_value = pearson_correlation(list(differences), timings)
            metric_value = corr
            confidence = p_value
            extracted_bit = 1 if corr > 0 else 0
            
        elif metric == MetricType.SPEARMAN:
            corr, p_value = spearman_correlation(list(differences), timings)
            metric_value = corr
            confidence = p_value
            extracted_bit = 1 if corr > 0 else 0
        else:
            raise ValueError(f"Métrique inconnue: {metric}")
        
        # Stocker le bit extrait
        self.extracted_bits[bit_position] = extracted_bit
        
        # Comparer avec la valeur réelle
        actual_bit = self.real_d_bits[bit_position] if bit_position < len(self.real_d_bits) else -1
        is_correct = (extracted_bit == actual_bit)
        
        return AttackResult(
            position=bit_position,
            extracted_value=extracted_bit,
            actual_value=actual_bit,
            confidence=confidence,
            metric_value=metric_value,
            is_correct=is_correct
        )
    
    def extract_bits_batch(
        self,
        start_position: int = 1,
        num_bits: int = 8,
        metric: MetricType = MetricType.MEAN_DIFFERENCE,
        progress_callback: Optional[Callable[[int, int, AttackResult], None]] = None
    ) -> List[AttackResult]:
        """
        Extrait plusieurs bits consécutifs.
        
        Args:
            start_position: Position de départ (0 = MSB, défaut 1 car MSB=1 connu)
            num_bits: Nombre de bits à extraire
            metric: Métrique statistique
            progress_callback: Callback appelé après chaque bit extrait
            
        Returns:
            Liste des résultats d'attaque
        """
        results = []
        
        # Réinitialiser l'état
        self.extracted_bits = {}
        self.current_d_partial = 1
        
        for i in range(num_bits):
            position = start_position + i
            
            # Extraire le bit
            result = self.extract_bit_kocher(position, metric)
            results.append(result)
            
            # Mettre à jour d_partial
            self.current_d_partial = (self.current_d_partial << 1) | result.extracted_value
            
            # Callback de progression
            if progress_callback:
                progress_callback(position, num_bits, result)
        
        return results
    
    def get_extracted_d(self) -> int:
        """Reconstruit l'exposant d à partir des bits extraits."""
        d_extracted = 1  # MSB
        
        for pos in sorted(self.extracted_bits.keys()):
            d_extracted = (d_extracted << 1) | self.extracted_bits[pos]
        
        # Ajouter les bits restants comme 0
        remaining = len(self.real_d_bits) - len(self.extracted_bits) - 1
        d_extracted = d_extracted << remaining
        
        return d_extracted
    
    def compute_extraction_rate(self) -> float:
        """
        Calcule le taux de bits correctement extraits.
        
        Returns:
            Taux de succès (0.0 à 1.0)
        """
        if not self.extracted_bits:
            return 0.0
        
        correct = 0
        for pos, extracted in self.extracted_bits.items():
            if pos < len(self.real_d_bits) and extracted == self.real_d_bits[pos]:
                correct += 1
        
        return correct / len(self.extracted_bits)