import csv
import re

target_addr = input("input address : ")
pid = input("input pid : ")
rounds = int(input("rounds : "))
f = open("./result.csv", 'w')
writer = csv.writer(f)
writer.writerow(["time"])

start_time = -1
end_time = -1
interval_time = -1

# read first line
with open("./script.log", "r") as script:
    data = script.readline()
    temp = data.strip()
    info = re.split(r'\s+', temp)
    index = 0
    while info[index].isdigit() is not True:
        index += 1
    script_time = float(info[index + 1][0: len(info[index + 1]) - 1])
    start_time = script_time

with open("./script.log", "r") as script:
    script.seek(0, 2)
    end_position = script.tell()
    script.seek(end_position - 500, 0)

    lines = script.readlines()

    if len(lines) >= 2:  # 判断是否最后至少有两行，这样保证了最后一行是完整的
        data = lines[-1]  # 取最后一行
        temp = data.strip()
        info = re.split(r'\s+', temp)
        index = 0
        while info[index].isdigit() is not True:
            index += 1
        script_time = float(info[index + 1][0: len(info[index + 1]) - 1])
        end_time = script_time

    else:
        print("seek error")
        exit()

interval_time = (end_time - start_time) / rounds
print(start_time, end_time, interval_time)

with open("./script.log", "r") as script:
    count = 0
    while True:
        data = script.readline()
        
        if len(data) == 0:
            f.close()
            break
        
        if target_addr not in data or pid not in data:
            continue
        else:
            temp = data.strip()
            # slip data by space
            info = re.split(r'\s+', temp)
            index = 0
            while info[index].isdigit() is not True:
                index += 1
            script_time = float(info[index + 1][0: len(info[index + 1]) - 1])
            script_pid = int(info[index], 10)
            writer.writerow([(script_time - start_time) % interval_time])



#7fffffffd790
#23576