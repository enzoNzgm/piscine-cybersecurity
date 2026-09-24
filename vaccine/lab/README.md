# Lab — application vulnerable (banc de test)

Cible locale pour tester `vaccine`. **Ne jamais exposer sur internet.**

## Installation

    python -m venv venv
    ./venv/bin/pip install -r requirements.txt

## Lancer

    ./run.sh            # sqlite (aucun serveur necessaire)
    ./run.sh mysql      # demarre le conteneur MySQL puis le lab

Ctrl-C arrete le lab. Le conteneur MySQL continue de tourner ; pour l'arreter :
`docker stop vaccine-mysql`.

La page d'accueil affiche le moteur actif : `Lab (sqlite)` ou `Lab (mysql)`.

## Points d'injection

| Route | Methode | Contexte | Colonnes |
|---|---|---|---|
| `/product?id=1` | GET | entier | 3 |
| `/search?name=a` | GET | chaine (quote simple) | 3 |
| `/login` | POST (`user`, `pass`) | chaine (quote simple) | 2 |
