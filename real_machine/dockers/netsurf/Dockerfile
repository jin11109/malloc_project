FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    netsurf \
    time \
    make \
    gcc

COPY ./two_mallocs /opt/two_mallocs
WORKDIR /opt/two_mallocs

# build two malloc
RUN make -C ./ptmalloc2_with_cold/ linux-malloc.so
RUN ./clone_another_ptmalloc2.sh
RUN make -C ./ptmalloc2_with_cold_2/ linux-malloc.so
RUN cp ./ptmalloc2_with_cold/libptmalloc2_with_cold.so /lib/
RUN cp ./ptmalloc2_with_cold_2/libptmalloc2_with_cold_2.so /lib/
# compile preload program
RUN gcc -fPIC -g -c mymalloc_with_cold.c -I./ptmalloc2_with_cold/ -I./ptmalloc2_with_cold_2/
RUN gcc -shared ./mymalloc_with_cold.o -L./ptmalloc2_with_cold/ -L./ptmalloc2_with_cold_2/ -lptmalloc2_with_cold -lptmalloc2_with_cold_2 -lpthread -o ./mymalloc_with_cold.so
RUN cp ./mymalloc_with_cold.so /lib/
# compile c to execute target program
RUN gcc -O3 ./program.c -o ./program
