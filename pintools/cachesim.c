#include <stdio.h>

int main() {
    FILE *file;
    char line[256];

    file = fopen("./fifo_pintools", "r");
    if (file == NULL) {
        perror("Failed to open file");
        return 1;
    }

    while (fgets(line, sizeof(line), file) != NULL) {
        printf("%s", line);
    }

    fclose(file);
    return 0;
}