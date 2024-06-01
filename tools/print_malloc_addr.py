import os
import re

path = input("path:\n")
all_data = os.listdir(path)
result = []
for data in all_data:
    if re.search(r'all_obj', data) is not None:
        output = data.split("_")
        result.append((int(output[0]), output[1]))
        
result.sort()
print("pid_in_drcachesim,pid_real,alloc_index_in_drcachesim,alloc_addr_in_drcachesim,alloc_addr_real,alloc_index_real,temperature,mark")
for i in result:        
    print(f'{i[0]},{i[1]},')
