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
import os
import bisect
import gc

end_time = 0

alloc_logs = {}
scripts = {}

df = {}
df_script = {}
df_joined = {}
pid_for_apply = 0
pool_begin = []
pool_end = []
pool_to_caller = {}

def to_hex(value):
    return hex(int(value))

def apply_join_key(addr):
    global pool_to_caller, pool_begin, pool_end
    begin = bisect.bisect_right(pool_begin, addr)
    end = bisect.bisect_right(pool_end, addr)
    if addr >= pool_begin[0] and  addr < pool_end[-1]:
        begin -= 1
        if pool_to_caller.get((pool_begin[begin], pool_end[end])) is None:
            return -1
        else:
            #print("begin end", begin, end)
            return pool_begin[begin]
    else:
        return -1
"""
def apply_data_addr(pool_begin, hit_addr):
    print("ok")
    global df, pid_for_apply
    mask = df[pid_for_apply]["mya"]["pool_begin"] == pool_begin
    print(mask)
    print(pool_begin)
    
    #temp = df[pid_for_apply]["mya"][mask]

    #print(temp)
    
    mask2 = (temp["data_addr"] <= hit_addr) & (temp["data_addr_end"] > hit_addr)
    temp = temp[mask2]
    result = temp["data_addr"].values
    
    print("okapply")

    if len(result) == 1:
        return result[0]
    elif len(result) > 1:
        print("error with hit multi data addr")
        return -1
    else:
        return -1
"""
def deal_with_files():
    global alloc_logs, scripts
    global df, df_joined, df_script

    all_data = os.listdir("./data")
    #print(all_data)
    for data in all_data:
        if "mya_" in data:
            pid = int(''.join(re.findall(r'\d+', data)), 10)
            if alloc_logs.get(pid) is None:
                alloc_logs[pid] = {}
            alloc_logs[pid]["mya"] = "./data/" + data
        elif "myf_" in data:
            pid = int(''.join(re.findall(r'\d+', data)), 10)
            if alloc_logs.get(pid) is None:
                alloc_logs[pid] = {}
            alloc_logs[pid]["myf"] = "./data/" + data
        elif "myi_" in data:
            pid = int(''.join(re.findall(r'\d+', data)), 10)
            if alloc_logs.get(pid) is None:
                alloc_logs[pid] = {}
            alloc_logs[pid]["myi"] = "./data/" + data
        elif "script_" in data:
            pid = int(''.join(re.findall(r'\d+', data)), 10)
            scripts[pid] = []
            all_chunks = os.listdir("./data/" + data)
            for chunk in all_chunks:
                scripts[pid].append("./data/"+ data + "/" + chunk)

    with open("./data/endtime", "r") as f:
        end_time = f.readline()
        end_time = float(end_time.strip())
        
    df_datatype = {
        "caller_addr" : "int64",
        "data_addr" : "int64",
        "size" : "int32",
        "alloc_time" : "float64",
        "free_time" : "float64",
        "begin" : "int64",
        "end" : "int64",
        "pool_begin" : "int64",
        "hit_addr" : "int64",
        "hit_time" : "float64",
        "data_addr_end" : "int64",
        "caller_objects_num" : "int32",
        "caller_total_alloc_size" : "int64",
        "generation" : "float64"
    }

    # open and initialize malloc obj files
    for pid in alloc_logs:
        
        # inner join free and malloc
        if (alloc_logs[pid].get("mya") is not None) and (alloc_logs[pid].get("myf") is not None):
            df_mya = vaex.from_csv(alloc_logs[pid]["mya"], dtype=df_datatype)
            df_myf = vaex.from_csv(alloc_logs[pid]["myf"], dtype=df_datatype)

            # inner join alloc and free
            df_mya = df_mya.join(df_myf, on="data_addr", how="left", allow_duplication=True)    
            df_mya["free_time"] = df_mya["free_time"].fillna(end_time)    

            # count malloc object and sum
            caller_objects_info = df_mya.groupby('caller_addr').agg({"caller_objects_num": 'count', "caller_total_alloc_size": vaex.agg.sum('size')})
            # inner join malloc object
            df_mya = df_mya.join(caller_objects_info, on="caller_addr", how="left", allow_duplication=False) 

            # add some info
            df_mya["data_addr_end"] = df_mya["data_addr"] + df_mya["size"]
            df_mya["generation"] = df_mya["free_time"] - df_mya["alloc_time"]

            print("export merge free and malloc " + str(pid))
            df_mya.export("./data/myaf_" + str(pid) + ".csv", progress=True)
        
            del df_mya, df_myf, caller_objects_info
            gc.collect()

            alloc_logs[pid]["myaf"] = "./data/myaf_" + str(pid) + ".csv"
            #df[pid]["myaf"] = vaex.from_csv("./data/myaf_" + str(pid) + ".csv", dtype=df_datatype)

    # open and initialize sript files
    scripts_with_poolkey = {}
    for pid in alloc_logs:
        # script didn't mach myaf (malloc files)
        if scripts.get(pid) is None:
            continue
        if alloc_logs[pid].get("myaf") is None or alloc_logs[pid].get("myi") is None:
            continue
        df_myi = vaex.from_csv(alloc_logs[pid]["myi"], dtype=df_datatype)
        df_myaf = vaex.from_csv(alloc_logs[pid]["myaf"], dtype=df_datatype)

        # get pool information to insert the pool key to script files and alloc log files 
        global pool_begin, pool_end, pool_to_caller
        pool_begin = df_myi["begin"].values
        pool_end = df_myi["end"].values
        pool_caller_adddr = df_myi["caller_addr"].values
        pool_to_caller = {}
        del df_myi
        gc.collect()

        for begin, end, caller_addr in zip(pool_begin, pool_end, pool_caller_adddr):
            pool_to_caller[(begin, end)] = caller_addr
        pool_begin.sort()
        pool_end.sort()

        # for every chunks, apply a new column "pool begin" as inner join key
        path = "./data/script_with_poolkey_" + str(pid) + "/"
        os.mkdir(path)
        dir_flag = True
        chunk_index = 0
        scripts_with_poolkey[pid] = []
        for chunk in scripts[pid]:
            df_script = vaex.from_csv(chunk, dtype=df_datatype)

            df_script["pool_begin"] = df_script["hit_addr"].apply(apply_join_key).evaluate()
            mask = df_script["pool_begin"] != -1
            df_script = df_script[mask]
            print("export chunk in script with pool key " + str(pid))
            
            if len(df_script) == 0:
                #del df_joined[pid]
                print(str(pid) + "this chunk in script didn't hit pool")
                continue
            
            dir_flag = False
            chunk_path = path + "chunk" + str(chunk_index) + ".csv"
            df_script.export(chunk_path, progress=True)
            
            del df_script
            gc.collect()
            scripts_with_poolkey[pid].append(chunk_path)
            chunk_index += 1

        # delete the dir without any chunks inside
        if dir_flag:
            os.rmdir(path)
            del scripts_with_poolkey[pid]

        # for alloc log files, apply a same new column "pool begin" as inner join key
        df_myaf["pool_begin"] = df_myaf["data_addr"].apply(apply_join_key).evaluate()
        print("export myaf with pool key " + str(pid))
        df_myaf.export("./data/myaf_" + str(pid) + ".csv", progress=True)
        del df_myaf
        gc.collect()

    # insert datakey to files in scripts_with_poolkey
    scripts_result = {}
    for pid in alloc_logs:
        if alloc_logs[pid].get("myaf") is None or scripts_with_poolkey.get(pid) is None:
            if scripts_with_poolkey.get(pid) is not None:
                del scripts_with_poolkey[pid]
            continue
        
        df_myaf = vaex.from_csv(alloc_logs[pid]["myaf"], dtype=df_datatype)
        group = df_myaf.groupby("pool_begin")

        # for every chunk, insert datakey
        path = "./data/script_with_datakey_" + str(pid) + "/"
        chunk_index = 0
        dir_flag = True
        scripts_result[pid] = []
        os.mkdir(path)
        for chunk in scripts_with_poolkey[pid]:
            df_script = vaex.from_csv(chunk, dtype=df_datatype)
            
            # turn df to dict datatype, and group data in this by poolkey
            apply_data_addr = []
            hit_addrs = df_script["hit_addr"].values
            hit_times = df_script["hit_time"].values
            pool_begins = df_script["pool_begin"].values
            df_dict = {}
            del df_script
            gc.collect()

            for hit_addr, hit_time, pool_begin in zip(hit_addrs, hit_times, pool_begins):
                if df_dict.get(pool_begin) is None:
                    df_dict[pool_begin] = []
                df_dict[pool_begin].append([hit_addr, hit_time, pool_begin])
            
            # initialize progress bar
            maxval = len(hit_addrs)
            count = 0
            widgets = ['merage ' + str(pid) + ' script and mya: ', Percentage(), '', Bar('#'), '', '', '', '', '', FileTransferSpeed()]
            pbar = ProgressBar(widgets=widgets, maxval=maxval).start()
            
            del hit_addrs, hit_times, pool_begins 
            gc.collect()

            # for every set of data whitch have the same poolkey in chunk
            for pool_begin in df_dict:
                # get all data in this pool whitch are recorded in alloc log files
                temp = group.get_group(pool_begin)
                data_begin = temp["data_addr"].values
                data_end = temp["data_addr_end"].values
                test_dict = {}
                
                # skip the poolkey in chunk doesn't mach that in alloc log files
                if len(temp) == 0:
                    for index in range(len(df_dict[pool_begin])):
                        pbar.update(count)
                        count += 1
                        df_dict[pool_begin][index].append(-1)
                    continue
                
                # init the dict to decide the addr of data is hit or not
                for begin, end in zip(data_begin, data_end):
                    test_dict[(begin, end)] = True
                
                data_begin.sort()
                data_end.sort()            
                
                # for every data(every hit) have the poolkey, insert datakey
                for index in range(len(df_dict[pool_begin])):
                    # update progress bar
                    pbar.update(count)
                    count += 1
                    # if success insert datakey, else insert -1  
                    hit_addr = df_dict[pool_begin][index][0]
                    begin = bisect.bisect_right(data_begin, hit_addr)
                    end = bisect.bisect_right(data_end, hit_addr)
                    if hit_addr >= data_begin[0] and  hit_addr < data_end[-1]:
                        begin -= 1
                        if test_dict.get((data_begin[begin], data_end[end])) is not None:
                            df_dict[pool_begin][index].append(data_begin[begin])
                        else:
                            df_dict[pool_begin][index].append(-1)
                    else:
                        df_dict[pool_begin][index].append(-1)
            
            # output the script chunk files with datakey
            hit_addrs = []
            hit_times = []
            pool_begins = []
            for pool_begin in df_dict:
                for data in df_dict[pool_begin]:
                    hit_addrs.append(data[0])
                    hit_times.append(data[1])
                    pool_begins.append(data[2])
                    apply_data_addr.append(data[3])
            
            del df_dict
            gc.collect()

            pbar.finish()
            df_script = vaex.from_arrays(data_addr=apply_data_addr, hit_addr=hit_addrs, hit_time=hit_times)
            print("export script with data key")
            chunk_path = path + "chunk" + str(chunk_index) + ".csv"
            df_script.export(chunk_path , progress=True)

            del hit_addrs, hit_times, pool_begins, df_script
            gc.collect()
            
            # merge chunk and alloc lof file with data key
            # reopen 
            df_script = vaex.from_csv(chunk_path, dtype=df_datatype)

            df_script = df_script.join(df_myaf, how="left", on="data_addr", allow_duplication=True)
            mask = df_script["data_addr"] != -1
            df_script = df_script[mask]
            print("export join with script and myaf " + str(pid))
            
            if len(df_script) == 0:
                del df_script
                continue
            
            dir_flag = False
            result_path = path + "chunk" + str(chunk_index) + ".csv"
            df_script.export(result_path, progress=True)
            del df_script
            gc.collect()
            scripts_result[pid].append(result_path)
            #df_joined[pid] = vaex.from_csv("./data/join_" + str(pid) + ".csv", dtype=df_datatype)

            chunk_index += 1

        # delete the dir without any chunks inside
        if dir_flag:
            os.rmdir(path)
            del scripts_result[pid]

    # add some information
    for pid in scripts_result:
        for chunk in scripts_result[pid]:
            df_script = vaex.from_csv(chunk, dtype=df_datatype)
            #print(df_script)
            df_script["interval_time"] = df_script["free_time"] - df_script["alloc_time"]
            df_script.export(chunk)
            del df_script
            gc.collect()

    # adjust time
    adjustment_time = 0
    with open("./data/adjustment_time", "w") as f:
        f.write(str(0) + "\n")
    '''
    adjustment_time  = -1
    temp1 = []
    temp2 = []
    for pid in scripts_result:
        for chunk in scripts_result[pid]:
            df_script = vaex.from_csv(chunk, dtype=df_datatype)
            mask = df_script["interval_time"] < 0.001
            result = df_script[mask]
            if len(result) != 0:
                temp1.extend(result["hit_time"].values)
                temp2.extend(result["alloc_time"].values)
                #adjustment_time = temp1[0] - temp2[0]
            del df_script
            gc.collect()

    for hit_time, alloc_time in zip(temp1, temp2):
        adjustment_time += hit_time - alloc_time
    adjustment_time /= len(temp1)

    with open("./data/adjustment_time", "w") as f:
        f.write(str(adjustment_time) + "\n")
    '''
    
    # export result
    pids = {}
    for pid in scripts_result:
        pids[pid] = True
    for pid in alloc_logs:
        pids[pid] = True

    for pid in pids:
        hit_caller_addrs = []
        # export hit malloc object result
        if  scripts_result.get(pid) is not None:
            path = "./result/result" +  "_" + str(pid) + "/"
            os.mkdir(path)
            chunk_index = 0
            for chunk in scripts_result[pid]:
                df_script = vaex.from_csv(chunk, dtype=df_datatype)
            
                df_script["hit_time"] = df_script["hit_time"] - adjustment_time
                df_script["hit_relative_time"] = (df_script["hit_time"] - df_script["alloc_time"]) / df_script["interval_time"] * 100
                df_script["caller_addr_str"] = df_script["caller_addr"].apply(to_hex)

                export_columns = ["caller_addr", "caller_addr_str", "data_addr", "alloc_time", "free_time", "hit_time", "interval_time", "hit_relative_time", "size", "caller_objects_num", "caller_total_alloc_size"]
                df_script = df_script[export_columns]
                print("export hit information result")
                df_script.export(path + "chunk" + str(chunk_index) + ".csv", progress=True)

                # record the mallocs which have event
                hit_caller_addrs += df_script["caller_addr"].tolist()

                del df_script
                gc.collect()

                chunk_index += 1

        # export malloc caller address not be sampled
        if alloc_logs.get(pid) is not None and alloc_logs[pid].get("myaf") is not None:
            df_myaf = vaex.from_csv(alloc_logs[pid]["myaf"], dtype=df_datatype)

            df_myaf = df_myaf.groupby('caller_addr', agg={'caller_total_alloc_size': vaex.agg.mean('caller_total_alloc_size')})
            mask = ~df_myaf["caller_addr"].isin(list(set(hit_caller_addrs)))
            df_myaf = df_myaf[mask]
            df_myaf["caller_addr_str"] = df_myaf["caller_addr"].apply(to_hex)

            export_columns = ["caller_addr", "caller_addr_str", "caller_total_alloc_size"]
            df_myaf = df_myaf[export_columns]
            print("export malloc caller address not be sampled")
            df_myaf.export("./result/result_not_be_sampled" +  "_" + str(pid) + ".csv", progress=True)

            del df_myaf
            gc.collect()



if __name__ == "__main__":
    vaex.settings.multithreading = True
    deal_with_files()
