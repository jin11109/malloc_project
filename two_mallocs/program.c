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
        int fifo_fd = open("./fifo_preload", O_WRONLY);
        if (fifo_fd == -1) {
            perror("open");
            return 1;
        }

        if (dup2(fifo_fd, 2) == -1) {
            perror("dup2");
            return 1;
        }
        
        setenv("LD_PRELOAD", "/lib/mymalloc_with_cold.so", 1);
        setenv("LD_LIBRARY_PATH", "./ptmalloc2_with_cold/:$LD_LIBRARY_PATH", 1);     
        execvp(argv[1], &argv[1]);

    }
    
    return 0;
}