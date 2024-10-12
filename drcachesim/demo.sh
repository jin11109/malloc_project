#!/bin/bash
set -e

if [ $# == 0 ]; then
    echo "demo.sh : parameter error"
    exit 0
fi

if [ ! "$1" = "online" ] && [ ! "$1" = "offline" ]; then
    echo "choose profiling mode use in drcachesim [online/offline]"
    exit 0
fi

# Get target program paremeter
target_program=""
for ((i = 2; i <= $#; i++)); do
    target_program="$target_program ${!i}"
done

./reset_dirs_files.sh

echo 0 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null

# Compile preload program
if [ "$1" = "online" ]; then
    gcc -shared -fPIC -O3 -pthread -DONLINE ./mymalloc.c -o ./mymalloc.so
elif [ "$1" = "offline" ]; then
    gcc -shared -fPIC -O3 -pthread -DOFFLINE ./mymalloc.c -o ./mymalloc.so
else
    exit 0
fi
sudo cp ./mymalloc.so /lib/

# Compile launcher to execute target program
gcc -O3 ./launcher.c -o ./launcher || { 
    echo "ERROR : compile launcher.c fail";
    exit 0;
}

# start
echo -e "\n\n=============================================================" 
echo -e "start experiment"
echo -e "=============================================================\n\n" 

if [ "$1" = "online" ]; then
    python3 ./data_record.py --profiling_mode online &
    ../../mydynamorio/dynamorio/build/bin64/drrun -t drcachesim -LL_miss_file ./data/cachemisses.csv.gz -- ./launcher $target_program
    # Wait for ./data_record.py
    wait

elif [ "$1" = "offline" ]; then
    if [ ! -e "./dr_raw_data" ]; then
        mkdir "./dr_raw_data"
    else
        rm -r ./dr_raw_data
        mkdir ./dr_raw_data
    fi
    python3 ./data_record.py --profiling_mode offline &
    ../../mydynamorio/dynamorio/build/bin64/drrun -t drcachesim -offline -outdir ./dr_raw_data -- ./launcher  $target_program
    # Wait for ./data_record.py
    wait
    echo "demo.sh : start simulate"
    ../../mydynamorio/dynamorio/build/bin64/drrun -t drcachesim -indir ./dr_raw_data/*$2* -LL_miss_file ./data/cachemisses.csv.gz

else
    exit 0
fi

gzip -d ./data/cachemisses.csv.gz
sed -i '1i miss_addr,pid,miss_time' ./data/cachemisses.csv

# Merge the data from LD_PRELOAD and drcachesim 
python3 ./data_merge.py --profiling_mode $1
cp ./data/endtime ./result/
cp ./data/starttime ./result/

# Show the result
python3 ./data_show.py --profiling_mode $1

rm ./fifo_preload
echo 1 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null