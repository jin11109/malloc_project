#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>

int main(int argc, char *argv[]) {
    int child = vfork();
    /*
    int fifo_fd = open("./fifo_preload", O_WRONLY);
    if (fifo_fd == -1) {
        perror("open");
        return 1;
    }

    if (dup2(fifo_fd, 2) == -1) {
        perror("dup2");
        return 1;
    }
    
    setenv("LD_PRELOAD", "/lib/mymalloc.so", 1);
    */
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
        
        setenv("LD_PRELOAD", "/lib/mymalloc.so", 1);
        execvp(argv[1], &argv[1]);

        /*
        char command[512] = "export LD_PRELOAD=$LD_PRELOAD:/lib/mymalloc.so && ";
        for (int i = 1; i < argc; i++){
            strcat(command, argv[i]);
            strcat(command, " ");
        }
        strcat(command, " 2>> ./fifo_preload");
        printf("%s\n", command);
        int err = system(command);
        */
    }
        
    //close(fifo_fd);
    
    return 0;
}