
#define _GNU_SOURCE

#include <stdio.h>
#include <time.h>
#include <sys/time.h>

int main() {
    /*
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) == -1) {
        perror("clock_gettime");
        return -1;
    }

    long long microseconds = ts.tv_sec * 1000000 + ts.tv_nsec / 1000;
    */
    struct timeval t;
    gettimeofday(&t, NULL);
    unsigned long long microseconds = t.tv_sec * 1000000 + t.tv_usec;

    FILE* file = fopen("./data/starttime", "w");
    fprintf(file, "%lld\n", microseconds);

    return 0;
}