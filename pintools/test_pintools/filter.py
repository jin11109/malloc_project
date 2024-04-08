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
    pattern_addr = int(number[0], 16)
    print("pattern addr :", pattern_addr)

    data = f.readline()
    number = re.findall(r'0x[0-9a-fA-F]+|\d+', data)
    pattern_addr_end = int(number[0], 16)
    print("pattern addr end :", pattern_addr_end)


    data = f.readline()
    number = re.findall(r'0x[0-9a-fA-F]+|\d+', data)
    pid = int(number[0], 10)
    print("pid :", pid)

    data = f.readline()
    number = re.findall(r'0x[0-9a-fA-F]+|\d+', data)
    element_num = int(number[0], 10)
    print("element num :", element_num)

mem_access_count = 0
target_access_count = 0
pattern_access_count = 0
target_hit_event_count = {}
pattern_hit_event_count = {}

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

        if script_pid == pid and (data_addr <= target_addr_end and data_addr >= target_addr):
            target_access_count += 1

            if target_hit_event_count.get(info[index + 3]) is None:
                target_hit_event_count[info[index + 3]] = 0
            target_hit_event_count[info[index + 3]] += 1
        
        if script_pid == pid and (data_addr <= pattern_addr_end and data_addr >= pattern_addr):
            pattern_access_count += 1

            if pattern_hit_event_count.get(info[index + 3]) is None:
                pattern_hit_event_count[info[index + 3]] = 0
            pattern_hit_event_count[info[index + 3]] += 1
         

        else:
            continue

print("mem access count", mem_access_count)
print("target access count", target_access_count)
print(target_hit_event_count)

print("pattern access count", pattern_access_count)
print(pattern_hit_event_count)
