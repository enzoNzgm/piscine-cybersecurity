# vaccine — explication ligne à ligne

Document de travail : à quoi sert chaque constante et chaque fonction, pourquoi
elle est écrite ainsi, et quel piège elle évite.

---

## Vue d'ensemble

Le programme suit toujours le même enchaînement :

```
parse_args()        les arguments de la ligne de commande
   |
parse_target()      URL  ->  (url sans query, dict des paramètres)
   |
baseline()          une requête normale, pour référence
   |
detect_engine()     une quote dans chaque paramètre  ->  moteur + paramètre vulnérable
   |
find_column_count() combien de colonnes, et dans quel contexte injecter
   |
enumerate_db()      base -> tables -> colonnes -> contenu
   |      \
   |       union_extract()   appelée 2 + 2×(nb de tables) fois
   |
save_report()       tout est écrit dans l'archive JSON
```

Le point important : **une seule fonction envoie des requêtes** (`send`), et
**une seule fonction extrait des données** (`union_extract`). Tout le reste
n'est que de la préparation de chaînes SQL.

---

## Les constantes

### `ERROR_SIGNATURES`

Fragments de messages d'erreur, par moteur. Sert à répondre à deux questions
d'un coup : *ce paramètre est-il injectable ?* et *quel SGBD y a-t-il derrière ?*

```python
"mysql":  ["You have an error in your SQL syntax", "MySQL server version"]
"sqlite": ["unrecognized token", "SQL logic error", "sqlite3."]
```

**Pourquoi des fragments courts ?** Le message complet de MySQL contient le
numéro de version : `...that corresponds to your MySQL server version for the
right syntax to use near ''' at line 1`. Une signature qui reprendrait la phrase
entière ne matcherait plus sur une autre installation.

**Pour ajouter un moteur**, il suffit d'ajouter une ligne ici (plus une dans
`MARKER_SQL`, `WRAP`, `GROUP` et `ENGINE_SQL`). Aucune fonction ne change.

### `MARK_A`, `MARK_B`, `MARKER`

```python
MARK_A = "qXv"
MARK_B = "q"
MARKER = "qXvq"
```

**C'est le point le plus subtil du programme.** On injecte non pas `'qXvq'` mais
`CONCAT('qXv','q')` (MySQL) ou `'qXv' || 'q'` (SQLite).

Pourquoi couper le marqueur en deux : beaucoup de sites réaffichent les
paramètres qu'ils reçoivent. Le lab le fait explicitement avec sa ligne
`debug SQL:`. Si on injectait `'qXvq'` en clair, on le retrouverait dans la page
**même quand la requête a échoué** — et on conclurait à tort que l'injection a
marché.

Avec le marqueur coupé, le payload envoyé ne contient jamais `qXvq`. Si la page
affiche `qXvq`, c'est nécessairement que **le SGBD a évalué la concaténation**.
Un réaffichage du payload ne peut pas produire ça.

C'est exactement le bug qui a été constaté pendant le développement :
`find_column_count` renvoyait `1` sur toutes les routes, parce que le marqueur
était lu dans la ligne de debug au lieu du résultat.

### `MAX_COLUMNS = 12`

Borne de la recherche du nombre de colonnes. Sans elle, une cible non injectable
ferait boucler le programme indéfiniment.

### `CONTEXTS`

```python
"-1 "           # contexte entier
"' AND 1=2 "    # contexte chaîne
```

Ce sont les deux façons d'entrer dans une requête SQL, selon que la valeur
injectée est entourée de quotes ou non.

Les deux ont la même propriété : **rendre la condition d'origine fausse**.

- `WHERE id = -1` — aucun produit n'a l'id -1
- `WHERE name LIKE '%' AND 1=2` — la quote est refermée, puis `1=2` annule tout

Conséquence : la requête d'origine ne renvoie plus aucune ligne, et **seules les
lignes du `UNION` ressortent**. Sans ça, les données volées seraient mélangées
aux vraies données du site, et impossibles à distinguer par programme.

