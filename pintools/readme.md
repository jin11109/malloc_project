About This Part
===
We are no longer using this method for the first part of our project.

What the [shell script](/pintools/demo.sh) do?
===
### 1. Produce preload library
For details on [mymalloc.c](/pintools/mymalloc.c), please refer to [drcachesim/mymalloc.c](/drcachesim/mymalloc.c)

### 2. Record ma-caller information
For details on [data_record.py](/pintools/data_record.py), please refer to [drcachesim/mymalloc.c](/drcachesim/data_record.py)

### 3. Record cache misses information
We use pintools to obtain cache miss information, writing a tool [catch_ldst.cpp](/pintools/catch_ldst.cpp) to capture each load and store instruction. Additionally, we wrote [cachesim.c](/pintools/cachesim.c) to simulate cache behavior at runtime, with communication carried out through named pipes.

### 4. Merge the data from ma-caller and pintools
For details on [data_merge.py](/pintools/data_merge.py), please refer to [drcachesim/data_merge.py](/drcachesim/data_merge.py)

### 5. Show the result of data
For details on [data_merge.py](/pintools/data_show.py), please refer to [drcachesim/data_merge.py](/drcachesim/data_merge.py)