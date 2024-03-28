#!/bin/bash
cd ../../DynamoRIO-Linux-10.0.0/samples/

if [ ! -e "./build" ]; then
    mkdir "./build" && cd ./build
else
    echo "environment is already set up"
    exit 0
fi

DYNAMORIO_HOME=$(find ~/ -type d -name "DynamoRIO-Linux-10.0.0")
cmake -DDynamoRIO_DIR=$DYNAMORIO_HOME/cmake $DYNAMORIO_HOME/samples/
