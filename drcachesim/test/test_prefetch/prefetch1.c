/*
 * test prefetch misses
 */
#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>

#define ARRAY_SIZE 100000
#define STRIDE 4096

int main() {
    int64_t *array = malloc(ARRAY_SIZE * sizeof(int64_t));
    int64_t sum = 0;

    printf("array %p\n", array);

    __builtin_prefetch(&array[0 + 2 * STRIDE], 0, 0);
    sum += array[0];

    printf("Sum: %ld \n", sum);

    free(array);
    return 0;
}
