#define _GNU_SOURCE
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

int target_num = 1000;
int target[1000];

// yield [0, n) rand number
int randint(int n) {
    if ((n - 1) == RAND_MAX) {
        return rand();
    } else {
        long end = RAND_MAX / n;
        assert(end > 0L);
        end *= n;

        // discard the value exceed end
        int r;
        while ((r = rand()) >= end)
            ;

        return r % n;
    }
}

int main(){
    srand(5);
    printf("target start : %p\n", target);
    printf("target end : %p\n", target + target_num);
    printf("pid : %d\n", getpid());

    long long int n = 100000;
    for (long long int i = 0; i < n; i++) {
        for (long long int j = 0; j < n; j++) {
            target[randint(target_num)]++;
        }
    }

    
}

/*
int main() {
    srand(5);
    int target_num = 1000;
    int* target = malloc(sizeof(int) * target_num);
    memset(target, 0, sizeof(int) * target_num);

    pid_t child = fork();
    if (child == 0) {
        long long int n = 200000;
        for (long long int i = 0; i < n; i++) {
            for (long long int j = 0; j < n; j++) {
                target[randint(target_num)]++;
            }
        }

    } else {
        printf("target start : %p\n", target);
        printf("target end : %p\n", target + target_num);
        printf("pid : %d\n", child);

        char pid_str[100];
        sprintf(pid_str, "%d", child);
        
        char* perf_command[128] = {
            "perf", "record",         "-e",     "ibs_op//", "-F",
            "max",  "--running-time", "--data", "-p",       pid_str};

        
        char* perf_command[128] = {
            "perf",         "stat", "-e",
            "instructions", "-p",   pid_str};

        execvp(perf_command[0], perf_command);

        wait(NULL);
    }
}
*/