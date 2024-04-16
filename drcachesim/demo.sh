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

echo 0 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null

# compile preload program
gcc -shared -fPIC -O3 -pthread ./mymalloc.c -o ./mymalloc.so
sudo cp ./mymalloc.so /lib/

# compile c to execute target program
gcc -O3 ./program.c -o ./program || { 
    echo "ERROR : compile program.c fail";
    exit 0;
}

# compile c to record start time
gcc -O3 ./record_starttime.c -o ./record_starttime || { 
    echo "ERROR : compile record_starttime.c fail";
    exit 0;
}

# start
echo -e "\n\n=============================================================" 
echo -e "start experiment"
echo -e "=============================================================\n\n" 

./record_starttime
python3 ./data_record.py &
../../mydynamorio/dynamorio/build/bin64/drrun -t drcachesim -LL_miss_file ./data/cachemisses.csv.gz -- ./program $*
#../../mydynamorio/dynamorio/build/bin64/drrun -t drcachesim -LL_miss_file ./data/cachemisses.csv.gz -L0_filter  -- ./program $*

# wait for ./data_record.py
wait

gzip -d ./data/cachemisses.csv.gz 
python3 ./data_split.py

# merge the data from pin tool and LD_PRELOAD function
python3 ./data_merge.py
cp ./data/myaf* ./result/
cp ./data/endtime ./result/
cp ./data/adjustment_time ./result/

# show the result
python3 ./data_show.py

rm ./fifo_preload
echo 1 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null