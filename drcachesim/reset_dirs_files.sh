#!/bin/bash

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

if [ -f "./timmer" ]; then
    rm ./timmer
fi

if [ -f "./data/cachemisses.csv" ]; then
    rm ./data/cachemisses.csv
fi