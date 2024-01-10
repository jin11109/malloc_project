import csv
import re

target_addr = int(input("input target address : "), 16)
"""
temp_addr = int(input("input temp address : "), 16)
i_addr = int(input("input i address : "), 16)
n_addr = int(input("input n address : "), 16)
"""
pid = int(input("input pid : "), 10)
target_hit_count = 0
temp_hit_count = 0
i_hit_count = 0
n_hit_count = 0
mem_access_count = 0

with open("./script.log", "r") as script:
    while True:
        data = script.readline()
        
        if len(data) == 0:
            print("target", target_hit_count)
            """
            print("temp", temp_hit_count)
            print("i", i_hit_count)
            print("n", n_hit_count)
            """
            print("mem", mem_access_count + target_hit_count)
            break
        
        temp = data.strip()
        info = re.split(r'\s+', temp) # slip data by space
        
        index = 0
        while info[index].isdigit() is not True:
            index += 1
        #script_time = float(info[index + 1][0: len(info[index + 1]) - 1])
        script_pid = int(info[index], 10)
        data_addr = int(info[index + 4], 16)
        
        if script_pid == pid and data_addr == target_addr:
            target_hit_count += 1
        
        elif data_addr != 0:
            mem_access_count += 1
        else:
            continue

        """
        elif script_pid == pid and data_addr == i_addr:
            i_hit_count += 1
        elif script_pid == pid and data_addr == temp_addr:
            temp_hit_count += 1
        elif script_pid == pid and data_addr == n_addr:
            n_hit_count += 1 
        """


