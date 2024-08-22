About This Part
===
We are no longer using this method for the first part of our project.

What the [shell script](/perf/demo.sh) do?
===
### 1. Produce preload library
For details on [mymalloc.c](/perf/mymalloc.c), please refer to [drcachesim/mymalloc.c](/drcachesim/mymalloc.c)

### 2. Record ma-caller information
For details on [data_record.py](/perf/data_record.py) and [program.sh](/perf/program.sh), please refer to [drcachesim/mymalloc.c](/drcachesim/data_record.py) and [drcachesim/program.c](/drcachesim/program.c)

### 3. Record cache misses information
[demo.sh](/perf/demo.sh#L82) used the Linux *perf* tool to obtain cache miss data, but due to the potential for **skid** in general events, which reduces accuracy, we needed to use special perf events to address this issue. On AMD processors, we utilized IBS technology, while on Intel processors, we used PEBS technology. This part of the project leverages both technologies to collect the necessary data. Notably, AMD's Zen 4 architecture introduced a new feature that perfectly fits our needs. Fortunately, this shell script allows you to select the appropriate tool for your processor by using the parameters intel, amdl3, or amdibs.

### 4. Split the data into chunks
For details on [data_split.py](/perf/data_split.py), please refer to [drcachesim/data_merge.py](/drcachesim/data_split.py)

### 5. Merge the data from ma-caller and perf
For details on [data_merge.py](/perf/data_merge.py), please refer to [drcachesim/data_merge.py](/drcachesim/data_merge.py)

### 6. Show the result of data
For details on [data_merge.py](/perf/data_show.py), please refer to [drcachesim/data_merge.py](/drcachesim/data_merge.py)