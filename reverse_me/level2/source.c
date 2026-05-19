#include <stdio.h>
#include <string.h>
#include <stdlib.h>

void no(void)

{
  puts("Nope.");
  exit(1);
}

void ok(void)

{
  puts("Good job.");
  return;
}

int main(void)
{
    char input[24];              // clé entrée par l'utilisateur
    char decoded[9];             // chaîne décodée (max 8 + '\0')
    int scan_result;

    int decoded_index = 1;       // position dans decoded
    unsigned int step = 2;

    printf("Please enter key: ");
    scan_result = scanf("%23s", input);

    if (scan_result != 1) {
        no();
    }

    // Vérification du préfixe "00"
    if (input[0] != '0' || input[1] != '0') {
        no();
    }

    fflush(stdin);

    // Initialisation de la chaîne décodée
    memset(decoded, 0, sizeof(decoded));
    decoded[0] = 'd'; // premier caractère fixé

    // Boucle de décodage
    while (strlen(decoded) < 8 && step < strlen(input)) {

        char buffer[4] = {0};

        // On récupère 3 caractères
        buffer[0] = input[step];
        buffer[1] = input[step + 1];
        buffer[2] = input[step + 2];
        buffer[3] = '\0';

        // Conversion en entier puis en caractère ASCII
        int value = atoi(buffer);
        decoded[decoded_index] = (char)value;

        // Incréments
        step += 3;
        decoded_index++;
    }

    decoded[decoded_index] = '\0';

    // Comparaison finale
    if (strcmp(decoded, "delabere") == 0) {
        ok();
    } else {
        no();
    }

    return 0;
}