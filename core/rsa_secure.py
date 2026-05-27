"""
Implémentation sécurisée de RSA avec contre-mesures :
- RSA Blinding
- Montgomery Ladder
"""

import random
from typing import Tuple
from core.rsa_naive import RSANaive


class RSABlinding(RSANaive):
    """
    RSA avec Blinding (aveuglement).
    
    Protège contre les attaques par timing en randomisant le chiffré
    avant le déchiffrement, ce qui rompt la corrélation entre le temps
    d'exécution et les bits de la clé privée.
    """
    
    def __init__(self, key_size: int = 1024, public_exponent: int = 65537):
        super().__init__(key_size, public_exponent)
        self._blinding_stats = {
            'total_time_ns': 0,
            'blind_time_ns': 0,
            'unblind_time_ns': 0
        }
    
    def decrypt_blinded(self, ciphertext: int) -> Tuple[int, int]:
        """
        Déchiffrement RSA avec Blinding.
        
        Algorithme :
        1. Générer r aléatoire tel que gcd(r, N) = 1
        2. Calculer r_e = r^e mod N
        3. Aveugler : c_blind = (c * r_e) mod N
        4. Déchiffrer : m_blind = c_blind^d mod N
        5. Désaveugler : m = (m_blind * r^(-1)) mod N
        
        Args:
            ciphertext: Message chiffré
            
        Returns:
            Tuple (message déchiffré, temps d'exécution en ns)
        """
        import time
        
        start_total = time.perf_counter_ns()
        
        # 1. Générer r aléatoire
        r = random.randint(2, self.N - 1)
        while self._gcd(r, self.N) != 1:
            r = random.randint(2, self.N - 1)
        
        # 2. Calculer r^e mod N
        r_e = pow(r, self.e, self.N)
        
        # 3. Aveugler le chiffré
        c_blind = (ciphertext * r_e) % self.N
        
        start_blind = time.perf_counter_ns()
        
        # 4. Déchiffrer l'aveuglé (utilise l'exponentiation naïve)
        m_blind = self.modular_exp_naive(c_blind, self.d, self.N)
        
        end_blind = time.perf_counter_ns()
        
        # 5. Désaveugler
        r_inv = pow(r, -1, self.N)  # Inverse modulaire de r
        m = (m_blind * r_inv) % self.N
        
        end_total = time.perf_counter_ns()
        
        # Mettre à jour les statistiques
        self._blinding_stats['total_time_ns'] = end_total - start_total
        self._blinding_stats['blind_time_ns'] = end_blind - start_blind
        self._blinding_stats['unblind_time_ns'] = end_total - end_blind
        
        return m, end_total - start_total
    
    def get_stats(self) -> dict:
        """Retourne les statistiques de blinding."""
        return self._blinding_stats.copy()
    
    def get_overhead(self, naive_time_ns: float) -> float:
        """
        Calcule le surcoût par rapport au RSA naïf.
        
        Args:
            naive_time_ns: Temps médian du RSA naïf en ns
            
        Returns:
            Pourcentage de surcoût
        """
        blind_time = self._blinding_stats['total_time_ns']
        if naive_time_ns > 0:
            return (blind_time / naive_time_ns - 1) * 100
        return 0.0


class RSAMontgomeryLadder(RSANaive):
    """
    RSA avec Montgomery Ladder pour l'exponentiation modulaire.
    
    La Montgomery Ladder effectue exactement 2 multiplications par bit,
    indépendamment de la valeur du bit, ce qui élimine la fuite temporelle.
    
    Note : En Python pur, le branchement if/else crée toujours une légère
    différence de timing au niveau CPU. Pour une protection complète,
    il faudrait implémenter en C avec des instructions à temps constant.
    """
    
    def montgomery_ladder(self, base: int, exp: int, modulus: int) -> int:
        """
        Exponentiation modulaire à temps constant - Montgomery Ladder.
        
        Effectue TOUJOURS exactement 2 multiplications par bit.
        Aucune branche conditionnelle asymétrique sur les bits de exp.
        
        Args:
            base: Base de l'exponentiation
            exp: Exposant
            modulus: Module N
            
        Returns:
            (base^exp) mod modulus
        """
        bits = self.get_bits_msb_first(exp)
        
        r0 = 1
        r1 = base
        
        for bit in bits:
            if bit == 0:
                # r1 = r0 * r1 mod N
                r1 = (r0 * r1) % modulus
                # r0 = r0 * r0 mod N
                r0 = (r0 * r0) % modulus
            else:
                # r0 = r0 * r1 mod N
                r0 = (r0 * r1) % modulus
                # r1 = r1 * r1 mod N
                r1 = (r1 * r1) % modulus
        
        return r0
    
    def decrypt_secure(self, ciphertext: int) -> int:
        """
        Déchiffrement RSA avec Montgomery Ladder.
        
        Args:
            ciphertext: Message chiffré
            
        Returns:
            Message clair
        """
        if self.N is None or self.d is None:
            raise ValueError("Clés non générées.")
        if ciphertext >= self.N:
            raise ValueError(f"Ciphertext {ciphertext} >= N ({self.N})")
        
        return self.montgomery_ladder(ciphertext, self.d, self.N)
    
    def encrypt(self, plaintext: int) -> int:
        """
        Chiffrement RSA (utilise aussi Montgomery Ladder).
        
        Args:
            plaintext: Message clair
            
        Returns:
            Message chiffré
        """
        if self.N is None or self.e is None:
            raise ValueError("Clés non générées.")
        if plaintext >= self.N:
            raise ValueError(f"Message {plaintext} >= N ({self.N})")
        
        return self.montgomery_ladder(plaintext, self.e, self.N)