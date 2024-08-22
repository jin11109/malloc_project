About This Part
===
This section applies to the second part of our project, where we will use this framework to simulate experiments and analyze the impact of separating ma-callers under ideal living conditions.

![alt text](/doc/image/two_identical_allocators_framework.png)

What the shell script do?
===
### 1. Produce ma-callers table
[produce_cold_addrs.py](/two_mallocs/produce_cold_addrs.py) will use the results from the first part of the project to generate a C language header file *cold_addrs.h*, which defines a global array indicating whether an ma-caller is cold.

### 2. Prepare allocator library, two ptmalloc2
We use [ptmalloc2_with_cold/](/two_mallocs/ptmalloc2_with_cold/) as our memory allocator. And use [clone_another_ptmalloc2.sh](/two_mallocs/clone_another_ptmalloc2.sh) to create an identical copy of ptmalloc2 and modify some identifiers using text replacement.

### 3. Prepare preload library
We write [mymalloc_with_cold.c](/two_mallocs/mymalloc_with_cold.c) as preload library. This will handle allocation requests and then choose which ptmalloc2 to call based on the result of *produce_cold_addrs.py*, *cold_addrs.h*. And, we use [program.c](/two_mallocs/program.c) sets the `LD_PRELOAD` environment variable to ensure that the test program uses our custom dynamic library.

### 4. Record data in runtime
*ptmalloc2_with_cold/* will output some `heap` information in runtime. We use [data_record.py](/two_mallocs/data_record.py) and passing information through a named pipe(fifo) to record this data as CSV file.

### 5. Process the data
After the experiment is completed, [data_reusedistance_space.py](/two_mallocs/data_reusedistance_space.py) [data_reusedistance_time.py](/two_mallocs/data_reusedistance_time.py) will be automatically called to process the data. Notably, *data_reusedistance_space.py* uses the LRU algorithm to calculate the reuse distance of pages.