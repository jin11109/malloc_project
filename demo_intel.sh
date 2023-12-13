#!/bin/bash

if [ $# == 0 ]; then
    echo "demo.sh : parameter error"
    exit 0
fi

# set enviroment
echo -1 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
echo 0 | sudo tee /proc/sys/kernel/kptr_restrict > /dev/null
echo 0 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null
echo 400000 | sudo tee /proc/sys/kernel/perf_event_max_sample_rate > /dev/null
# 39750

# compile preload program
gcc -shared -fPIC -O0 -pthread ./mymalloc.c -o ./mymalloc.so
sudo cp ./mymalloc.so /lib/
#if [ ! -e "/home/jin/project/project/mymalloc.so" ]; then
#    echo "demo : mymalloc.so not at /home/jin/project/project/mymalloc.so"
#    exit 0
#fi

# create fifo
if [ ! -e "./fifo" ]; then
    mkfifo "./fifo"
else
    rm ./fifo
    mkfifo "./fifo"
fi

if [ ! -e "./data" ]; then
    mkdir "./data"
fi

if [ ! -e "./result" ]; then
    mkdir "./result"
fi
# create the shell with preload 
echo "#!/bin/bash" > ./program.sh
#echo "export LD_PRELOAD=\$LD_PRELOAD:/home/jin/project/project/mymalloc.so" >> ./program.sh
echo "export LD_PRELOAD=\$LD_PRELOAD:/lib/mymalloc.so" >> ./program.sh
program_command="$* 2>> ./fifo"
echo $program_command >> ./program.sh
chmod +x ./program.sh

# create 
if [ ! -e "./myperf.data" ]; then
    touch "./myperf.data"
fi

# start 
python3 ./data_record.py &
perf record -e mem-stores:ppp,mem-loads:ppp -F max --running-time --data -o ./myperf.data ./program.sh
perf script -F +addr,+time,+data_src -i ./myperf.data >> ./fifo

# wait for ./data_capturer.py
wait

rm ./fifo
perf report -i ./myperf.data

# set enviroment
echo 4 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
echo 1 | sudo tee /proc/sys/kernel/kptr_restrict > /dev/null
echo 2 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null

#python3 ./data_merge.py
#python3 ./data_show.py

#rm -r ./data