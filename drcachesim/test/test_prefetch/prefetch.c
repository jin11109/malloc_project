/*
 * test if prefetch cause cachemisses
 */
#include <stdio.h>
#include <stdlib.h>

typedef struct{
    int a[1024];
} test_data_t;

int main() {
    test_data_t* data = malloc(sizeof(test_data_t));
    
    __builtin_prefetch(&data, 0, 0);
    
    free(data);
    return 0;
}