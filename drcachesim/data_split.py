import csv
from progressbar import*
from pathlib import Path
import os

class Split_file:
    def __init__(self, index, size, pid):
        self.path = "./data/script_" + str(pid) + "/chunk" + str(index) + ".csv"
        self.index = index
        self.size = size
        self.pid = pid 

# file_names[pid][datatype] = filename
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
    

def capture_cachemisses():
    global files_to_close, file_writers, split_files
    script_start_time = -1
    count_sample = 0
    data_corruption = 0
    print("data_record.py : read ./data/cachemisses.csv : ./fifo open")
    with open("./data/cachemisses.csv", "r") as file:
        # progress bar
        file_size = Path(r"./data/cachemisses.csv").stat().st_size
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
                print("data_split.py : ./data/cachemisses.csv close with get zero")
                for f in files_to_close:
                    f.close()
                files_to_close.clear()
                file_writers.clear()
                print("data_split.py : data corruption " + str(data_corruption))
                break
            
            data = data.strip()
            # slip data by comma
            info = data.split(',')

            # deal with the data to fit into meaning fileds
            if len(info) != 3:
                data_corruption += 1
                print(info)
                continue 

            if True:
                pid = int(info[1], 10)
                data_addr = int(info[0], 16)
                script_time = float(info[2])

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
                
                # in order to split big files into chunks every 500MB
                # ~= 500MB -> 500 * 1024 * 1024 / 26.89 = 19497508(lines)
                if split_files[pid].size < 19000000:
                    split_files[pid].size += 1
                else:
                    split_files[pid] = Split_file(split_files[pid].index + 1, 0, pid)
                    write_data(["hit_addr", "hit_time"], path=split_files[pid].path)
                
                write_data([data_addr, script_time / 1000000], path=split_files[pid].path)

            
            #    print(info)
            #    data_corruption += 1

if __name__ == "__main__":
    capture_cachemisses()

    
    