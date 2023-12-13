#define _GNU_SOURCE
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
/*
int main() {
    pid_t child = fork();
    int* flag1 = mmap(NULL, sizeof(int), PROT_READ | PROT_WRITE | PROT_EXEC,
                      MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
    int* flag2 = mmap(NULL, sizeof(int), PROT_READ | PROT_WRITE | PROT_EXEC,
                      MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
    *flag1 = 1;
    *flag2 = 0;

    if (child == 0) {
        int target = 0;
        printf("target address : %d\n", &target);
        while (*flag1) {
            while (*flag2) {
                target++;
            }
        }
    } 
    else {
        pid_t child2 = fork();
        if (child2 == 0) {
            int test_round = 100;
            for (int i = 0; i < test_round; i++){
                for (int j = 0; j < 180; j++){
                    sleep(1);
                    double sleep_time =
                }
            }
        } 
        else {
            char pid_str[100];
            printf("pid = %d\n", child);
            sprintf(pid_str, "%d", child);
            char* perf_command[128] = {
                "perf", "record", "-e", "ibs_op//", "-F",
                "max",  "--running-time", "--data", "-p", pid_str};
            wait(NULL);
            wait(NULL);
        }
    }
}
*/


int main(){
    int child = fork();

    if (child == 0){
        int data_access[10];
        memset(data_access, 0, sizeof(data_access));
        printf("target %p ~ %p\n", data_access, data_access + sizeof(data_access));

        struct timespec t, star_time, last_time;
        clock_gettime(CLOCK_REALTIME, &star_time);

        int rounds = 100;
        last_time = star_time;
        double last_angle = 0;
        for (int i = 0; i < rounds; i++){
            for (int j = 0; j < 180; j++){
                double angle = (double)j / 180 * 3.1415926;
                long int sleep_time = 100000 * (sin(angle));
                usleep(sleep_time);
                for (int k = 0; k < 100000; k++){
                    data_access[0]++;
                }
            }
            printf("round %d finish\n", i);
        }
    }
    else{

        char pid_str[100];
        printf("pid = %d\n", child);
        sprintf(pid_str, "%d", child);
        char* perf_command[128] = {
            "perf",
            "record",
            "-e",
            "ibs_op//",
            "-F",
            "max",
            "--running-time",
            "--data",
            "-p",
            pid_str
        };
        execvp(perf_command[0], perf_command);

        wait(NULL);


    }


}
