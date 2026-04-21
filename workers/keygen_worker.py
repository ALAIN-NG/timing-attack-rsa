"""
Worker QThread pour la génération de clés RSA.
"""

from PyQt6.QtCore import QThread, pyqtSignal
from core.rsa_naive import RSANaive


class KeygenWorker(QThread):
    """
    Worker thread pour générer les clés RSA sans bloquer l'interface.
    """
    
    # Signaux émis pendant la génération
    progress = pyqtSignal(int)           # Progression (0-100)
    log = pyqtSignal(str, str)           # (niveau, message)
    finished = pyqtSignal(object)        # Instance RSANaive avec clés
    error = pyqtSignal(str)              # Message d'erreur
    
    def __init__(self, key_size: int = 1024, public_exponent: int = 65537):
        """
        Initialise le worker.
        
        Args:
            key_size: Taille du module N en bits
            public_exponent: Exposant public e
        """
        super().__init__()
        self.key_size = key_size
        self.public_exponent = public_exponent
        
    def run(self):
        """Exécute la génération de clés dans un thread séparé."""
        try:
            self.log.emit("INFO", f"Démarrage de la génération de clés RSA-{self.key_size} bits...")
            self.log.emit("INFO", f"Exposant public e = {self.public_exponent}")
            self.progress.emit(10)
            
            # Créer l'instance RSA
            rsa = RSANaive(key_size=self.key_size, public_exponent=self.public_exponent)
            self.progress.emit(30)
            
            # Générer les clés
            self.log.emit("INFO", "Génération des nombres premiers p et q (Miller-Rabin, 40 itérations)...")
            p, q, N, e, d = rsa.generate_keys()
            self.progress.emit(80)
            
            # Vérifier les clés
            if rsa.validate_keys():
                self.log.emit("OK", f"Clés générées avec succès !")
                self.log.emit("INFO", f"p = {hex(p)[:20]}... ({p.bit_length()} bits)")
                self.log.emit("INFO", f"q = {hex(q)[:20]}... ({q.bit_length()} bits)")
                self.log.emit("INFO", f"N = {hex(N)[:30]}... ({N.bit_length()} bits)")
                self.log.emit("INFO", f"d = [MASQUÉ] ({d.bit_length()} bits)")
            else:
                raise ValueError("Échec de validation des clés : e*d ≠ 1 mod φ(N)")
            
            self.progress.emit(100)
            self.finished.emit(rsa)
            
        except Exception as e:
            self.log.emit("ERROR", f"Erreur lors de la génération des clés : {str(e)}")
            self.error.emit(str(e))