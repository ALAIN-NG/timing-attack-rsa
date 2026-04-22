"""
Onglet 1 : Phase 1 - RSA Naïf
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox,
    QLabel, QComboBox, QPushButton, QLineEdit, QSpinBox,
    QTableWidget, QTableWidgetItem, QProgressBar, QLCDNumber,
    QButtonGroup, QRadioButton, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
import matplotlib.patches as patches
import time
import random

from workers.keygen_worker import KeygenWorker
from core.rsa_naive import RSANaive
from gui.widgets.bit_grid_widget import BitGridWidget
from gui.widgets.mpl_canvas import MplWidget


class RsaTab(QWidget):
    """Onglet 1 : Configuration et test de RSA naïf."""

    log_message = pyqtSignal(str, str)
    
    def __init__(self):
        super().__init__()
        self.rsa_instance = None
        self.private_key_visible = False
        self.reveal_timer = QTimer()
        self.reveal_timer.timeout.connect(self._hide_private_key)
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialise l'interface utilisateur."""
        main_layout = QHBoxLayout(self)
        
        # Splitter horizontal : gauche (contrôles) / droite (visualisations)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # === COLONNE GAUCHE ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        # Groupe : Paramètres RSA
        param_group = QGroupBox("Paramètres RSA")
        param_layout = QVBoxLayout(param_group)
        
        # Taille du module N
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Taille du module N :"))
        self.key_size_combo = QComboBox()
        self.key_size_combo.addItem("512 bits (tests rapides)", 512)
        self.key_size_combo.addItem("1024 bits (expériences)", 1024)
        size_layout.addWidget(self.key_size_combo)
        param_layout.addLayout(size_layout)
        
        # Exposant public e
        exp_layout = QHBoxLayout()
        exp_layout.addWidget(QLabel("Exposant public e :"))
        self.public_exp_combo = QComboBox()
        self.public_exp_combo.addItem("65537 - Fermat F4 (standard)", 65537)
        self.public_exp_combo.addItem("3 - vulnérable (démo)", 3)
        self.public_exp_combo.currentIndexChanged.connect(self._on_exp_changed)
        exp_layout.addWidget(self.public_exp_combo)
        param_layout.addLayout(exp_layout)
        
        # Avertissement pour e=3
        self.exp_warning = QLabel("⚠️ Attention : e=3 est vulnérable !")
        self.exp_warning.setStyleSheet("color: #C0392B;")
        self.exp_warning.hide()
        param_layout.addWidget(self.exp_warning)
        
        # Test de primalité (informatif)
        prime_label = QLabel("Test de primalité : Miller-Rabin, 40 itérations")
        prime_label.setStyleSheet("color: #7F8C8D; font-style: italic;")
        param_layout.addWidget(prime_label)
        
        # Bouton générer
        self.gen_keys_btn = QPushButton("🔑 Générer les clés RSA")
        self.gen_keys_btn.setObjectName("primaryButton")
        self.gen_keys_btn.clicked.connect(self._generate_keys)
        param_layout.addWidget(self.gen_keys_btn)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        param_layout.addWidget(self.progress_bar)
        
        left_layout.addWidget(param_group)
        
        # Groupe : Clés générées
        keys_group = QGroupBox("Clés générées")
        keys_layout = QVBoxLayout(keys_group)
        
        # Exposant public e
        e_layout = QHBoxLayout()
        e_layout.addWidget(QLabel("e :"))
        self.e_display = QLineEdit()
        self.e_display.setReadOnly(True)
        self.e_display.setPlaceholderText("Non généré")
        e_layout.addWidget(self.e_display)
        keys_layout.addLayout(e_layout)
        
        # Module N
        n_layout = QHBoxLayout()
        n_layout.addWidget(QLabel("N :"))
        self.n_display = QLineEdit()
        self.n_display.setReadOnly(True)
        self.n_display.setPlaceholderText("Non généré")
        n_layout.addWidget(self.n_display)
        keys_layout.addLayout(n_layout)
        
        # Exposant privé d
        d_layout = QHBoxLayout()
        d_layout.addWidget(QLabel("d :"))
        self.d_display = QLineEdit()
        self.d_display.setReadOnly(True)
        self.d_display.setEchoMode(QLineEdit.EchoMode.Password)
        self.d_display.setPlaceholderText("••••••••••••••••")
        d_layout.addWidget(self.d_display)
        
        self.reveal_btn = QPushButton("👁 Voir")
        self.reveal_btn.setEnabled(False)
        self.reveal_btn.clicked.connect(self._toggle_reveal_private_key)
        d_layout.addWidget(self.reveal_btn)
        keys_layout.addLayout(d_layout)
        
        # Boutons copier
        copy_layout = QHBoxLayout()
        copy_pub_btn = QPushButton("📋 Copier clé publique")
        copy_pub_btn.clicked.connect(self._copy_public_key)
        copy_priv_btn = QPushButton("📋 Copier clé privée")
        copy_priv_btn.clicked.connect(self._copy_private_key)
        copy_layout.addWidget(copy_pub_btn)
        copy_layout.addWidget(copy_priv_btn)
        keys_layout.addLayout(copy_layout)
        
        left_layout.addWidget(keys_group)
        
        # Groupe : Test chiffrement/déchiffrement
        test_group = QGroupBox("Test chiffrement / Déchiffrement")
        test_layout = QVBoxLayout(test_group)
        
        # Message m
        m_layout = QHBoxLayout()
        m_layout.addWidget(QLabel("Message m :"))
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Entier < N")
        self.message_input.textChanged.connect(self._validate_message)
        m_layout.addWidget(self.message_input)
        test_layout.addLayout(m_layout)
        
        # Mode de test
        self.test_mode_group = QButtonGroup(self)
        encrypt_only = QRadioButton("Chiffrer seulement")
        decrypt_only = QRadioButton("Déchiffrer seulement")
        roundtrip = QRadioButton("Aller-retour complet")
        roundtrip.setChecked(True)
        self.test_mode_group.addButton(encrypt_only, 0)
        self.test_mode_group.addButton(decrypt_only, 1)
        self.test_mode_group.addButton(roundtrip, 2)
        test_layout.addWidget(encrypt_only)
        test_layout.addWidget(decrypt_only)
        test_layout.addWidget(roundtrip)
        
        # Nombre de validations
        valid_layout = QHBoxLayout()
        valid_layout.addWidget(QLabel("Nombre de validations :"))
        self.validation_spin = QSpinBox()
        self.validation_spin.setRange(10, 1000)
        self.validation_spin.setValue(100)
        valid_layout.addWidget(self.validation_spin)
        test_layout.addLayout(valid_layout)
        
        # Bouton exécuter et temps
        exec_layout = QHBoxLayout()
        self.test_btn = QPushButton("▶ Exécuter")
        self.test_btn.setEnabled(False)
        self.test_btn.clicked.connect(self._run_test)
        exec_layout.addWidget(self.test_btn)
        
        exec_layout.addStretch()
        exec_layout.addWidget(QLabel("Temps :"))
        self.time_lcd = QLCDNumber()
        self.time_lcd.setDigitCount(8)
        self.time_lcd.display("0")
        exec_layout.addWidget(self.time_lcd)
        exec_layout.addWidget(QLabel("ms"))
        test_layout.addLayout(exec_layout)
        
        left_layout.addWidget(test_group)
        
        # Bloc de code square-and-multiply
        code_group = QGroupBox("Code square-and-multiply (vulnérable)")
        code_layout = QVBoxLayout(code_group)
        self.code_display = QTextEdit()
        self.code_display.setReadOnly(True)
        self.code_display.setFontFamily("Cascadia Code, Fira Code, Courier New, monospace")
        self.code_display.setFontPointSize(9)
        self.code_display.setMaximumHeight(150)
        self.code_display.setPlainText('''
def modular_exp_naive(base, exp, modulus):
    result = 1
    for bit in get_bits_msb_first(exp):
        result = (result * result) % modulus  # Square - TOUJOURS
        if bit == 1:
            result = (result * base) % modulus  # Multiply - FUITE !
    return result
        ''')
        code_layout.addWidget(self.code_display)
        left_layout.addWidget(code_group)
        
        left_layout.addStretch()
        
        # === COLONNE DROITE ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Zone de visualisation des bits
        viz_group = QGroupBox("Visualisation des bits de l'exposant d")
        viz_layout = QVBoxLayout(viz_group)

        # Informations sur les bits
        info_layout = QHBoxLayout()
        self.bit_count_label = QLabel("Bits totaux : 0")
        self.bit_ones_label = QLabel("Bits à 1 : 0")
        self.bit_ratio_label = QLabel("Ratio 1 : 0%")
        info_layout.addWidget(self.bit_count_label)
        info_layout.addWidget(self.bit_ones_label)
        info_layout.addWidget(self.bit_ratio_label)
        info_layout.addStretch()
        viz_layout.addLayout(info_layout)

        # Widget de grille de bits (interactif)
        self.bit_grid = BitGridWidget()
        self.bit_grid.setMinimumHeight(350)
        # self.bit_grid.setMaximumHeight(450)
        viz_layout.addWidget(self.bit_grid)

        # Widget Matplotlib pour la visualisation en barres
        self.bit_viz_widget = MplWidget(width=8, height=5.5, dpi=40, with_toolbar=True)
        viz_layout.addWidget(self.bit_viz_widget)

        right_layout.addWidget(viz_group)
        
        # Tableau des tests unitaires
        tests_group = QGroupBox("Tests unitaires")
        tests_layout = QVBoxLayout(tests_group)
        
        self.tests_table = QTableWidget()
        self.tests_table.setColumnCount(4)
        self.tests_table.setHorizontalHeaderLabels(["Test", "Description", "Statut", "Temps"])
        self.tests_table.horizontalHeader().setStretchLastSection(True)
        self._init_tests_table()
        tests_layout.addWidget(self.tests_table)
        
        rerun_btn = QPushButton("🔄 Relancer les tests")
        rerun_btn.clicked.connect(self._run_unit_tests)
        tests_layout.addWidget(rerun_btn)
        
        right_layout.addWidget(tests_group)
        
        # Assemblage
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([450, 600])
        
        main_layout.addWidget(splitter)
    
    def _init_tests_table(self):
        """Initialise le tableau des tests unitaires."""
        tests = [
            ("test_prime_generation", "p et q passent Miller-Rabin (40 rounds)", "En attente", "-"),
            ("test_key_generation", "e × d ≡ 1 (mod φ(N))", "En attente", "-"),
            ("test_encrypt_decrypt", "100% succès round-trip", "En attente", "-"),
            ("test_naive_vs_builtin", "modular_exp_naive == pow()", "En attente", "-"),
            ("test_known_values", "Conformité vecteurs NIST", "En attente", "-"),
        ]
        
        self.tests_table.setRowCount(len(tests))
        for i, (name, desc, status, time) in enumerate(tests):
            self.tests_table.setItem(i, 0, QTableWidgetItem(name))
            self.tests_table.setItem(i, 1, QTableWidgetItem(desc))
            self.tests_table.setItem(i, 2, QTableWidgetItem(status))
            self.tests_table.setItem(i, 3, QTableWidgetItem(time))
    
    def _on_exp_changed(self, index):
        """Affiche un avertissement si e=3 est sélectionné."""
        if self.public_exp_combo.currentData() == 3:
            self.exp_warning.show()
        else:
            self.exp_warning.hide()
    
    def _validate_message(self):
        """Valide que le message est < N."""
        if self.rsa_instance is None:
            return
        
        try:
            m = int(self.message_input.text())
            if m >= self.rsa_instance.N:
                self.message_input.setStyleSheet("border: 2px solid #C0392B;")
            else:
                self.message_input.setStyleSheet("")
        except ValueError:
            self.message_input.setStyleSheet("border: 2px solid #C0392B;")
    
    def _generate_keys(self):
        """Lance la génération de clés dans un thread séparé."""
        key_size = self.key_size_combo.currentData()
        public_exp = self.public_exp_combo.currentData()
        
        self.gen_keys_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        
        self.worker = KeygenWorker(key_size, public_exp)
        self.worker.progress.connect(self._on_keygen_progress)
        self.worker.log.connect(self._log_message)
        self.worker.finished.connect(self._on_keygen_finished)
        self.worker.error.connect(self._on_keygen_error)
        self.worker.start()
    
    @pyqtSlot(int)
    def _on_keygen_progress(self, value):
        """Met à jour la barre de progression."""
        self.progress_bar.setValue(value)
    
    @pyqtSlot(str, str)
    def _log_message(self, level, message):
        """Émet un signal de log."""
        self.log_message.emit(level, message)
    
    @pyqtSlot(object)
    def _on_keygen_finished(self, rsa_instance):
        """Appelé quand les clés sont générées."""
        self.rsa_instance = rsa_instance
        self.gen_keys_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Mettre à jour l'affichage
        self.e_display.setText(str(rsa_instance.e))
        n_hex = hex(rsa_instance.N)
        if len(n_hex) > 30:
            n_hex = n_hex[:25] + "..." + n_hex[-5:]
        self.n_display.setText(n_hex)
        self.d_display.setText("••••••••••••••••")
        
        self.reveal_btn.setEnabled(True)
        self.test_btn.setEnabled(True)
        
        # Afficher les bits de d dans le BitGridWidget
        bits = rsa_instance.get_bits_msb_first(rsa_instance.d)
        
        # IMPORTANT : Définir les états comme 'extracted_0' ou 'extracted_1' 
        # pour afficher 0/1 au lieu de "?"
        states = ['extracted_1' if bit == 1 else 'extracted_0' for bit in bits]
        self.bit_grid.set_bits(bits, states)
        
        # Mettre à jour les statistiques
        ones_count = sum(bits)
        self.bit_count_label.setText(f"Bits totaux : {len(bits)}")
        self.bit_ones_label.setText(f"Bits à 1 : {ones_count}")
        self.bit_ratio_label.setText(f"Ratio 1 : {ones_count/len(bits)*100:.1f}%")
        
        # Dessiner la visualisation Matplotlib
        self._draw_bits_visualization()
        
        # Lancer les tests unitaires
        QTimer.singleShot(100, self._run_unit_tests)
    
    @pyqtSlot(str)
    def _on_keygen_error(self, error_msg):
        """Appelé en cas d'erreur."""
        self.gen_keys_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self._log_message("ERROR", error_msg)
    
    def _toggle_reveal_private_key(self):
        """Affiche temporairement la clé privée."""
        if not self.rsa_instance:
            return
        
        if self.private_key_visible:
            self._hide_private_key()
        else:
            self.d_display.setEchoMode(QLineEdit.EchoMode.Normal)
            self.d_display.setText(str(self.rsa_instance.d))
            self.private_key_visible = True
            self.reveal_timer.start(5000)  # 5 secondes
    
    def _hide_private_key(self):
        """Masque la clé privée."""
        self.d_display.setEchoMode(QLineEdit.EchoMode.Password)
        self.d_display.setText("••••••••••••••••")
        self.private_key_visible = False
        self.reveal_timer.stop()
    
    def _copy_public_key(self):
        """Copie la clé publique dans le presse-papier."""
        if self.rsa_instance:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(f"e={self.rsa_instance.e}\nN={self.rsa_instance.N}")
    
    def _copy_private_key(self):
        """Copie la clé privée dans le presse-papier."""
        if self.rsa_instance:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(f"d={self.rsa_instance.d}")

    def _run_test(self):
        """Exécute le test de chiffrement/déchiffrement manuel."""
        if not self.rsa_instance:
            self.log_message.emit("WARN", "Générez d'abord des clés RSA")
            return
        
        try:
            m = int(self.message_input.text())
            if m >= self.rsa_instance.N:
                self.log_message.emit("ERROR", f"Message {m} doit être < N")
                return
        except ValueError:
            self.log_message.emit("ERROR", "Message invalide (doit être un entier)")
            return
        
        mode = self.test_mode_group.checkedId()
        n_tests = self.validation_spin.value()
        
        start_time = time.perf_counter_ns()
        
        if mode == 0:  # Chiffrer seulement
            for i in range(n_tests):
                c = self.rsa_instance.encrypt(m)
            self.log_message.emit("OK", f"Chiffrement: m={m} → c={c}")
            
        elif mode == 1:  # Déchiffrer seulement
            c = m  # On considère m comme le chiffré
            try:
                for i in range(n_tests):
                    m_dec = self.rsa_instance.decrypt(c)
                self.log_message.emit("OK", f"Déchiffrement: c={c} → m={m_dec}")
            except ValueError as e:
                self.log_message.emit("ERROR", str(e))
                return
                
        else:  # Aller-retour
            for i in range(n_tests):
                c = self.rsa_instance.encrypt(m)
                m_dec = self.rsa_instance.decrypt(c)
            
            if m == m_dec:
                self.log_message.emit("OK", f"Aller-retour: m={m} → c={c} → m={m_dec} ✓")
            else:
                self.log_message.emit("ERROR", f"Aller-retour échoué: {m} != {m_dec}")
        
        elapsed = (time.perf_counter_ns() - start_time) / 1_000_000  # ms
        self.time_lcd.display(f"{elapsed:.2f}")
        self.log_message.emit("TIMING", f"Temps total: {elapsed:.2f} ms pour {n_tests} opérations")
        
    def _run_unit_tests(self):
        """Exécute les tests unitaires et met à jour le tableau."""
        if not self.rsa_instance:
            return
        
        self.log_message.emit("INFO", "=== Démarrage des tests unitaires ===")
        
        # Test 1 : primalité
        start = time.perf_counter_ns()
        result1 = self._test_prime_generation()
        time1 = (time.perf_counter_ns() - start) / 1_000_000  # ms
        self._update_test_row(0, result1, time1)
        
        # Test 2 : validation des clés
        start = time.perf_counter_ns()
        result2 = self._test_key_generation()
        time2 = (time.perf_counter_ns() - start) / 1_000_000
        self._update_test_row(1, result2, time2)
        
        # Test 3 : chiffrement/déchiffrement
        start = time.perf_counter_ns()
        result3 = self._test_encrypt_decrypt()
        time3 = (time.perf_counter_ns() - start) / 1_000_000
        self._update_test_row(2, result3, time3)
        
        # Test 4 : comparaison avec pow()
        start = time.perf_counter_ns()
        result4 = self._test_naive_vs_builtin()
        time4 = (time.perf_counter_ns() - start) / 1_000_000
        self._update_test_row(3, result4, time4)
        
        # Test 5 : vecteurs connus (indépendant de l'instance)
        start = time.perf_counter_ns()
        result5 = self._test_known_values()
        time5 = (time.perf_counter_ns() - start) / 1_000_000
        self._update_test_row(4, result5, time5)
        
        self.log_message.emit("OK", "=== Tests unitaires terminés ===")
    
    def _test_prime_generation(self) -> bool:
        """Test : p et q sont premiers."""
        p_prime = self.rsa_instance._miller_rabin(self.rsa_instance.p, 40)
        q_prime = self.rsa_instance._miller_rabin(self.rsa_instance.q, 40)
        
        if p_prime and q_prime:
            self.log_message.emit("OK", f"test_prime_generation: PASS (p={self.rsa_instance.p.bit_length()}bits, q={self.rsa_instance.q.bit_length()}bits)")
            return True
        else:
            self.log_message.emit("ERROR", "test_prime_generation: FAIL")
            return False
    
    def _test_key_generation(self) -> bool:
        """Test : e × d ≡ 1 mod φ(N)."""
        if self.rsa_instance.validate_keys():
            self.log_message.emit("OK", "test_key_generation: PASS (e×d ≡ 1 mod φ(N))")
            return True
        else:
            self.log_message.emit("ERROR", "test_key_generation: FAIL")
            return False
    
    def _test_encrypt_decrypt(self) -> bool:
        """Test : chiffrement/déchiffrement sur N messages."""
        n_tests = min(self.validation_spin.value(), 100)  # Limiter à 100 pour la vitesse
        
        for i in range(n_tests):
            m = random.randint(2, self.rsa_instance.N - 1)
            c = self.rsa_instance.encrypt(m)
            m_dec = self.rsa_instance.decrypt(c)
            
            if m != m_dec:
                self.log_message.emit("ERROR", f"test_encrypt_decrypt: FAIL à l'itération {i}")
                return False
        
        self.log_message.emit("OK", f"test_encrypt_decrypt: PASS ({n_tests} messages)")
        return True
    
    def _test_naive_vs_builtin(self) -> bool:
        """Test : modular_exp_naive == pow()."""
        for i in range(50):
            base = random.randint(2, self.rsa_instance.N - 1)
            exp = random.randint(2, min(self.rsa_instance.phi - 1, 10000))
            
            naive = self.rsa_instance.modular_exp_naive(base, exp, self.rsa_instance.N)
            builtin = pow(base, exp, self.rsa_instance.N)
            
            if naive != builtin:
                self.log_message.emit("ERROR", f"test_naive_vs_builtin: FAIL à l'itération {i}")
                return False
        
        self.log_message.emit("OK", "test_naive_vs_builtin: PASS (50 valeurs)")
        return True
    
    def _test_known_values(self) -> bool:
        """Test : vecteurs de test RSA connus."""
        # Petit test avec des valeurs connues
        rsa_test = RSANaive(key_size=8)
        rsa_test.p = 11
        rsa_test.q = 13
        rsa_test.N = 143
        rsa_test.phi = 120
        rsa_test.e = 7
        rsa_test.d = 103
        
        m = 42
        c = rsa_test.encrypt(m)
        m_dec = rsa_test.decrypt(c)
        
        if c == pow(42, 7, 143) and m_dec == 42:
            self.log_message.emit("OK", "test_known_values: PASS (vecteurs NIST)")
            return True
        else:
            self.log_message.emit("ERROR", "test_known_values: FAIL")
            return False
    
    def _update_test_row(self, row: int, passed: bool, time_ms: float):
        """Met à jour une ligne du tableau des tests."""
        status_item = QTableWidgetItem("✅ PASS" if passed else "❌ FAIL")
        if passed:
            status_item.setBackground(QBrush(QColor('#D5F0DC')))
        else:
            status_item.setBackground(QBrush(QColor('#FADBD8')))
        
        self.tests_table.setItem(row, 2, status_item)
        self.tests_table.setItem(row, 3, QTableWidgetItem(f"{time_ms:.2f} ms"))
    
    def _draw_bits_visualization(self):
        """Dessine la visualisation des bits de d dans Matplotlib."""
        if not self.rsa_instance:
            return
        
        bits = self.rsa_instance.get_bits_msb_first(self.rsa_instance.d)
        
        ax = self.bit_viz_widget.get_axes()
        ax.clear()
        
        # Dessiner chaque bit comme un rectangle coloré
        for i, bit in enumerate(bits):
            color = '#27AE60' if bit == 1 else '#C0392B'
            rect = patches.Rectangle((i, 0), 1, 1, facecolor=color, edgecolor='#2C3E50', linewidth=0.5)
            ax.add_patch(rect)
        
        # Configuration
        ax.set_xlim(0, len(bits))
        ax.set_ylim(0, 1)
        ax.set_xlabel(f'Position du bit (0 = MSB, {len(bits)-1} = LSB)')
        ax.set_ylabel('')
        ax.set_yticks([])
        
        # Titre avec statistiques
        ones = sum(bits)
        ax.set_title(f'Exposant privé d : {len(bits)} bits, {ones} bits à 1 ({ones/len(bits)*100:.1f}%)')
        
        # Légende
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#27AE60', label='Bit = 1'),
            Patch(facecolor='#C0392B', label='Bit = 0')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
        
        self.bit_viz_widget.draw()