#!/bin/bash
mkdir ../../DynamoRIO-Linux-10.0.0/samples/build
cd ../../DynamoRIO-Linux-10.0.0/samples/build/

DYNAMORIO_HOME=$(find ~/ -type d -name "DynamoRIO-Linux-10.0.0")
cmake -DDynamoRIO_DIR=$DYNAMORIO_HOME/cmake $DYNAMORIO_HOME/samples/
