About This Ptmalloc2
===

This package is a modified version of Wolfram Gloger's ptmalloc2 (http://www.malloc.de/en/).

### Our target :

We want to customize this ptmalloc2 to handle allocation requests from specific addresses, ensuring that it does not conflict with the native glibc malloc on the system.
We will list our modification in final part.

Quick start
===
To singly build this version of ptmalloc2 just use :
 
``` bash
#in ptmalloc2_with_cold folder
#for linux have pthread
make linux-malloc.so
```
After this, *libptmalloc2_with_cold.so* will occur in *ptmalloc2_with_cold* folder.

**compile way :** The simple way to use this library is just linking the *libptmalloc2_with_cold.so* and use the head file *_my_malloc.h* to call the public functions in the library.

There is a simple C example for using this ptmalloc2
```c
/* You should put ptmalloc2_with_cold folder in your root of workplace first */
#include <stdio.h>
/* System glibc malloc */
#include <malloc.h>
/* _my_ version of ptmalloc2 */
#include "ptmalloc2_with_cold/_my_malloc.h"

int main() {
    int* ptr_from_system_glibc = malloc(sizeof(int));
    void* ptr = _my_realloc(ptr_from_system_glibc, sizeof(int) * 2);
    if (is_flag_mmapped(ptr)) {
        printf("This new memory is alloced directly by mmap\n");
    } else if (is_flag_notmy(ptr)) {
        printf("The address, ptr_from_system_glibc, is not alloced by _my_ version\n");
    } else {
        printf("This represent it use _my_realloc to alloc memory and not directly use mmap\n");
    }

    /* For using this return value, you should unable flag first*/
    int* int_array = (int*)(unable_flag(ptr));
}
```

##
Modification
===
### To avoid symbol conflicts : 
We use a lot of definition in *_my_malloc.c* to rename functions' name and variables' name by the prefix **"\_my\_"**.

### To avoid errors related to using brk() and sbrk() :
Because we cannot ensure that all allocation requests are handled by our custom malloc, some requests will still be managed by the native system's glibc malloc. This situation may cause both types of malloc to simultaneously use the **"main_arena"** and indirectly use **brk()** or **sbrk()** for allocation. To prevent this issue, we have disabled the **"main_arena"** in this implementation of ptmalloc2.

### To prevent this version of ptmalloc2 from attempting to free (realloc) memory allocated by another malloc.
Due to the previously mentioned issue of having more than one versions of malloc coexisting, there is a risk that this implementation of ptmalloc2 might attempt to free or realloc memory maintained by another version of malloc. This could lead to unpredictable errors. Therefore, we have added two checks in the **"public_free()"** and **"public_realloc()"** function:

1. Check if the allocation belongs to the **main_area**.
2. Use the size field in the **"heap_info"** structure, which we deliberately modify during creation, to identify the allocation.
We set the highest five bits of the **"heap_info"** **size** field to **"0b10101"** as below.

        struct heap_info 
        |+-+-+-+-+-+-+-+-+-+- ar_ptr +-+-+-+-+-+-+-+-+-+-|
        |+-+-+-+-+-+-+-+-+-+- *prev +-+-+-+-+-+-+-+-+-+-+|
        |1|0|1|0|1|+-+-+-+-+-+ size +-+-+-+-+-+-+-+-+-+-+|
        |+-+-+-+-+-+-+-+-+-+-+ pad +-+-+-+-+-+-+-+-+-+-+-|


Additionally, if more than two versions of malloc need to coexist, these five bits can be customized to create a unique identifier for each version of malloc.

### To easily obtain information about this version of ptmalloc2:
When using this version of ptmalloc2, it is likely that you will need some important additional information during memory allocation. For example, to determine whether the memory address passed to the **free** function belongs to the space maintained by this version, you must pass this information in some way. Therefore, we have modified the return values of **malloc**, **calloc**, **realloc**, and **free** to use the highest two bits to identify whether the space is not maintained by this version (**is_flag_notmy**) and whether the space is directly mapped (**is_flag_mmapped**). These definitions can be found in *_my_malloc.h*.

The reason we can make these modifications is that ptmalloc2 is used in user space, and due to its addressing range, the highest few bits are not utilized. Thus, we use them to convey the necessary information.

        M : represent whether is mmaped
        V : represent whether is belong to this version 
        x : not consider

        return values
        _my_malloc  : |x|M|-+-+-+ (void*)return values +-+-++-+|
        _my_calloc  : |x|M|-+-+-+ (void*)return values +-+-++-+|
        _my_realloc : |V|M|-+-+-+ (void*)return values +-+-++-+|
        _my_free    : |V|x|-+-+-+ (void*)return values +-+-++-+|


### To facilitate analysis in "two_mallocs":

To simplify future analysis processes, we ensure that the **"heap"** in ptmalloc2 is never truly deleted. This approach allows ptmalloc2 to reuse the virtual memory addresses without releasing the entire heap space. The benefit is that we can directly compare the heap range with the results from other analysis tools. For example, when using DynamoRIO to obtain cache miss information, we can directly compare it with the heap range to determine if it falls within the area managed by our ptmalloc2.