
#define _GNU_SOURCE

#include <stdio.h>
#include <time.h>
#include <sys/time.h>

int main(int argc, char** argv) {
    struct timeval t;
    gettimeofday(&t, NULL);
    unsigned long long microseconds = t.tv_sec * 1000000 + t.tv_usec;

    FILE* file = fopen(argv[1], "w");
    fprintf(file, "%llu\n", microseconds);

    return 0;
}