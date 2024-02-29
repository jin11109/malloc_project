#!/bin/bash

# set enviroment
echo -1 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
echo 0 | sudo tee /proc/sys/kernel/kptr_restrict > /dev/null
echo 0 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null
# 39750

# compile program
gcc -O3 -g ./test_shadowing1.c -o ./test_shadowing1
gcc -O3 -g ./test_shadowing2.c -o ./test_shadowing2

#perf stat -e instructions ./test_perf_hit_random
for (( i=0; i<1; i=i+1 )); do
    echo 150000 | sudo tee /proc/sys/kernel/perf_event_max_sample_rate > /dev/null

    # create the shell with pin tools 
    echo "#!/bin/bash" > ./program.sh
    echo "../pin-3.30-98830-g1d7b601b3-gcc-linux/pin -t ./insert_nop.so -- ./test_shadowing1" >> ./program.sh
    chmod +x ./program.sh    
    
    perf record -e MEM_UOPS_RETIRED.ALL_STORES:ppp,MEM_UOPS_RETIRED.ALL_LOADS:ppp --count=20000 --timestamp --data ./program.sh > ./temp.log
    perf script -F +addr,+time,+data_src --ns -i ./perf.data > ./script.log
    rm ./program.sh
    
    python3 ./filter.py

    #cp ./result.csv ./result${i}.csv
    #cp ./script.log ./script${i}.log
    #cp ./perf.data ./perf${i}.data

    # next test 
    # create the shell with pin tools 
    echo "#!/bin/bash" > ./program.sh
    echo "../pin-3.30-98830-g1d7b601b3-gcc-linux/pin -t ./insert_nop.so -- ./test_shadowing2" >> ./program.sh
    chmod +x ./program.sh 

    perf record -e MEM_UOPS_RETIRED.ALL_STORES:ppp,MEM_UOPS_RETIRED.ALL_LOADS:ppp --count=20000 --timestamp --data ./program.sh > ./temp.log
    perf script -F +addr,+time,+data_src --ns -i ./perf.data > ./script.log
    rm ./program.sh

    python3 ./filter.py

    # original
    perf record -e MEM_UOPS_RETIRED.ALL_STORES:ppp,MEM_UOPS_RETIRED.ALL_LOADS:ppp --count=20000 --timestamp --data ./test_shadowing1 > ./temp.log
    perf script -F +addr,+time,+data_src --ns -i ./perf.data > ./script.log

    python3 ./filter.py

done


# set enviroment
echo 4 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
echo 1 | sudo tee /proc/sys/kernel/kptr_restrict > /dev/null
echo 2 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null

rm ./temp.log
