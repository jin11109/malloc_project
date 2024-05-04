#!/bin/bash

if [ $# == 0 ]; then
    echo "demo.sh : parameter error"
    echo "usage : ./demo.sh [intel/amd] target_program"
    exit 0
fi

if [ ! "$1" = "amd" ] && [ ! "$1" = "intel" ]; then
    echo "choose arch (amd/intel)"
    exit 0
fi

# get target program paremeter
target_program=""
for ((i = 2; i <= $#; i++)); do
    target_program="$target_program ${!i}"
done

# set enviroment
echo -1 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
echo 0 | sudo tee /proc/sys/kernel/kptr_restrict > /dev/null
echo 0 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null
echo 150000 | sudo tee /proc/sys/kernel/perf_event_max_sample_rate > /dev/null

# compile preload program
gcc -shared -fPIC -O3 -pthread ./mymalloc.c -o ./mymalloc.so
sudo cp ./mymalloc.so /lib/

# create fifo
if [ ! -e "./fifo" ]; then
    mkfifo "./fifo"
else
    rm ./fifo
    mkfifo "./fifo"
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

# create the shell with preload 
echo "#!/bin/bash" > ./program.sh
echo "export LD_PRELOAD=\$LD_PRELOAD:/lib/mymalloc.so" >> ./program.sh
echo "$target_program 2>> ./fifo" >> ./program.sh
chmod +x ./program.sh

# create "myperf.data" for perf record
if [ ! -e "./myperf.data" ]; then
    touch "./myperf.data"
fi

# start 
python3 ./data_record.py &

# for amd cpu
if [ "$1" = "amd" ]; then
    #perf record -e ibs_op/cnt_ctl=1/pp --count=50000 --timestamp --data -o ./myperf.data ./program.sh
    perf record -e ibs_op/l3missonly=1,cnt_ctl=1/pp --count=1000 --timestamp --data -o ./myperf.data ./program.sh
# for intel cpu
elif [ "$1" = "intel" ]; then
    #perf record -e MEM_UOPS_RETIRED.ALL_STORES:ppp,MEM_UOPS_RETIRED.ALL_LOADS:ppp --count=20000 --timestamp --data -o ./myperf.data ./program.sh
    perf record -e MEM_LOAD_UOPS_RETIRED.L3_MISS:ppp --count=500 --timestamp --data -o ./myperf.data ./program.sh
else
    echo "choose arch (amd/intel)"
    exit 0
fi
# wait for ./data_record.py
wait

# transfer myperf.data and split the result in small chunks
python3 ./data_split.py &
perf script -F +addr,+time,+data_src --ns -i ./myperf.data >> ./fifo
# wait for ./data_split.py
wait

rm ./fifo

python3 ./data_merge.py
cp ./data/myaf* ./result/
cp ./data/endtime ./result/
cp ./data/adjustment_time ./result/

python3 ./data_show.py

# set enviroment
echo 4 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
echo 1 | sudo tee /proc/sys/kernel/kptr_restrict > /dev/null
echo 2 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null
