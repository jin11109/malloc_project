#!/bin/bash
set -e

if [ $# == 0 ]; then
    echo "demo.sh : parameter error"
    exit 0
fi

# create fifo for preload fubction
if [ ! -e "./fifo_preload" ]; then
    mkfifo "./fifo_preload"
else
    rm ./fifo_preload
    mkfifo "./fifo_preload"
fi

# this "data" folder include data from "data_record.py" and the temporary files from "data_merge.py"  
if [ ! -e "./data" ]; then
    mkdir "./data"
else
    rm -r ./data
    mkdir "./data"
fi

# this "result" folder include data from "data_merge.py" for "data_show.py" 
if [ ! -e "./result" ]; then
    mkdir "./result"
else
    rm -r ./result
    mkdir ./result
fi

if [ ! -e "./result_picture" ]; then
    mkdir "./result_picture"
else
    rm -r ./result_picture
    mkdir ./result_picture
fi

if [ ! -f "./event_moment.txt" ]; then
    touch "./event_moment.txt"
else
    rm ./event_moment.txt
    touch ./event_moment.txt
fi

echo 0 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null

# for producing a file which has variables in and can be included by preload library
python3 ./produce_cold_addrs.py

# compile preload program
gcc -fPIC -g -c mymalloc_with_cold.c -I./ptmalloc2_with_cold/ -I./ptmalloc2_with_cold_2/
gcc -shared ./mymalloc_with_cold.o -L./ptmalloc2_with_cold/ -L./ptmalloc2_with_cold_2/ -lptmalloc2_with_cold -lptmalloc2_with_cold_2 -lpthread -o ./mymalloc_with_cold.so
sudo cp ./mymalloc_with_cold.so /lib/
# also copy ptmalloc2 library to /lib/
make -C ./ptmalloc2_with_cold/ linux-malloc.so
./clone_another_ptmalloc2.sh
make -C ./ptmalloc2_with_cold_2/ linux-malloc.so
sudo cp ./ptmalloc2_with_cold/libptmalloc2_with_cold.so /lib/
sudo cp ./ptmalloc2_with_cold_2/libptmalloc2_with_cold_2.so /lib/

# compile c to execute target program
gcc -O3 ./program.c -o ./program || { 
    echo "ERROR : compile program.c fail";
    exit 0;
}

# start
echo -e "\n\n=============================================================" 
echo -e "start experiment"
echo -e "=============================================================\n\n" 

python3 ./data_record.py &
../../mydynamorio/dynamorio/build/bin64/drrun -t drcachesim -LL_miss_file ./data/cachemisses.csv.gz -- ./program $*
#../../mydynamorio/dynamorio/build/bin64/drrun -t drcachesim -LL_miss_file ./data/cachemisses.csv.gz -L0_filter  -- ./program $*

# wait for ./data_record.py
wait

gzip -d ./data/cachemisses.csv.gz 
sed -i '1i addr,pid' ./data/cachemisses.csv

# caculate page reuse distance and output files in result_picture
python3 ./data_reusedistance.py

rm ./fifo_preload
echo 1 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null