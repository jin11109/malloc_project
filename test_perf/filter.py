import csv
import re

bin_addr = []

with open("./temp.log", 'r') as f:
    for i in range(0, 4):
        data = f.readline()
        number = re.findall(r'0x[0-9a-fA-F]+|\d+', data)
        bin_addr.append((int(number[1], 16), int(number[2], 16)))
        print(f"bin{i} addr :", bin_addr[-1])

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
writer.writerow(["bin", "count", "current_total_hit", "porpotion", "time"])

start_time = -1
last_record_time = 0
current_total_hit = 0
count = [0, 0, 0, 0]

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
        script_time = float(info[index + 1][0: len(info[index + 1]) - 1])
        script_pid = int(info[index], 10)
        data_addr = int(info[index + 4], 16)

        if start_time == -1:
            start_time = script_time
            last_record_time = script_time

        if script_time - last_record_time >= 1:
            if current_total_hit != 0:
                for i in range(0, 4):
                    writer.writerow([i, count[i], current_total_hit, count[i] / current_total_hit, script_time])
            last_record_time = script_time
        
        for i in range(0, 4):
            if pid == script_pid and (data_addr >= bin_addr[i][0] and data_addr <= bin_addr[i][1]):
                count[i] += 1
                current_total_hit += 1


print("count", count)