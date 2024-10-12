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
import argparse
import swifter
import dask.dataframe as dd
from dask.diagnostics import ProgressBar

# ptmalloc2 DEFAULT_MMAP_THRESHOLD
MMAP_THRESHOLD = 128 * 1024
# Difference between 1970 and 1601 in seconds
UNIX_TO_WINDOWS_EPOCH_DIFF_SECONDS = 11644473600

datatype_mya = {
    "alloc_type" : str,
    "size" : int,
    "data_addr" : int,
    "alloc_time" : int,
    "callchain0" : int,
    "callchain1" : int,
    "callchain2" : int,
    "callchain3" : int,
}
datatype_myf = {
    "free_type" : str,
    "data_addr" : int,
    "free_time" : int
}
datatype_miss = {
    "miss_addr" : str,
    "pid" : int,
    "miss_time" : int
}

def transform_time_as_dr_use(alloc_df, free_df):
    if args.profiling_mode == "online":
        None
    elif args.profiling_mode == "offline":
        alloc_df["alloc_time"] += UNIX_TO_WINDOWS_EPOCH_DIFF_SECONDS * 1000000
        free_df["free_time"] += UNIX_TO_WINDOWS_EPOCH_DIFF_SECONDS * 1000000

def merge_alloc_free_info_to_obj_info(pid):
    all_data = os.listdir("./data")
    for data in all_data:
        if ("mya_" in data) and (str(pid) in data):
            alloc_data = f"./data/{data}"
        if ("myf_" in data) and (str(pid) in data):
            free_data = f"./data/{data}"
    alloc_df = pd.read_csv(alloc_data, dtype=datatype_mya)
    alloc_df = pd.DataFrame(alloc_df)
    free_df = pd.read_csv(free_data, dtype=datatype_myf)
    free_df = pd.DataFrame(free_df)
    
    # Adjust time
    transform_time_as_dr_use(alloc_df, free_df)
    alloc_df["alloc_time"] -= starttime
    free_df["free_time"] -= starttime
    # Merge "allocate" and "free" information to be "object" infomation
    obj_df = pd.merge(alloc_df, free_df, on='data_addr', how='left')
    obj_df = obj_df.dropna()
    # We don't take "realloc" in consider now
    mask = (obj_df["alloc_type"] != "r") & (obj_df["free_type"] != "r")
    obj_df = obj_df[mask]
    # Because "ptmalloc2" allocate big object by mmap directly
    mask = obj_df["size"] <  MMAP_THRESHOLD
    obj_df = obj_df[mask]
    # we don't use this column anymore
    obj_df = obj_df.drop(columns=['free_type'])

    obj_df.to_csv(f"./result/obj_{pid}.csv", index=False, header=True)
    return obj_df

def miss_addr_to_data_addr(row, data_addrs):
    miss_addr, pid = row['miss_addr'], row['pid']
    if data_addrs.get(pid) is None:
        return 0

    # TODO : Before the part below we can test whether the miss_addr is
    # in memory pool first. This can speed up transfer miss_addr to 
    # data_addr
    miss_addr = int(miss_addr, 16)
    data_addr_idx = bisect.bisect_right(data_addrs[pid]["data_addrs"], 
                                        miss_addr) - 1
    if data_addr_idx >= 0:
        if ((data_addrs[pid]["data_addrs"][data_addr_idx] + 
             data_addrs[pid]["size"][data_addr_idx]) > miss_addr):
            return data_addrs[pid]["data_addrs"][data_addr_idx]
        else:
            return 0
    else:
        return 0

def main():
    pids = []
    
    # get all pid num
    all_data = os.listdir("./data")
    for data in all_data:
        if ("mya_" in data) or ("myf_" in data):
            pid = int(''.join(re.findall(r'\d+', data)), 10)
            pids.append(pid)

    # Process alloc and free data for each pid
    data_addrs = {}
    for pid in pids:
        obj_df = merge_alloc_free_info_to_obj_info(pid)
        sorted_pairs = sorted(zip(obj_df["data_addr"].to_list(),
                                   obj_df["size"].to_list()), key=lambda x: x[0])
        data_addrs_in_this_pid, sizes_in_this_pid = zip(*sorted_pairs)
        data_addrs[pid] = {
            "data_addrs" : list(data_addrs_in_this_pid),
            "size" : list(sizes_in_this_pid)
        }
        del obj_df
        gc.collect()

    # Process miss data for each chunk
    chunk_size = 100000000
    chunk_count = 0
    is_chunk_pid_first_seen = {}
    miss_data_reader = pd.read_csv("./data/cachemisses.csv", chunksize=chunk_size, 
                                   dtype=datatype_miss)
    for df_chunk in miss_data_reader:
        print("data_merge.py : df_counk", chunk_count)
        df_chunk['miss_time'] -= starttime
        # Two ways of apply option for muti-process. Although dd is indeed muti-process 
        # and swifter may not, swifter still faster than dd. But for bigger data I have 
        # no idea witch is better.
        if True:
            df_chunk['data_addr'] = df_chunk.swifter.apply(
                lambda row: miss_addr_to_data_addr(row, data_addrs), axis=1)
        else:
            ddf_chunk = dd.from_pandas(df_chunk, npartitions=32)
            ddf_chunk["data_addr"] = ddf_chunk.apply(miss_addr_to_data_addr, axis=1, 
                                                    args=(data_addrs,), 
                                                    meta=('data_addr', 'i8'))
            with ProgressBar():
                df_chunk = ddf_chunk.compute()
        
        # Dump the result of this part to filess
        df_chunk = df_chunk[df_chunk['data_addr'] != 0]
        for pid in pids:
            mask = df_chunk['pid'] == pid
            if is_chunk_pid_first_seen.get(pid) is not None:
                df_chunk[mask][['data_addr', 'miss_time']].to_csv(
                    f"./result/miss_{pid}.csv", mode='a', header=False, index=False)
            else:
                is_chunk_pid_first_seen[pid] = False
                df_chunk[mask][['data_addr', 'miss_time']].to_csv(
                    f"./result/miss_{pid}.csv", mode='a', header=True, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        usage="python3 ./data_merge\n\
               --profiling_mode [online]\n"
    )
    parser.add_argument('--profiling_mode', type=str, default="online", 
                        help="[online / offline]")
    args = parser.parse_args()
    
    with open("./data/starttime", "r") as f:
        starttime = f.readline()
        starttime = int(starttime.strip())
    with open("./data/endtime", "r") as f:
        endtime = f.readline()
        endtime = int(endtime.strip())
        
    main()
