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
    with open("./fifo", "r") as fifo:

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

def capture_script():
    global files_to_close, file_writers, filesript_names
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
            if filesript_names.get(pid) is None:
                filesript_names[pid] = "./data/script_" + str(pid) + ".csv"
                write_data(["hit_addr", "hit_time"], filename=filesript_names[pid])
            write_data([data_addr, script_time], filename=filesript_names[pid])

"""            
def deal_with_files():
    global file_names, filesript_names
    count_progress = 0
    # deal with dataset
    df = {}
    df_script = {}
    df_joined = {}
    df_datatype = {
        "caller_addr" : "int64",
        "data_addr" : "int64",
        "size" : "int32",
        "alloc_time" : "float64",
        "free_time" : "float64",
        "begin" : "int64",
        "end" : "int64"
    }
    df_script_datatype = {
        "hit_addr" : "int64",
        "hit_time" : "float64"
    }

    # open and initialize malloc obj files
    for pid in file_names:
        df[pid] = {}
        for datatype in file_names[pid]:
            df[pid][datatype] = vaex.from_csv(file_names[pid][datatype], dtype=df_datatype)
        # inner join free and malloc
        if (file_names[pid].get("mya") is not None) and (file_names[pid].get("myf") is not None):
            df[pid]["mya"] = df[pid]["mya"].join(df[pid]["myf"], on="data_addr", how="left", allow_duplication=True)    
            df[pid]["mya"]["free_time"] = df[pid]["mya"]["free_time"].fillna(end_time)    
        
        df[pid]["mya"]["data_addr_end"] = df[pid]["mya"]["data_addr"] + df[pid]["mya"]["size"]

    # open and initialize sript files
    for pid in filesript_names:
        df_script[pid] = vaex.from_csv(filesript_names[pid], dtype=df_script_datatype)


    # cross script files and my files to find each samples' hit on wiht data
    for pid in df:
        if df_script.get(pid) is None:
            continue

        print("deal with " + str(pid) + " cross product")
        # filte out not hit pool
        df_script[pid]["joined"] = np.full(len(df_script[pid]), 1)
        df[pid]["myi"]["joined"] = np.full(len(df[pid]["myi"]), 1)
        df_joined[pid] = df_script[pid].join(df[pid]["myi"], how="left", on="joined", allow_duplication=True)
        mask = (df_joined[pid]["begin"] <= df_joined[pid]["hit_addr"]) & (df_joined[pid]["end"] > df_joined[pid]["hit_addr"])
        df_joined[pid] = df_joined[pid][mask]
        print("deal with " + str(pid) + " cross product done")

        print("deal with " + str(pid) + " inner product")
        # filte out not hit data
        if len(df_joined[pid]) == 0:
            del df_joined[pid]
            continue

        df_joined[pid] = df_joined[pid].join(df[pid]["mya"], how="right", on="caller_addr", allow_duplication=True)
        mask = (df_joined[pid]["data_addr"] <= df_joined[pid]["hit_addr"]) & (df_joined[pid]["data_addr_end"] > df_joined[pid]["hit_addr"])
        df_joined[pid] = df_joined[pid][mask]
        print("deal with " + str(pid) + " inner product done")


    for pid in df_joined:
        df_joined[pid]["interval_time"] = df_joined[pid]["free_time"] - df_joined[pid]["alloc_time"]

    # adjust time
    adjustment_time  = -1
    for pid in df_joined:
        mask = df_joined[pid]["interval_time"] < 0.001
        result = df_joined[pid][mask]
        if len(result) != 0:
            temp1 = result["hit_time"].values
            temp2 = result["alloc_time"].values
            adjustment_time = temp1[0] - temp2[0]
            with open("./data/adjustment_time", "w") as f:
                f.write(str(adjustment_time) + "\n")
            break
    
    # export result
    for pid in df_joined:
        df_joined[pid]["hit_time"] = df_joined[pid]["hit_time"] - adjustment_time
        df_joined[pid]["hit_relative_time"] = (df_joined[pid]["hit_time"] - df_joined[pid]["alloc_time"]) / df_joined[pid]["interval_time"] * 100
        df_joined[pid]["caller_addr_str"] = df_joined[pid]["caller_addr"].apply(to_hex)

        export_columns = ["caller_addr", "caller_addr_str", "data_addr", "alloc_time", "free_time", "hit_time", "interval_time", "hit_relative_time"]
        df_joined[pid] = df_joined[pid][export_columns]
        df_joined[pid].export("./data/result" +  "_" + str(pid) + ".csv", progress=True)
        fileresult_names[pid] = "./data/result" +  "_" + str(pid) + ".csv"
        
def show_diagram():
    dtype = {
        "caller_addr" : int,
        "data_addr" : int,
        "caller_addr_str" : str,
        "interval_time" : float,
        "hit_time" : float,
        "alloc_time" : float,
        "free_time" : float,
        "hit_relative_time" : float
    }
    
    for pid in fileresult_names:       
        df = pd.read_csv(fileresult_names[pid], dtype=dtype)
        df = pd.DataFrame(df)

        # drop error
        df.drop_duplicates(subset=["hit_time"], keep=False, inplace=True)

        plt.figure()
        plt.title('hit pid=' + str(pid))
        
        indicate = df.groupby("caller_addr_str", as_index=True).size().reset_index().rename(columns={0: 'size'})
        #print(indicate)
        indicate = indicate.sort_values("size", ascending=False)
        indicate = indicate.head(50)

        mask = df["interval_time"] > 1
        mask2 = df["caller_addr_str"].isin(indicate["caller_addr_str"])
        df_temp = df[mask & mask2]
        sns.histplot(x=df_temp["hit_relative_time"], y=df_temp["caller_addr_str"], legend=True, cbar=True, bins=100) 
        plt.show()
"""

            

if __name__ == "__main__":
    vaex.settings.multithreading = True
    capture_data()
    capture_script()

    
    