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



int main(){
    int target = 0;
    int patten = 0;
    int temp = 0;
    printf("target address : %p\n", &target);
    //printf("temp address : %p\n", &temp);
    printf("pid : %d\n", getpid());

    long long int i = 0;
    long long int n = 5000000000;
    //printf("i address : %p\n", &i);
    //printf("n address : %p\n", &n);

    for (; i < n; i++) {
        temp += target;
        temp += patten;
        temp += patten;
        temp += patten;

        temp += patten;
        temp += patten;
        temp += patten;
        temp += patten;

        temp += patten;
        temp += patten;
        temp += patten;
        temp += patten;

        temp += patten;
        temp += patten;
        temp += patten;
        temp += patten;
    }
}