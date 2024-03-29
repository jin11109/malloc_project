import time
import csv
import re
import vaex
import numpy as np
from progressbar import*
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

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
    """
    count += 1
    if count >= 100000:
        file_writers[filename][1].flush()
        count = 0
    """

# this function capture data from fifo (mymalloc.so output)
def capture_data():
    global file_names, end_time, files_to_close

    flag = {}

    print("data_record.py : read fifo for the mymalloc.so output : ./fifo open")
    with open("./fifo_preload", "r") as fifo:

        start_time = time.time()
        while True:
            data = fifo.readline()
    
            if len(data) == 0:
                print("data_record.py : read fifo for the mymalloc.so output : ./fifo close with get zero")
                end_time = time.time() - start_time
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
                    write_data(["size", "data_addr", "caller_addr", "alloc_time"], filename)
                elif info[0] == "myf":
                    write_data(["data_addr", "free_time"], filename)
                elif info[0] == "myi":
                    write_data(["begin", "end", "caller_addr"], filename)

            if info[0] == "mya":
                write_data([int(info[2], 10), int(info[3], 16), int(info[4], 16), time.time() - start_time], filename)
            elif info[0] == "myf":
                write_data([int(info[2], 16), time.time() - start_time], filename)
            elif info[0] == "myi":
                write_data([int(info[2], 16), int(info[3], 16), int(info[4], 16)], filename)

            if file_names.get(pid) is None:
                file_names[pid] = {}
            file_names[pid][info[0]] = filename

def capture_ldst():
    global files_to_close, file_writers, filesript_names
    script_start_time = -1
    count_sample = 0
    data_corruption = 0
    print("data_record.py : read ./data/ldst_data.raw : ./fifo open")
    with open("./data/ldst_data.raw", "r") as file:
        file_size = Path(r"./data/ldst_data.raw").stat().st_size
        maxval = int(file_size / 30)
        widgets = ['capture_script: ', Percentage(), '', Bar(
            '#'), '', '', '', '', '', FileTransferSpeed()]
        pbar = ProgressBar(widgets=widgets, maxval=maxval).start()

        while True:
            data = file.readline()

            count_sample += 1
            if count_sample < maxval:
                pbar.update(count_sample)

            if len(data) == 0:
                pbar.finish()
                print("data_record.py : ./data/ldst_data.raw close with get zero")
                for f in files_to_close:
                    f.close()
                files_to_close.clear()
                file_writers.clear()
                break
            
            data = data.strip()
            # slip data by space
            info = re.split(r'\s+', data)

            # deal with the data to fit into meaning fileds
            if len(info) != 5:
                data_corruption += 1
                print(info)
                continue 

            try:
                pid = int(info[0], 10)
                data_addr = int(info[1], 16)
                size = int(info[2], 10)
                script_time = float(info[3])
                rw = info[4]

                if script_start_time == -1:
                    script_start_time = script_time
                script_time -= script_start_time

                if data_addr == 0:
                    continue
                
                # record
                if filesript_names.get(pid) is None:
                    filesript_names[pid] = "./data/script_" + str(pid) + ".csv"
                    write_data(["hit_addr", "hit_time"], filename=filesript_names[pid])
                write_data([data_addr, script_time], filename=filesript_names[pid])
            except:
                print(info)
                data_corruption += 1

if __name__ == "__main__":
    capture_data()
    capture_ldst()

    
    