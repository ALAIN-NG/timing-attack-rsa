FROM python:3.12-slim

LABEL maintainer="Votre nom <votre.email@example.com>"
LABEL description="INF4268 - Attaque par canal auxiliaire (timing) sur RSA"

# Éviter les prompts interactifs pendant l'installation
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Installer les dépendances système nécessaires pour PyQt6 et Matplotlib
RUN apt-get update && apt-get install -y \
    # Dépendances Qt6
    libgl1-mesa-glx \
    libglib2.0-0 \
    libfontconfig1 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    libxcb-cursor0 \
    libxcb-xfixes0 \
    libxcb-sync1 \
    # Dépendances Matplotlib
    libfreetype6 \
    libpng16-16 \
    # Outils utiles
    htop \
    # Nettoyage
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de dépendances d'abord (meilleure mise en cache Docker)
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code source
COPY . .

# Créer les dossiers de données
RUN mkdir -p data/raw data/exports

# Commande par défaut
CMD ["python", "main.py"]