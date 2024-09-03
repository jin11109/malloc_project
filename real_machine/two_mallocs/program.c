#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>

int main(int argc, char *argv[]) {
    int child = vfork();
    
    if (child != 0){
        wait(NULL);
    }else {        
        setenv("LD_PRELOAD", "/lib/mymalloc_with_cold.so", 1);
        execvp(argv[1], &argv[1]);

    }
    
    return 0;
}