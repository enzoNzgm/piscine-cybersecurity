# vaccine

Detecteur d'injections SQL. On lui donne une URL avec ses parametres, il teste
chacun d'eux et, si l'un est vulnerable, il extrait le contenu de la base.

Python 3, **aucune dependance** : uniquement la bibliotheque standard.

## Utilisation

    ./vaccine [-o FICHIER] [-X METHODE] URL

| Option | Role | Defaut |
|---|---|---|
| `-o` | fichier d'archive des resultats | `vaccine.json` |
| `-X` | methode HTTP : `GET` ou `POST` | `GET` |

Les parametres a tester sont ceux de l'URL. En `POST`, ils sont envoyes dans le
corps de la requete au lieu de la query string.

    ./vaccine "http://127.0.0.1:5000/product?id=1"
    ./vaccine -X POST "http://127.0.0.1:5000/login?user=admin&pass=x"

Aucune configuration n'est necessaire.

## Exemple

```
$ ./vaccine "http://127.0.0.1:5000/search?name=a"
[*] cible      : http://127.0.0.1:5000/search
[*] methode    : GET
[*] parametres : name
[*] archive    : vaccine.json
[*] baseline   : 200, 158 octets, 0.010s
[+] moteur     : mysql
[+] parametre  : name
[+] payload    : a'
[+] colonnes   : 3
[+] contexte   : "' AND 1=2"
[+] base       : shop

    [products]  colonnes : id, name, price
      1:Keyboard:49
      2:Mouse:19
      3:Screen:199

    [users]  colonnes : id, username, password
      1:admin:s3cr3t
      2:enzo:hunter2
      3:guest:guest
```

## Fonctionnement

1. **Baseline** — une requete avec les parametres d'origine sert de reference.
2. **Detection (error-based)** — une quote est ajoutee a chaque parametre ; le
   message d'erreur renvoye identifie a la fois le parametre vulnerable et le
   moteur de base de donnees.
3. **Contexte et colonnes** — un marqueur coupe en deux (`'qXv' || 'q'`) est
   injecte dans un nombre croissant de colonnes. Le voir reapparaitre dans la
   page prouve que le `UNION` est passe : le moteur a recolle les morceaux, ce
   qu'un simple reaffichage du payload ne pourrait pas faire.
4. **Exploitation (UNION-based)** — nom de la base, tables, colonnes, puis
   contenu de chaque table.

### Moteurs supportes

| | MySQL | SQLite |
|---|---|---|
| Nom de la base | `database()` | `main` |
| Tables | `information_schema.tables` | `sqlite_master` |
| Colonnes | `information_schema.columns` | `pragma_table_info()` |
| Concatenation | `CONCAT_WS` | `\|\|` |
| Separateur `group_concat` | `SEPARATOR '~~'` | `, '~~'` |

Ajouter un moteur = ajouter une entree dans `ERROR_SIGNATURES`, `MARKER_SQL`,
`WRAP`, `GROUP` et `ENGINE_SQL`. Aucune fonction n'est a modifier.

### Techniques

- **error-based** : detection du parametre vulnerable et du moteur
- **UNION-based** : extraction des donnees

Contextes d'injection geres : entier (`-1 ...`) et chaine (`' AND 1=2 ...`).

## Tests

Le dossier `lab/` contient une application volontairement vulnerable servant de
cible. Voir `lab/README.md`.

    cd lab
    ./run.sh          # SQLite
    ./run.sh mysql    # MySQL

Elle expose trois points d'injection : `/product?id=1` (GET, contexte entier),
`/search?name=a` (GET, contexte chaine) et `/login` (POST, contexte chaine).
