#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
int main(int argc, char *argv[]) {

    setenv("LD_PRELOAD", "/lib/mymalloc.so", 1);

    if (execvp(argv[1], &argv[1]) == -1) {
        perror("execvp");
        return 1;
    }

    return 0;
}