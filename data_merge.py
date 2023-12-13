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
fileresult_names = {}
file_names = {}
filescript_names = {}

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
    global file_names, filescript_names
    global df, df_joined, df_script

    all_data = os.listdir("./data")
    #print(all_data)
    for data in all_data:
        if "mya_" in data:
            pid = int(''.join(re.findall(r'\d+', data)), 10)
            if file_names.get(pid) is None:
                file_names[pid] = {}
            file_names[pid]["mya"] = "./data/" + data
        elif "myf_" in data:
            pid = int(''.join(re.findall(r'\d+', data)), 10)
            if file_names.get(pid) is None:
                file_names[pid] = {}
            file_names[pid]["myf"] = "./data/" + data
        elif "myi_" in data:
            pid = int(''.join(re.findall(r'\d+', data)), 10)
            if file_names.get(pid) is None:
                file_names[pid] = {}
            file_names[pid]["myi"] = "./data/" + data
        elif "script_" in data:
            pid = int(''.join(re.findall(r'\d+', data)), 10)
            filescript_names[pid] = "./data/" + data

    with open("./data/endtime", "r") as f:
        end_time = f.readline()
        end_time = float(end_time.strip())
        
    # deal with dataset
    
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
        "data_addr_end" : "int64"
    }

    # open and initialize malloc obj files
    for pid in file_names:
        #df[pid] = {}
        #for datatype in file_names[pid]:
        #    df[pid][datatype] = vaex.from_csv(file_names[pid][datatype], dtype=df_datatype)
        
        # inner join free and malloc
        if (file_names[pid].get("mya") is not None) and (file_names[pid].get("myf") is not None):
            df_mya = vaex.from_csv(file_names[pid]["mya"], dtype=df_datatype)
            df_myf = vaex.from_csv(file_names[pid]["myf"], dtype=df_datatype)

            df_mya = df_mya.join(df_myf, on="data_addr", how="left", allow_duplication=True)    
            df_mya["free_time"] = df_mya["free_time"].fillna(end_time)    
        
            df_mya["data_addr_end"] = df_mya["data_addr"] + df_mya["size"]
        
            print("export merage free and malloc " + str(pid))
            df_mya.export("./data/myaf_" + str(pid) + ".csv", progress=True)
            del df_mya, df_myf
            gc.collect()

            file_names[pid]["myaf"] = "./data/myaf_" + str(pid) + ".csv"
            #df[pid]["myaf"] = vaex.from_csv("./data/myaf_" + str(pid) + ".csv", dtype=df_datatype)

    # open and initialize sript files
    #for pid in filescript_names:
    #    df_script[pid] = vaex.from_csv(filescript_names[pid], dtype=df_datatype)

    filescript_newnames = {}
    for pid in file_names:
        # script didn't record
        if filescript_names.get(pid) is None:
            continue
        if file_names[pid].get("myaf") is None or file_names[pid].get("myi") is None:
            continue
        df_myi = vaex.from_csv(file_names[pid]["myi"], dtype=df_datatype)
        df_myaf = vaex.from_csv(file_names[pid]["myaf"], dtype=df_datatype)
        df_script = vaex.from_csv(filescript_names[pid], dtype=df_datatype)

        # filte out not hit pool
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

        df_script["pool_begin"] = df_script["hit_addr"].apply(apply_join_key).evaluate()
        mask = df_script["pool_begin"] != -1
        df_script = df_script[mask]
        print("export script with pool_begin key " + str(pid))
        
        if len(df_script) == 0:
            #del df_joined[pid]
            print(str(pid) + " script didn't hit pool")
            continue
        
        df_script.export("./data/scriptnew_" + str(pid) + ".csv", progress=True)
        del df_script
        gc.collect()
        #df_joined[pid] = vaex.from_csv("./data/scriptnew_" + str(pid) + ".csv",  dtype=df_datatype)
        filescript_newnames[pid] = "./data/scriptnew_" + str(pid) + ".csv"

        df_myaf["pool_begin"] = df_myaf["data_addr"].apply(apply_join_key).evaluate()
        print("export myaf with pool_begin key " + str(pid))
        df_myaf.export("./data/myaf_" + str(pid) + ".csv", progress=True)
        del df_myaf
        gc.collect()
        #df[pid]["mya"] = vaex.from_csv("./data/myaf_" + str(pid) + ".csv", dtype=df_datatype)


    for pid in file_names:
        if file_names[pid].get("myaf") is None or filescript_newnames.get(pid) is None:
            if filescript_newnames.get(pid) is not None:
                del filescript_newnames[pid]
            continue
        
        #df_joined[pid] = df_joined[pid].join(df[pid]["mya"], how="left", on="caller_addr", allow_duplication=True)
        #mask = (df_joined[pid]["data_addr"] <= df_joined[pid]["hit_addr"]) & (df_joined[pid]["data_addr_end"] > df_joined[pid]["hit_addr"])
        #df_joined[pid] = df_joined[pid][mask]
       
        #df_joined[pid]["data_addr"] = df_joined[pid].apply(apply_data_addr, arguments=[df_joined[pid]["pool_begin"], df_joined[pid]["hit_addr"]]).evaluate()
        df_myaf = vaex.from_csv(file_names[pid]["myaf"], dtype=df_datatype)
        df_script = vaex.from_csv(filescript_newnames[pid], dtype=df_datatype)

        apply_data_addr = []
        newdf_hit_addr = df_script["hit_addr"].values
        newdf_hit_time = df_script["hit_time"].values
        newdf_pool_begin = df_script["pool_begin"].values
        newdf_dict = {}
        del df_script
        gc.collect()
        
        group = df_myaf.groupby("pool_begin")

        for hit_addr, hit_time, pool_begin in zip(newdf_hit_addr, newdf_hit_time, newdf_pool_begin):
            if newdf_dict.get(pool_begin) is None:
                newdf_dict[pool_begin] = []
            newdf_dict[pool_begin].append([hit_addr, hit_time, pool_begin])
        
        maxval = len(newdf_hit_addr)
        count = 0
        widgets = ['merage ' + str(pid) + ' script and mya: ', Percentage(), '', Bar('#'), '', '', '', '', '', FileTransferSpeed()]
        pbar = ProgressBar(widgets=widgets, maxval=maxval).start()
        
        del newdf_hit_addr, newdf_hit_time, newdf_pool_begin 
        gc.collect()

        for pool_begin in newdf_dict:
            
            temp = group.get_group(pool_begin)
            data_begin = temp["data_addr"].values
            data_end = temp["data_addr_end"].values
            test_dict = {}
            
            if len(temp) == 0:
                for index in range(len(newdf_dict[pool_begin])):
                    pbar.update(count)
                    count += 1
                    newdf_dict[pool_begin][index].append(-1)
                continue

            for begin, end in zip(data_begin, data_end):
                test_dict[(begin, end)] = True
            
            data_begin.sort()
            data_end.sort()            
            
            for index in range(len(newdf_dict[pool_begin])):
                pbar.update(count)
                count += 1

                hit_addr = newdf_dict[pool_begin][index][0]
                begin = bisect.bisect_right(data_begin, hit_addr)
                end = bisect.bisect_right(data_end, hit_addr)
                if hit_addr >= data_begin[0] and  hit_addr < data_end[-1]:
                    begin -= 1
                    if test_dict.get((data_begin[begin], data_end[end])) is not None:
                        newdf_dict[pool_begin][index].append(data_begin[begin])
                    else:
                        newdf_dict[pool_begin][index].append(-1)
                else:
                    newdf_dict[pool_begin][index].append(-1)
        
        newdf_hit_addr = []
        newdf_hit_time = []
        newdf_pool_begin = []
        for pool_begin in newdf_dict:
            for data in newdf_dict[pool_begin]:
                newdf_hit_addr.append(data[0])
                newdf_hit_time.append(data[1])
                newdf_pool_begin.append(data[2])
                apply_data_addr.append(data[3])
        
        del newdf_dict
        gc.collect()

        pbar.finish()

        #print(apply_data_addr)

        df_script = vaex.from_arrays(data_addr=apply_data_addr, hit_addr=newdf_hit_addr, hit_time=newdf_hit_time)
        print("export script with data key")
        df_script.export("./data/script_data_" + str(pid) + ".csv", progress=True)

        del newdf_hit_addr, newdf_hit_time, newdf_pool_begin, df_script
        gc.collect()
        
        filescript_newnames[pid] = "./data/script_data_" + str(pid) + ".csv"
        df_script = vaex.from_csv(filescript_newnames[pid], dtype=df_datatype)

        #df[pid]["mya"].execute()
        #print(len(df_joined[pid]), len(df[pid]["mya"]))
        #print(df_joined[pid])
        #print(df[pid]["mya"])

        df_script = df_script.join(df_myaf, how="left", on="data_addr", allow_duplication=True)
        mask = df_script["data_addr"] != -1
        df_script = df_script[mask]
        print("export join with script and myaf " + str(pid))
        
        if len(df_script) == 0:
            del df_script, filescript_newnames[pid]
            continue
        
        df_script.export("./data/join_" + str(pid) + ".csv", progress=True)
        del df_script
        gc.collect()
        filescript_newnames[pid] = "./data/join_" + str(pid) + ".csv"
        #df_joined[pid] = vaex.from_csv("./data/join_" + str(pid) + ".csv", dtype=df_datatype)

        
    for pid in filescript_newnames:
        df_script = vaex.from_csv(filescript_newnames[pid], dtype=df_datatype)
        print(df_script)
        df_script["interval_time"] = df_script["free_time"] - df_script["alloc_time"]
        df_script.export(filescript_newnames[pid])
        del df_script
        gc.collect()

    # adjust time
    adjustment_time  = -1
    temp1 = []
    temp2 = []
    for pid in filescript_newnames:
        df_script = vaex.from_csv(filescript_newnames[pid], dtype=df_datatype)
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

    
    # export result
    pids = {}
    for pid in filescript_newnames:
        pids[pid] = True
    for pid in file_names:
        pids[pid] = True

    for pid in pids:
        hit_caller_addrs = np.array([])
        # export hit malloc object result
        if  filescript_newnames.get(pid) is not None:
            df_script = vaex.from_csv(filescript_newnames[pid], dtype=df_datatype)
        
            df_script["hit_time"] = df_script["hit_time"] - adjustment_time
            df_script["hit_relative_time"] = (df_script["hit_time"] - df_script["alloc_time"]) / df_script["interval_time"] * 100
            df_script["caller_addr_str"] = df_script["caller_addr"].apply(to_hex)

            export_columns = ["caller_addr", "caller_addr_str", "data_addr", "alloc_time", "free_time", "hit_time", "interval_time", "hit_relative_time", "size"]
            df_script = df_script[export_columns]
            print("export hit information result")
            df_script.export("./result/result" +  "_" + str(pid) + ".csv", progress=True)

            hit_caller_addrs = np.array(df_script["caller_addr"].tolist(), dtype=int)
            
            del df_script
            gc.collect()

        if file_names.get(pid) is not None and file_names[pid].get("myaf"):
        # export malloc caller address not be sampled
            df_myaf = vaex.from_csv(file_names[pid]["myaf"], dtype=df_datatype)

            df_myaf = df_myaf.groupby('caller_addr', agg={'total_size': vaex.agg.sum('size')})
            mask = ~df_myaf["caller_addr"].isin(hit_caller_addrs)
            df_myaf = df_myaf[mask]
            df_myaf["caller_addr_str"] = df_myaf["caller_addr"].apply(to_hex)

            export_columns = ["caller_addr", "caller_addr_str", "total_size"]
            df_myaf = df_myaf[export_columns]
            print("export malloc caller address not be sampled")
            df_myaf.export("./result/result_not_be_sampled" +  "_" + str(pid) + ".csv", progress=True)

            del df_myaf
            gc.collect()



if __name__ == "__main__":
    vaex.settings.multithreading = True
    deal_with_files()
