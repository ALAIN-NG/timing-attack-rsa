"""
Fonctions statistiques pour l'analyse des timings.
"""

import numpy as np
from scipy import stats
from typing import List, Tuple, Optional


def compute_snr(signal_timings: List[float], noise_floor: float) -> float:
    """
    Calcule le rapport signal/bruit.
    
    Args:
        signal_timings: Liste des temps de signal
        noise_floor: Bruit de fond estimé
        
    Returns:
        SNR en dB
    """
    if not signal_timings:
        return 0.0
    
    signal_power = np.var(signal_timings) if len(signal_timings) > 1 else 0
    if signal_power == 0:
        return 0.0
    
    snr = 10 * np.log10(signal_power / (noise_floor ** 2))
    return snr


def welch_ttest(group0: List[float], group1: List[float]) -> Tuple[float, float]:
    """
    Test t de Welch (ne suppose pas l'égalité des variances).
    
    Args:
        group0: Timings pour l'hypothèse bit=0
        group1: Timings pour l'hypothèse bit=1
        
    Returns:
        Tuple (statistique t, p-value)
    """
    # Conversion explicite en tableaux numpy de type float64
    g0 = np.array(group0, dtype=np.float64)
    g1 = np.array(group1, dtype=np.float64)
    
    if len(g0) < 2 or len(g1) < 2:
        return 0.0, 1.0
    
    # Supprimer les NaN et inf
    g0 = g0[np.isfinite(g0)]
    g1 = g1[np.isfinite(g1)]
    
    if len(g0) < 2 or len(g1) < 2:
        return 0.0, 1.0
    
    t_stat, p_value = stats.ttest_ind(g0, g1, equal_var=False)
    return float(t_stat), float(p_value)


def ks_test(group0: List[float], group1: List[float]) -> Tuple[float, float]:
    """
    Test de Kolmogorov-Smirnov pour comparer deux distributions.
    
    Args:
        group0: Timings pour l'hypothèse bit=0
        group1: Timings pour l'hypothèse bit=1
        
    Returns:
        Tuple (statistique KS, p-value)
    """
    g0 = np.array(group0, dtype=np.float64)
    g1 = np.array(group1, dtype=np.float64)
    
    if len(g0) < 2 or len(g1) < 2:
        return 0.0, 1.0
    
    g0 = g0[np.isfinite(g0)]
    g1 = g1[np.isfinite(g1)]
    
    if len(g0) < 2 or len(g1) < 2:
        return 0.0, 1.0
    
    ks_stat, p_value = stats.ks_2samp(g0, g1)
    return float(ks_stat), float(p_value)


def pearson_correlation(x: List[float], y: List[float]) -> Tuple[float, float]:
    """
    Corrélation de Pearson.
    
    Args:
        x: Première série
        y: Deuxième série
        
    Returns:
        Tuple (coefficient de corrélation, p-value)
    """
    # Conversion explicite en tableaux numpy de type float64
    x_arr = np.array(x, dtype=np.float64)
    y_arr = np.array(y, dtype=np.float64)
    
    if len(x_arr) < 2 or len(y_arr) < 2:
        return 0.0, 1.0
    
    # Supprimer les paires avec NaN ou inf
    mask = np.isfinite(x_arr) & np.isfinite(y_arr)
    x_arr = x_arr[mask]
    y_arr = y_arr[mask]
    
    if len(x_arr) < 2:
        return 0.0, 1.0
    
    # Vérifier qu'il y a de la variance
    if np.std(x_arr) == 0 or np.std(y_arr) == 0:
        return 0.0, 1.0
    
    try:
        corr, p_value = stats.pearsonr(x_arr, y_arr)
        return float(corr), float(p_value)
    except Exception as e:
        print(f"Erreur pearson_correlation: {e}")
        return 0.0, 1.0


