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
int target[10000];

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
    printf("element num : %d\n", target_num);

    long long int n = 10000000000;
    int temp = 0;
    for (long long int i = 0; i < n; i++) {    
        temp += target[randint(target_num)];
    }   
}