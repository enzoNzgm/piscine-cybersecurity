# ft_otp

Description
- Exécutable `ft_otp` pour un exercice lié à OTP (one-time password) et fichiers de clé.

Prérequis
- Exécutable binaire fourni
- Si implémenté en Python, vérifier `python3` et dépendances

Contenu
- `ft_otp` : exécutable
- `ft_otp.key`, `key.txt` : fichiers de clés/support

Installation
- Rendre exécutable si nécessaire :

```bash
chmod +x ft_otp
```

Usage
- Vérifier l'aide intégrée :

```bash
./ft_otp --help
```

- Commandes courantes (si implémentées) :

```bash
# Spécifier un fichier de clé
./ft_otp -k key.txt

# Mode verbeux
./ft_otp --verbose
```

Conseils
- Ne partagez pas `key.txt` si elle contient des secrets.

