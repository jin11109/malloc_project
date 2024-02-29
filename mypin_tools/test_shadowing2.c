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
#include <stdatomic.h>

#define MEGA << 20
#define KILO << 10

int target_num = (16 MEGA);
long long int target[(16 MEGA)];
long long int pattern[(16 MEGA)];

int main(){
    srand48(time(NULL));

    printf("target start : %p\n", target);
    printf("target end : %p\n", &target[target_num - 1]);
    printf("pid : %d\n", getpid());
    printf("element num : %d\n", target_num);
    printf("size : %ld\n", sizeof(target));

    long long int n = 1;
    n = n << 34; // ~= 1.72 * 10^10
    int temp = 0;
    for (long long int i = 0; i < n; i++) {    
        int index = lrand48() % target_num;
        //temp += atomic_load_explicit(&target[index], memory_order_relaxed);
        temp += atomic_load_explicit(&pattern[index], memory_order_relaxed) + atomic_load_explicit(&target[index], memory_order_relaxed);
    }
    printf("temp : %d\n", temp);

}