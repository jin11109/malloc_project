#!/bin/bash
set -e

if [ $# == 0 ]; then
    echo "demo.sh : parameter error, input a service"
    exit 0
fi

echo 0 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null

# for producing a file which has variables in and can be included by preload library
cd ./two_mallocs
python3 ./produce_cold_addrs.py
cd ..

# build preload library and two mallocs library in docker
docker-compose build $*
# run program in docker
docker-compose up $*

echo 1 | sudo tee /proc/sys/kernel/randomize_va_space > /dev/null