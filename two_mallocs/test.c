// export LD_LIBRARY_PATH="./ptmalloc2_with_cold/:$LD_LIBRARY_PATH"
// export LD_PRELOAD="./mymalloc_with_cold.so"
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>
int main(int argc, char *argv[]){
    pid_t child = fork();
    if (child != 0){
        wait(NULL);
    }else {
        setenv("LD_PRELOAD", "/lib/mymalloc_with_cold.so", 1);
        setenv("LD_LIBRARY_PATH", "./ptmalloc2_with_cold/:$LD_LIBRARY_PATH", 1);
        setenv("LD_LIBRARY_PATH", "./ptmalloc2_with_cold_2/:$LD_LIBRARY_PATH", 1);
        //setenv("LD_PRELOAD", "./ptmalloc2/malloc.so", 1);
        execvp(argv[1], &argv[1]);
    }

}