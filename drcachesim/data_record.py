import csv
import os
import argparse
import mmap
import struct
import time

# Difference between 1970 and 1601 in seconds
UNIX_TO_WINDOWS_EPOCH_DIFF_SECONDS = 11644473600
MAX_DEPTH_OF_CALL_CHAIN = 12

# Files to record preload function output
files = {}
file_writers = {}
files_to_close = []

# tools
def is_hexadecimal(input_str):
    return all(c.isdigit() or c.lower() in 'abcdef' for c in input_str)

def write_data(data, filename):
    global file_writers, files_to_close, files
    if file_writers.get(filename) is None:
        f = open(files[filename], 'a')
        writer = csv.writer(f)
        file_writers[filename] = writer
        files_to_close.append(f)

    file_writers[filename].writerow(data)

def dump_time(path):
    with open(path, "w") as time_f:
        if args.profiling_mode == "offline":
            time_data = time.time_ns() // 1000
            time_data += UNIX_TO_WINDOWS_EPOCH_DIFF_SECONDS * 1000000
            time_f.write(str(time_data))
        elif args.profiling_mode == "online":
            if path == "./data/starttime":
                time_f.write(str(0))
                return
            with open("timmer", "r+b") as f:
                time_data = mmap.mmap(f.fileno(), 8, access=mmap.ACCESS_READ)
                time_data = time_data.read(8)
                time_data = struct.unpack('q', time_data)
                time_f.write(str(time_data[0]))

# this function capture data from fifo (mymalloc.so output)
def main():
    global files_to_close, files
                
    print("data_record.py : read fifo_preload for the mymalloc.so output")
    with open("./fifo_preload", "r") as fifo:
        dump_time("./data/starttime")

        while True:
            data = fifo.readline()
            if len(data) == 0:
                print("data_record.py : fifo_preload close with get zero\n")
                dump_time("./data/endtime")
                for f in files_to_close:
                    f.close()
                break

            data = data.strip()
            # be careful to this when output some infomation to stderr. 
            # such as we change the output infomation in mymalloc.so 
            # when output "mymalloc.so : (some info)" to "_mymalloc.so : (some info)" 
            if ((data[0: 3] != "mya") and (data[0: 3] != "myf")):
                print(data)
                continue

            info = data.split(" ")
            pid = int(info[2], 10)
            filetype = info[0]
            filename = filetype + str(pid)
            filepath = f"./data/{filetype}_{pid}.csv"
            
            if files.get(filename) is None:
                files[filename] = filepath
                if info[0] == "mya":
                    write_data(["alloc_type", "size", "data_addr", "alloc_time", 
                                "callchain0", "callchain1", "callchain2", "callchain3", 
                                "callchain4", "callchain5", "callchain6", "callchain7", 
                                "callchain8", "callchain9", "callchain10", "callchain11"],
                               filename)
                elif info[0] == "myf":
                    write_data(["free_type", "data_addr", "free_time"], filename)

            if info[0] == "mya":
                type_ = info[1]
                size = int(info[3], 10)
                data_addr = int(info[4], 16)
                alloc_time = int(info[5], 10)
                output_data = [type_, size, data_addr, alloc_time]
                for i in range(6, 6 + MAX_DEPTH_OF_CALL_CHAIN):
                    output_data.append(int(info[i], 16))
                write_data(output_data, filename)
            
            elif info[0] == "myf":
                type_ = info[1]
                data_addr = int(info[3], 16)
                free_time = int(info[4], 10)
                write_data([type_, data_addr, free_time], filename)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        usage="python3 ./data_merge\n\
               --profiling_mode [online]\n"
    )
    parser.add_argument('--profiling_mode', type=str, default="online", 
                        help="[online / offline]")
    args = parser.parse_args()
    main()

    
    