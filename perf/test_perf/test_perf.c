#include <stdio.h>
#include <stdlib.h>
#include <stdatomic.h>
#include <sys/types.h>
#include <unistd.h>
#include <time.h>
#define MEGA << 20
#define KILO << 10

int element_num = (16 MEGA);
long long int bin0[(16 MEGA)], bin1[(16 MEGA)], bin2[(16 MEGA)], bin3[(16 MEGA)];

int main(){
    srand48(time(NULL));

    printf("bin0 addr : %p %p\n", bin0, &bin0[element_num - 1]);
    printf("bin1 addr : %p %p\n", bin1, &bin1[element_num - 1]);
    printf("bin2 addr : %p %p\n", bin2, &bin2[element_num - 1]);
    printf("bin3 addr : %p %p\n", bin3, &bin3[element_num - 1]);

    printf("pid : %d\n", getpid());
    printf("element num : %d\n", element_num);

    int freq0 = 1 << 1, freq1 = 1 << 6, freq2 = 1 << 11, freq3 = 1 << 16;
    printf("freq %d %d %d %d\n", freq0, freq1, freq2, freq3);
    
    long long int n = (long long int)1 << 32;
    int temp = 0;
    for (long long int i = 0; i < n; i++) {
        if (i << 63 == 0){
            int index = lrand48() % element_num;
            temp += atomic_load_explicit(&bin0[index], memory_order_relaxed);
        }
        if (i << 58 == 0){
            int index = lrand48() % element_num;
            temp += atomic_load_explicit(&bin1[index], memory_order_relaxed);
        }
        if (i << 53 == 0){
            int index = lrand48() % element_num;
            temp += atomic_load_explicit(&bin2[index], memory_order_relaxed);
        }
        if (i << 48 == 0){
            int index = lrand48() % element_num;
            temp += atomic_load_explicit(&bin3[index], memory_order_relaxed);
        }
        
    }
    printf("temp : %d\n", temp);

}