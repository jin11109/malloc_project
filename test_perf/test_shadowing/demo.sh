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
gcc -O3 -g ./test_shadowing.c -o ./test_shadowing

#perf stat -e instructions ./test_perf_hit_random
for (( i=0; i<$2; i=i+1 )); do
    echo 150000 | sudo tee /proc/sys/kernel/perf_event_max_sample_rate > /dev/null

    perf record -e ibs_op/l3missonly=1,cnt_ctl=1/pp --count=$1 --timestamp --data ./test_shadowing > ./temp.log
    perf script -F +addr,+time,+data_src --ns -i ./perf.data > ./script.log
    
    python3 ./filter.py

done


# set enviroment
echo 4 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
echo 1 | sudo tee /proc/sys/kernel/kptr_restrict > /dev/null
echo 2 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null

rm ./temp.log
rm ./perf.data.old
