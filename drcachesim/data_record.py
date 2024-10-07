import csv
import os

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

# this function capture data from fifo (mymalloc.so output)
def capture_data():
    global files_to_close, files
    os.system("./record_time ./data/starttime")
    print("data_record.py : read fifo_preload for the mymalloc.so output")
    with open("./fifo_preload", "r") as fifo:

        while True:
            data = fifo.readline()
            if len(data) == 0:
                print("data_record.py : fifo_preload close with get zero\n")
                os.system("./record_time ./data/endtime")
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
                    write_data(["alloc_type", "size", "data_addr", "alloc_time", "callchain0", "callchain1", "callchain2", "callchain3"], filename)
                elif info[0] == "myf":
                    write_data(["free_type", "data_addr", "free_time"], filename)

            if info[0] == "mya":
                type_ = info[1]
                size = int(info[3], 10)
                data_addr = int(info[4], 16)
                alloc_time = int(info[5], 10)
                callchain0 = int(info[6], 16)
                callchain1 = int(info[7], 16)
                callchain2  = int(info[8], 16)
                callchain3 = int(info[9], 16)
                write_data([type_, size, data_addr, alloc_time, callchain0, callchain1, callchain2, callchain3], filename)
            
            elif info[0] == "myf":
                type_ = info[1]
                data_addr = int(info[3], 16)
                free_time = int(info[4], 10)
                write_data([type_, data_addr, free_time], filename)

if __name__ == "__main__":
    capture_data()

    
    