Les contextes sont essayés dans l'ordre. Le contexte entier tenté sur un
paramètre de type chaîne ne provoque aucune erreur (il finit simplement à
l'intérieur de la chaîne), mais ne produit pas le marqueur non plus : il est
donc rejeté, et on passe au suivant.

### `MARKER_SQL` et `WRAP`

```python
MARKER_SQL["mysql"]  = "CONCAT('{a}','{b}')"              -> vaut "qXvq"
WRAP["mysql"]        = "CONCAT('{a}','{b}', {expr}, '{a}','{b}')"
```

`MARKER_SQL` sert à *sonder* (find_column_count), `WRAP` à *extraire* : il
encadre une expression de marqueurs, ce qui permet ensuite de la retrouver par
expression régulière dans le HTML.

### `ROW_SEP = "~~"`

Séparateur utilisé par `group_concat`. Le séparateur par défaut est la virgule —
mais les données dumpées peuvent contenir des virgules, et le découpage côté
Python se ferait alors au mauvais endroit. `~~` est improbable dans des données
réelles.

### `GROUP`

```python
"mysql":  "group_concat({expr} SEPARATOR '~~')"
"sqlite": "group_concat({expr}, '~~')"
```

`group_concat` existe dans les deux moteurs et fait la même chose — écraser N
lignes en une seule cellule — mais **son séparateur ne s'écrit pas pareil** :
mot-clé `SEPARATOR` chez MySQL, deuxième argument chez SQLite.

### `ENGINE_SQL`

Les requêtes d'énumération, sous forme de couples `(expression, source)` :

| | MySQL | SQLite |
|---|---|---|
| `database` | `database()` | `'main'` (SQLite n'a pas cette notion) |
| `tables` | `information_schema.tables` filtré sur `table_schema = database()` | `sqlite_master WHERE type='table'` |
| `columns` | `information_schema.columns` filtré sur le schéma **et** `table_name` | `pragma_table_info('{table}')` |

Les filtres ne sont pas décoratifs : sans `table_schema = database()`, MySQL
renvoie les centaines de tables de `information_schema`, `performance_schema` et
`mysql`. Sans `NOT LIKE 'sqlite_%'`, SQLite renvoie ses tables internes.

Il n'y a que **trois** entrées, pas quatre : la requête de dump ne peut pas être
écrite d'avance, puisqu'elle dépend des colonnes découvertes à l'exécution.

---

## Les fonctions

### `parse_target(url)`

**Entrée** : une URL. **Sortie** : `(url_sans_query, {param: valeur})`.

```python
parse_target("127.0.0.1:5000/login?user=admin&pass=x")
-> ("http://127.0.0.1:5000/login", {"user": "admin", "pass": "x"})
```

Le test `if "://" not in url` ajoute le schéma manquant. Pourquoi ce test
plutôt que `if not split_res.scheme` : `urlsplit("localhost:5000/x")` renvoie
`scheme='localhost'` — un schéma non vide mais absurde. Tester la présence de
`://` attrape les deux cas.

L'URL et les paramètres sont séparés parce que le programme passe son temps à
reconstruire l'URL avec **une seule valeur modifiée**. Travailler sur une chaîne
entière imposerait des `str.replace()` fragiles.

`parse_qsl` (et non `parse_qs`) renvoie une liste de paires, que `dict()`
convertit en `{param: valeur}`. `parse_qs` renverrait `{'user': ['admin']}`,
un dict de listes, pénible à manipuler.

### `send(url, params, method)`

**Entrée** : une cible, des paramètres, une méthode.
**Sortie** : `(corps, code_http, durée)`.

C'est le `curl` du programme. **La seule fonction qui envoie des requêtes.**

Trois propriétés à défendre :

**1. Elle ne lève jamais d'exception.** Trois issues, un seul type de retour :

| Situation | `body` | `code` |
|---|---|---|
| réponse normale | le HTML | 200, 302… |
| 4xx / 5xx (`HTTPError`) | le HTML **quand même** | 404, 500… |
| serveur injoignable (`URLError`) | `""` | `0` |

`HTTPError` n'est une erreur que du point de vue d'`urlopen` : elle possède un
`.code` et un `.read()`, donc elle se lit comme une réponse normale. C'est même
la réponse la plus intéressante, puisqu'une injection qui casse le serveur
renvoie un 500 dont le corps contient le message SQL.

Le code `0` pour `URLError` est une convention interne : aucun code HTTP réel ne
vaut 0, donc l'appelant sait sans ambiguïté que la requête n'a pas abouti. C'est
ce qui permet à `main` de tester `if code == 0` sans aucun `try/except`.

**L'ordre des `except` est obligatoire** : `HTTPError` hérite de `URLError`.
Intervertis les deux et tous les 404/500 sont avalés par la mauvaise branche,
leurs corps perdus.

**2. GET et POST partagent le même dict.** `urlencode(params)` produit la même
chaîne dans les deux cas ; seule sa destination change : query string en GET,
corps de requête en POST (converti en **bytes**, exigence d'`urlopen`).

**3. Pourquoi `urlencode` et pas une concaténation maison.** Un payload contient
des espaces, des quotes, des virgules — tous illégaux ou ambigus dans une URL.
Pire : un payload contenant `&` ou `=` serait interprété par le serveur comme un
séparateur de paramètres, et l'injection se transformerait en deux paramètres
bidons. `urlencode` échappe tout, et préserve notamment **l'espace final du
`-- `** (encodé `+`), sans lequel MySQL ne reconnaît pas le commentaire.

`timeout=10` évite qu'une cible lente fige le programme.

### `baseline(url, params, method)`

Un appel à `send` avec les paramètres d'origine, non modifiés. Techniquement un
alias ; son rôle est de **nommer le concept** de réponse de référence.
Supprimable sans conséquence.

### `detect_engine(url, params, method)`

**Sortie** : `{"engine", "param", "payload"}` au premier succès, `None` sinon.

Pour chaque paramètre : ajouter une quote à sa valeur, envoyer, chercher une
signature dans la réponse.

**Pourquoi une simple quote ?** Elle casse les deux contextes. En contexte
chaîne elle déséquilibre les quotes ; en contexte entier c'est un caractère
illégal. Dans les deux cas, erreur de syntaxe. C'est la sonde universelle.

**La ligne critique :**

```python
test = dict(params)      # une COPIE
test[name] = payload
```

Avec `params[name] = payload`, le dict d'origine serait modifié. Au tour
suivant, le paramètre précédent porterait encore son payload : on enverrait
`user=admin'&pass=x'` et on ne saurait plus lequel des deux a déclenché
l'erreur. Aucun plantage, mais tous les résultats faux.

**`None` ne veut pas dire « pas vulnérable »**, mais « pas d'error-based ». Une
cible qui masque ses erreurs reste attaquable autrement.

**Limite assumée** : la fonction s'arrête au premier paramètre trouvé. Sur
`/login`, elle trouve `user` et ne teste jamais `pass`, qui est vulnérable
aussi.

### `union_payload(context, columns, source="")`

Assemble un payload complet :

```
"-1 " + "UNION SELECT " + "CONCAT('qXv','q'), CONCAT('qXv','q')" + " FROM users" + " -- "
```

Un seul endroit fabrique les payloads : l'ordre des morceaux et le `-- ` final
n'existent qu'ici.

**L'espace après `--` est obligatoire.** MySQL exige un caractère blanc après
les deux tirets, sinon il lit deux opérateurs moins et la requête casse. SQLite
l'accepte sans, mais on écrit toujours avec pour rester portable.

### `find_column_count(url, params, method, param, engine)`

**Sortie** : `(nombre, contexte)` ou `(0, None)`.

Double boucle : pour chaque contexte, pour un nombre croissant de colonnes,
injecter le marqueur autant de fois et regarder s'il ressort.

**Pourquoi `UNION SELECT <marqueur>` et pas `ORDER BY n` ?** Les deux permettent
de trouver le nombre de colonnes, mais :

- `ORDER BY n` ne donne qu'un signal **négatif** : quand le compte est bon, la
  page est identique à la normale. Le seul indice est « ça a cassé » au-delà. Si
  le site masque ses erreurs et réaffiche une page d'apparence normale, il n'y a
  plus rien à observer.
- `UNION SELECT <marqueur>` donne un signal **positif** : quand le compte est
  bon, du contenu nouveau apparaît. Aucun message d'erreur nécessaire.

**Pourquoi renvoyer aussi le contexte ?** Parce que `union_extract` a besoin du
**même** préfixe. Le nombre de colonnes et le contexte décrivent ensemble
« comment injecter ici » ; les séparer obligerait à redécouvrir le contexte à
chaque extraction.

### `union_extract(url, params, method, param, count, context, engine, expression, source="")`

**Le cœur du programme.** Entrée : une expression SQL. Sortie : la liste des
valeurs qu'elle a produites.

```python
union_extract(..., "database()")
-> ["shop"]

union_extract(..., "group_concat(table_name SEPARATOR '~~')",
                   "FROM information_schema.tables WHERE table_schema = database()")
-> ["products~~users"]
```

**L'expression est placée dans *toutes* les colonnes** (`[marked] * count`).
Ainsi, peu importe laquelle la page affiche : pas besoin de chercher la
« colonne réfléchie » par sondages successifs. Une requête au lieu de N.
Limite : cela suppose un moteur tolérant sur les types de colonnes, ce qui est
vrai pour MySQL et SQLite mais pas pour Oracle ou SQL Server.

**L'extraction** :

```python
re.findall(MARKER + "(.*?)" + MARKER, body, re.S)
```

`(.*?)` est non-gourmand : sans le `?`, une seule capture avalerait tout ce qui
sépare le premier et le dernier marqueur de la page. `re.S` autorise `.` à
matcher les retours à la ligne, indispensable pour des valeurs multilignes.

Le dédoublonnage conserve l'ordre : la même valeur revient une fois par colonne
affichée, et l'ordre a un sens (celui du `group_concat`).

**Cette fonction ne connaît ni `information_schema`, ni `sqlite_master`, ni
`users`.** Elle prend une expression et rend des chaînes. C'est ce qui permet à
toute l'énumération de tenir dans quelques appels.

### `grouped(engine, expression)`

Enveloppe une expression dans un `group_concat` avec le bon séparateur et la
bonne syntaxe selon le moteur. Transforme N lignes en une seule cellule — donc
**une requête au lieu d'une par ligne**.

### `row_expression(engine, columns)`

Concatène les colonnes d'une ligne en `"1:admin:s3cr3t"`.

```python
mysql  -> CONCAT_WS(':', id, username, password)
sqlite -> IFNULL(id,'') || ':' || IFNULL(username,'') || ':' || IFNULL(password,'')
```

**Pourquoi `IFNULL` côté SQLite ?** Parce que `NULL || 'x'` vaut `NULL` : une
seule colonne vide suffirait à annuler la ligne entière, qui disparaîtrait
silencieusement du dump. `CONCAT_WS` de MySQL ignore les NULL nativement, d'où
l'asymétrie.

### `enumerate_db(url, params, method, param, count, context, engine)`

Enchaîne les appels à `union_extract` : nom de base, puis tables, puis pour
chaque table ses colonnes, puis son contenu.

Nombre de requêtes HTTP : `2 + 2 × nombre_de_tables`.

`target` regroupe les sept paramètres communs pour éviter de les réécrire à
chaque appel (`union_extract(*target, expression, source)`).

Le `{table}` des requêtes `columns` est rempli à l'exécution par
`source.format(table=table)`.

**Sortie** : un dict imbriqué, directement sérialisable en JSON :

```python
{"database": "shop",
 "tables": {"users": {"columns": ["id","username","password"],
                      "rows": ["1:admin:s3cr3t", ...]}}}
```

### `save_report(path, report)`

Lit l'archive existante, ajoute le rapport, réécrit le tout.

Le `os.path.exists` répond littéralement à l'exigence du sujet : le fichier est
créé au premier run s'il n'existe pas.

Le `try/except (ValueError, OSError)` couvre l'archive corrompue ou illisible :
on repart d'une liste vide plutôt que de planter. **Le programme ne doit jamais
mourir à cause de son propre fichier de sortie.**

**L'archive est une liste**, pas un objet : elle s'accumule d'un run à l'autre,
chaque entrée horodatée. C'est le sens de « storage file for the data » — un
historique, pas un écrasement.

### `finish(path, report, status)`

Écrit l'archive puis renvoie le code de sortie. Trois lignes qui évitent de
répéter `save_report` avant chacune des cinq sorties de `main`.

Sans ce raccourci, il serait facile d'oublier un chemin de sortie — et le
fichier ne serait pas créé dans ce cas précis, justement celui que le correcteur
teste.

### `parse_args()`

`-o` devient `args.o`, `-X` devient `args.X` (argparse prend la lettre comme
nom). `choices=["GET","POST"]` refuse toute autre méthode avec un message
propre, et documente dans le `-h` que les deux méthodes exigées sont gérées.

### `main()`

Orchestration et affichage. **Aucun calcul, aucune requête directe.**

Le rapport est construit progressivement et enrichi à chaque étape
(`report.update(found)` insère directement le dict de `detect_engine` — c'est
pourquoi cette fonction renvoie un dict et non un tuple).

Toutes les sorties passent par `finish`, donc l'archive est écrite dans tous les
cas, y compris quand rien n'est trouvé (`"vulnerable": false`).

Codes de retour : `0` si le scan s'est déroulé, `1` si la cible est inutilisable
(aucun paramètre, ou injoignable). `sys.exit(main())` les transmet au shell.

---

## Questions probables en soutenance

**« Pourquoi le marqueur est-il coupé en deux ? »**
Pour distinguer une donnée venue de la base d'un simple réaffichage du payload.
Le payload ne contient jamais le marqueur entier ; seul le SGBD peut le
reconstituer.

**« Pourquoi `dict(params)` et pas `params` ? »**
Pour ne pas polluer le dict d'origine. Sans la copie, les payloads
s'accumuleraient d'un paramètre à l'autre et les résultats seraient faux sans
aucun plantage.

**« Pourquoi `send` n'a-t-elle qu'un seul `return` ? »**
Pour que l'appelant n'ait jamais à gérer d'exception ni à savoir si on est en
GET ou en POST. Les trois issues possibles sont normalisées en un seul type de
retour.

**« Comment ajouterais-tu PostgreSQL ? »**
Une entrée dans `ERROR_SIGNATURES` (`unterminated quoted string`), `MARKER_SQL`,
`WRAP`, `GROUP` (`string_agg`) et `ENGINE_SQL` (`information_schema`, comme
MySQL). Aucune fonction à modifier.

**« Que se passe-t-il si le site masque ses erreurs SQL ? »**
`detect_engine` renvoie `None` et le programme s'arrête là. C'est une limite
documentée : il faudrait une détection boolean-based ou time-based, qui ne
repose pas sur les messages d'erreur. `find_column_count`, lui, fonctionnerait
encore, puisqu'il s'appuie sur un signal positif.

**« Pourquoi `-1` et `AND 1=2` ? »**
Pour rendre la condition d'origine fausse et ne laisser remonter que les lignes
du `UNION`. Sans ça, les données extraites seraient mélangées aux données
légitimes du site.
