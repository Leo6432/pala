# Paladium Market Dashboard

Dashboard de trading pour le serveur Paladium — analyse les prix du marché et recommande quoi acheter/vendre.

## Démarrage rapide

```bash
pip install -r requirements.txt
cd src
python main.py
# Ouvre http://localhost:8000
```

## Passer à la vraie API

```bash
cp .env.example .env
# Éditer USE_MOCK=false dans .env
```

## Fonctionnalités

- **Recommandations** Acheter / Vendre / Attendre par article
- **Score de confiance** basé sur position dans la fourchette + tendance SMA
- **Graphique historique** au clic sur un article
- **Recherche et filtre** en temps réel
- **Auto-refresh** toutes les 60 secondes
