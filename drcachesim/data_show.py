import time
import csv
import re
import vaex
import numpy as np
from progressbar import*
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import seaborn as sns
import os
import threading
import bisect
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean
from scipy.stats import wasserstein_distance
import json
import argparse
import shutil
import random
import math
import copy
import swifter
import dask.dataframe as dd
from dask.diagnostics import ProgressBar

LIFE_TIME_THRESHOLD = 100
LONG_LIFE_TIME_PROPOTION = 0.8
SMALL_AMOUNT_OF_OBJS = 5
INTERVAL_TIME_BOUND = (0.20, 0.60)
INTERVAL_TIME_PROPOTION_THRESHOLD = 0.001
HIT_LIFETIME_PERCENTAGE_BOUND = (20, 70)
HIT_LIFETIME_BOUND_PROPOTION_THRESHOLD = 0.001
OBJ_SIMILARITY_SELECTNUM = 50
BATHTUB_UPPER_BOUND = 99
BATHTUB_LOWER_BOUND = 1

CONTINUE_NUM = 100000

# 0~2 depth
MAX_CALL_CHAIN_DEPTH = 2

obj_dtype = {
    'alloc_type' : str,
    'size' : int,
    'data_addr' : int,
    'alloc_time' : int,
    'callchain0' : int,
    'callchain1' : int,
    'callchain2' : int,
    'callchain3' : int,
    'free_time' : int
}
miss_dtype = {
    'data_addr' : int,
    'miss_time' : int
}

endtime = -1
starttime = -1
alloc_type_mapping = {
    "m" : "malloc",
    "r" : "realloc",
    "c" : "calloc"
}
time_uint_table = {
    "online" : "instructions",
    "offline" : "seconds"
}
time_uint = ""

#============================== Dump Pictures ======================================
#===================================================================================

def show_single_group_info(miss_df, callchain, obj_df, depth, path):
    mask = miss_df["data_addr"].isin(obj_df["data_addr"])
    miss_df = miss_df[mask]

    fig, axs = plt.subplots(1, 3, figsize=(17, 7), gridspec_kw={'bottom': 0.3, 'top': 0.9})
    plt.subplots_adjust(wspace=0.3)

    # real miss time : the miss event actually occur at real time during excuting the
    # program
    bins = np.linspace(-1, endtime + 1, 101)
    sns.histplot(x=miss_df["miss_time"], ax=axs[0], bins=bins)
    axs[0].set_title(f'The Time When a Accessing DRAM Event Occurs\ndue to Accessing Objects within the Group')
    axs[0].set_xlabel(f'Time of Accessing DRAM Event\nOccurs ({time_uint})')
    axs[0].set_ylabel('Number of Accessing DRAM Event')
    axs[0].set_yscale('log')
    axs[0].set_ylim(1, None)
    axs[0].tick_params(axis='x', rotation=15)

    # life time
    sns.histplot(x=obj_df["free_time"] - obj_df["alloc_time"], ax=axs[1], bins=100)
    axs[1].set_title('Object lifetime Distribution Chart whithin the Group')
    axs[1].set_xlabel(f'Length of lifetime ({time_uint})')
    axs[1].set_ylabel('Number of Objects')
    axs[1].set_yscale('log')
    axs[1].set_ylim(1, None)
    
    # objs size
    sns.histplot(x=obj_df["size"], ax=axs[2], bins=100)
    axs[2].set_title('Object Size Distribution Chart whithin the Group')
    axs[2].set_xlabel(f'Size (bytes)')
    axs[2].set_ylabel('Number of Objects')
    axs[2].set_yscale('log')
    axs[2].set_ylim(1, None)

    # Add some raw information to picture
    malloc_info = "Group information"\
        + "\n" + f"|  Group by call-chain (depth) : {hex(callchain)} ({depth})" \
        + "\n" + f"|  Number of events occur due to objects within the group: {len(miss_df)}"\
        + "\n" + f"|  Size of objects within the group : {sum(obj_df['size'].to_list())}"\
        + "\n" + f"|  Number of objects within the group : {len(obj_df)}"
        
    fig.text(0.2, 0.2,  malloc_info, ha='left', va='top', fontsize=10, color='blue')
    
    if not Path(path).exists():
        os.makedirs(path)
    plt.savefig(path + f"/{hex(callchain)}_{depth}")
    plt.close(fig)

