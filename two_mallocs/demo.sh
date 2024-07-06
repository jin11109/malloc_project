#!/bin/bash
gcc -fPIC -g -c mymalloc_with_cold.c -I./ptmalloc2_with_cold/
gcc -shared ./mymalloc_with_cold.o -L./ptmalloc2_with_cold/ -lptmalloc2_with_cold -o ./mymalloc_with_cold.so

gcc ./test.c -g -o ./test