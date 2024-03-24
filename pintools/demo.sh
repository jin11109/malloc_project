#!/bin/bash

set -e

if [ $# == 0 ]; then
    echo "demo.sh : parameter error"
    exit 0
fi

# 
echo 0 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null

# compile pin tools
cp ./catch_ldst.cpp ../../pin/source/tools/ManualExamples/
if [ ! -e "../../pin/source/tools/ManualExamples/obj-intel64/" ]; then
    mkdir "../../pin/source/tools/ManualExamples/obj-intel64/"
fi
make -C ../../pin/source/tools/ManualExamples/ obj-intel64/catch_ldst.so TARGET=intel64
cp ../../pin/source/tools/ManualExamples/obj-intel64/catch_ldst.so ./ 

# compile preload program
gcc -shared -fPIC -O3 -pthread ./mymalloc.c -o ./mymalloc.so
sudo cp ./mymalloc.so /lib/

# compile cache simulation program
gcc -O3 ./cachesim.c -o ./cachesim || { 
    echo "ERROR : compile cache simulation program fail";
    exit 0;
}

# create fifo for preload fubction
if [ ! -e "./fifo_preload" ]; then
    mkfifo "./fifo_preload"
else
    rm ./fifo_preload
    mkfifo "./fifo_preload"
fi

# create fifo for intel pin tools
if [ ! -e "./fifo_pintools" ]; then
    mkfifo "./fifo_pintools"
else
    rm ./fifo_pintools
    mkfifo "./fifo_pintools"
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
program_command="$* 2>> ./fifo_preload"
echo $program_command >> ./program.sh
chmod +x ./program.sh

# start
echo -e "\n\n=============================================================\n\n" 
echo -e "start experiment\n"

python3 ./data_record.py &
./cachesim &
#cat ./fifo_pintools &
#cat ./fifo_preload &
../../pin/pin -follow_execv -t /catch_ldst.so -- ./program.sh

# wait for ./data_record.py
wait

echo 1 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null

# merge the data from pin tool and LD_PRELOAD function
python3 ./data_merge.py
cp ./data/myaf* ./result/
cp ./data/endtime ./result/
cp ./data/adjustment_time ./result/

# show the result
python3 ./data_show.py

rm ./fifo_pintools ./fifo_preload
