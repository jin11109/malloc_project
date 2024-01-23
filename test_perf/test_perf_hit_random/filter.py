import csv
import re

with open("./temp.log", 'r') as f:
    data = f.readline()
    number = re.findall(r'0x[0-9a-fA-F]+|\d+', data)
    target_addr = int(number[0], 16)
    print("target addr :", target_addr)

    data = f.readline()
    number = re.findall(r'0x[0-9a-fA-F]+|\d+', data)
    target_addr_end = int(number[0], 16)
    print("target addr end :", target_addr_end)

    data = f.readline()
    number = re.findall(r'0x[0-9a-fA-F]+|\d+', data)
    pid = int(number[0], 10)
    print("pid :", pid)

    data = f.readline()
    number = re.findall(r'0x[0-9a-fA-F]+|\d+', data)
    element_num = int(number[0], 10)
    print("element num :", element_num)


f = open("./result.csv", 'w')
writer = csv.writer(f)
writer.writerow(["data_index", "count"])

result = [0] * element_num
mem_access_count = 0
target_access_count = 0

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
            target_access_count += 1
        else:
            continue

for data_index in range(len(result)):
    writer.writerow([data_index, result[data_index]])

print("mem access count", mem_access_count)
print("target access count", target_access_count)