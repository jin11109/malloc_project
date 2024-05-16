/*
use way
    1. gcc -shared -fPIC -pthread mymalloc_0817.c -o mymalloc_0817.so
(compiling)
    2. export LD_PRELOAD=./mymalloc_0817.so (setting LD_PRELOAD)

clear
    unset LD_PRELOAD

*/
#define _GNU_SOURCE
#define GIGA << 30
#define MEGA << 20
#define KILO << 10
#define MEMPOOL_SIZE 64 MEGA
#define MAX_QUANTITY 1000000
#include <assert.h>
#include <dlfcn.h>
#include <math.h>
#include <pthread.h>
#include <sched.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <unistd.h>

pthread_mutex_t malloc_mutex;

typedef struct mem_pool {
        size_t size; // memory pool size
        void* return_addr;
        void* free_ptr; // memory in the pool start from this pointer had not
                        // been used before
        void* end_ptr;  // end of memory pool

} Mem_pool; // (32 byte)

// used to record the information of "malloc"
typedef struct head {
        // unsigned long pading[2];
        size_t size;        // the malloc size
        unsigned long flag; // to record whether this memory has been free
         /**
         * This data type is designed to ensure that the data following it will
         * not be prematurely added to the cache line (64byte) along with the
         * cache memory due to being written to the head before being accessed.
         */
        unsigned long pading[6];

} Head; // (64 byte)

/*============================ tools =======================================
 * ==========================================================================*/
// used to know malloc not to print the message
int big_alloc_flag = 0;

void* address_add(void* addr, long long int num) {
    return (void*)((unsigned long)addr + num);
}

size_t align(size_t s, size_t alignment) {
    if (s == 0) return 0;
    if ((s % alignment) == 0) return s;
    return ((s / alignment) + 1) * alignment;
}

int addr_to_string(void* addr, char* buffer) {
    unsigned long a = (unsigned long)addr;
    char num[16] = {'0', '1', '2', '3', '4', '5', '6', '7',
                    '8', '9', 'a', 'b', 'c', 'd', 'e', 'f'};

    int size = 2;
    while (a > 0) {
        buffer[size] = num[a % 16];
        a /= 16;
        size++;
    }

    for (int i = 0; i < (size - 2) / 2; i++) {
        char temp;
        temp = buffer[i + 2];
        buffer[i + 2] = buffer[size - i - 1];
        buffer[size - i - 1] = temp;
    }
    buffer[0] = '0';
    buffer[1] = 'x';
    // buffer[size] = '\n';
    buffer[size] = '\0';

    return size;
}

int num_to_string(long long num, char* buffer) {
    if (num == 0) {
        buffer[0] = '0';
        buffer[1] = '\0';
        return 1;
    }

    int digit = 0;
    long long int temp = num;
    while (temp > 0) {
        temp /= 10;
        digit++;
    }

    int index = digit;
    // char string[digit + 1];

    while (num > 0) {
        buffer[index - 1] = num % 10 + '0';
        num /= 10;
        index--;
    }
    buffer[digit] = '\0';

    return digit;
}

/*
void print_addr(void* addr) {
    unsigned long a = (unsigned long)addr;
    char num[16] = {'0', '1', '2', '3', '4', '5', '6', '7',
                    '8', '9', 'a', 'b', 'c', 'd', 'e', 'f'};
    char string[30];
    int size = 2;
    while (a > 0) {
        string[size] = num[a % 16];
        a /= 16;
        size++;
    }

    for (int i = 0; i < (size - 2) / 2; i++) {
        char temp;
        temp = string[i + 2];
        string[i + 2] = string[size - i - 1];
        string[size - i - 1] = temp;
    }
    string[0] = '0';
    string[1] = 'x';
    string[size] = '\n';
    string[++size] = '\0';

    write(2, string, sizeof(char) * (size));
}

void print_num(long long int num) {
    int digit = 0;
    long long int temp = num;
    while (temp > 0) {
        temp /= 10;
        digit++;
    }

    int index = digit;
    char string[digit + 1];

    while (num > 0) {
        string[index - 1] = num % 10 + '0';
        num /= 10;
        index--;
    }
    string[digit] = '\n';

    write(2, string, (digit + 1) * sizeof(char));
}

*/

