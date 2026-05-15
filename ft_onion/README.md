# FT_ONION

![Tor Badge](https://img.shields.io/badge/Network-Tor-purple)

Petit guide pour héberger un site web accessible uniquement via le réseau Tor (adresse .onion).

## Description

Ce projet montre une configuration minimale pour déployer une page statique via **Nginx** et rendre le service disponible uniquement sur le réseau Tor en utilisant un *Hidden Service*.

Le stack utilisé :
- Tor (service caché)
- Nginx (serveur HTTP)
- SSH (administration)

La page d'exemple affiche une simple balise :

```html
<h1>My Website with .onion</h1>
```

## Table des matières

- Installation
- Configuration Tor
- Configuration Nginx
- Vérifications & logs
- Dépannage

## Prérequis

- Distribution Linux avec systemd
- `tor`, `nginx`, `openssh-server` installés
- Accès `sudo`

## Installation rapide

1. Créer l'arborescence du site :

```bash
sudo mkdir -p /var/www/onion
sudo chown -R $USER:www-data /var/www/onion
```

2. Déposer la page HTML dans `/var/www/onion/index.html`.

## Configuration Tor (Hidden Service)

Ajouter dans `/etc/tor/torrc` :

```text
HiddenServiceDir /var/lib/tor/hidden_service/
HiddenServicePort 80 127.0.0.1:80
```

Puis redémarrer Tor :

```bash
sudo systemctl restart tor
```

Récupérer l'adresse .onion :

```bash
sudo cat /var/lib/tor/hidden_service/hostname
```

## Configuration Nginx

Éditez le site (ex : `/etc/nginx/sites-available/default`) pour pointer sur `/var/www/onion` :

```nginx
server {
    listen 80 default_server;
    server_name _;
    root /var/www/onion;
    index index.html;
}
```

Redémarrer Nginx :

```bash
sudo systemctl restart nginx
```

## Vérifications utiles

- Vérifier les ports ouverts :

```bash
sudo ss -tulpn
```

- Tester Nginx en local :

```bash
curl -I http://127.0.0.1
```

- Voir les logs Nginx :

```bash
sudo tail -n 200 /var/log/nginx/access.log
sudo tail -n 200 /var/log/nginx/error.log
```

- Voir les logs Tor :

```bash
sudo journalctl -u tor -f
```

## Dépannage

- Si l'adresse .onion n'apparaît pas, vérifier les permissions du dossier `HiddenServiceDir` et relancer Tor.
- S'assurer que Nginx écoute bien sur `127.0.0.1:80` si Tor est configuré de cette façon.

