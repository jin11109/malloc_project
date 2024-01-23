import csv
import re

target_addr = int(input("input address : "), 16)
target_addr_end = int(input("input address end : "), 16)
pid = int(input("input pid : "), 10)
element_num = int(input("input element num : "), 10)
f = open("./result.csv", 'w')
writer = csv.writer(f)
writer.writerow(["data_index", "count"])

result = [0] * element_num
mem_access_count = 0

with open("./script.log", "r") as script:
    while True:
        data = script.readline()
        
        if len(data) == 0:
            break
        
        temp = data.strip()
        info = re.split(r'\s+', temp) # slip data by space
        
        index = 0
        while info[index].isdigit() is not True:
            index += 1
        #script_time = float(info[index + 1][0: len(info[index + 1]) - 1])
        script_pid = int(info[index], 10)
        data_addr = int(info[index + 4], 16)
        
        if data_addr != 0:
            mem_access_count += 1

        if script_pid == pid and (data_addr < target_addr_end and data_addr >= target_addr):
            data_index = int((data_addr - target_addr) / 8)
            result[data_index] += 1
        else:
            continue

for data_index in range(len(result)):
    writer.writerow([data_index, result[data_index]])

print("mem access_count", mem_access_count)