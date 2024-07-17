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
/* for using lock */
#include <pthread.h>
/* include "_my_" version of ptmalloc2 */
#include "ptmalloc2_with_cold/_my_malloc.h"
/* include for array of cold mallocs' address */
#include "cold_addrs.h"

#define PAGESIZE 4096
#define is_cold(p) (cold_addrs[(((uintptr_t)(p)) & (PAGESIZE - 1))])

/*======================= init functions and pointers =======================
 *==========================================================================*/

static pthread_mutex_t init_mutex = PTHREAD_MUTEX_INITIALIZER;
static void init_dlsym_hook();
static void* (*orig_malloc)(size_t);
static void* (*orig_realloc)(void*, size_t);
static void* (*orig_calloc)(size_t, size_t);
static void (*orig_free)(void*);
static void (*init_dlsym)(void) = init_dlsym_hook;

static void init_dlsym_hook() {
    orig_malloc = dlsym(RTLD_NEXT, "malloc");
    orig_calloc = dlsym(RTLD_NEXT, "calloc");
    orig_realloc = dlsym(RTLD_NEXT, "realloc");
    orig_free = dlsym(RTLD_NEXT, "free");
    init_dlsym = NULL;
    fprintf(stderr, "ok\n");
}

/*============================ prelaod functions ============================
 *==========================================================================*/

void* malloc(size_t bytes) {
    if (init_dlsym) {
        if (!pthread_mutex_trylock(&init_mutex)){
            init_dlsym();
            pthread_mutex_unlock(&init_mutex);
        } else {
            pthread_mutex_lock(&init_mutex);
            pthread_mutex_unlock(&init_mutex);
        }
    }

    void* return_addr = __builtin_extract_return_addr(__builtin_return_address(
        0)); // value of 0 yields return address of the current function
    if (is_cold(return_addr)) {
        void* ptr = _my_malloc(bytes);
        if (bytes == 0 || is_flag_mmaped(ptr)) {
            return unable_flag(ptr);
        }
        fprintf(stderr, "mya %d %lu %p %p %c\n", getpid(), bytes, ptr, return_addr, 'm');
        return ptr;

    } else {
        return (orig_malloc)(bytes);
    }
}

void* realloc(void* addr, size_t size) {
    if (init_dlsym) {
        if (!pthread_mutex_trylock(&init_mutex)){
            //fprintf(stderr, "ok\n");
            init_dlsym();
            pthread_mutex_unlock(&init_mutex);
        } else {
            pthread_mutex_lock(&init_mutex);
            pthread_mutex_unlock(&init_mutex);
        }
    }

    void* return_addr = __builtin_extract_return_addr(__builtin_return_address(
        0)); // value of 0 yields return address of the current function

    void* ptr = _my_realloc(addr, size);
    if (is_flag_notmy(ptr)) {
        return (orig_realloc)(addr, size);
    }
    if (is_flag_mmaped(ptr)) {
        return unable_flag(ptr);
    }
    // Is mine, and not mmapped
    fprintf(stderr, "mya %d %lu %p %p %c\n", getpid(), size, ptr, return_addr, 'r');
    return ptr;

    /*
     * This way will change the object form cold space to hot space. It is more 
     * suitable way for our policy, but there are some error when using this way. 
     */
    /*
    if (is_cold(return_addr)) {
        fprintf(stderr, "mya %d %lu %p %p %c\n", getpid(), size, ptr, return_addr, 'r');
        return ptr;
    } else {
        
         *  In this siuation, '_my_' version of realloc return a memory witch is not 
         *  a cold object. So, we free this memory frist and use another version of 
         *  malloc to alloc memory.
         
        _my_free(ptr);
        return (orig_malloc)(size);
    }
    */
    
}

void* calloc(size_t nmemb, size_t size) {
    if (init_dlsym) {
        if (!pthread_mutex_trylock(&init_mutex)){
            init_dlsym();
            pthread_mutex_unlock(&init_mutex);
        } else {
            return unable_flag(_my_calloc(nmemb, size));
        }
    }

    void* return_addr = __builtin_extract_return_addr(__builtin_return_address(
        0)); // value of 0 yields return address of the current function
    if (is_cold(return_addr)) {
        void* ptr = _my_calloc(nmemb, size);

        if (size * nmemb == 0 | is_flag_mmaped(ptr)) {
            return unable_flag(ptr);
        }
        fprintf(stderr, "mya %d %lu %p %p %c\n", getpid(), size, ptr, return_addr, 'c');
        return ptr;
    } else {
        return (orig_calloc)(nmemb, size);
    }
    
}

void free(void* addr) {
    if (init_dlsym) {
        if (!pthread_mutex_trylock(&init_mutex)){
            init_dlsym();
            pthread_mutex_unlock(&init_mutex);
        } else {
            pthread_mutex_lock(&init_mutex);
            pthread_mutex_unlock(&init_mutex);
        }
    }
    void* ptr = _my_free(addr);
    if (!is_flag_notmy(ptr)) { // this represent to successfully free the memory by _my_free
        return ;
    } else { // call original free to process this memory
        (orig_free)(addr);
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