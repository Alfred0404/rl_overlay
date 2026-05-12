# Mode Test - Guide d'utilisation

Lorsque le serveur Rocket League est down, vous pouvez utiliser le **mode test** pour continuer à développer et tester l'overlay.

## Démarrage en mode test

### Windows (PowerShell)

```powershell
.\run_test.ps1
```

Ou manuellement:

```powershell
$env:TEST_MODE = "true"
python -m uvicorn src.server:app --reload --host 0.0.0.0 --port 8000
```

### Linux/Mac

```bash
./run_test.sh
```

Ou manuellement:

```bash
TEST_MODE=true python -m uvicorn src.server:app --reload --host 0.0.0.0 --port 8000
```

## Données de test

Le fichier `data/test_event.json` contient un événement complet avec:

- **6 joueurs**: 3 par équipe (NRG vs G2)
- **Tous les champs**: Score, Goals, Shots, Assists, Saves, Boost, Speed
- **État du match**: Score, temps, noms d'équipes

En mode test:

- Les données sont broadcastées toutes les 0.5s
- Pas de connexion TCP requise
- Parfait pour tester le frontend sans serveur RL

## Éditer les données de test

Modifiez `data/test_event.json` pour tester différents scénarios:

- Changer les noms des joueurs
- Modifier les valeurs de Boost (0-100)
- Changer les scores et temps
- Ajouter/retirer des joueurs

Les changements prendront effet à la prochaine mise à jour du broadcast (après 0.5s).

## Accès à l'overlay

Une fois le serveur lancé:

- **Dashboard**: http://localhost:8000/
- **Stream Overlay**: http://localhost:8000/overlay
- **État actuel (JSON)**: http://localhost:8000/state
