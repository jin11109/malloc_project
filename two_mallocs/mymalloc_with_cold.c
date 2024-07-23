#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
/* include "_my_" version of ptmalloc2 */
#include "ptmalloc2_with_cold/_my_malloc.h"
/* include "_my2_" version of ptmalloc2 */
#include "ptmalloc2_with_cold_2/_my2_malloc.h"
/* include for array of cold mallocs' address */
#include "cold_addrs.h"

#define PAGESIZE 4096
#define is_cold(p) (cold_addrs[(((uintptr_t)(p)) & (PAGESIZE - 1))])

/*
 * This structure is defined in malloc.c. We move this to here because we
 * need to realloc the memeory witch should get the memory size from chunk's
 * information.
 */
struct malloc_chunk {
        size_t prev_size;        /* Size of previous chunk (if free).  */
        size_t size;             /* Size in bytes, including overhead. */
        struct malloc_chunk* fd; /* double links -- used only if free. */
        struct malloc_chunk* bk;
};

/*============================ prelaod functions ============================
 *==========================================================================*/

void* malloc(size_t bytes) {
    void* return_addr = __builtin_extract_return_addr(__builtin_return_address(
        0)); // value of 0 yields return address of the current function
    if (is_cold(return_addr)) {
        void* ptr = _my_malloc(bytes);
        return unable_flag(ptr);
    } else {
        void* ptr = _my2_malloc(bytes);
        return unable_flag(ptr);
    }
}

void* realloc(void* addr, size_t size) {
    void* return_addr = __builtin_extract_return_addr(__builtin_return_address(
        0)); // value of 0 yields return address of the current function

    void* ptr = _my_realloc(addr, size);
    if (is_flag_notmy(ptr)) {
        void* ptr2 = _my2_realloc(addr, size);
        if (is_flag_notmy(ptr2)) {
            /*
             * In this situation, it represent that the address witch want to
             * realloc is alloced from system glibc. So, originaly we should
             * use dlysm to find the second realloc and use this to realloc
             * the address. But it will occur some error because dlysm use
             * mallocs and callocs inside its function (glibc 2.31 only). So
             * that, we temporarily use our ptmalloc2 to alloc a new memory for
             * this.
             */
            // call original free to process this memory
            // void* orig_realloc = dlsym(RTLD_NEXT, "realloc");
            // return ((void* (*)(void*, size_t))orig_realloc)(addr, size);
            struct malloc_chunk* p =
                ((struct malloc_chunk*)((char*)(addr)-2 * (sizeof(size_t))));
            void* newmem = unable_flag(_my2_malloc(size));
            memcpy(newmem, addr, p->size & ~((unsigned long)0b111));
            return newmem;
        }
        if (is_flag_mmapped(ptr2)) {
            return unable_flag(ptr2);
        }
        // Is '_my2_', and not mmapped
        return ptr2;
    }
    if (is_flag_mmapped(ptr)) {
        return unable_flag(ptr);
    }
    // Is '_my_', and not mmapped
    return ptr;
}

void* calloc(size_t nmemb, size_t size) {
    void* return_addr = __builtin_extract_return_addr(__builtin_return_address(
        0)); // value of 0 yields return address of the current function
    if (is_cold(return_addr)) {
        void* ptr = _my_calloc(nmemb, size);
        return unable_flag(ptr);
    } else {
        void* ptr = _my2_calloc(nmemb, size);
        return unable_flag(ptr);
    }
}

void free(void* addr) {
    void* ptr = _my_free(addr);
    if (is_flag_notmy(ptr)) {
        // this represent to successfully free the memory by _my_free
        void* ptr2 = _my2_free(addr);
        if (is_flag_notmy(ptr2)) {
            // call original free to process this memory
            void* orig_free = dlsym(RTLD_NEXT, "free");
            ((void (*)(void*))orig_free)(addr);
            return;
        }
        return;
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