/*
    編譯 mymalloc_with_cold.c，使用動態庫 libptmalloc2_with_cold.so
    1. 編譯成.o
        $gcc -g -c mymalloc_with_cold.c -I./ptmalloc2_with_cold/
    2. 編譯成執行檔
        $gcc ./mymalloc_with_cold.o -L./ptmalloc2_with_cold/ -lptmalloc2_with_cold -o ./mymalloc_with_cold
    使用
        $export LD_LIBRARY_PATH=./ptmalloc2_with_cold/:$LD_LIBRARY_PATH
*/
/*
    gcc -fPIC -g -c mymalloc_with_cold.c -I./ptmalloc2_with_cold/
    gcc -shared ./mymalloc_with_cold.o -L./ptmalloc2_with_cold/ -lptmalloc2_with_cold -o ./mymalloc_with_cold.so
*/

// export LD_LIBRARY_PATH="./ptmalloc2_with_cold/:$LD_LIBRARY_PATH"
// export LD_PRELOAD="./mymalloc_with_cold.so"

#define _GNU_SOURCE
#include <stdio.h>
#include <unistd.h>
#include <stdint.h>
#include <dlfcn.h>
#include "ptmalloc2_with_cold/_my_malloc.h"

/*============================ prelaod functions ============================
 *==========================================================================*/

void* malloc(size_t bytes) {
    void* ptr = _my_malloc(bytes);
    void* return_addr = __builtin_extract_return_addr(__builtin_return_address(
        0)); // value of 0 yields return address of the current function
    if (bytes == 0 || is_flag_mmaped(ptr)) {
        return unable_flag(ptr);
    }

    fprintf(stderr, "mya %d %ld %p %p %c\n", getpid(), bytes, ptr, return_addr, 'm');

    return ptr;
}

void* realloc(void* addr, size_t size) {
    void* ptr = _my_realloc(addr, size);
    void* return_addr = __builtin_extract_return_addr(__builtin_return_address(
        0)); // value of 0 yields return address of the current function
    if (is_flag_notmy(ptr)) {
        void* orig_free = dlsym(RTLD_NEXT, "realloc");
        return ((void* (*)(void*, size_t))orig_free)(addr, size);
    }
    if (is_flag_mmaped(ptr)) {
        return unable_flag(ptr);
    }

    fprintf(stderr, "mya %d %ld %p %p %c\n", getpid(), size, ptr, return_addr, 'r');
    
    return ptr;
}

void* calloc(size_t nmemb, size_t size) {
    void* ptr = _my_calloc(nmemb, size);
    void* return_addr = __builtin_extract_return_addr(__builtin_return_address(
        0)); // value of 0 yields return address of the current function
    if (size * nmemb == 0 | is_flag_mmaped(ptr)) {
        return unable_flag(ptr);
    }

    fprintf(stderr, "mya %d %ld %p %p %c\n", getpid(), size, ptr, return_addr, 'c');
    
    return ptr;
}

void free(void* addr) {
    void* ptr = _my_free(addr);
    if (!is_flag_notmy(ptr)) { // this represent to successfully free the memory by _my_free
        return ;
    } else { // call original free to process this memory
        void* orig_free = dlsym(RTLD_NEXT, "free");
        ((void (*)(void*))orig_free)(addr);
    }
    
}

void cfree(void* addr) {
    free(addr);
    return;
}
/*
void* memalign(size_t alignment, size_t size) {
    void* ptr = _my_memalign(alignment, size);
    return ptr;
}

void* valloc(size_t size) {
    void* ptr = _my_valloc(size);
    return ptr;
}

void* pvalloc(size_t size) {
    void* ptr = _my_pvalloc(size);
    return ptr;
}
*/

/*
void* __default_morecore(ptrdiff_t size) {
    return _my___default_morecore(size);
}

int mallopt(int __param, int __val) {
    return _my_mallopt(__param, __val);
}

int malloc_trim (size_t __pad) {
    return _my_malloc_trim(__pad);
}

size_t malloc_usable_size (void* __ptr) {
    return _my_malloc_usable_size(__ptr);
}

void malloc_stats (void) {
    _my_malloc_stats();
}

void* malloc_get_state(void) {
    return _my_malloc_get_state();
}

int malloc_set_state(void* __ptr) {
    return _my_malloc_set_state(__ptr);
}

void __malloc_check_init(void) {
    _my___malloc_check_init();
}

_my_mstate _int_new_arena(size_t __ini_size) {
    return _my__int_new_arena(__ini_size);
}

void* _int_malloc(_my_mstate __m, size_t __size) {
    return _my__int_malloc(__m, __size);
}

void _int_free(_my_mstate __m, void* __ptr) {
    return _my__int_free(__m, __ptr);
}

void* _int_realloc(_my_mstate __m, void* __ptr, size_t __size) {
    return _my__int_realloc(__m, __ptr, __size);
}

void* _int_memalign(_my_mstate __m, size_t __alignment, size_t __size) {
    return _my__int_memalign(__m, __alignment, __size);
}

_my_mstate _int_get_arena(int __n) {
    return _my__int_get_arena(__n);
}

void _int_get_arena_info
(_my_mstate __m, struct _my_malloc_arena_info *__ma) {
    return _my__int_get_arena_info(__m, __ma);
}

void _int_get_global_info(struct _my_malloc_global_info *__m) {
    return _int_get_global_info(__m);
}

int __posix_memalign (void **memptr, size_t alignment, size_t size) {
    return _my___posix_memalign(memptr, alignment, size);
}
*/