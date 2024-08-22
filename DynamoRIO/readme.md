About This Part
===
We are no longer using this method for the first part of our project.

What the [shell script](/DynamoRIO/demo.sh) do?
===
### 1. Produce preload library
For details on [mymalloc.c](/DynamoRIO/mymalloc.c), please refer to [drcachesim/mymalloc.c](/drcachesim/mymalloc.c)

### 2. Record ma-caller information
For details on [data_record.py](/DynamoRIO/data_record.py) and [program.c](/DynamoRIO/program.c), please refer to [drcachesim/mymalloc.c](/drcachesim/data_record.py) and [drcachesim/program.c](/drcachesim/program.c)

### 3. Record cache misses information
We use the more general features of DynamoRIO to obtain cache miss information, utilizing its sample code [memtrace_x86](/DynamoRIO/memtrace_x86.c) to capture each load and store instruction. Additionally, we wrote [cachesim.c](/DynamoRIO/cachesim.c) to simulate cache behavior at runtime, with communication carried out through named pipes.

### 4. Merge the data from ma-caller and DynamoRIO
For details on [data_merge.py](/DynamoRIO/data_merge.py), please refer to [drcachesim/data_merge.py](/drcachesim/data_merge.py)

### 5. Show the result of data
For details on [data_merge.py](/DynamoRIO/data_show.py), please refer to [drcachesim/data_merge.py](/drcachesim/data_merge.py)