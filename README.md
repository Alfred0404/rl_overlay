# RL Overlay

![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)
![Uvicorn](https://img.shields.io/badge/Uvicorn-latest-6f42c1.svg)

![License](https://img.shields.io/badge/license-MIT-green.svg)

RL Overlay est un overlay web léger pour afficher en direct les informations d'une partie Rocket League : score, temps, noms d'équipes, joueurs et jauges de boost. Le projet s'appuie sur **Python**, **FastAPI** et **WebSocket** pour récupérer les événements et les pousser vers l'interface navigateur.

## Table des matières

- [Structure du projet](#structure-du-projet)
- [Installation](#installation)
- [Utilisation](#utilisation)
  - [Logos des équipes](#2-logos-des-équipes)
- [Tests](#tests)
- [Sources](#sources)

---

## Structure du projet

```bash
rl_overlay/
├─ data/                     # État parsé et données de test
│  ├─ parsed_state.json      # Dernier état reçu et sérialisé
│  └─ test_event.json        # Événement de test utilisé en mode démo
├─ src/
│  ├─ main.py                # Lanceur de test / consommation du flux
│  ├─ server.py              # API FastAPI, WebSocket et routes overlay
│  └─ streamer.py            # Récupération et streaming des événements RL
├─ templates/
│  ├─ overlay.html           # Interface overlay affichée dans le navigateur
│  ├─ template.html          # Page de test / débogage
│  └─ images/
│     ├─ image.png           # Fond de démonstration utilisé pour le gameplay
│     ├─ logo_vitality.png   # Logo de l'équipe Vitality
│     └─ logo_nrg.png        # Logo de l'équipe NRG
├─ run_test.ps1              # Lancement en mode test sous Windows
├─ run_test.sh               # Lancement en mode test sous Linux / macOS
├─ requirements.txt          # Dépendances Python
└─ README.md                 # Documentation du projet
```

---

## Installation

1. Créer un environnement Python _(`venv` recommandé)_

   ```bash
   python -m venv .venv

   # Linux
   source .venv/bin/activate
   # macOS
   source .venv/bin/activate
   # Windows
   .venv\Scripts\activate
   ```

2. Installer les dépendances

   ```bash
   pip install -r requirements.txt
   ```

3. _(Optionnel)_ Vérifier que les fichiers de test sont bien présents
   ```bash
   ls data templates
   ```

---

# Utilisation

## 1. Aperçu visuel

<p align="center">
   <img src="templates/images/image.png" alt="Fond de démonstration" width="700">
  <br/>
  <em>Fig 1. Fond de démonstration utilisé pour simuler le gameplay pendant l'affichage de l'overlay.</em>
</p>

L'overlay HTML se superpose à ce fond pour simuler une partie en cours avec les panneaux joueurs, le bandeau central et les indicateurs d'état.

## 2. Logos des équipes

<p align="center">
   <img src="templates/images/logo_vitality.png" alt="Logo Vitality" width="300">
   &nbsp;&nbsp;
   <img src="templates/images/logo_nrg.png" alt="Logo NRG" width="300">
   <br/>
   <em>Fig 2. Logos des équipes Vitality et NRG utilisés dans l'overlay.</em>
</p>

Ces logos peuvent être affichés à côté des noms d'équipes dans le bandeau central de l'overlay.

## 3. Lancement en mode test

```bash
# Linux / macOS
./run_test.sh

# Windows
.\run_test.ps1
```

Le serveur démarre en mode test avec des événements mockés depuis `data/test_event.json`. L'overlay est ensuite disponible sur `http://localhost:8000/overlay`.

## 4. Lancement manuel

```bash
uvicorn src.server:app --reload --host 0.0.0.0 --port 8000
```

Cette commande lance le serveur FastAPI manuellement. L'overlay principal reste accessible sur `http://localhost:8000/overlay`, et l'état courant sur `http://localhost:8000/state`.

---

## Tests

Le projet ne contient pas de suite `pytest` dédiée. La vérification la plus simple consiste à démarrer le serveur de test et à contrôler les routes exposées.

1. Lancer le serveur en mode test

   ```bash
   # Linux / macOS
   ./run_test.sh

   # Windows
   .\run_test.ps1
   ```

2. Ouvrir l'overlay dans le navigateur

   ```text
   http://localhost:8000/overlay
   ```

3. Vérifier l'état brut exposé par l'API
   ```text
   http://localhost:8000/state
   ```

---

## Sources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Uvicorn Documentation](https://www.uvicorn.org/)

<p align="center">
	<img src="https://raw.githubusercontent.com/catppuccin/catppuccin/main/assets/footers/gray0_ctp_on_line.svg?sanitize=true" />
</p>
