import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import ScalarFormatter
import os
import re
import json
import gc
import shutil
from progressbar import*

PAGE_SIZE = 4096
COLD = 0
OTHER = 1
NOT_CONSIDER = 2
COLD_HEAP = 21
OTHER_HEAP = 10

dtype = {
    "addr" : str,
    "mmapped_addr" : int,
    "size" : int,
    "version_key" : int,
    "pid" : int,
    "tid" : int,
    "pid_page" : "uint64",
    "temperature" : "uint8",
    "page" : "uint64"
}
dtype_vaex = {
    "page" : "int64",
    "pid" : "int32",
    "pid_page" : "int64",
    "temperature" : "int32"
}

def add_temperature_col(df_cold, df_other, input_path, output_path):
    chunk_size = 100000000
    reader = pd.read_csv(input_path, chunksize=chunk_size, dtype=dtype)
    first_chunk = True

    chunk_index = 0
    print("chunk already done: ", end='', flush=True)
    for df_chunk in reader:
        df_chunk["addr"] = df_chunk["addr"].apply(lambda x: int(x, 16))
        df_chunk["addr"] = df_chunk["addr"]
        df_chunk['temperature'] = NOT_CONSIDER
        for index, row in df_other.iterrows():
            condition = (df_chunk['addr'] >= row['mmapped_addr']) & (df_chunk['addr'] < row['max_mmapped_addr']) & (df_chunk["pid"] == row['pid'])
            df_chunk.loc[condition, "temperature"] = OTHER
        for index, row in df_cold.iterrows():
            condition = (df_chunk['addr'] >= row['mmapped_addr']) & (df_chunk['addr'] < row['max_mmapped_addr']) & (df_chunk["pid"] == row['pid'])
            df_chunk.loc[condition, "temperature"] = COLD

        df_chunk["page"] = df_chunk["addr"] // PAGE_SIZE
        df_chunk = df_chunk.drop(['addr'], axis=1)
        gc.collect()

        if first_chunk:
            df_chunk.to_csv(output_path, index=False)
            first_chunk = False
        else:
            df_chunk.to_csv(output_path, mode='a', index=False, header=False)
        
        print(f"{chunk_index} ", end='', flush=True)
        chunk_index += 1
    print()
    del reader
    gc.collect()

def calculate_reuse_distances(input_path):
    reuse_distance = {
        COLD : [],
        OTHER : [],
        NOT_CONSIDER : []
    }
    chunk_size = 100000000
    reader = pd.read_csv(input_path, chunksize=chunk_size, dtype=dtype)

    stack = []
    have_seen = {}
    chunk_index = 0
    last_seen = 0
    stack_len = 0
    for df_chunk in reader:
        # initialize progress bar
        maxval = len(df_chunk)
        widgets = [f'calculate reuse dist chunk:{chunk_index} ', Percentage(), '', Bar('#'), '', '', '', '', '', FileTransferSpeed()]
        pbar = ProgressBar(widgets=widgets, maxval=maxval).start()
        chunk_index += 1
        
        count = 0
        for pid, temperature, page in df_chunk.itertuples(index=False):
            if last_seen == (pid, page):
                reuse_distance[temperature].append(0)
                count += 1
                continue
            else:
                last_seen = (pid, page)

            if have_seen.get((pid, page)) is not None:
                index = 0
                for i in range(stack_len-2, -1, -1):
                    if stack[i] == (pid, page):
                        index = i
                        break
                distance = stack_len - index - 1
                reuse_distance[temperature].append(distance)
                stack.append(stack.pop(index))
            else:
                stack.append((pid, page))
                have_seen[(pid, page)] = True
                stack_len += 1

            count += 1
            pbar.update(count)
    
    pbar.finish()

    return reuse_distance

def output(reuse_dist, savepath):
    fig, axs = plt.subplots(1, 1, figsize=(14, 10), gridspec_kw={"bottom": 0.3, "top": 0.9})
    sns.histplot(x=reuse_dist, ax=axs, bins=200)
    axs.set_title("Page Reuse Distance Frequency Chart")
    axs.set_ylabel("Reference Count")
    axs.set_xlabel("Reuse Distance")
    axs.set_yscale("log")

    obj_info = "malloc objects information" \
                + "\n" + "|  " + str()
    
    fig.text(0.2, 0.2,  obj_info, ha="left", va="top", fontsize=10, color="blue")
    
    # close Scientific Notation
    ax = plt.gca()
    ax.xaxis.set_major_formatter(ScalarFormatter(useOffset=False))
    ax.xaxis.get_major_formatter().set_scientific(False)

    fig.savefig("./result_picture/" + savepath)
    plt.close(fig)

def main():
    not_yet_calculate_reuse_dise = True
    if not_yet_calculate_reuse_dise:
        df_heap = pd.read_csv("./data/mynewheap.csv", dtype=dtype)
        df_heap["max_mmapped_addr"] = df_heap["mmapped_addr"] + df_heap["size"]
        df_cold = df_heap[df_heap["version_key"] == COLD_HEAP]
        df_other = df_heap[df_heap["version_key"] == OTHER_HEAP]

        # processing cachemisses
        add_temperature_col(df_cold, df_other, input_path="./data/cachemisses.csv", output_path="./data/cachemisses_space.csv")
        reuse_distance = calculate_reuse_distances(input_path="./data/cachemisses_space.csv")

        with open("./result/cold_reuse_distance_space.json", 'w') as file:
            json.dump(reuse_distance[COLD], file)
        with open("./result/other_reuse_distance_space.json", 'w') as file:
            json.dump(reuse_distance[OTHER], file)
        with open("./result/not_condider_reuse_distance_space.json", 'w') as file:
            json.dump(reuse_distance[NOT_CONSIDER], file)

        del reuse_distance
        gc.collect()

    # already have reuse distance data 
    with open("./result/cold_reuse_distance_space.json", 'r') as file:
        reuse_distance = json.load(file)
        output(reuse_distance, "cold_reusedist_space")
    with open("./result/other_reuse_distance_space.json", 'r') as file:
        reuse_distance = json.load(file)
        output(reuse_distance, "other_reuse_distance_space")
    # with open("./result/not_condider_reuse_distance_space.json", 'r') as file:
    #     reuse_distance = json.load(file)
    #     output(reuse_distance, "not_condider_reuse_distance_space")
    
if __name__ == "__main__":
    plt.rcParams["axes.formatter.useoffset"] = False
    main()
