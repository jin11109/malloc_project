#!/bin/bash

if [ $# == 0 ]; then
    echo "demo.sh : parameter error"
    exit 0
fi

# compile pin tools
cp ./catch_ldst.cpp ../../pin/source/tools/ManualExamples/
mkdir ../../pin/source/tools/ManualExamples/obj-intel64/
make -C ../../pin/source/tools/ManualExamples/ obj-intel64/catch_ldst.so TARGET=intel64
cp ../../pin/source/tools/ManualExamples/obj-intel64/catch_ldst.so ./

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
program_command="$* 2>> ./fifo"
echo $program_command >> ./program.sh
chmod +x ./program.sh

# start
echo -e "\n\n=============================================================\n\n" 
echo -e "start experiment\n"
#python3 ./data_record.py &
cat ./fifo &
../../pin/pin -follow_execv -t /catch_ldst.so -- ./program.sh

# wait for ./data_record.py
#wait

# merge the data from pin tool and LD_PRELOAD function
#python3 ./data_merge.py
#cp ./data/myaf* ./result/
#cp ./data/endtime ./result/
#cp ./data/adjustment_time ./result/

# show the result
#python3 ./data_show.py

rm ./fifo
