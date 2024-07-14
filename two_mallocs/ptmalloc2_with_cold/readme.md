About This Ptmalloc2
===

This package is a modified version of Wolfram Gloger's ptmalloc2 (http://www.malloc.de/en/).

### Our target :

We want to customize this ptmalloc2 to handle allocation requests from specific addresses, ensuring that it does not conflict with the native glibc malloc on the system.
We will list our modification in final part.

How to build
===
To singly build this version of ptmalloc2 just use :
 
``` bash
#in ptmalloc2_with_cold folder
#for linux have pthread
make linux-malloc.so
```
After this, *libptmalloc2_with_cold.so* will occur in *ptmalloc2_with_cold* folder.

**Quick start :** The simple way to use this library is just linking the *libptmalloc2_with_cold.so* and use the head file *_my_malloc.h* to call the public functions in the library.

##
Modification
===
### To avoid symbol conflicts : 
We use a lot of definition in *_my_malloc.c* to rename functions' name and variables' name by the prefix **"\_my\_"**.

### To avoid errors related to using brk() and sbrk() :
Because we cannot ensure that all allocation requests are handled by our custom malloc, some requests will still be managed by the native system's glibc malloc. This situation may cause both types of malloc to simultaneously use the **"main_arena"** and indirectly use **brk()** or **sbrk()** for allocation. To prevent this issue, we have disabled the **"main_arena"** in this implementation of ptmalloc2.

### To prevent this version of ptmalloc2 from attempting to free memory allocated by another malloc.
Due to the previously mentioned issue of having two versions of malloc coexisting, there is a risk that this implementation of ptmalloc2 might attempt to free memory maintained by another version of malloc. This could lead to unpredictable errors. Therefore, we have added two checks in the **"public_free()"** function:

1. Check if the allocation belongs to the **main_area**.
2. Use the size field in the **"heap_info"** structure, which we deliberately modify during creation, to identify the allocation.
We set the highest five bits of the **"heap_info"** **size** field to **"0b10101"** as below.

        struct heap_info 
    
        |+-+-+-+-+-+-+-+-+-+- ar_ptr +-+-+-+-+-+-+-+-+-+-|

        |+-+-+-+-+-+-+-+-+-+- *prev +-+-+-+-+-+-+-+-+-+-+|
    
        |1|0|1|0|1|+-+-+-+-+-+ size +-+-+-+-+-+-+-+-+-+-+|

        |+-+-+-+-+-+-+-+-+-+-+ pad +-+-+-+-+-+-+-+-+-+-+-|


Additionally, if more than two versions of malloc need to coexist, these five bits can be customized to create a unique identifier for each version of malloc.