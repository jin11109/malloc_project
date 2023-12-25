import csv
import re

target_addr = int(input("input address : "), 16)
target_addr_end = int(input("input address end :"), 16)
pid = int(input("input pid : "), 10)
f = open("./result.csv", 'w')
writer = csv.writer(f)
writer.writerow(["data_addr", "count"])

#result = {}
result = [0] * 1000

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
        
        if script_pid == pid and (data_addr < target_addr_end and data_addr >= target_addr):
            data_index = int((data_addr - target_addr) / 4)
            result[data_index] += 1
        else:
            continue

for data_index in range(len(result)):
    writer.writerow([data_index, result[data_index]])

