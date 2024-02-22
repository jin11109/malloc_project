#!/bin/bash

if [ $# == 0 ]; then
    echo "demo.sh : parameter error"
    exit 0
fi

# set enviroment
echo -1 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
echo 0 | sudo tee /proc/sys/kernel/kptr_restrict > /dev/null
echo 0 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null
echo 150000 | sudo tee /proc/sys/kernel/perf_event_max_sample_rate > /dev/null

# compile preload program
gcc -shared -fPIC -O0 -pthread ./mymalloc.c -o ./mymalloc.so
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
program_command="$* 2>> ./fifo"
echo $program_command >> ./program.sh
chmod +x ./program.sh

# create "myperf.data" for perf record
if [ ! -e "./myperf.data" ]; then
    touch "./myperf.data"
fi

# start 
python3 ./data_record.py &
perf record -e ibs_op/cnt_ctl=1/pp --count=50000 --running-time --data -o ./myperf.data ./program.sh
perf script -F +addr,+time,+data_src --ns -i ./myperf.data >> ./fifo

# wait for ./data_capturer.py
wait

rm ./fifo

# set enviroment
echo 4 | sudo tee /proc/sys/kernel/perf_event_paranoid > /dev/null
echo 1 | sudo tee /proc/sys/kernel/kptr_restrict > /dev/null
echo 2 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null

python3 ./data_merge.py
python3 ./data_show.py

#rm -r ./data