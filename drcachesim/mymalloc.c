#define _GNU_SOURCE
#define GIGA << 30
#define MEGA << 20
#define KILO << 10
#define MEMPOOL_SIZE (((uint64_t)4)GIGA)
#define MAX_DEPTH_OF_CALL_CHAIN 4

#include <assert.h>
#include <dlfcn.h>
#include <execinfo.h>
#include <fcntl.h>
#include <math.h>
#include <pthread.h>
#include <sched.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <unistd.h>

// lock
pthread_mutex_t malloc_mutex;
pthread_mutex_t trace_mutex;
__thread bool have_trace_lock = 0;

typedef struct pool {
        // memory pool size
        size_t size;
        pid_t pid;
        // Memory in the pool start from this pointer had not been used before
        void* free_ptr;
        // end of memory pool
        void* end_ptr;

} pool_t;

// used to record the information of "malloc"
typedef struct head {
        // the malloc size
        size_t size;
        /**
         * This data type is designed to ensure that the data following it will
         * not be prematurely added to the cache line (64byte) along with the
         * cache memory due to being written to the head before being accessed.
         */
        uint64_t pading[7];

} Head; // (64 byte, must be equal to cacheline)

/*============================ tools =======================================
 * ==========================================================================*/
#define address_add(addr, num) ((void*)(((uintptr_t)(addr)) + (num)))

// Timmer
#ifdef ONLINE
uint64_t* timer_ptr;
#endif

size_t align(size_t s, size_t alignment) {
    if (s == 0) return 0;
    if ((s % alignment) == 0) return s;
    return ((s / alignment) + 1) * alignment;
}

uint64_t get_program_time() {
    uint64_t time = 0;
#ifdef ONLINE
    time = *timer_ptr;
#else
#ifdef OFFLINE
    struct timeval t;
    gettimeofday(&t, NULL);
    time = t.tv_sec * 1000000 + t.tv_usec;
#else
    fprintf(stderr,
            "_mymalloc.so : you shoud define profiling mode "
            "[-DONLINE/-DOFFLINE]\n");
#endif
#endif
    return time;
}

void print_info_free(pid_t pid, void* addr, char type) {
    /**
     * type f means original 'free'
     *      r means 'free' call by 'realloc'
     */
    fprintf(stderr, "myf %c %d %p %lu\n", type, pid, addr, get_program_time());
}

void print_info_alloc(pid_t pid, size_t size, void* addr, void* return_addrs[],
                      char type) {
    /**
     * type m means 'malloc'
     *      r means 'realloc'
     *      c means 'calloc'
     */
    fprintf(stderr, "mya %c %d %lu %p %lu %p %p %p %p\n", type, pid, size, addr,
            get_program_time(), return_addrs[0], return_addrs[1],
            return_addrs[2], return_addrs[3]);
}

/*============================ memory pool operations ======================
 * ==========================================================================*/

bool is_pool_init = false;
pool_t pool;

