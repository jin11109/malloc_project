#!/bin/bash
set -e

if [ $# == 0 ]; then
    echo "demo.sh : parameter error"
    exit 0
fi

if [ ! -e "../../DynamoRIO-Linux-10.0.0/samples/build/" ]; then
    ./setenv.sh || {
        echo "ERROR : set DynamoRIO camke fail";
        exit 0;
    }   
fi

echo 0 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null

# compile preload program
#gcc -shared -fPIC -O3 -pthread ./mymalloc.c -o ./mymalloc.so
#sudo cp ./mymalloc.so /lib/

make -C ../../DynamoRIO-Linux-10.0.0/samples/build/ memtrace_x86_text
client_path=../../DynamoRIO-Linux-10.0.0/samples/build/bin/libmemtrace_x86_text.so 

# start
echo -e "\n\n=============================================================" 
echo -e "start experiment"
echo -e "=============================================================\n\n" 
../../DynamoRIO-Linux-10.0.0/bin64/drrun -c $client_path -- $*