def spearman_correlation(x: List[float], y: List[float]) -> Tuple[float, float]:
    """
    Corrélation de Spearman (robuste aux non-linéarités).
    
    Args:
        x: Première série
        y: Deuxième série
        
    Returns:
        Tuple (coefficient de corrélation, p-value)
    """
    # Conversion explicite en tableaux numpy de type float64
    x_arr = np.array(x, dtype=np.float64)
    y_arr = np.array(y, dtype=np.float64)
    
    if len(x_arr) < 2 or len(y_arr) < 2:
        return 0.0, 1.0
    
    # Supprimer les paires avec NaN ou inf
    mask = np.isfinite(x_arr) & np.isfinite(y_arr)
    x_arr = x_arr[mask]
    y_arr = y_arr[mask]
    
    if len(x_arr) < 2:
        return 0.0, 1.0
    
    try:
        corr, p_value = stats.spearmanr(x_arr, y_arr)
        # spearmanr peut retourner un objet de type SignificanceResult
        if hasattr(corr, 'statistic'):
            return float(corr.statistic), float(corr.pvalue)
        elif hasattr(corr, 'correlation'):
            return float(corr.correlation), float(corr.pvalue)
        else:
            return float(corr), float(p_value)
    except Exception as e:
        print(f"Erreur spearman_correlation: {e}")
        return 0.0, 1.0


def compute_roc_curve(
    predictions: List[float],
    true_labels: List[int],
    num_thresholds: int = 100
) -> Tuple[List[float], List[float], float]:
    """
    Calcule la courbe ROC pour l'évaluation de l'attaque.
    
    Args:
        predictions: Scores de prédiction (différence de timing)
        true_labels: Vraies étiquettes (0 ou 1)
        num_thresholds: Nombre de seuils à évaluer
        
    Returns:
        Tuple (taux_faux_positifs, taux_vrais_positifs, AUC)
    """
    if len(predictions) != len(true_labels):
        raise ValueError("predictions et true_labels doivent avoir la même longueur")
    
    # Conversion en tableaux numpy
    pred = np.array(predictions, dtype=np.float64)
    labels = np.array(true_labels, dtype=np.int32)
    
    # Trier par score décroissant
    sorted_indices = np.argsort(pred)[::-1]
    sorted_labels = labels[sorted_indices]
    
    tpr_list = []
    fpr_list = []
    
    n_pos = int(np.sum(labels))
    n_neg = len(labels) - n_pos
    
    if n_pos == 0 or n_neg == 0:
        return [0.0, 1.0], [0.0, 1.0], 0.5
    
    tp = 0
    fp = 0
    
    for label in sorted_labels:
        if label == 1:
            tp += 1
        else:
            fp += 1
        
        tpr = tp / n_pos
        fpr = fp / n_neg
        
        tpr_list.append(float(tpr))
        fpr_list.append(float(fpr))
    
    # Calculer l'AUC (méthode des trapèzes)
    auc = 0.0
    for i in range(1, len(fpr_list)):
        auc += (fpr_list[i] - fpr_list[i-1]) * (tpr_list[i] + tpr_list[i-1]) / 2
    
    return fpr_list, tpr_list, auc


def confusion_matrix(
    predicted: List[int],
    actual: List[int]
) -> Tuple[int, int, int, int]:
    """
    Calcule la matrice de confusion.
    
    Args:
        predicted: Prédictions (0 ou 1)
        actual: Valeurs réelles (0 ou 1)
        
    Returns:
        Tuple (TP, FP, TN, FN)
    """
    pred = np.array(predicted, dtype=np.int32)
    act = np.array(actual, dtype=np.int32)
    
    tp = int(np.sum((pred == 1) & (act == 1)))
    fp = int(np.sum((pred == 1) & (act == 0)))
    tn = int(np.sum((pred == 0) & (act == 0)))
    fn = int(np.sum((pred == 0) & (act == 1)))
    
    return tp, fp, tn, fn