void print_info_newpool(pid_t pid, void* begin, void* end, void* malloc_addr) {
    char end_s[30], begin_s[30], pid_s[10], malloc_addr_s[30], buffer[110];
    int endlen, beginlen, pidlen, maddrlen;
    endlen = addr_to_string(end, end_s);
    beginlen = addr_to_string(begin, begin_s);
    pidlen = num_to_string(pid, pid_s);
    maddrlen = addr_to_string(malloc_addr, malloc_addr_s);

    int index = 0;
    buffer[index++] = 'm';
    buffer[index++] = 'y';
    buffer[index++] = 'i';
    buffer[index++] = ' ';

    for (int i = 0; i < pidlen; i++) {
        buffer[index + i] = pid_s[i];
    }
    index += pidlen;
    buffer[index++] = ' ';

    for (int i = 0; i < beginlen; i++) {
        buffer[index + i] = begin_s[i];
    }
    index += beginlen;
    buffer[index++] = ' ';

    for (int i = 0; i < endlen; i++) {
        buffer[index + i] = end_s[i];
    }
    index += endlen;
    buffer[index++] = ' ';

    for (int i = 0; i < maddrlen; i++) {
        buffer[index + i] = malloc_addr_s[i];
    }
    index += maddrlen;
    buffer[index++] = '\n';

    int wsize = write(2, buffer, index);
}

void print_info_free(pid_t pid, void* addr) {
    char addr_s[30], pid_s[10], buffer[80];
    int addrlen, pidlen;
    addrlen = addr_to_string(addr, addr_s);
    pidlen = num_to_string(pid, pid_s);

    int index = 0;
    buffer[index++] = 'm';
    buffer[index++] = 'y';
    buffer[index++] = 'f';
    buffer[index++] = ' ';

    for (int i = 0; i < pidlen; i++) {
        buffer[index + i] = pid_s[i];
    }
    index += pidlen;
    buffer[index++] = ' ';

    for (int i = 0; i < addrlen; i++) {
        buffer[index + i] = addr_s[i];
    }
    index += addrlen;
    buffer[index++] = '\n';

    int wsize = write(2, buffer, index);
}

void print_info_alloc(pid_t pid, size_t size, void* addr, void* malloc_addr, char alloc_type) {
    if (big_alloc_flag) {
        big_alloc_flag = 0;
        return;
    }

    char addr_s[30], pid_s[10], size_s[30], malloc_addr_s[30], buffer[110];
    int addrlen, pidlen, sizelen, maddrlen;
    addrlen = addr_to_string(addr, addr_s);
    pidlen = num_to_string(pid, pid_s);
    sizelen = num_to_string(size, size_s);
    maddrlen = addr_to_string(malloc_addr, malloc_addr_s);

    int index = 0;
    buffer[index++] = 'm';
    buffer[index++] = 'y';
    buffer[index++] = 'a';
    buffer[index++] = ' ';

    for (int i = 0; i < pidlen; i++) {
        buffer[index + i] = pid_s[i];
    }
    index += pidlen;
    buffer[index++] = ' ';

    for (int i = 0; i < sizelen; i++) {
        buffer[index + i] = size_s[i];
    }
    index += sizelen;
    buffer[index++] = ' ';

    for (int i = 0; i < addrlen; i++) {
        buffer[index + i] = addr_s[i];
    }
    index += addrlen;
    buffer[index++] = ' ';

    for (int i = 0; i < maddrlen; i++) {
        buffer[index + i] = malloc_addr_s[i];
    }
    index += maddrlen;
    buffer[index++] = ' ';

    // record is malloc or realloc or calloc
    buffer[index++] = alloc_type;

    buffer[index++] = '\n';

    int wsize = write(2, buffer, index);
}

