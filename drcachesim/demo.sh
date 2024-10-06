#!/bin/bash
set -e

if [ $# == 0 ]; then
    echo "demo.sh : parameter error"
    exit 0
fi

if [ ! "$1" = "online" ] && [ ! "$1" = "offline" ]; then
    echo "choose profiling use in drcachesim [online/offline]"
    exit 0
fi

# get target program paremeter
target_program=""
for ((i = 2; i <= $#; i++)); do
    target_program="$target_program ${!i}"
done

./reset_dirs_files.sh

echo 0 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null

# compile preload program
if [ "$1" = "online" ]; then
    gcc -shared -fPIC -O3 -pthread -DONLINE ./mymalloc.c -o ./mymalloc.so
elif [ "$1" = "offline" ]; then
    gcc -shared -fPIC -O3 -pthread -DOFFLINE ./mymalloc.c -o ./mymalloc.so
else
    exit 0
fi
sudo cp ./mymalloc.so /lib/

# compile launcher to execute target program
gcc -O3 ./launcher.c -o ./launcher || { 
    echo "ERROR : compile launcher.c fail";
    exit 0;
}

# compile c to record start time
gcc -O3 ./record_time.c -o ./record_time || { 
    echo "ERROR : compile record_starttime.c fail";
    exit 0;
}

# start
echo -e "\n\n=============================================================" 
echo -e "start experiment"
echo -e "=============================================================\n\n" 

if [ "$1" = "online" ]; then
    python3 ./data_record.py &
    ../../mydynamorio/dynamorio/build/bin64/drrun -t drcachesim -LL_miss_file ./data/cachemisses.csv.gz -- ./launcher $target_program
    # wait for ./data_record.py
    wait

elif [ "$1" = "offline" ]; then
    if [ ! -e "./dr_raw_data" ]; then
        mkdir "./dr_raw_data"
    else
        rm -r ./dr_raw_data
        mkdir ./dr_raw_data
    fi
    python3 ./data_record.py &
    ../../mydynamorio/dynamorio/build/bin64/drrun -t drcachesim -offline -outdir ./dr_raw_data -- ./launcher  $target_program
    # wait for ./data_record.py
    wait
    echo "demo.sh : start simulate"
    ../../mydynamorio/dynamorio/build/bin64/drrun -t drcachesim -indir ./dr_raw_data/*$2* -LL_miss_file ./data/cachemisses.csv.gz

else
    exit 0
fi

gzip -d ./data/cachemisses.csv.gz 
# python3 ./data_split.py

# # merge the data from pin tool and LD_PRELOAD function
# python3 ./data_merge.py
# cp ./data/myaf* ./result/
# cp ./data/endtime ./result/
# cp ./data/adjustment_time ./result/

# # show the result
# python3 ./data_show.py

# rm ./fifo_preload
# echo 1 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null