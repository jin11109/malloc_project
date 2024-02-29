#!/bin/bash

# set enviroment
echo -1 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
echo 0 | sudo tee /proc/sys/kernel/kptr_restrict > /dev/null
echo 0 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null
# 39750

# compile program
gcc -O3 -g ./test_perf_hit_random.c -o ./test_perf_hit_random

# count 
count=(100000 50000 30000 20000 10000)

#perf stat -e instructions ./test_perf_hit_random
for (( i=0; i<1; i=i+1 )); do
    echo 150000 | sudo tee /proc/sys/kernel/perf_event_max_sample_rate > /dev/null

    #perf record -e ibs_op/cnt_ctl=1/pp -F max --timestamp --data ./test_perf_hit_random > ./temp.log
    #perf record -e ibs_op/cnt_ctl=1/pp --count=${count[2]} --timestamp --realtime=99 --mmap-pages=65536 --data ./test_perf_hit_random > ./temp.log    
    perf record -e ibs_op/cnt_ctl=1/pp --count=50000 --timestamp --data ./test_perf_hit_random > ./temp.log
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
