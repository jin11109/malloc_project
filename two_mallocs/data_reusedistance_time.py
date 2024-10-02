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
    "temperature" : "uint8"
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
        df_chunk['temperature'] = NOT_CONSIDER
        for index, row in df_other.iterrows():
            condition = (df_chunk['addr'] >= row['mmapped_addr']) & (df_chunk['addr'] < row['max_mmapped_addr']) & (df_chunk["pid"] == row['pid'])
            df_chunk.loc[condition, "temperature"] = OTHER
        for index, row in df_cold.iterrows():
            condition = (df_chunk['addr'] >= row['mmapped_addr']) & (df_chunk['addr'] < row['max_mmapped_addr']) & (df_chunk["pid"] == row['pid'])
            df_chunk.loc[condition, "temperature"] = COLD

        df_chunk["page"] = df_chunk["addr"] // PAGE_SIZE
        df_chunk['pid_page'] = df_chunk['pid'] * 10000000000000000 + df_chunk['page']
        df_chunk = df_chunk.drop(['addr', 'page', 'pid'], axis=1)
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

def add_index_col(input_path, output_path):
    df = pd.read_csv(input_path, dtype=dtype)
    df["global_index"] = df.index
    print("add index", end='', flush=True)
    df.to_csv(output_path, index=False)
    del df
    gc.collect()
    print(" done")

def build_key_groups(key_dir, input_path):
    try:
        shutil.rmtree(key_dir)
    except:
        None
    try:
        os.mkdir(key_dir)
    except:
        None
    chunk_size = 100000000
    reader = pd.read_csv(input_path, chunksize=chunk_size, dtype=dtype)
    chunk_index = 0
    keys = {}
    for df_chunk in reader:
        groups = df_chunk.groupby('pid_page')
        # initialize progress bar
        maxval = len(groups)
        count = 0
        widgets = [f'build_key_groups chunk:{chunk_index} ', Percentage(), '', Bar('#'), '', '', '', '', '', FileTransferSpeed()]
        pbar = ProgressBar(widgets=widgets, maxval=maxval).start()

        for (key, group) in groups:
            filename = f"{key}.csv"
            if keys.get(filename) is not None:
                group[["temperature", "global_index"]].to_csv(f"{key_dir}{filename}", mode='a', index=False, header=False)
            else:
                keys[filename] = True
                group[["temperature", "global_index"]].to_csv(f"{key_dir}{filename}", index=False)
            pbar.update(count)
            count += 1

        chunk_index += 1
    
    pbar.finish()
    del reader
    gc.collect()

def calculate_reuse_distances(key_dir):
    reuse_distance = {
        COLD : [],
        OTHER : [],
        NOT_CONSIDER : []
    }
    all_data = os.listdir(key_dir)
    
    # initialize progress bar
    maxval = len(all_data)
    count = 0
    widgets = ['calculate reuse distances ', Percentage(), '', Bar('#'), '', '', '', '', '', FileTransferSpeed()]
    pbar = ProgressBar(widgets=widgets, maxval=maxval).start()
    
    for data_path in all_data:
        df = pd.read_csv(key_dir + data_path, dtype=dtype)
        df['last_seen'] = df['global_index'].shift(1)

        df['reuse_distance'] = df['global_index'] - df['last_seen']
        df = df.dropna(subset=['reuse_distance'])
        df['reuse_distance'] = df['reuse_distance'].astype(int)

        reuse_distance[COLD].extend(df[df["temperature"] == COLD]["reuse_distance"].to_list())
        reuse_distance[OTHER].extend(df[df["temperature"] == OTHER]["reuse_distance"].to_list())
        reuse_distance[NOT_CONSIDER].extend(df[df["temperature"] == NOT_CONSIDER]["reuse_distance"].to_list())

        pbar.update(count)
        count += 1

    pbar.finish()
    del df
    gc.collect()
    return reuse_distance

def output(reuse_dist, savepath):
    df_cold = pd.DataFrame({'reuse_dist': reuse_dist['cold_reuse_dist'], 'category': 'cold_reuse_dist'})
    df_other = pd.DataFrame({'reuse_dist': reuse_dist['other_reuse_dist'], 'category': 'other_reuse_dist'})
    df = pd.concat([df_cold, df_other])

    fig, axs = plt.subplots(1, 1, figsize=(7, 5), gridspec_kw={"bottom": 0.3, "top": 0.9})
    sns.histplot(data=df, x='reuse_dist', ax=axs, bins=150, hue='category')
    axs.set_title("Page Reuse Distance Frequency Chart")
    axs.set_ylabel("Reference Count")
    axs.set_xlabel("Reuse Distance")
    axs.set_yscale("log")

    obj_info = "malloc objects information" \
                + "\n" + "|  " + str()
    
    fig.text(0.2, 0.2,  obj_info, ha="left", va="top", fontsize=10, color="blue")
    
    # close Scientific Notation
    # ax = plt.gca()
    # ax.xaxis.set_major_formatter(ScalarFormatter(useOffset=False))
    # ax.xaxis.get_major_formatter().set_scientific(False)

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
        add_temperature_col(df_cold, df_other, input_path="./data/cachemisses.csv", output_path="./data/cachemisses_time.csv")
        add_index_col(input_path="./data/cachemisses_time.csv", output_path="./data/cachemisses_with_index.csv")
        build_key_groups(key_dir="./data/reusedist_keys/", input_path="./data/cachemisses_with_index.csv")
        reuse_distance = calculate_reuse_distances(key_dir="./data/reusedist_keys/")

        with open("./result/cold_reuse_distance_time.json", 'w') as file:
            json.dump(reuse_distance[COLD], file)
        with open("./result/other_reuse_distance_time.json", 'w') as file:
            json.dump(reuse_distance[OTHER], file)
        with open("./result/not_condider_reuse_distance_time.json", 'w') as file:
            json.dump(reuse_distance[NOT_CONSIDER], file)

        del reuse_distance
        gc.collect()

    # already have reuse distance data
    reuse_dist = {}
    with open("./result/cold_reuse_distance_time.json", 'r') as file:
        reuse_dist["cold_reuse_dist"] = json.load(file)
    with open("./result/other_reuse_distance_time.json", 'r') as file:
        reuse_dist["other_reuse_dist"] = json.load(file)
    output(reuse_dist, "reuse_distance_time")
    # with open("./result/not_condider_reuse_distance_time.json", 'r') as file:
    #     reuse_distance = json.load(file)
    #     output(reuse_distance, "not_condider_reuse_distance_time")
    
if __name__ == "__main__":
    plt.rcParams["axes.formatter.useoffset"] = False
    main()