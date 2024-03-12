#!/bin/bash

if [ $# -lt 2 ]; then
    echo "demo.sh : parameter error (usage : demo.sh counts rounds)"
    exit 0
fi
echo "coubt $1, rounds $2"
# set enviroment
echo -1 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
echo 0 | sudo tee /proc/sys/kernel/kptr_restrict > /dev/null
echo 0 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null
# 39750

# compile program
gcc -O3 -g ./test_perf_cachemisses.c -o ./test_perf_cachemisses

#perf stat -e instructions ./test_perf_hit_random
for (( i=0; i<$2; i=i+1 )); do
    echo 150000 | sudo tee /proc/sys/kernel/perf_event_max_sample_rate > /dev/null

    #perf record -e mem-stores:ppp,mem-loads:ppp -F max --running-time --data ./test_perf_hit_random > ./temp.log
    #perf record -e MEM_UOPS_RETIRED.ALL_STORES:ppp,MEM_UOPS_RETIRED.ALL_LOADS:ppp --count=$1 --timestamp --data ./test_perf_hit_random > ./temp.log
    perf record -e MEM_LOAD_UOPS_RETIRED.L3_MISS:ppp --count=$1 --timestamp --data ./test_perf_cachemisses > ./temp.log
    perf script -F +addr,+time,+data_src --ns -i ./perf.data > ./script.log
    
    python3 ./filter.py
    #python3 ./show.py

    cp ./result.csv ./result${i}.csv
    cp ./script.log ./script${i}.log
    cp ./perf.data ./perf${i}.data
done

# set enviroment
echo 4 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
echo 1 | sudo tee /proc/sys/kernel/kptr_restrict > /dev/null
echo 2 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null

rm ./temp.log
