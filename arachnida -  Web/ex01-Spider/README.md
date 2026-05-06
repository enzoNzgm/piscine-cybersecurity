# Ex01 - Spider

Description
- Script Python `spider.py` pour récupérer des images récursivement depuis des sources web.

Prérequis
- Python 3.8+ installé
- Virtualenv recommandé
- Connexion réseau si le spider atteint des URLs

Installation
- (optionnel) Créer et activer un environnement virtuel :

```bash
python3 -m venv .venv
source .venv/bin/activate
```

- Installer les dépendances si présentées :

```bash
pip install -r ../requirement.txt
```

Contenu
- `spider.py` : le script principal
- `data/` : exemples et sorties

Usage
- Vérifier l'aide intégrée si disponible :

```bash
python3 spider.py --help
```

- Commandes courantes (adapter selon les options implémentées) :

```bash
# Lancer le spider sur une URL
python3 spider.py -u https://example.com

# Lancer et écrire la sortie dans un fichier nommé choisi
python3 spider.py -u https://example.com -p filename

# Lancer le spider sur un URL et télécharger récursivement les images
# Profondeur de 5 par default
python3 spider.py -u https://example.com -r

# Lancer le spider sur un URL et télécharger récursivement les images avec profondeur spécifique
python3 spider.py -u https://example.com -r -l nombre
```

Options possibles (si implémentées)
- `-u` : URL cible
- `-p` : fichier de sortie
- `-l` : nombre de profondeur
- `-h, --help` : mode verbeux