def show_groups_score_distribution(groups_info, groups_non_devide_info, path):
    fig, axs = plt.subplots(1, 2, figsize=(10, 4), gridspec_kw={'bottom': 0.3, 'top': 0.9})
    plt.subplots_adjust(wspace=0.3)
    bins = np.arange(0, 101, 1)

    sns.histplot(x=groups_info["score"], ax=axs[0], bins=bins)
    axs[0].set_title(f'Score distribution')
    axs[0].set_xlabel(f'Score')
    axs[0].set_ylabel('Number of Groups')
    axs[0].set_xlim(0, 100)

    sns.histplot(x=groups_non_devide_info["score"], ax=axs[1], bins=bins)
    axs[1].set_title(f'Score distribution non devide')
    axs[1].set_xlabel(f'Score')
    axs[1].set_ylabel('Number of Groups')
    axs[1].set_xlim(0, 100)

    plt.savefig(path)
    plt.close(fig)

def show_groups_info(groups_info, groups_non_devide_info, path):
    total_memory_occupation = groups_info['memory_occupation'].sum()
    def agg_function(group):
        nonlocal total_memory_occupation
        return pd.Series({
            'total_size' : np.sum(group['total_size']),
            'memory_occupation' : np.sum(group['memory_occupation']) / total_memory_occupation *100
        })
    summarize_info = groups_info.groupby('is_suitable_for_swap').apply(agg_function).reset_index()
    summarize_non_devide_info = groups_non_devide_info.groupby('is_suitable_for_swap').apply(agg_function).reset_index()
    
    fig, axs = plt.subplots(1, 2, figsize=(10, 4), gridspec_kw={'bottom': 0.3, 'top': 0.9})
    plt.subplots_adjust(wspace=0.3)
    sns.barplot(y='memory_occupation', hue='is_suitable_for_swap', data=summarize_info, ax=axs[0])
    sns.barplot(y='memory_occupation', hue='is_suitable_for_swap', data=summarize_non_devide_info, ax=axs[1])

    axs[0].set_ylim(0, 100)
    axs[1].set_ylim(0, 100)
    for container in axs[0].containers:
        labels = [f"{float(v.get_height()):.2f}%" for v in container]
        axs[0].bar_label(container, labels=labels)

    info = f"true size : {summarize_info['total_size']}\n"
               
    fig.text(0.2, 0.2, info, ha='left', va='top', fontsize=10, color='blue')

    fig.savefig(path)
    plt.close(fig)

def show_max_non_access_time_distribution(obj_dfs, path):
    fig, axs = plt.subplots(1, 2, figsize=(10, 4), gridspec_kw={'bottom': 0.3, 'top': 0.9})
    plt.subplots_adjust(wspace=0.3)
    
    # Log yscale
    sns.histplot(x=obj_dfs["max_non_access_time"] / 1000000, ax=axs[0], bins=100)
    axs[0].set_title(f'Max Non Access Time Distribution')
    axs[0].set_xlabel(f'Times (seconds)')
    axs[0].set_ylabel('Number of Objectss')
    axs[0].set_yscale('log')
    axs[0].set_ylim(1, None)

    # Normal yscale
    sns.histplot(x=obj_dfs["max_non_access_time"] / 1000000, ax=axs[1], bins=100)
    axs[1].set_title(f'Max Non Access Time Distribution')
    axs[1].set_xlabel(f'Times (seconds)')
    axs[1].set_ylabel('Number of Objectss')
    axs[1].set_ylim(0, None)

    plt.savefig(path)
    plt.close(fig)

def show_realtime_access_distribution(groups_info, obj_dfs, miss_dfs, path):
    suitable_mask = groups_info["is_suitable_for_swap"]
    group_mask = obj_dfs["group_id"].isin(groups_info["group_id"][suitable_mask])
    data_addr_mask = miss_dfs["data_addr"].isin(obj_dfs["data_addr"][group_mask])

    fig, axs = plt.subplots(1, 2, figsize=(10, 4), gridspec_kw={'bottom': 0.3, 'top': 0.9})
    plt.subplots_adjust(wspace=0.3)
    
    # For suitable swap objs
    sns.histplot(x=miss_dfs["miss_time"][data_addr_mask] / 1000000, ax=axs[0], bins=100)
    axs[0].set_title(f'For suitable swap objs')
    axs[0].set_xlabel(f'Times (seconds)')
    axs[0].set_ylabel('Number of Access Event Occur')
    axs[0].set_yscale('log')
    axs[0].set_ylim(1, None)

    # For total objs
    sns.histplot(x=miss_dfs["miss_time"] / 1000000, ax=axs[1], bins=100)
    axs[1].set_title(f'For total objs')
    axs[1].set_xlabel(f'Times (seconds)')
    axs[1].set_ylabel('Number of Access Event Occur')
    axs[1].set_ylim(0, None)

    plt.savefig(path)
    plt.close(fig)

