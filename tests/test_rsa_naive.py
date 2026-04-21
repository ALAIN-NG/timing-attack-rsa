"""
Tests unitaires pour l'implémentation RSA naïve.
"""

import pytest
from core.rsa_naive import RSANaive


class TestRSANaive:
    """Tests pour la classe RSANaive."""
    
    @pytest.fixture
    def rsa_512(self):
        """Fixture : instance RSA 512 bits avec clés générées."""
        rsa = RSANaive(key_size=512)
        rsa.generate_keys()
        return rsa
    
    @pytest.fixture
    def rsa_1024(self):
        """Fixture : instance RSA 1024 bits avec clés générées."""
        rsa = RSANaive(key_size=1024)
        rsa.generate_keys()
        return rsa
    
    def test_prime_generation(self, rsa_512):
        """Test : p et q sont premiers (Miller-Rabin)."""
        assert rsa_512._miller_rabin(rsa_512.p, 40)
        assert rsa_512._miller_rabin(rsa_512.q, 40)
    
    def test_key_generation(self, rsa_512):
        """Test : e * d ≡ 1 mod φ(N)."""
        assert rsa_512.validate_keys()
    
    def test_encrypt_decrypt_512(self, rsa_512):
        """Test : chiffrement/déchiffrement sur 100 messages aléatoires."""
        import random
        for _ in range(100):
            m = random.randint(2, rsa_512.N - 1)
            c = rsa_512.encrypt(m)
            m_dec = rsa_512.decrypt(c)
            assert m == m_dec
    
    def test_encrypt_decrypt_1024(self, rsa_1024):
        """Test : chiffrement/déchiffrement sur 50 messages aléatoires."""
        import random
        for _ in range(50):
            m = random.randint(2, rsa_1024.N - 1)
            c = rsa_1024.encrypt(m)
            m_dec = rsa_1024.decrypt(c)
            assert m == m_dec
    
    def test_naive_vs_builtin(self, rsa_512):
        """Test : modular_exp_naive == pow() pour 50 valeurs."""
        import random
        for _ in range(50):
            base = random.randint(2, rsa_512.N - 1)
            exp = random.randint(2, rsa_512.phi - 1)
            assert rsa_512.modular_exp_naive(base, exp, rsa_512.N) == pow(base, exp, rsa_512.N)
    
    def test_known_values(self):
        """Test : vecteurs de test RSA connus."""
        # Vecteur de test simple (petits nombres)
        rsa = RSANaive(key_size=8)  # Petit pour test
        rsa.p = 11
        rsa.q = 13
        rsa.N = 143
        rsa.phi = 120
        rsa.e = 7
        rsa.d = 103  # 7 * 103 = 721 ≡ 1 mod 120
        
        m = 42
        c = rsa.encrypt(m)
        assert c == pow(42, 7, 143)
        assert rsa.decrypt(c) == 42
    
    def test_get_bits_msb_first(self):
        """Test : extraction des bits MSB first."""
        rsa = RSANaive()
        assert rsa.get_bits_msb_first(13) == [1, 1, 0, 1]  # 13 = 1101 en binaire
        assert rsa.get_bits_msb_first(0) == [0]
        assert rsa.get_bits_msb_first(1) == [1]
    
    def test_mod_inverse(self):
        """Test : calcul de l'inverse modulaire."""
        rsa = RSANaive()
        assert rsa._mod_inverse(7, 120) == 103
        assert rsa._mod_inverse(3, 11) == 4  # 3 * 4 = 12 ≡ 1 mod 11
        
        with pytest.raises(ValueError):
            rsa._mod_inverse(2, 4)  # pgcd(2,4) = 2 ≠ 1
    
    def test_encrypt_message_too_large(self, rsa_512):
        """Test : chiffrement d'un message ≥ N lève une exception."""
        with pytest.raises(ValueError):
            rsa_512.encrypt(rsa_512.N + 1)
    
    def test_decrypt_ciphertext_too_large(self, rsa_512):
        """Test : déchiffrement d'un chiffré ≥ N lève une exception."""
        with pytest.raises(ValueError):
            rsa_512.decrypt(rsa_512.N + 1)