void pool_init() {
    pool.pid = getpid();
    pool.size = MEMPOOL_SIZE;
    pool.free_ptr = mmap(NULL, MEMPOOL_SIZE, PROT_READ | PROT_WRITE | PROT_EXEC,
                         MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
    pool.end_ptr = address_add(pool.free_ptr, MEMPOOL_SIZE);
    is_pool_init = true;

#ifdef ONLINE
    int timmer_fd = open("timmer", O_RDONLY, 0666);
    timer_ptr = (uint64_t*)(mmap(0, 8, PROT_READ, MAP_SHARED, timmer_fd, 0));
#endif

    fprintf(
        stderr,
        "_mymalloc.so : init pool, pid %d, size %lu, freeptr %p, endptr %p\n",
        pool.pid, pool.size, pool.free_ptr, pool.end_ptr);
}

void* pool_alloc(size_t size) {
    // test memory in pool is enough to allocate
    assert(address_add(pool.free_ptr,
                       size + sizeof(Head) + _Alignof(max_align_t)) <
           pool.end_ptr);

    // Use head to record meta data
    Head* head = pool.free_ptr;
    head->size = size;

    // For return available memory address
    void* addr = address_add(pool.free_ptr, sizeof(Head));
    // Update new free pointer
    pool.free_ptr = address_add(pool.free_ptr, size + sizeof(Head));

    return addr;
}

// allocate new memory and copy data from original address to new one
// and return the new address
void* pool_realloc(size_t new_size, void* ori_addr) {
    // record the original size
    Head* head = address_add(ori_addr, sizeof(Head) * -1);
    size_t ori_size = head->size;

    void* new_addr = pool_alloc(new_size);

    // copy the data start from original address to new address
    memcpy(new_addr, ori_addr, ori_size);

    return new_addr;
}

/*============================= PRE_LOAD functions =========================
 * ==========================================================================*/

void* malloc(size_t size) {
    if (!have_trace_lock) pthread_mutex_lock(&malloc_mutex);

#ifdef DEBUG
    fprintf(stderr, "malloc %lu\n", size);
#endif

    if (size == 0) {
        pthread_mutex_unlock(&malloc_mutex);
        return NULL;
    }
    if (!is_pool_init) pool_init();

    size_t ori_size = size;
    size = align(size, _Alignof(max_align_t));
    void* addr = pool_alloc(size);

    if (!have_trace_lock) {
        pthread_mutex_lock(&trace_mutex);
        have_trace_lock = true;

        void* return_addrs[MAX_DEPTH_OF_CALL_CHAIN];
        int depth = backtrace(return_addrs, MAX_DEPTH_OF_CALL_CHAIN);
        for (int i = MAX_DEPTH_OF_CALL_CHAIN - 1; i > depth - 1; i--) {
            /**
             * This is because the actually depth of call-chain is smaller than
             * we want. So we should set these value to represent None. But, if
             * set to zero the output will be (nil) which python file should
             * apecially change this to zero.
             */
            return_addrs[i] = (void*)1;
        }
        print_info_alloc(getpid(), ori_size, addr, return_addrs, 'm');

        have_trace_lock = false;
        pthread_mutex_unlock(&trace_mutex);
    }

    pthread_mutex_unlock(&malloc_mutex);
    return addr;
}

void free(void* addr) {
    if (have_trace_lock) return;

    pthread_mutex_lock(&malloc_mutex);

#ifdef DEBUG
    fprintf(stderr, "free %p\n", addr);
#endif

    if (addr != 0) print_info_free(getpid(), addr, 'f');

    pthread_mutex_unlock(&malloc_mutex);
    return;
}

void* realloc(void* ori_addr, size_t new_size) {
    if (!have_trace_lock) pthread_mutex_lock(&malloc_mutex);

#ifdef DEBUG
    fprintf(stderr, "realloc %p %lu\n", ori_addr, new_size);
#endif

    if (!is_pool_init) pool_init();

    size_t ori_new_size = new_size;
    new_size = align(new_size, _Alignof(max_align_t));

    if (new_size == 0) { // like free
        print_info_free(getpid(), ori_addr, 'f');
        pthread_mutex_unlock(&malloc_mutex);
        return NULL;

    } else if (ori_addr == NULL) { // like malloc
        void* new_addr = pool_alloc(new_size);

        if (!have_trace_lock) {
            pthread_mutex_lock(&trace_mutex);
            have_trace_lock = true;

            void* return_addrs[MAX_DEPTH_OF_CALL_CHAIN];
            int depth;
            depth = backtrace(return_addrs, MAX_DEPTH_OF_CALL_CHAIN);
            for (int i = MAX_DEPTH_OF_CALL_CHAIN - 1; i > depth - 1; i--) {
                return_addrs[i] = (void*)1;
            }

            print_info_alloc(getpid(), ori_new_size, new_addr, return_addrs,
                             'm');

            have_trace_lock = false;
            pthread_mutex_unlock(&trace_mutex);
        }
        pthread_mutex_unlock(&malloc_mutex);
        return new_addr;

    } else { // realloc
        void* new_addr = pool_realloc(new_size, ori_addr);
        if (!have_trace_lock) {
            pthread_mutex_lock(&trace_mutex);
            have_trace_lock = true;

            void* return_addrs[MAX_DEPTH_OF_CALL_CHAIN];
            int depth;
            depth = backtrace(return_addrs, MAX_DEPTH_OF_CALL_CHAIN);
            for (int i = MAX_DEPTH_OF_CALL_CHAIN - 1; i > depth - 1; i--) {
                return_addrs[i] = (void*)1;
            }

            print_info_alloc(getpid(), ori_new_size, new_addr, return_addrs,
                             'r');
            print_info_free(getpid(), ori_addr, 'r');

            have_trace_lock = false;
            pthread_mutex_unlock(&trace_mutex);
        }
        pthread_mutex_unlock(&malloc_mutex);
        return new_addr;
    }
}

void* calloc(size_t count, size_t size) {
    if (!have_trace_lock) pthread_mutex_lock(&malloc_mutex);

#ifdef DEBUG
    fprintf(stderr, "calloc %lu %lu\n", count, size);
#endif

    if (!is_pool_init) pool_init();

    size_t ori_size = count * size;
    if (!count || !size) {
        pthread_mutex_unlock(&malloc_mutex);
        return NULL;
    }

    size_t new_size = align(count * size, _Alignof(max_align_t));
    void* addr = pool_alloc(new_size);
    /**
     * Because we need to know the access event to the required mamory.
     * Althought mmap space is already set to zero value ,we still keep memset
     * as the similar way to ptmalloc2.
     */
    memset(addr, 0, new_size);

    if (!have_trace_lock) {
        pthread_mutex_lock(&trace_mutex);
        have_trace_lock = true;

        void* return_addrs[MAX_DEPTH_OF_CALL_CHAIN];
        int depth;
        depth = backtrace(return_addrs, MAX_DEPTH_OF_CALL_CHAIN);
        for (int i = MAX_DEPTH_OF_CALL_CHAIN - 1; i > depth - 1; i--) {
            return_addrs[i] = (void*)1;
        }
        print_info_alloc(getpid(), ori_size, addr, return_addrs, 'c');

        have_trace_lock = false;
        pthread_mutex_unlock(&trace_mutex);
    }

    pthread_mutex_unlock(&malloc_mutex);

    return addr;
}
