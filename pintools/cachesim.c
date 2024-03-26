#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

typedef struct ldstdata {
        int pid;
        int size;
        void *addr;
        double time;
        char rw;
} Ldstdata;

typedef struct cache_set {
        unsigned long cache_addr[8]; // tag
        char valid[8];
        char dirty[8];
        int run; // FIFO
} Cache_set;

struct timespec init_ts, ts;
int count = 0;
int is_cache_inited = 0;
Cache_set llc_cache[16384];

// initialize cache
void initCache() { memset(llc_cache, 0, sizeof(Cache_set) * (16384)); }

// return cache_addr
unsigned long get_cache_addr(unsigned long addr) { return addr >> 6; }

// return cache set
Cache_set *getCacheSet(unsigned long cache_addr) {
    // like cache_addr % 16384
    return &llc_cache[cache_addr & 0x3fff];
}

// decide the data will occur cache miss or cache hit
int is_hit(unsigned long addr, char rw) {
    if (rw == 'r')
        rw = 0;
    else
        rw = 1;

    if (is_cache_inited == 0) {
        initCache();
        is_cache_inited = 1;
    }
    unsigned long cache_addr = get_cache_addr(addr);
    Cache_set *cacheSet = getCacheSet(cache_addr);

    // cache hit
    for (int i = 0; i < 8; i++) {
        if (cacheSet->valid[i] == 0) continue;
        if (cacheSet->cache_addr[i] == cache_addr) {
            if (rw == 1) cacheSet->dirty[i] = 1;
            // check(addr, cacheSet, 1);
            return 1;
        }
    }
    // cache miss
    for (int i = 0; i < 8; i++) {
        if (cacheSet->valid[i] == 0) {
            cacheSet->cache_addr[i] = cache_addr;
            cacheSet->valid[i] = 1;
            cacheSet->dirty[i] = rw;
            // check(addr, cacheSet, 2);
            return 0;
        }
    }

    cacheSet->cache_addr[cacheSet->run] = cache_addr;
    cacheSet->valid[cacheSet->run] = 1;
    cacheSet->dirty[cacheSet->run] = rw;
    cacheSet->run++;
    cacheSet->run = cacheSet->run % 8;
    // check(addr, cacheSet, 3);
    return 0;
}

int cachesim(unsigned long addr, char rw, int size) {
    unsigned long tmp = addr >> 6;
    int cache_miss = 0;
    // check if address across cache lines
    for (int align = 1; align || (addr >> 6) != tmp;) {
        if (is_hit(addr, rw) == 0) {
            cache_miss++;
        }
        if (!align) break;
        addr = addr + size - 1;
        align = 0;
    }
    return cache_miss;
}

void output(Ldstdata data, FILE *file, int misses) {
    for (int i = 0; i < misses; i++) {
        fprintf(file, "%d %p %d %lf %c\n", data.pid, data.addr, data.size,
                data.time, data.rw);
    }
}

int main() {
    FILE *fifo, *output_file;
    char line[128];

    fifo = fopen("./fifo_pintools", "r");
    output_file = fopen("./data/ldst_data.raw", "w");
    if (fifo == NULL || output_file == NULL) {
        perror("ERROR : Failed to open file");
        return 1;
    }

    clock_gettime(CLOCK_REALTIME, &init_ts);

    while (fread(line, 128, 1, fifo) != 0) {
        // printf("test %s\n", line);
        Ldstdata new;
        clock_gettime(CLOCK_REALTIME, &ts);
        new.time = (double)(ts.tv_sec - init_ts.tv_sec) +
                   (double)(ts.tv_nsec) / 1000000000 -
                   (double)(init_ts.tv_nsec) / 1000000000;

        sscanf(line, "%d %p %d %c\n", &new.pid, &new.addr, &new.size, &new.rw);

        int cache_misses =
            cachesim((unsigned long)(intptr_t) new.addr, new.rw, new.size);
        output(new, output_file, cache_misses);
    }

    fclose(fifo);
    fclose(output_file);
    return 0;
}