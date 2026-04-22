# 🔐 INF4268 – Attaque par Canal Auxiliaire (Timing) sur RSA

![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt-6.5%2B-green)
![Licence](https://img.shields.io/badge/Licence-MIT-yellow)

**Projet 3 – Cryptographie Asymétrique**  
Master 1 Sécurité Informatique – Université de Yaoundé 1  
Enseignant : Dr. Ekodeck Stéphane Gaël R.

---

## 📖 Description

Ce projet implémente une **attaque par canal auxiliaire temporel (timing attack)** contre une implémentation naïve de RSA. L'application PyQt6 permet de :

- Générer des clés RSA (512 et 1024 bits)
- Mesurer les temps de déchiffrement avec une précision nanoseconde
- Extraire les bits de la clé privée par analyse statistique (algorithme de Kocher, 1996)
- Évaluer deux contre-mesures : **RSA Blinding** et **Montgomery Ladder**

Toutes les opérations sont pilotées depuis l'interface graphique, **sans jamais utiliser le terminal**.

---

## 🚀 Installation

### Prérequis
- Python 3.10 ou supérieur
- pip
- (Optionnel) Docker pour la reproductibilité

### Étapes

```bash
# 1. Cloner le dépôt
git clone https://github.com/ALAIN-NG/timing-attack-rsa.git
cd timing-attack-rsa

# 2. Créer un environnement virtuel
python -m venv venv
source venv/bin/activate      # Linux/macOS
# ou
venv\Scripts\activate         # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer l'application
python main.py
```

### Avec Docker

```bash
docker build -t rsa-timing-attack .
docker run -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix rsa-timing-attack
```

---

## 📁 Structure du projet

```
timing-attack-rsa/
├── main.py                     # Point d'entrée de l'application
├── requirements.txt            # Dépendances Python
├── README.md                   # Documentation
├── LICENSE                     # Licence MIT
├── Dockerfile                  # Conteneur de reproduction
│
├── core/                       # Logique métier (indépendante de la GUI)
│   ├── rsa_naive.py            # RSA avec square-and-multiply vulnérable
│   ├── rsa_secure.py           # RSA avec contre-mesures (Blinding, Montgomery)
│   ├── timing_bench.py         # Banc de mesure de timing
│   ├── attack_engine.py        # Algorithme d'attaque de Kocher
│   └── stats.py                # Fonctions statistiques (t-test, KS, IQR)
│
├── gui/                        # Interface graphique PyQt6
│   ├── main_window.py          # Fenêtre principale + QTabWidget
│   ├── tab_rsa.py              # Onglet 1 : RSA Naïf
│   ├── tab_timing.py           # Onglet 2 : Mesures de Timing
│   ├── tab_attack.py           # Onglet 3 : Attaque
│   ├── tab_defense.py          # Onglet 4 : Contre-mesures
│   ├── widgets/
│   │   ├── console_widget.py   # Console de logs colorée
│   │   ├── bit_grid_widget.py  # Grille animée des bits extraits
│   │   └── mpl_canvas.py       # Wrapper Matplotlib pour PyQt6
│   └── styles/
│       ├── dark_theme.qss      # Thème sombre
│       └── light_theme.qss     # Thème clair
│
├── workers/                    # QThread workers (calculs non bloquants)
│   ├── keygen_worker.py        # Génération de clés RSA
│   ├── timing_worker.py        # Collecte des mesures de timing
│   ├── attack_worker.py        # Attaque bit par bit
│   └── defense_worker.py       # Évaluation des contre-mesures
│
├── data/
│   ├── raw/                    # Fichiers CSV des mesures brutes
│   └── exports/                # Graphiques PNG exportés
│
└── tests/                      # Tests unitaires (pytest, pytest-qt)
    ├── test_rsa_naive.py
    ├── test_rsa_secure.py
    ├── test_timing_bench.py
    ├── test_attack_engine.py
    └── test_gui.py
```

---

## 🖥️ Aperçu de l'interface

| Onglet | Fonctionnalité |
|--------|----------------|
| **Phase 1 – RSA Naïf** | Génération de clés, chiffrement/déchiffrement, tests unitaires, visualisation de l'exposant privé |
| **Phase 2 – Mesures de Timing** | Collecte de timings, histogrammes, boxplots, heatmaps, export CSV |
| **Phase 3 – Attaque** | Extraction bit par bit (BitGridWidget animé), courbe ROC, matrice de confusion |
| **Phase 4 – Contre-mesures** | RSA Blinding et Montgomery Ladder, graphiques comparatifs, tests statistiques |

---

## 📊 Résultats attendus

| Scénario | Taille de clé | Mesures | Taux d'extraction attendu |
|----------|---------------|---------|---------------------------|
| S1 – Baseline | 512 bits | 1 000 | 80–95 % |
| S2 – Principal | 1024 bits | 2 000 | 70–90 % |
| S3 – Bruit faible | Docker isolé | 1 000 | 85–95 % |
| S4 – Bruit fort | Charge CPU simulée | 2 000 | 60–75 % |
| S5 – Seuil minimal | 512 bits | Variable | ≥ 8 bits extraits |

---

## 🧪 Tests

```bash
# Lancer tous les tests
pytest tests/ -v

# Avec couverture
pytest tests/ --cov=core --cov=gui --cov-report=html
```

---

## 📚 Références

- **Kocher, P. (1996).** *Timing Attacks on Implementations of Diffie-Hellman, RSA, DSS, and Other Systems.* CRYPTO'96.
- **Brumley, D., & Boneh, D. (2003).** *Remote Timing Attacks are Practical.* USENIX Security.
- **OpenSSL Security Advisory (2003).** *RSA blinding vulnerability.*

---

## 👥 Auteurs

- **NGUEUDJANG DJOMO ALAIN GILDAS** – 22W2183
- **ESSIMBI MBALLA GABRIELLE** – 22U2019

Master 1 Sécurité Informatique – INF4268

---

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## ✅ État d'avancement actuel

| Phase | État | Description |
|-------|------|-------------|
| **S1** | ✅ Terminé | Squelette PyQt6, thème, GitHub, README |
| **S2-S3** | ✅ Terminé | Phase 1 - RSA Naïf (génération, tests, visualisation) |
| **S4** | ✅ Terminé | Phase 2 - Mesures de Timing (banc de mesure, worker, interface) |
| **S5-S6** | ⏳ À faire | Phase 3 - Attaque par timing |
| **S7** | ⏳ À faire | Phase 4 - Contre-mesures |
| **S8** | ⏳ À faire | Finalisation, rapport, soutenance |

---
