import csv
import re
from progressbar import*
from pathlib import Path
import os

class Split_file:
    def __init__(self, index, size, pid):
        self.path = "./data/script_" + str(pid) + "/chunk" + str(index) + ".csv"
        self.index = index
        self.size = size
        self.pid = pid 

split_files = {}
file_writers = {}
files_to_close = []
end_time = 0

count = 0

# tools
def is_hexadecimal(input_str):
    return all(c.isdigit() or c.lower() in 'abcdef' for c in input_str)

def write_data(data, path):
    global file_writers, files_to_close, count
    if file_writers.get(path) is None:
        f = open(path, 'a')
        writer = csv.writer(f)
        file_writers[path] = (writer, f)
        files_to_close.append(f)

    file_writers[path][0].writerow(data)

def capture_script():
    global files_to_close, file_writers, split_files
    script_start_time = -1
    count_sample = 0
    print("data_script.py : read fifo for perf script output : ./fifo open")
    with open("./fifo", "r") as script:
        file_size = Path(r"./myperf.data").stat().st_size
        maxval = int(file_size / 50)
        widgets = ['capture_script: ', Percentage(), '', Bar(
            '#'), '', '', '', '', '', FileTransferSpeed()]
        pbar = ProgressBar(widgets=widgets, maxval=maxval).start()

        while True:
            data = script.readline()

            count_sample += 1
            if count_sample < maxval:
                pbar.update(count_sample)

            if len(data) == 0:
                pbar.finish()
                print("data_script.py : read fifo for perf script output : ./fifo close with get zero")
                for f in files_to_close:
                    f.close()
                files_to_close.clear()
                file_writers.clear()
                break
            
            data = data.strip()
            # slip data by space
            info = re.split(r'\s+', data)

            # the information must longer than 15 words
            info_len = len(info)
            if info_len < 15:
                print(info)
                continue

            index = 0
            index2 = info_len - 1

            while info[index].isdigit() is not True:
                index += 1
            while is_hexadecimal(info[index2]) is not True:
                index2 -= 1
            
            # special case for epiphany
            if info[index] == "00":
                index += 1

            # deal with the data to fit into meaning fileds
            pid = int(info[index], 10)
            script_time = float(info[index + 1][0: len(info[index + 1]) - 1])
            event = info[index + 3]
            data_addr = int(info[index + 4], 16)

            if script_start_time == -1:
                script_start_time = script_time
            script_time -= script_start_time

            if data_addr == 0:
                continue
            
            # record
            if split_files.get(pid) is None:
                os.mkdir("./data/script_" + str(pid))
                split_files[pid] = Split_file(0, 0, pid)
                write_data(["hit_addr", "hit_time"], path=split_files[pid].path)
            
            # in order to split big files into chunks
            if split_files[pid].size < 15000000:
                split_files[pid].size += 1
            else:
                split_files[pid] = Split_file(split_files[pid].index + 1, 0, pid)
                write_data(["hit_addr", "hit_time"], path=split_files[pid].path)
            
            write_data([data_addr, script_time], path=split_files[pid].path)

if __name__ == "__main__":
    capture_script()
