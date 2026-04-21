"""
Implémentation naïve de RSA avec exponentiation modulaire vulnérable.
Expose volontairement une fuite temporelle via square-and-multiply.
"""

import random
from typing import Tuple, List

class RSANaive:
    """Classe implémentant RSA avec exponentiation modulaire vulnérable."""
    
    def __init__(self, key_size: int = 1024, public_exponent: int = 65537):
        """
        Initialise une instance RSA.
        
        Args:
            key_size: Taille du module N en bits (512 ou 1024)
            public_exponent: Exposant public e (défaut: 65537 = F4)
        """
        self.key_size = key_size
        self.e = public_exponent
        self.p = None
        self.q = None
        self.N = None
        self.phi = None
        self.d = None
        
    def generate_keys(self) -> Tuple[int, int, int, int, int]:
        """
        Génère une paire de clés RSA.
        
        Returns:
            Tuple (p, q, N, e, d) contenant les paramètres RSA
        """
        # 1. Générer deux nombres premiers p et q de taille key_size/2 bits
        half_size = self.key_size // 2
        self.p = self._generate_prime(half_size)
        self.q = self._generate_prime(half_size)
        
        # S'assurer que p != q
        while self.p == self.q:
            self.q = self._generate_prime(half_size)
        
        # 2. Calculer N = p * q
        self.N = self.p * self.q
        
        # 3. Calculer φ(N) = (p-1) * (q-1)
        self.phi = (self.p - 1) * (self.q - 1)
        
        # 4. Vérifier que e est premier avec φ(N)
        while self._gcd(self.e, self.phi) != 1:
            # Normalement e=65537 est premier avec φ(N) pour des p,q aléatoires
            # Mais si ce n'est pas le cas, on régénère q
            self.q = self._generate_prime(half_size)
            self.N = self.p * self.q
            self.phi = (self.p - 1) * (self.q - 1)
        
        # 5. Calculer d = e^(-1) mod φ(N) via Euclide étendu
        self.d = self._mod_inverse(self.e, self.phi)
        
        return self.p, self.q, self.N, self.e, self.d
    
    def _generate_prime(self, bits: int) -> int:
        """
        Génère un nombre premier de 'bits' bits en utilisant Miller-Rabin.
        
        Args:
            bits: Taille en bits du nombre premier à générer
            
        Returns:
            Un nombre premier de la taille spécifiée
        """
        while True:
            # Générer un nombre impair de 'bits' bits
            candidate = random.getrandbits(bits)
            candidate |= (1 << (bits - 1))  # Forcer le bit de poids fort à 1
            candidate |= 1                   # Forcer le bit de poids faible à 1 (impair)
            
            if self._miller_rabin(candidate, 40):
                return candidate
    
    def _miller_rabin(self, n: int, k: int = 40) -> bool:
        """
        Test de primalité de Miller-Rabin.
        
        Args:
            n: Nombre à tester
            k: Nombre d'itérations (défaut: 40)
            
        Returns:
            True si n est probablement premier, False sinon
        """
        if n < 2:
            return False
        if n in (2, 3):
            return True
        if n % 2 == 0:
            return False
        
        # Écrire n-1 = 2^s * d avec d impair
        s, d = 0, n - 1
        while d % 2 == 0:
            s += 1
            d //= 2
        
        # Effectuer k tests
        for _ in range(k):
            a = random.randint(2, n - 2)
            x = pow(a, d, n)
            
            if x == 1 or x == n - 1:
                continue
            
            for _ in range(s - 1):
                x = pow(x, 2, n)
                if x == n - 1:
                    break
            else:
                return False
        
        return True
    
    def _gcd(self, a: int, b: int) -> int:
        """Calcule le PGCD de a et b (algorithme d'Euclide)."""
        while b:
            a, b = b, a % b
        return a
    
    def _extended_gcd(self, a: int, b: int) -> Tuple[int, int, int]:
        """
        Algorithme d'Euclide étendu.
        
        Returns:
            Tuple (gcd, x, y) tel que a*x + b*y = gcd
        """
        if a == 0:
            return b, 0, 1
        
        gcd, x1, y1 = self._extended_gcd(b % a, a)
        x = y1 - (b // a) * x1
        y = x1
        
        return gcd, x, y
    
    def _mod_inverse(self, a: int, m: int) -> int:
        """
        Calcule l'inverse modulaire de a modulo m.
        
        Args:
            a: Nombre dont on veut l'inverse
            m: Module
            
        Returns:
            L'inverse modulaire a^(-1) mod m
        """
        gcd, x, _ = self._extended_gcd(a, m)
        if gcd != 1:
            raise ValueError(f"Pas d'inverse modulaire pour {a} mod {m}")
        return x % m
    
    def get_bits_msb_first(self, n: int) -> List[int]:
        """
        Retourne les bits de n, du plus significatif (MSB) au moins significatif (LSB).
        
        Args:
            n: Entier à décomposer en bits
            
        Returns:
            Liste des bits [MSB, ..., LSB]
        """
        if n == 0:
            return [0]
        bits = []
        while n > 0:
            bits.append(n & 1)
            n >>= 1
        bits.reverse()
        return bits
    
    def modular_exp_naive(self, base: int, exp: int, modulus: int) -> int:
        """
        Exponentiation modulaire NAIVE - INTENTIONNELLEMENT VULNÉRABLE.
        
        Pour chaque bit b de l'exposant (de gauche à droite) :
            - On effectue TOUJOURS un carré (square) → temps ~constant
            - On effectue une multiplication SEULEMENT si b == 1 → FUITE TEMPORELLE
        
        Args:
            base: Base de l'exponentiation
            exp: Exposant (clé privée d ou autre)
            modulus: Module N
            
        Returns:
            (base^exp) mod modulus
        """
        result = 1
        bits = self.get_bits_msb_first(exp)
        
        for bit in bits:
            # Carré - toujours exécuté
            result = (result * result) % modulus
            
            # Multiplication - seulement si le bit est 1
            # C'EST ICI LA FUITE TEMPORELLE !
            if bit == 1:
                result = (result * base) % modulus
                
        return result
    
    def encrypt(self, plaintext: int) -> int:
        """
        Chiffrement RSA : c = m^e mod N.
        
        Args:
            plaintext: Message clair (entier < N)
            
        Returns:
            Message chiffré
        """
        if self.N is None or self.e is None:
            raise ValueError("Clés non générées. Appelez generate_keys() d'abord.")
        if plaintext >= self.N:
            raise ValueError(f"Message {plaintext} >= N ({self.N})")
        
        return self.modular_exp_naive(plaintext, self.e, self.N)
    
    def decrypt(self, ciphertext: int) -> int:
        """
        Déchiffrement RSA : m = c^d mod N.
        Utilise l'exponentiation modulaire vulnérable.
        
        Args:
            ciphertext: Message chiffré
            
        Returns:
            Message clair
        """
        if self.N is None or self.d is None:
            raise ValueError("Clés non générées. Appelez generate_keys() d'abord.")
        if ciphertext >= self.N:
            raise ValueError(f"Ciphertext {ciphertext} >= N ({self.N})")
        
        return self.modular_exp_naive(ciphertext, self.d, self.N)
    
    def validate_keys(self) -> bool:
        """
        Vérifie que les clés générées sont valides.
        
        Returns:
            True si e * d ≡ 1 mod φ(N)
        """
        if self.e is None or self.d is None or self.phi is None:
            return False
        return (self.e * self.d) % self.phi == 1