import time
import csv
import re
import numpy as np
from progressbar import*
from pathlib import Path

# file_names[pid][datatype] = filename
file_names = {}
filesript_names = {}
fileresult_names = {}
file_writers = {}
files_to_close = []
end_time = 0

count = 0

# tools
def is_hexadecimal(input_str):
    return all(c.isdigit() or c.lower() in 'abcdef' for c in input_str)

def write_data(data, filename):
    global file_writers, files_to_close, count
    if file_writers.get(filename) is None:
        f = open(filename, 'a')
        writer = csv.writer(f)
        file_writers[filename] = (writer, f)
        files_to_close.append(f)

    file_writers[filename][0].writerow(data)

# this function capture data from fifo (mymalloc.so output)
def capture_data():
    global file_names, end_time, files_to_close

    flag = {}

    print("data_record.py : read fifo for the mymalloc.so output : ./fifo open")
    with open("./fifo_preload", "r") as fifo:

        with open("./data/starttime", "r") as f:
            record_start_time = time.monotonic()
            start_time = int(f.readline(), 10) / 1000000
        while True:
            data = fifo.readline()
    
            if len(data) == 0:
                print("data_record.py : read fifo for the mymalloc.so output : ./fifo close with get zero")
                end_time = time.monotonic() - record_start_time
                with open("./data/endtime", "w") as f:
                    f.write(str(end_time) + "\n")
                
                for f in files_to_close:
                    f.close()
                files_to_close.clear()
                file_writers.clear()

                break

            data = data.strip()
            if data[0: 2] != "my":
                print(data)
                continue
            
            info = data.split(" ")
            filename = "./data/" + info[0] + "_" + info[1] + ".csv"
            pid = int(info[1], 10)

            if flag.get(info[0] + info[1]) is None:
                flag[info[0] + info[1]] = True
                if info[0] == "mya":
                    write_data(["size", "data_addr", "caller_addr", "alloc_time", "alloc_type"], filename)
                elif info[0] == "myf":
                    write_data(["data_addr", "free_time"], filename)
                elif info[0] == "myi":
                    write_data(["begin", "end", "caller_addr"], filename)

            if info[0] == "mya":
                write_data([int(info[2], 10), int(info[3], 16), int(info[4], 16), int(info[5], 10) / 1000000 - start_time, info[6]], filename)
            elif info[0] == "myf":
                write_data([int(info[2], 16), int(info[3], 10) / 1000000 - start_time], filename)
            elif info[0] == "myi":
                write_data([int(info[2], 16), int(info[3], 16), int(info[4], 16)], filename)

            if file_names.get(pid) is None:
                file_names[pid] = {}
            file_names[pid][info[0]] = filename

if __name__ == "__main__":
    capture_data()

    
    