/*============================ memory pool operations ======================
 * ==========================================================================*/

// mempool array
Mem_pool** pool_table;
// used to count how many memory pools have been used
// int pool_counter = 0;
volatile int* pool_counter = NULL;
// used to record whether the pool_table has been initialized
volatile int* pooltable_flag = NULL;

// allocate space for memory pool array with size of MAX_QUANTITY
void pooltable_init() {
    if (!pooltable_flag) {
        pool_table = mmap(NULL, sizeof(Mem_pool) * MAX_QUANTITY,
                          PROT_READ | PROT_WRITE | PROT_EXEC,
                          MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
        pooltable_flag =
            mmap(NULL, sizeof(int), PROT_READ | PROT_WRITE | PROT_EXEC,
                 MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
        *pooltable_flag = 1;
    }
    ////write(2, "table ok\n", sizeof("table ok\n"));
}

// search by iteration.
// If it's found, return memory pool pointer, if's not found, return NULL
Mem_pool* pool_search(void* return_addr) {
    if (pool_counter == NULL) {
        ////write(2, "ok\n", sizeof("ok\n"));
        pool_counter = (int*)mmap(NULL, sizeof(int), PROT_READ | PROT_WRITE,
                                  MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        *pool_counter = 0;
        return NULL;
    }

    ////write(2, "search\n", sizeof("search\n"));
    
    for (long int i = *pool_counter - 1; i >= 0; i--) {
        if (pool_table[i]->return_addr == return_addr) {
            return pool_table[i];
        }
    }
    
    /*
    long int left = 0;
    long int right = *pool_counter; 
    long int index;
    while(1){
        index = (left + right) / 2;
        void* temp = pool_table[index]->return_addr;
        if (temp == return_addr){
            return pool_table[index];
        }
        else if (left == right - 1){
            return NULL;
        }
        else if (temp > return_addr){
            right = index;
        }
        else{
            left = index;
        }
    }
    */
    ////write(2, "searchdone\n", sizeof("searchdone\n"));
    return NULL;
}

// initialize memory pool with size of MEMPOOL_SIZE
// Return new memory pool pointer
Mem_pool* pool_init(size_t size, void* return_addr) {
    // test
    if (size > MEMPOOL_SIZE) {
        // write(2, "malloc bigger than 128 MB\n", sizeof("malloc bigger than
        // 128 MB\n"));
    }
    assert(size <= MEMPOOL_SIZE);
    size = MEMPOOL_SIZE;

    Mem_pool* pool_ptr =
        mmap(NULL, sizeof(Mem_pool), PROT_READ | PROT_WRITE | PROT_EXEC,
             MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);

    pool_ptr->free_ptr = mmap(NULL, size + _Alignof(max_align_t),
                              PROT_READ | PROT_WRITE | PROT_EXEC,
                              MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
    // align free_ptr
    pool_ptr->free_ptr =
        (Mem_pool*)(align((size_t)pool_ptr->free_ptr, _Alignof(max_align_t)));

    pool_ptr->end_ptr = address_add(pool_ptr->free_ptr, size);
    pool_ptr->return_addr = return_addr;
    pool_ptr->size = size;

    print_info_newpool(getpid(), pool_ptr->free_ptr, pool_ptr->end_ptr,
                       return_addr);

    // print_num(*pool_counter);
    ////write(2, "pid : ", sizeof("pid : "));
    // print_num(getpid());
    ////write(2, "pool init :\n    ", sizeof("pool init :\n    "));
    // print_addr(pool_ptr->free_ptr);
    ////write(2, "    ", sizeof("    "));
    // print_addr(pool_ptr->end_ptr);
    ////write(2, "\n", sizeof("\n"));

    return pool_ptr;
}

// Insertion sort. If new_pool is NULL, initialize first.
// Return the memory pool pointer
Mem_pool* pool_insert(void* return_addr, Mem_pool* new_pool, size_t size) {
    if (new_pool == NULL) {
        new_pool = pool_init(size, return_addr);
    }

    // Insertion sort
    if (*pool_counter == 0) { // table is empty
        pool_table[0] = new_pool;
    } else {
        // write(2, "insert", sizeof("insert"));
        // print_num(*pool_counter);

        // test
        if (*pool_counter + 1 >= MAX_QUANTITY) {
            int wsize = write(2, "exceed max number of memory pool\n",
                  sizeof("exceed max number of memory pool\n"));
        }
        assert(*pool_counter + 1 < MAX_QUANTITY);

        int flag = 1;
        for (long int i = *pool_counter - 1; i >= 0; i--) {
            pool_table[i + 1] = pool_table[i];
            if (return_addr > pool_table[i]->return_addr) {
                pool_table[i] = new_pool;
                flag = 0;
                break;
            }
        }
        if (flag) {
            pool_table[0] = new_pool;
        }
    }

    (*pool_counter)++;

    return new_pool;
}

// build a new memory pool to use, and update the information in mempool
// structure
void pool_expand(size_t new_size, Mem_pool* pool_ptr, void* return_addr) {
    // write(2, "expand\n", sizeof("expand\n"));

    pool_ptr->size = new_size;
    pool_ptr->free_ptr = mmap(NULL, (MEMPOOL_SIZE) + _Alignof(max_align_t),
                              PROT_READ | PROT_WRITE | PROT_EXEC,
                              MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
    // align free_ptr
    pool_ptr->free_ptr =
        (Mem_pool*)(align((size_t)pool_ptr->free_ptr, _Alignof(max_align_t)));
    pool_ptr->end_ptr = address_add(pool_ptr->free_ptr, MEMPOOL_SIZE);

    print_info_newpool(getpid(), pool_ptr->free_ptr, pool_ptr->end_ptr,
                       return_addr);
}

// allocate memory
// 1. for the allocted size bigger than MEMPOOL_SIZE, use mmap to allocted
// memory directly
// 2. for others, use memory pool
// return address of available memory
void* pool_alloc(size_t size, void* return_addr) {
    // allocate big size of memory
    if (size + sizeof(Head) + _Alignof(max_align_t) > MEMPOOL_SIZE) {
        // write(2, "alloc big size\n", sizeof("alloc big size\n"));

        big_alloc_flag = 1;

        void* ptr =
            mmap(NULL, size + _Alignof(max_align_t) + sizeof(Head),
                 PROT_READ | PROT_WRITE | PROT_EXEC,
                 MAP_ANONYMOUS | MAP_PRIVATE, -1, 0); // allocate size MB memory
        // align pool_ptr
        ptr = (void*)(align((size_t)ptr, _Alignof(max_align_t)));

        Head* head = ptr;
        head->flag = 1;
        head->size = size;

        return address_add(ptr, sizeof(Head));
    }

    // allocate memory smaller than MEMPOOL_SIZE

    Mem_pool* pool_ptr = pool_search(return_addr);

    ////write(2, "ok2\n", sizeof("ok2\n"));

    // if there is not memory pool
    if (pool_ptr == NULL) {
        pool_ptr = pool_insert(return_addr, NULL, size + sizeof(Head));
    }

    assert(pool_ptr != NULL);

    ////write(2, "ok1\n", sizeof("ok1\n"));

    // if memory in pool is not enough to allocate
    if (address_add(pool_ptr->free_ptr,
                    size + sizeof(Head) + _Alignof(max_align_t)) >=
        pool_ptr->end_ptr) {
        pool_expand(pool_ptr->size + (MEMPOOL_SIZE), pool_ptr, return_addr);
    }

    ////write(2, "ok\n", sizeof("ok\n"));

    // use 16 byte to record the the state of allocated memory
    // and return the available memory address
    Head* head = pool_ptr->free_ptr;
    head->flag = 1;
    head->size = size;

    void* addr = address_add(pool_ptr->free_ptr,
                             sizeof(Head)); // the available memory address
    pool_ptr->free_ptr =
        address_add(pool_ptr->free_ptr,
                    size + sizeof(Head)); // the new free pointer in memory pool

    return addr;
}

// allocate new memory and copy data from original address to new one
// return the new address
void* pool_realloc(size_t new_size, void* ori_addr, void* return_addr) {
    // record the original size
    Head* head = address_add(ori_addr, sizeof(Head) * -1);
    size_t ori_size = head->size;

    // get available memory
    void* new_addr = pool_alloc(new_size, return_addr);

    // copy the data start from original address to new address
    memcpy(new_addr, ori_addr, ori_size);

    return new_addr;
}

/*============================= PRE_LOAD functions =========================
 * ==========================================================================*/

void* malloc(size_t size) {
    pthread_mutex_lock(&malloc_mutex);
    size_t ori_size = size;

    if (size == 0) {
        pthread_mutex_unlock(&malloc_mutex);
        return NULL;
    }

    // initialize pool_table
    pooltable_init();

    size = align(size, _Alignof(max_align_t));

    void* return_addr = __builtin_extract_return_addr(__builtin_return_address(
        0)); // value of 0 yields return address of the current function
    void* addr = pool_alloc(size, return_addr);

    print_info_alloc(getpid(), ori_size, addr, return_addr, 'm');

    pthread_mutex_unlock(&malloc_mutex);

    return addr;
}

void free(void* addr) {
    pthread_mutex_lock(&malloc_mutex);
    
    if (addr != 0)
        print_info_free(getpid(), addr);

    pthread_mutex_unlock(&malloc_mutex);

    return;
}

void* realloc(void* addr, size_t new_size) {
    pthread_mutex_lock(&malloc_mutex);

    // initialize pool_table
    pooltable_init();
    size_t ori_new_size = new_size;

    new_size = align(new_size, _Alignof(max_align_t));

    void* return_addr = __builtin_extract_return_addr(__builtin_return_address(
        0)); // value of 0 yields return address of the current function
    pthread_mutex_unlock(&malloc_mutex);

    free(addr);

    pthread_mutex_lock(&malloc_mutex);
    if (new_size == 0) { // like free
        //print_info_alloc(getpid(), ori_new_size, NULL, return_addr);
        pthread_mutex_unlock(&malloc_mutex);
        return NULL;
    }
    else if (addr == NULL) { // like malloc
        void* return_value = pool_alloc(new_size, return_addr);

        print_info_alloc(getpid(), ori_new_size, return_value, return_addr, 'r');
        pthread_mutex_unlock(&malloc_mutex);

        return return_value;
    } 
    else { // realloc
        void* return_value = pool_realloc(new_size, addr, return_addr);

        print_info_alloc(getpid(), ori_new_size, return_value, return_addr, 'r');
        pthread_mutex_unlock(&malloc_mutex);
        return return_value;
    }
}

void* calloc(size_t count, size_t size) {
    pthread_mutex_lock(&malloc_mutex);
    size_t ori_size = count * size;
    // initialize pool_table
    pooltable_init();

    if (!count || !size) {
        pthread_mutex_unlock(&malloc_mutex);
        return NULL;
    }

    void* return_addr = __builtin_extract_return_addr(__builtin_return_address(
        0)); // value of 0 yields return address of the current function

    size_t new_size = align(count * size, _Alignof(max_align_t));

    void* addr = pool_alloc(new_size, return_addr);

    memset(addr, 0, new_size);

    print_info_alloc(getpid(), ori_size, addr, return_addr, 'c');

    pthread_mutex_unlock(&malloc_mutex);

    return addr;
}

/*
int (*original_clone)(int (*fn) (void *arg), void *child_stack, int flags, void
*arg, ...); int clone (int (*fn) (void *arg), void *child_stack, int flags, void
*arg, ...){
    //write(2, "igotyou\n", sizeof("igotyou\n"));

    // 在此处添加 CLONE_VM 标志
    flags |= CLONE_VM;
    va_list args;
    va_start(args, arg);


    // 获取原始的 clone 函数地址
    if (!original_clone) {
        original_clone = dlsym(RTLD_NEXT, "clone");
    }

    // 调用原始的 clone 函数
    int result = original_clone(fn, child_stack, flags, arg, args);
    va_end(args);

    return result;
}
*/

/*
void* valloc (size_t size){
    return malloc(size);
}

void cfree (void* addr){
    return free(addr);
}

void* memalign (size_t alignment, size_t size){
    return malloc (size);
}

void* sh_malloc (size_t bytes, const char* file, int line){
  return malloc(bytes);
}

void* sh_realloc (void* ptr, size_t size, const char* file, int line){
  return realloc(ptr, size);
}

void sh_free (void* mem, const char* file, int line){
  free(mem);
}

void* sh_memalign (size_t alignment, size_t size, const char* file, int line){
  return memalign(alignment, size);
}

void* sh_calloc (size_t n, size_t s, const char* file, int line){
    return calloc(n, s);
}

void sh_cfree (void* mem, const char* file, int line){
    cfree(mem);
}

void* sh_valloc (size_t size, const char* file, int line){
  return valloc(size);
}

/*
void* aligned_alloc(size_t alignment, size_t size){
    pthread_mutex_lock(&malloc_mutex);

    ////write(2, "malloc ", sizeof("malloc "));

    // initialize pool_table
    if (!pooltable_flag){
        pooltable_flag = 1;
        pooltable_init();
    }

    size = align(size, _Alignof(max_align_t));

    void* return_addr = __builtin_extract_return_addr (__builtin_return_address
(0)); // value of 0 yields return address of the current function

    void* addr = pool_alloc(size, return_addr);


    //print_addr(addr);
    //print_num(*pool_counter);

    pthread_mutex_unlock(&malloc_mutex);

    return addr;
}


void* xmalloc (size_t size){
    pthread_mutex_lock(&malloc_mutex);

    ////write(2, "malloc ", sizeof("malloc "));

    // initialize pool_table
    if (!pooltable_flag){
        pooltable_flag = 1;
        pooltable_init();
    }

    size = align(size, _Alignof(max_align_t));

    void* return_addr = __builtin_extract_return_addr (__builtin_return_address
(0)); // value of 0 yields return address of the current function

    void* addr = pool_alloc(size, return_addr);


    //print_addr(addr);
    //print_num(*pool_counter);

    pthread_mutex_unlock(&malloc_mutex);

    return addr;
}

void* xrealloc (void* addr, size_t new_size){

    pthread_mutex_lock(&malloc_mutex);

    ////write(2, "realloc ", sizeof("realloc "));

    // initialize pool_table
    if (!pooltable_flag){
        pooltable_flag = 1;
        pooltable_init();
    }

    new_size = align(new_size, _Alignof (max_align_t));

    void* return_addr = __builtin_extract_return_addr (__builtin_return_address
(0)); // value of 0 yields return address of the current function

    pthread_mutex_unlock(&malloc_mutex);
    free(addr);
    pthread_mutex_lock(&malloc_mutex);

    if (addr == NULL){ // like malloc
        void* return_value = pool_alloc(new_size, return_addr);
        //print_addr(return_value);
        pthread_mutex_unlock(&malloc_mutex);
        return return_value;
    }
    else if (new_size == 0){ // like free
        pthread_mutex_unlock(&malloc_mutex);
        return NULL;
    }
    else{ // realloc
        ////write(2, "rr", sizeof("rr"));
        void* return_value = pool_realloc(new_size, addr, return_addr);
        //print_addr(return_value);
        pthread_mutex_unlock(&malloc_mutex);
        return return_value;
    }


}

void xfree (void* addr){

    pthread_mutex_lock(&malloc_mutex);
    ////write(2, "free\n", sizeof("free\n"));

    if (addr){
        addr = address_add(addr, sizeof(Head) * -1);
        Head *head = addr;
        head->flag = 0;
    }

    pthread_mutex_unlock(&malloc_mutex);
    return;
}
*/
