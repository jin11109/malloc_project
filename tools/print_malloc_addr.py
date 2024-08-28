import os
import re
import csv

path = input("dir path:\n")
pid = input("pid:\n")
temperature = input("temperature:\n")

all_data = os.listdir(path)
result = []
for data in all_data:
    if re.search(r'all_obj', data) is not None:
        output = data.split("_")
        result.append((int(output[0]), output[1]))

filename = 'cold_alloc_addr_table.csv'
file_exists = os.path.exists(filename)
if file_exists:
    data = []
else:
    data = [
        ['pid_in_drcachesim', 'pid_real', 'alloc_index_in_drcachesim', 'alloc_addr_in_drcachesim', 
         'alloc_addr_real', 'alloc_index_real', 'temperature', 'symbol', 'position', 'mark'],
    ]

result.sort()
for i in result:
    per_data = [pid, None, i[0], i[1], None, None, temperature, None, None, None]
    data.append(per_data)


with open(filename, 'a' if file_exists else 'w') as csvfile:
    csvwriter = csv.writer(csvfile)
    for row in data:
        csvwriter.writerow(row)