#============================== Data Processing ====================================
#===================================================================================
class group_score_t:
    groups = {}
    score = -1

def calc_score_for_each_groups(obj_df, depth):
    group_score = {}
    if depth > MAX_CALL_CHAIN_DEPTH:
        None
    else:
        # recursively get the groups by the depth of call-chain and calcualate score
        for callchain in set(obj_df[f"callchain{depth}"].to_list()):
            mask_callchain = obj_df[f"callchain{depth}"] == callchain
            obj_with_callchain_df = obj_df[mask_callchain]
            mask_long_non_access_obj = obj_with_callchain_df["max_non_access_time"] >= \
                                       args.non_access_threshold    
            
            group_score[callchain] = group_score_t()
            group_score[callchain].score = len(obj_with_callchain_df[mask_long_non_access_obj]) \
                                           / len(obj_with_callchain_df) * 100
            group_score[callchain].groups = calc_score_for_each_groups(obj_with_callchain_df, 
                                                                       depth + 1)
    return group_score

def is_group_need_to_divide(obj_df, groups, depth, mask):
    # Use loc option to avoid SettingWithCopyWarning
    obj_df.loc[mask, "group_by_depth"] += 1
    obj_df.loc[mask, "group_id"] += obj_df.loc[mask, f"callchain{depth}"].astype(str)

    if depth > MAX_CALL_CHAIN_DEPTH - 1:
        return
    # For each group
    for callchain in groups:
        # This means the depth is more than max depth of some objects' call-chain. 
        # So, the group can't devide anymore.
        if groups[callchain].groups.get(1) is not None:
            devide = False
        else:
            score = groups[callchain].score
            # Count the average score of the group's score more than args.score_threshold
            after_devide_avg_score = 0
            for next_depth_callchain in groups[callchain].groups:
                next_depth_group_score = groups[callchain].groups[next_depth_callchain].score
                if next_depth_group_score >= args.score_threshold:
                    after_devide_avg_score += next_depth_group_score

            after_devide_avg_score /= len(groups[callchain].groups)
            if score >= after_devide_avg_score:
                devide = False
            else:
                devide = True

        if devide:
            to_devide_mask = (obj_df[f"callchain{depth}"] == callchain) & mask
            is_group_need_to_divide(obj_df, groups[callchain].groups, depth + 1, to_devide_mask)

def add_max_non_access_time_colunm(obj_df, miss_df, path):
    def max_non_access_time_func(row, data_addrs_with_misses):
        alloc_time, free_time, data_addr = row['alloc_time'], row['free_time'], row['data_addr']
        times = data_addrs_with_misses.get(data_addr, [])
        # This represent that the obj have non access. We now take it as smallest max 
        # non_access_time, and we don't specialy process these data.
        if len(times) == 0:
            return -1
        times.extend([alloc_time, free_time])
        times.sort()
        max_non_access_time = np.max(np.diff(np.array(times)))
        return max_non_access_time

    print(f"data_show.py : calculate obj max non_access_time {path}")
    data_addrs_with_misses = miss_df.groupby('data_addr')['miss_time'].apply(list).to_dict()
    # Two ways of apply option for muti-process. Although dd is indeed muti-process and swifter
    # may not, swifter still faster than dd. But for bigger data I have no idea witch is better.
    if True:
        obj_df["max_non_access_time"] = obj_df.swifter.apply(
                lambda row: max_non_access_time_func(row, data_addrs_with_misses), axis=1)
    else:
        ddf = dd.from_pandas(obj_df, npartitions=32)
        ddf["max_non_access_time"] = ddf.apply(max_non_access_time_func, axis=1, 
                                            args=(data_addrs_with_misses,), 
                                            meta=('max_non_access_time', 'i8'))
        with ProgressBar():
            obj_df = ddf.compute()

    obj_df.to_csv(path, index=False)

