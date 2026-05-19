# reverse_me

Description
- Collection de challenges de reverse engineering : binaires, sources C et fichiers ASM.

Prérequis
- Outils recommandés : `gcc`, `objdump`, `gdb`, `radare2`/`r2`, `strings`, `ltrace`, `strace`

Contenu
- `a.out` : binaire de test
- `binary/` : niveaux et fichiers ASM
- `level1/`, `level2/` : sources, mots de passe et instructions

- Extraire les chaînes :

```bash
strings a.out | less
```

- Désassembler :

```bash
objdump -d a.out | less
```

- Lancer en debug :

```bash
gdb --args ./a.out
```

## Méthode conseillée

Pour chaque niveau, garder la même logique d'analyse :

1. Commencer par `strings` pour repérer d'éventuels indices déjà présents dans le binaire.
2. Utiliser `objdump` ou `gdb` pour lire le code assembleur et comprendre le flux d'exécution.
3. Si une fonction sensible comme `strcmp` apparaît, lancer `ltrace` pour observer les appels en temps réel.
4. Compléter avec des outils comme `dogbolt` quand une comparaison avec d'autres désassemblages peut aider.

```bash
strings a.out | less
objdump -d a.out | less
gdb --args ./a.out
ltrace ./a.out
```

## Notes par niveau

### Level 1

- Commencer par chercher des chaînes intéressantes avec `strings`.
- Examiner le désassemblage avec `objdump` et vérifier le comportement dans `gdb`.
- Si la logique repose sur `strcmp`, `ltrace` permet de suivre les comparaisons plus facilement.

### Level 2

- Reprendre la même méthode que pour le niveau 1.
- Ajouter `dogbolt` si le besoin est d'obtenir une vue croisée ou de comparer plusieurs désassemblages.

## Compilation

Pour compiler une source C :

```bash
gcc source.c -o levelX
```
