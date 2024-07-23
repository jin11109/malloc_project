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

    flag = False

    print("data_record.py : read fifo for the mymalloc.so output : ./fifo open")
    with open("./fifo_preload", "r") as fifo:
        record_start_time = time.monotonic()
        filename = "./data/mynewheap.csv"
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
            if data[0: 9] != "mynewheap":
                print(data)
                continue
            
            info = data.split(" ")
            
            if flag == False:
                flag = True    
                write_data(["pid", "tid", "mmapped_addr", "size", "version_key"], filename)
    
            write_data([int(info[1], 10), int(info[2], 10), int(info[3], 16), int(info[4], 10), int(info[5], 10)], filename)

if __name__ == "__main__":
    capture_data()

    
    