def add_group_id_column(obj_df, pid, path):
    groups = calc_score_for_each_groups(obj_df, 0)
    obj_df["group_by_depth"] = -1
    obj_df["group_id"] = str(pid) + "_"
    mask = obj_df["group_id"] == obj_df["group_id"]
    is_group_need_to_divide(obj_df, groups, 0, mask)
    obj_df.to_csv(path, index=False)

def get_groups_info(obj_dfs, group_column):
    def agg_function(group):
        return pd.Series({
            'score': np.sum(group['max_non_access_time'] >= args.non_access_threshold) / len(group) * 100,
            'total_size': np.sum(group['size']),
            'number_of_objs': len(group),
            'memory_occupation' : np.sum(group['size'] * (group['free_time'] - group['alloc_time']) / 1000000)
        })

    groups_info = obj_dfs.groupby(group_column).apply(agg_function).reset_index()
    groups_info["is_suitable_for_swap"] = groups_info["score"] >= args.score_threshold
    return groups_info

def main():
    global endtime, starttime, args
    with open("./result/endtime", "r") as f:
        endtime = f.readline()
        endtime = int(endtime.strip())
    with open("./result/starttime", "r") as f:
        start_time = f.readline()
        start_time = int(start_time.strip())

    pids = {}
    
    all_data = os.listdir("./result")
    for data in all_data:
        if (re.search(r'\d', data) is not None) and "obj_" in data:
            pid = int(''.join(re.findall(r'\d+', data)), 10)
            pids[pid] = True

    # Add some columns first, if there is already exist then skip.
    obj_dfs = []
    miss_dfs = []
    for pid in pids:
        obj_df = pd.read_csv(f"./result/obj_{pid}.csv", dtype=obj_dtype)
        obj_df = pd.DataFrame(obj_df)
        if os.path.isfile(f"./result/miss_{pid}.csv"):
            miss_df = pd.read_csv(f"./result/miss_{pid}.csv", dtype=miss_dtype)
            miss_df = pd.DataFrame(miss_df)
        else:
            miss_df = pd.DataFrame({})

        if args.have_max_non_access_time == False:
            add_max_non_access_time_colunm(obj_df, miss_df, f"./result/obj_{pid}.csv")

        if args.have_group_id == False:
            add_group_id_column(obj_df, pid, f"./result/obj_{pid}.csv")
        
        # XXX : This way may spend a lot of memory. Considering Using histogram and free
        # the reference of obj_df and free_df.
        obj_dfs.append(obj_df)
        miss_dfs.append(miss_df)

    # Record the result of entire testing program
    obj_dfs = pd.concat(obj_dfs, axis=0)
    miss_dfs = pd.concat(miss_dfs, axis=0)

    groups_info = get_groups_info(obj_dfs, "group_id")
    groups_non_devide_info = get_groups_info(obj_dfs, "callchain0")

    #print(groups_info[groups_info["score"] >= args.score_threshold])

    show_groups_score_distribution(groups_info, groups_non_devide_info, 
                                   "./result_picture/groups_score")
    show_groups_info(groups_info, groups_non_devide_info, "./result_picture/groups_info")
    show_max_non_access_time_distribution(obj_dfs, "./result_picture/max_non_access_time")
    show_realtime_access_distribution(groups_info, obj_dfs, miss_dfs, 
                                      "./result_picture/realtime_access")


if __name__ == "__main__":
    # Turn off the automatic using scientific notation at axis lable
    plt.rcParams['axes.formatter.useoffset'] = False

    parser = argparse.ArgumentParser(
        usage="python3 ./data_show\n" + \
              "--profiling_mode [online]\n" + \
              "--non_access_threshold [60000000]\n" + \
              "--score_threshold [100]\n" + \
              "--have_max_non_access_time [False]\n" + \
              "--have_group_id [False]\n"
    )
    parser.add_argument('--profiling_mode', type=str, default="online",
                        help="[online / offline]")
    parser.add_argument('--non_access_threshold', type=int, default=60000000,
                        help="[micro-seconds]")
    parser.add_argument('--score_threshold', type=int, default=100,
                        help="[0~100]")
    parser.add_argument('--have_max_non_access_time', type=bool, default=False,
                        help="[True / False]")
    parser.add_argument('--have_group_id', type=bool, default=False,
                        help="[True / False]")
    args = parser.parse_args()
    
    time_uint = time_uint_table[args.profiling_mode]

    main()
