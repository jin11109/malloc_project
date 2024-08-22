About This Part
===
This section applies to the first part of our project. We will use this framework to observe the behavior of dynamic memory objects. This framework employs a specialized allocator for subsequent analysis and observation. During data processing, it will determine the properties of ma-callers, ultimately producing a series of charts for review.

![alt text](/doc/image/data_collection_framework.png)

What the [shell script](/drcachesim/demo.sh) do?
===
### 1. Produce preload library
[mymalloc.c](/drcachesim/mymalloc.c) builds a dynamic library witch redefines *malloc*, *realloc*, *calloc*, and *free* functions. This dynamic library allocates space using memory pools, with a unique feature that objects from the same ma-caller are placed consecutively in the same memory pool. Additionally, each object is preceded by metadata and padding. The metadata records the size of the object, while the padding ensures that when writing to the metadata or accessing adjacent objects, the cache does not simultaneously pull both the metadata and the object or multiple objects into the cache. Without padding, it would be difficult to determine which object or metadata is responsible for compulsory miss events.

The library pass ma-caller information through `stderr`.

### 2. Record ma-caller information
Before the experiment begins, we use [program.c](/drcachesim/program.c) to redirect `stderr` to a named pipe(fifo), with [data_record.py](/drcachesim/data_record.py) recording this information. At the same time, *program.c* also sets the `LD_PRELOAD` environment variable to ensure that the test program uses our custom dynamic library.

### 3. Record cache misses information
We use the *drcachesim* feature in *DynamoRIO* to simulate cache behavior and use the `-LL_miss_file` option to output data during execution. However, this option currently does not provide enough information for our experiments, so we have made some modifications to parts of this open-source software.

### 4. Split the data into chunks
After the experiment, due to the large size of the raw data and the frequent need for join operations during subsequent processing, we use [data_split.py](/drcachesim/data_split.py) to divide the data into several chunks for processing.

### 5. Merge the data from ma-caller and drcachesim
Due to the large size of the data, [data_merge.py](/drcachesim/data_merge.py) use `Vaex` in Python to handle the data. In this program we employ various memory optimization techniques.

### 6. Show the result of data
After the data is prepared, we use [data_show.py](/drcachesim/data_show.py) prepares various charts based on the collected data and use a formula to determine whether an ma-caller is "cold."