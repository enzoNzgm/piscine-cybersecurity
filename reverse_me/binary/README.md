# reverse_me/binary

Description
- Contient plusieurs niveaux (exécutables et fichiers ASM) destinés au reverse engineering.

Fichiers principaux
- `level1`, `level1.asm`, `level2`, `level2.asm`, `level3`.

Usage et analyse
- Ne pas exécuter directement les binaires sur la machine hôte ; utiliser VM/containérisation.

Commandes utiles :

```bash
# Obtenir les chaînes
strings level1 | less

# Désassembler
objdump -d level1 | less

# Lancer en debug
gdb --args ./level1
```

Pour les fichiers ASM, ouvrez-les dans un éditeur ou assemblez-les si nécessaire.

