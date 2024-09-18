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

dtype = {
    "caller_addr" : int,
    "data_addr" : int,
    "caller_addr_str" : str,
    "interval_time" : float,
    "hit_time" : float,
    "alloc_time" : float,
    "free_time" : float,
    "hit_relative_time" : float,
    "size" : int,
    "caller_objects_num" : int,
    "caller_total_alloc_size" : int,
    "data_addr_end" : int,
    "pool_begin" : int,
    "generation" : float,
    "lifetime" : float,
    "alloc_type" : str
}

endtime = -1
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

alloc_type_mapping = {
    "m" : "malloc",
    "r" : "realloc",
    "c" : "calloc"
}
event_moment = []


def DTW(df_per_malloc, savepath, malloc_info):
    global endtime
    print(df_per_malloc)
    
    # obtain the graph of all the data to be our standard for comparison
    standard = df_per_malloc["hit_absolute_time"].to_numpy()
    standard.sort()
    # create interval of hisplot bins
    bin_edges = np.arange(0, endtime, endtime / 101)
    bin_edges[0] -= 1000
    bin_edges[-1] += 1000
    # create x-axis to display graph
    x_axis = bin_edges[0 : -1].copy()
    x_axis[0] = 0
    # convert the graph into a histogram
    standard_hist, bins = np.histogram(standard, bins=bin_edges)
    standard_hist_avg = standard_hist.copy() / float(malloc_info["count_of_objs"].to_string(index = False))

    # discard some mallocs which have few objects
    #if len(standard) < 200 or standard[-1] - standard[0] < 1:
    #    return

    # obtain data graphs for each objec
    malloc_objs = df_per_malloc.groupby("data_addr", as_index=False).size()
    malloc_objs = malloc_objs["data_addr"].to_dict()
    #malloc_objs.columns = malloc_objs.columns.map(''.join)
    #print(malloc_objs)

    dtws = []
    normalized_dtws = []
    sampled_dtws = []
    sampled_normalized_dtws = []
    hit_count = []

    for index in malloc_objs:
        obj = malloc_objs[index]
        print(index, obj)
        mask = df_per_malloc["data_addr"] == obj
        obj_performance = df_per_malloc[mask]["hit_absolute_time"].to_numpy()
        
        obj_performance_hist, bins = np.histogram(obj_performance, bins=bin_edges)
        standard_hist_resize = standard_hist_avg.copy() * (len(obj_performance))

        distance1 = wasserstein_distance(x_axis, x_axis, standard_hist, obj_performance_hist)
        distance2 = wasserstein_distance(x_axis, x_axis, standard_hist_resize, obj_performance_hist)

        normalized_distance1 = distance1 / (len(obj_performance))
        normalized_distance2 = distance2 / (len(obj_performance))

        # save the picture of objects performance diagram
        if len(obj_performance) > 100:
            print("obj_performance", obj_performance)

            fig, axs = plt.subplots(1, 3, figsize=(14, 5), gridspec_kw={'bottom': 0.3, 'top': 0.9})
        
            sns.lineplot(x=x_axis, y=standard_hist, ax=axs[0])
            sns.lineplot(x=x_axis, y=standard_hist_resize, ax=axs[1])
            sns.lineplot(x=x_axis, y=obj_performance_hist, ax=axs[2])            

            obj_info = "malloc object information" \
                        + "\n" + "|  DTW (normalized_standard and normalized obj_performance) : " + str(distance1) \
                        + "\n" + "|  DTW Normalized Distance : " + str(normalized_distance1) \
                        + "\n" + "|" \
                        + "\n" + "|  DTW (sampled_normalized_standard and normalized obj_performance) : " + str(distance2) \
                        + "\n" + "|  DTW Normalized Distance : " + str(normalized_distance2)
            fig.text(0.2, 0.2,  obj_info, ha='left', va='top', fontsize=10, color='blue')

            fig.savefig(savepath + "_object" + str(index))
            plt.close(fig)
        
        dtws.append(distance1)
        normalized_dtws.append(normalized_distance1)
        sampled_dtws.append(distance2)
        sampled_normalized_dtws.append(normalized_distance2)
        hit_count.append(len(obj_performance))
        

    fig, axs = plt.subplots(2, 2, figsize=(14, 14), gridspec_kw={'bottom': 0.2, 'top': 0.9})
    sns.histplot(x=hit_count, y=dtws, ax=axs[0][0], cbar=True)
    sns.histplot(x=hit_count, y=normalized_dtws, ax=axs[0][1], cbar=True)
    #sns.histplot(x=hit_count, y=sampled_dtws, ax=axs[1][0], cbar=True)
    #print(sampled_normalized_dtws, len(sampled_normalized_dtws))
    #print(hit_count, len(hit_count))
    #sns.histplot(x=hit_count, y=sampled_normalized_dtws, ax=axs[1][1], cbar=True)

    fig.savefig(savepath + "_all_objects")
    plt.close(fig)

    #print("DTW :", distance)
    #print("path :", path)
    print("\n\n\n")

# save the picture shows that the count of hits and size of all objs alloced from this malloc
def record_objs(obj_sizes, statistics_hits, statistics_lifetime, no_event_objs, savepath):

    number_of_short_lifetime = 0
    number_of_total_objs = len(obj_sizes)
    number_of_zreo_hit = 0 
    number_of_hit_between_1_10 = 0

    for i in statistics_hits:
        if i == 0:
            number_of_zreo_hit += 1
        elif i <= 10 and i >= 1:
            number_of_hit_between_1_10 += 1
    
    for i in statistics_lifetime:
        if i < LIFE_TIME_THRESHOLD:
            number_of_short_lifetime += 1
        
    
    fig, axs = plt.subplots(1, 2, figsize=(14, 7), gridspec_kw={'bottom': 0.3, 'top': 0.9})
    sns.histplot(x=statistics_hits, ax=axs[0], bins=100)
    axs[0].set_title('Counting the number of times an object is hit')
    axs[0].set_ylabel('number of objects')
    axs[0].set_xlabel('number of hits(cachemisses)')
    axs[0].set_yscale('log')
    sns.histplot(x=obj_sizes, ax=axs[1], bins=100)
    axs[1].set_title('Measuring object sizes')
    axs[1].set_ylabel('number of objects')
    axs[1].set_xlabel('sizes')
    axs[1].set_yscale('log')
    
    obj_info = "malloc objects information" \
                + "\n" + "|  Number of tatal objects : " + str(number_of_total_objs) \
                + "\n" + f"|  Number of objects with lifetime < {LIFE_TIME_THRESHOLD}s : " +  str(number_of_short_lifetime)\
                + "\n" + f"|  Number of Objects with lifetime >= {LIFE_TIME_THRESHOLD}s : " + str(number_of_total_objs - number_of_short_lifetime) \
                + "\n" + "|  Number of objects with times of hit is 0 : " + str(number_of_zreo_hit) \
                + "\n" + "|  Number of objects with times of hit is between 1~10 : " + str(number_of_hit_between_1_10) \
                + "\n" + "|  Number of objects with times of hit is > 10 : " + str(number_of_total_objs - number_of_hit_between_1_10 - number_of_zreo_hit) \
                + "\n" + f"|  Porpotion of long lifetime objects (lifetime >= {LIFE_TIME_THRESHOLD}s): " + str((1 - number_of_short_lifetime / number_of_total_objs) * 100) + "%"
    fig.text(0.2, 0.2,  obj_info, ha='left', va='top', fontsize=10, color='blue')
    fig.savefig(savepath + "_all_obj")
    plt.close(fig)

    # for objs don't have any event
    if len(no_event_objs) == 0:
        return
    
    no_event_obj_lifetime = no_event_objs["lifetime"]
    no_event_obj_sizes = no_event_objs["size"]
    fig, axs = plt.subplots(1, 2, figsize=(14, 7), gridspec_kw={'bottom': 0.3, 'top': 0.9})
    sns.histplot(x=no_event_obj_lifetime, ax=axs[0], bins=100)
    axs[0].set_title('Counting the number of lifetime')
    axs[0].set_ylabel('number of objects')
    axs[0].set_xlabel('value of lifetime(seconds)')
    axs[0].set_yscale('log')
    sns.histplot(x=no_event_obj_sizes, ax=axs[1], bins=100)
    axs[1].set_title('Measuring object sizes')
    axs[1].set_ylabel('number of objects')
    axs[1].set_xlabel('sizes')
    axs[1].set_yscale('log')
    
    number_of_total_no_event_objs = len(no_event_objs)
    number_of_no_event_objs_shortlifetime = len(no_event_objs[no_event_objs["lifetime"] < LIFE_TIME_THRESHOLD])
    number_of_no_event_objs_smallsize = len(no_event_objs[no_event_objs["size"] < 64])
    obj_info = "malloc objects information" \
                + "\n" + "|  Number of tatal no event objects : " + str(number_of_total_no_event_objs) \
                + "\n" + f"|  Number of no event objects with lifetime < {LIFE_TIME_THRESHOLD} : " +  str(number_of_no_event_objs_shortlifetime)\
                + "\n" + f"|  Number of no event Objects with lifetime >= {LIFE_TIME_THRESHOLD} : " + str(number_of_total_no_event_objs - number_of_no_event_objs_shortlifetime) \
                + "\n" + "|  Number of no event objects with size < 64 : " + str(number_of_no_event_objs_smallsize) \
                + "\n" + "|  Number of no event objects with size >= 64 : " + str(number_of_total_no_event_objs - number_of_no_event_objs_smallsize) \
                + "\n" + "|  " + str()
    fig.text(0.2, 0.2,  obj_info, ha='left', va='top', fontsize=10, color='blue')
    fig.savefig(savepath + "_noevent_obj")
    plt.close(fig)

# save the picture shows that the interval hit time and size of each objs alloced from this malloc
def record_obj(obj_life_time, obj_size, obj_interval, obj_performance, obj_alloctime, obj_freetime, savepath, obj_addr, index):
    
    #save picture
    fig, axs = plt.subplots(1, 2, figsize=(14, 7), gridspec_kw={'bottom': 0.3, 'top': 0.9})
    sns.histplot(x=obj_performance, ax=axs[0], bins=100)
    axs[0].set_title('Hits Count for Malloc Object')
    axs[0].set_ylabel('count')
    axs[0].set_xlabel('time (second) : actually hit time - alloc time')
    axs[0].set_yscale('log')
    sns.histplot(x=obj_interval, ax=axs[1], bins=100)
    axs[1].set_title('Count Ineterval Hit Time for Malloc object')
    axs[1].set_ylabel('count')
    axs[1].set_xlabel('interval time (second) : ith hit time - (i - 1)th hit time')
    axs[1].set_yscale('log')
    
    obj_info = "malloc object information" \
                + "\n" + "|  obj addr : " + obj_addr \
                + "\n" + "|  object size : " +  str(obj_size)\
                + "\n" + "|  life time : " + str(obj_life_time) \
                + "\n" + "|  total cachemisses : " + str(len(obj_performance)) \
                + "\n" + "|  alloc time : " + str(obj_alloctime) \
                + "\n" + "|  free time : " + str(obj_freetime) \
                + "\n" + "|  " + str()
    fig.text(0.2, 0.2,  obj_info, ha='left', va='top', fontsize=10, color='blue')
    fig.savefig(savepath + "obj_" + str(index))
    if not Path(savepath + "size" + str(obj_size)).exists():
        os.makedirs(savepath + "size" + str(obj_size))
    fig.savefig(savepath + "size" + str(obj_size) + "/" + "obj_" + str(index))
    plt.close(fig)

# save the picture shows that the interval hit time of all objs alloced from this malloc
def record_internal(intervals, intervals_128kfilter, obj_sizes, obj_sizes_128kfilter, savepath):
    #save picture
    fig, axs = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={'bottom': 0.3, 'top': 0.9})
    sns.histplot(x=intervals, ax=axs[0], bins=100)
    axs[0].set_title('Count Sampling Hits Ineterval time')
    axs[0].set_ylabel('count')
    axs[0].set_xlabel('interval time (second)')
    axs[0].set_yscale('log')
    sns.histplot(x=intervals_128kfilter, ax=axs[1], bins=100)
    axs[1].set_title('Count Sampling Hits Ineterval time with 128k filter')
    axs[1].set_ylabel('count')
    axs[1].set_xlabel('interval time (second)')
    axs[1].set_yscale('log')
    
    avgsize = sum(obj_sizes) / len(obj_sizes)
    if len(obj_sizes_128kfilter) == 0:
        avgsize_filter128k = 0
    else:
        avgsize_filter128k = sum(obj_sizes_128kfilter) / len(obj_sizes_128kfilter)
    
    obj_info = "malloc objects information" \
                + "\n" + "|  avg object size : " +  str(avgsize)\
                + "\n" + "|  Number of Objects : " + str(len(obj_sizes)) \
                + "\n" + "|  " + str() \
                + "\n" + "|  avg object size without which size bigger than 128k : " + str(avgsize_filter128k) \
                + "\n" + "|  Number of Objects without which size bigger than 128k : " + str(len(obj_sizes_128kfilter)) \
                + "\n" + "|  " + str() \
                + "\n" + "|  " + str()
    fig.text(0.2, 0.2,  obj_info, ha='left', va='top', fontsize=10, color='blue')
    fig.savefig(savepath + "_all_interval")
    plt.close(fig)

# save the picture shows that the real hit itme of all objs alloced from this malloc,
# and if there is a time of important event we already recorded in ./event_moment.txt,
# highlight these time to the realtime picture
def record_malloc_with_realtime(df, savepath):
    global event_moment, endtime

    # create interval of hisplot bins
    bin_edges = np.arange(0, endtime, endtime / 101)
    bin_edges[0] -= 1000
    bin_edges[-1] += 1000
    # create x-axis to display graph
    x_axis = bin_edges[0 : -1].copy()
    x_axis[0] = 0

    fig, axs = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={'bottom': 0.3, 'top': 0.9}) # bottom and top is percentage 
    plt.subplots_adjust(wspace=0.3)
    # convert the graph into a histogram
    hist, bins = np.histogram(df["hit_time"], bins=bin_edges)
    # real time
    sns.histplot(x=x_axis, weights=hist, ax=axs[0], bins=100)
    axs[0].set_title('Sampling Hits Count for Malloc Objects in Real time')
    axs[0].set_xlabel('Real Timing of Sampling Hits Across lifetimes (seconds)')
    axs[0].set_ylabel('Number of Sampling Hits')
    for moment in event_moment:
        axs[0].axvline(x=moment, color='green', linestyle='--')

    plt.savefig(savepath + '_realtime')
    plt.close(fig)

# save the picture shows that absolute/relative hit time and lifetime of all objs alloed from this malloc
def record_malloc(df_abs, df_lifetime, df_rel, per_caller_info, long_lifetime_propotion, is_cold, cold_score, savepath):
    global alloc_type_mapping
    
    fig, axs = plt.subplots(1, 3, figsize=(17, 7), gridspec_kw={'bottom': 0.3, 'top': 0.9}) # bottom and top is percentage 
    plt.subplots_adjust(wspace=0.3)
    # absolute time
    sns.histplot(x=df_abs["hit_absolute_time"], ax=axs[0], bins=100)
    axs[0].set_title('Sampling Hits Count for Malloc Objects')
    axs[0].set_xlabel('Timing of Sampling Hits Across lifetimes (seconds)')
    axs[0].set_ylabel('Number of Sampling Hits')
    axs[0].tick_params(axis='x', rotation=15)
    axs[0].set_yscale('log')
    
    # relatine time
    rel_bins = np.linspace(-3, 103, 101)
    sns.histplot(x=df_rel["hit_relative_time"], ax=axs[1], bins=rel_bins)
    axs[1].set_title('Sampling Hits Count for Malloc Objects')
    axs[1].set_xlabel('Timing of Sampling Hits Across lifetimes (%)')
    axs[1].set_ylabel('Number of Sampling Hits')
    axs[1].set_yscale('log')
    #axs[1].set_xlim(-3, 103)

    # life time
    sns.histplot(x=df_lifetime["lifetime"], ax=axs[2], bins=100)
    axs[2].set_title('lifetime Lengths of Malloc Objects')
    axs[2].set_xlabel('lifetime Lengths (seconds)')
    axs[2].set_ylabel('Number of Malloc Objects')
    axs[2].tick_params(axis='x', rotation=15)
    axs[2].set_yscale('log')
    
    # add some information to picture
    alloc_type = alloc_type_mapping[df_lifetime["alloc_type"].iloc[0]]
    if is_cold:
        temperature = "cold"
        cold_score_text = str(cold_score * 100) + "%"
    else:
        if cold_score == -1:
            temperature = "other"
            cold_score_text = "None"
        else:
            temperature = "other"
            cold_score_text = str(cold_score * 100) + "%"

    malloc_info = "alloc information (type: "+  alloc_type + ")" + " (temperature: " + temperature + ")"\
        + "\n" + "|  malloc address : " + per_caller_info["caller_addr_str"].to_string(index=False) \
        + "\n" + "|  Sampling Hits Count of malloc Objects : " + per_caller_info["count_of_hits"].to_string(index=False) \
        + "\n" + "|  Size of All Allocated Spaces by this malloc: " + per_caller_info["total_alloc_size"].to_string(index=False) \
        + "\n" + "|  Number of Objects Allocated by this malloc : " + per_caller_info["count_of_objs"].to_string(index=False) \
        + "\n" + f"|  Propotion of Long Lifetime Objects (lifetime >= {LIFE_TIME_THRESHOLD}s) : " + str(long_lifetime_propotion * 100) + "%" \
        + "\n" + f"|  Propotion of hit at percentage of lifetime between ({HIT_LIFETIME_PERCENTAGE_BOUND[0]}%, {HIT_LIFETIME_PERCENTAGE_BOUND[1]}%) : " + cold_score_text
    
    fig.text(0.2, 0.2,  malloc_info, ha='left', va='top', fontsize=10, color='blue')
    #fig.text(0.6, 0.2, other_info, ha='left', va='top', fontsize=10, color='blue')
    
    plt.savefig(savepath)
    plt.close(fig)

    record_malloc_with_realtime(df_abs, savepath)

# save the picture shows that the lifetime and size of each objs alloced from this malloc
def record_objs_with_no_event(df_myaf, savepath):

    number_of_total_objs = len(df_myaf)
    number_of_small_size = len(df_myaf[df_myaf["size"] <= 64])
    number_of_short_lifetime = len(df_myaf[df_myaf["lifetime"] < LIFE_TIME_THRESHOLD])

    # print(number_of_short_lifetime, number_of_small_size, number_of_total_objs)

    fig, axs = plt.subplots(1, 2, figsize=(14, 7), gridspec_kw={'bottom': 0.3, 'top': 0.9})
    sns.histplot(x=df_myaf["lifetime"], ax=axs[0], bins=100)
    axs[0].set_title('Counting the number of lifetime of an object')
    axs[0].set_ylabel('number of objects')
    axs[0].set_xlabel('number of lifetime')
    axs[0].set_yscale('log')
    sns.histplot(x=df_myaf["size"], ax=axs[1], bins=100)
    axs[1].set_title('Measuring object sizes')
    axs[1].set_ylabel('number of objects')
    axs[1].set_xlabel('sizes')
    axs[1].set_yscale('log')
    
    obj_info = "malloc objects information" \
                + "\n" + "|  Size of tatal objects : " + str(df_myaf["size"].sum()) \
                + "\n" + "|  Number of tatal objects : " + str(number_of_total_objs) \
                + "\n" + f"|  Number of objects with lifetime < {LIFE_TIME_THRESHOLD}s : " +  str(number_of_short_lifetime)\
                + "\n" + f"|  Number of Objects with lifetime >= {LIFE_TIME_THRESHOLD}s : " + str(number_of_total_objs - number_of_short_lifetime) \
                + "\n" + "|  Number of objects with size <= 64 : " + str(number_of_small_size) \
                + "\n" + "|  " + str()
    fig.text(0.2, 0.2,  obj_info, ha='left', va='top', fontsize=10, color='blue')
    fig.savefig(savepath + "_all_obj")
    plt.close(fig)

# save the picture shows that the total size of each objs alloced from this malloc
def record_size_with_no_event(pid, df_not):
    # save the picture that shows size of total obj alloced from each malloc    
    df_not = df_not.sort_values("caller_total_alloc_size", ascending=False)
    indicate = df_not.head(50)

    fig = plt.figure(figsize=(10, 8), dpi=100)
    plt.title('total alloc size for mallocs which objs not have any event pid=' + str(pid))
    sns.barplot(data=indicate, x="caller_total_alloc_size", y="caller_addr_str")
    plt.savefig("./result_picture/" + str(pid) + "_no_event_size" + ".png")

def record_obj_similarity(indexs, malloc_objs, df_per_malloc, savepath):
    fig, axs = plt.subplots(1, 2, figsize=(14, 8), gridspec_kw={'bottom': 0.1, 'top': 0.9})
    objs_performance = []
    objs_index = []
    for index in indexs:
        obj = malloc_objs[index]
        mask = df_per_malloc["data_addr"] == obj
        df_obj = df_per_malloc[mask]
        obj_interval = df_obj["hit_relative_time"].to_numpy()
        obj_performance = list(obj_interval.copy())
        objs_performance += obj_performance
        objs_index += [str(index)] * len(obj_performance)
    sns.stripplot(x=objs_performance, y=objs_index, ax=axs[0], jitter=False, s=5, marker="o", linewidth=1, alpha=.35)
    axs[0].set_xlim(-1, 101)
    axs[0].set_xlabel('Cache Miss Occurring Across lifetime of object (%)')
    axs[0].set_ylabel('Index of Objects')
    plt.savefig(savepath)
    plt.close(fig)

# statistics interval hit time and some information, then call other funcs to save pictures
def statistics(df_per_malloc, df_myaf, filter_flag, savepath, interval_data):
    global endtime
    #print(df_per_malloc)
    #print("df myaf")
    #print(df_myaf)

    malloc_objs_df = df_per_malloc.groupby("data_addr", as_index=False).size()
    malloc_objs = malloc_objs_df["data_addr"].to_dict()

    # data and information
    intervals = []
    intervals_128kfilter = []
    obj_sizes = []
    obj_sizes_128kfilter = []
    statistics_hits = []

    # for every objects calculate the interval hit time
    def process_obj(indexs, statistics_hits_local, intervals_local, intervals_128kfilter_local):
        nonlocal malloc_objs, df_per_malloc
        
        for index in indexs:
            # record the object hit interval
            obj_interval = []
            # get data
            obj = malloc_objs[index]
            # print("    ", index, obj)
            # print(df_per_malloc)

            mask = df_per_malloc["data_addr"] == obj
            df_obj = df_per_malloc[mask]
            obj_interval = df_obj["hit_absolute_time"].to_numpy()
            obj_performance = list(obj_interval.copy())

            obj_life_time = float(df_obj["lifetime"].iloc[0: 1].to_string(index = False))
            obj_size = int(df_obj["size"].iloc[0: 1].to_string(index = False), 10)
            obj_performance_without_lifetime = obj_performance.copy()
            obj_interval = np.append(obj_interval, obj_life_time)
            obj_performance.append(obj_life_time)
            obj_addr = hex(int(df_obj["data_addr"].iloc[0: 1].to_string(index = False), 10))
            obj_alloctime = float(df_obj["alloc_time"].iloc[0: 1].to_string(index = False))
            obj_freetime = float(df_obj["free_time"].iloc[0: 1].to_string(index = False))

            obj_interval = np.sort(obj_interval)
            first_hit = obj_interval[0]
            obj_interval = np.diff(obj_interval)
            obj_interval = list(np.append(obj_interval, first_hit))

            intervals_local += obj_interval
            if obj_size <= 128 * 1024:
                intervals_128kfilter_local += obj_interval

            # record other information
            if len(obj_performance) > 100 or (filter_flag and len(malloc_objs) < 1000):
                record_obj(obj_life_time, obj_size, obj_interval, obj_performance_without_lifetime, obj_alloctime, obj_freetime, savepath + "_obj/", obj_addr, index)

            statistics_hits_local.append(len(obj_performance_without_lifetime))

    # just show objects
    if args.just_show_obj_similarity:
        random_index = random.sample(malloc_objs.keys(), OBJ_SIMILARITY_SELECTNUM)
        record_obj_similarity(random_index, malloc_objs, df_per_malloc, savepath + "_obj_similarity")
        return
    
    else:            
        if not Path(savepath + "_obj").exists():
            os.makedirs(savepath + "_obj")
        # if there is so many obj in this malloc
        # use multithreading to calculate
        if len(malloc_objs) > 100:
            thread_num = 16
            split_index = list(malloc_objs.keys())
            split_index = np.array_split(split_index, thread_num)
            statistics_hits_locals = [[] for _ in range(thread_num)]
            intervals_locals = [[] for _ in range(thread_num)]
            intervals_128kfilter_local = [[] for _ in range(thread_num)]
            threads = []
            for i in range(thread_num):
                thread = threading.Thread(target=process_obj, args=(split_index[i], statistics_hits_locals[i], intervals_locals[i], intervals_128kfilter_local[i]))
                threads.append(thread)
                thread.start()

            # wait for all threads
            for thread in threads:
                thread.join()
            
            for i in range(thread_num):
                statistics_hits += statistics_hits_locals[i]
                intervals += intervals_locals[i]
                intervals_128kfilter += intervals_128kfilter_local[i]

        # else use original ways
        else:
            process_obj(list(malloc_objs.keys()), statistics_hits, intervals, intervals_128kfilter)

        try:
            os.rmdir(savepath + "_obj")
        except:
            None

    # statistics some information
    
    # mask for objs which do not have any event
    mask = ~df_myaf["data_addr"].isin(malloc_objs_df["data_addr"])
    # mask for objs' size bigger then 128k 
    mask_128ksize = df_myaf["size"] <= 128 * 1024

    intervals += df_myaf[mask]["lifetime"].to_numpy().tolist()
    intervals_128kfilter += df_myaf[mask & mask_128ksize]["lifetime"].to_numpy().tolist()
    obj_sizes = df_myaf["size"].to_numpy().tolist()
    obj_sizes_128kfilter = df_myaf[mask_128ksize]["size"].to_numpy().tolist()
    statistics_hits += [0] * len(df_myaf[mask])
    statistics_lifetime = df_myaf["lifetime"].to_numpy().tolist()
    # objs have no event
    no_event_objs = df_myaf[mask]
    
    record_internal(intervals, intervals_128kfilter, obj_sizes, obj_sizes_128kfilter, savepath)
    record_objs(obj_sizes, statistics_hits, statistics_lifetime, no_event_objs, savepath)

    # dump the data of interval time for this malloc
    # this is use to filter out cold malloc
    interval_data["intervals"] = intervals
    interval_data["intervals_128kfilter"] = intervals_128kfilter

    with open(savepath + "_interval_data.json", 'w') as file:
        json.dump(interval_data, file)

def record_score_global_data(global_data):
    global endtime
    hit_bin_edges = np.linspace(0, 100, 1001)
    hit_bin_centers = (hit_bin_edges[:-1] + hit_bin_edges[1:]) / 2
    lifetime_bin_edges = np.linspace(0, endtime, 1001)
    lifetime_bin_centers = (lifetime_bin_edges[:-1] + lifetime_bin_edges[1:]) / 2
    lifetime_bin_centers = [round(num) for num in lifetime_bin_centers]
    #save picture
    fig, axs = plt.subplots(1, 2, figsize=(18, 9), gridspec_kw={'bottom': 0.3, 'top': 0.9}, dpi=300)
    sns.lineplot(x=hit_bin_centers, y=global_data["total_hit_hist"], ax=axs[0], linewidth = 2)
    axs[0].fill_between(hit_bin_centers, global_data["total_hit_hist"], 0, alpha=0.5)

    axs[0].axvline(x=BATHTUB_LOWER_BOUND, color='red', linestyle='--', linewidth=1.5)
    axs[0].axvline(x=BATHTUB_UPPER_BOUND, color='red', linestyle='--', linewidth=1.5)
    axs[0].annotate(f'x={BATHTUB_LOWER_BOUND}', xy=(BATHTUB_LOWER_BOUND, axs[0].get_ylim()[1]), xytext=(5, 5),
                    textcoords='offset points', color='red', fontsize=14,
                    arrowprops=dict(arrowstyle='->', color='red'))
    axs[0].annotate(f'x={BATHTUB_UPPER_BOUND}', xy=(BATHTUB_UPPER_BOUND, axs[0].get_ylim()[1]), xytext=(5, 5),
                    textcoords='offset points', color='red', fontsize=14,
                    arrowprops=dict(arrowstyle='->', color='red'))
    axs[0].tick_params(axis='x', length=10, width=2, labelsize=14)
    axs[0].tick_params(axis='y', length=10, width=2, labelsize=14)
    axs[0].set_xlabel('Bins', fontsize=16)
    axs[0].set_ylabel('Frequency', fontsize=16)
    axs[0].set_title('Histogram with Bin Edges', fontsize=16)
    

    # lifetime 
    sns.lineplot(x=lifetime_bin_centers, y=global_data["total_lifetime_hist"], ax=axs[1], linewidth = 2)
    axs[1].fill_between(lifetime_bin_centers, global_data["total_lifetime_hist"], 0, alpha=0.5)

    axs[1].axvline(x=LIFE_TIME_THRESHOLD, color='red', linestyle='--', linewidth=1.5)
    axs[1].annotate(f'x={LIFE_TIME_THRESHOLD}', xy=(LIFE_TIME_THRESHOLD, axs[1].get_ylim()[1]), xytext=(5, 5),
                    textcoords='offset points', color='red', fontsize=14,
                    arrowprops=dict(arrowstyle='->', color='red'))
    axs[1].tick_params(axis='x', length=10, width=2, labelsize=14)
    axs[1].tick_params(axis='y', length=10, width=2, labelsize=14)
    axs[1].set_xlabel('Bins', fontsize=16)
    axs[1].set_ylabel('Frequency', fontsize=16)
    axs[1].set_title('Histogram with Bin Edges', fontsize=16)
    
    path = "./result_picture/score/"
    if not Path(path).exists():
        os.makedirs(path)
    fig.savefig(path + "threshold")
    plt.close(fig)

    # log picture

    fig, axs = plt.subplots(1, 2, figsize=(18, 9), gridspec_kw={'bottom': 0.3, 'top': 0.9}, dpi=300)
    sns.lineplot(x=hit_bin_centers, y=global_data["total_hit_hist"], ax=axs[0], linewidth = 2)
    axs[0].fill_between(hit_bin_centers, global_data["total_hit_hist"], 0, alpha=0.5)

    axs[0].axvline(x=BATHTUB_LOWER_BOUND, color='red', linestyle='--', linewidth=1.5)
    axs[0].axvline(x=BATHTUB_UPPER_BOUND, color='red', linestyle='--', linewidth=1.5)
    axs[0].annotate(f'x={BATHTUB_LOWER_BOUND}', xy=(BATHTUB_LOWER_BOUND, axs[0].get_ylim()[1]), xytext=(5, 5),
                    textcoords='offset points', color='red', fontsize=14,
                    arrowprops=dict(arrowstyle='->', color='red'))
    axs[0].annotate(f'x={BATHTUB_UPPER_BOUND}', xy=(BATHTUB_UPPER_BOUND, axs[0].get_ylim()[1]), xytext=(5, 5),
                    textcoords='offset points', color='red', fontsize=14,
                    arrowprops=dict(arrowstyle='->', color='red'))
    axs[0].tick_params(axis='x', length=10, width=2, labelsize=14)
    axs[0].tick_params(axis='y', length=10, width=2, labelsize=14)
    axs[0].set_xlabel('Bins', fontsize=16)
    axs[0].set_ylabel('Frequency', fontsize=16)
    axs[0].set_title('Histogram with Bin Edges', fontsize=16)
    axs[0].set_yscale('log', base=2)

    # lifetime 
    sns.lineplot(x=lifetime_bin_centers, y=global_data["total_lifetime_hist"], ax=axs[1], linewidth = 2)
    axs[1].fill_between(lifetime_bin_centers, global_data["total_lifetime_hist"], 0, alpha=0.5)

    axs[1].axvline(x=LIFE_TIME_THRESHOLD, color='red', linestyle='--', linewidth=1.5)
    axs[1].annotate(f'x={LIFE_TIME_THRESHOLD}', xy=(LIFE_TIME_THRESHOLD, axs[1].get_ylim()[1]), xytext=(5, 5),
                    textcoords='offset points', color='red', fontsize=14,
                    arrowprops=dict(arrowstyle='->', color='red'))
    axs[1].tick_params(axis='x', length=10, width=2, labelsize=14)
    axs[1].tick_params(axis='y', length=10, width=2, labelsize=14)
    axs[1].set_xlabel('Bins', fontsize=16)
    axs[1].set_ylabel('Frequency', fontsize=16)
    axs[1].set_title('Histogram with Bin Edges', fontsize=16)
    axs[1].set_yscale('log', base=2)
    path = "./result_picture/score/"
    if not Path(path).exists():
        os.makedirs(path)
    fig.savefig(path + "threshold2")
    plt.close(fig)

def record_all_allocs(score_data, unsampled_allocs):
    temp = {
        "cold" : 0,        
        "other" : 0,
        "unsampled" : 0
    }
    count = temp.copy()
    alloc_size = temp.copy()
    lifetime_objsize_product = temp.copy()

    for data in score_data.values():
        if data["is_cold_flag"] == True:
            count["cold"] += 1
            alloc_size["cold"] += data["alloc_size"]
            lifetime_objsize_product["cold"] += data["lifetime_objsize_product"]
        else:
            count["other"] += 1
            alloc_size["other"] += data["alloc_size"]
            lifetime_objsize_product["other"] += data["lifetime_objsize_product"]
    
    for data in unsampled_allocs.values():
        count["unsampled"] += 1
        alloc_size["unsampled"] += data["alloc_size"]
        lifetime_objsize_product["unsampled"] += data["lifetime_objsize_product"]

    all_data = {
        "count" : count,
        "alloc_size" : alloc_size,
        "lifetime_objsize_product" : lifetime_objsize_product
    }

    raw_data = copy.deepcopy(all_data)

    for dtype in all_data:
        total_value = 0
        for alloc_temper in all_data[dtype]:
            total_value += all_data[dtype][alloc_temper]
        for alloc_temper in all_data[dtype]:
            all_data[dtype][alloc_temper] = round(all_data[dtype][alloc_temper] / total_value * 100, 3)
    
    df = pd.DataFrame.from_dict(all_data)
    df = df.reset_index().rename(columns={'index': 'temperature'})
    df_long = pd.melt(df, id_vars='temperature', value_vars=['count', 'alloc_size', 'lifetime_objsize_product'],
                  var_name='method', value_name='propotion')

    fig, axs = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={'bottom': 0.3, 'top': 0.9})
    plt.subplots_adjust(wspace=0.3)
    sns.barplot(x='method', y='propotion', hue='temperature', data=df_long, ax=axs[0])
    for container in axs[0].containers:
        labels = [f"{float(v.get_height()):.2f}%" for v in container]
        axs[0].bar_label(container, labels=labels)

    info = "count : " + str(raw_data["count"]) + "\n" \
           "alloc_size : " + str(raw_data["alloc_size"]) + "\n" \
           "lifetime_objsize_product : " + str(raw_data["lifetime_objsize_product"]) + "\n"
               

    fig.text(0.2, 0.2, info, ha='left', va='top', fontsize=10, color='blue')

    path = "./result_picture/score/"
    if not Path(path).exists():
        os.makedirs(path)
    fig.savefig(path + f"all_allocs_{args.cold_propotion}")
    plt.close(fig)

def record_judge_result(score_data, judge_score):
    global endtime
    score_distribution = []
    for data in score_data.values():
        score_distribution.append(data["score"][0])
    
    fig, axs = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={'bottom': 0.3, 'top': 0.9})
    plt.subplots_adjust(wspace=0.3)
    bin_edges = np.linspace(0, 100, 101)
    sns.histplot(x=score_distribution, ax=axs[0], bins=bin_edges)
    axs[0].axvline(x=judge_score[0], color='red', linestyle='--', linewidth=1.5)
    axs[0].annotate(f'x={judge_score[0]}', xy=(judge_score[0], axs[0].get_ylim()[1]), xytext=(5, 5),
                    textcoords='offset points', color='red', fontsize=14,
                    arrowprops=dict(arrowstyle='->', color='red'))

    path = "./result_picture/score/"
    if not Path(path).exists():
        os.makedirs(path)
    fig.savefig(path + f"score_{args.cold_propotion}")
    plt.close(fig)


    cold_realtime_hist = []
    for data in score_data.values():
        if data["is_cold_flag"] == True:
            cold_realtime_hist.append(data["data"]["realtime_hist"])

    zipped_hist = zip(*cold_realtime_hist)
    cold_realtime_hist = [sum(group) for group in zipped_hist]

    realtime_bin_edges = np.linspace(0, endtime, 1001)
    realtime_bin_centers = (realtime_bin_edges[:-1] + realtime_bin_edges[1:]) / 2
    realtime_bin_centers = [round(num) for num in realtime_bin_centers]

    fig, axs = plt.subplots(1, 2, figsize=(18, 9), gridspec_kw={'bottom': 0.3, 'top': 0.9}, dpi=300)
    sns.histplot(x=realtime_bin_centers, weights=cold_realtime_hist, ax=axs[0], bins=100)
    axs[0].set_yscale('log')
    sns.histplot(x=realtime_bin_centers, weights=cold_realtime_hist, ax=axs[1], bins=100)
    fig.savefig(path + f"interval_{args.cold_propotion}")
    plt.close(fig)

# use flag to move a image to a target dir 
def classify_image(source_dir, name, target_dir, flag):
    if flag is False:
        return
    if not Path(target_dir).exists():
        os.makedirs(target_dir)
    
    all_data = os.listdir(source_dir)
    for data in all_data:
        if name in data and data.endswith(".png"):
            shutil.copy(source_dir + '/' + data, target_dir)

# the policy of test if a malloc is cold or not 
def calc_score(data, global_data):
    return [data["bathtub_obj_num"] / data["caller_obj_num"] * 100, data["caller_obj_num"]]

def prepare_score_data(df, endtime):
    lifetime_mask = df["lifetime"] > LIFE_TIME_THRESHOLD
    long_lifetime_obj_num = df[lifetime_mask]["data_addr"].nunique()
    df_bathtub_obj = df[lifetime_mask][["data_addr", "hit_relative_time"]].copy()
    #print(df_bathtub_obj)
    df_bathtub_obj["is_bathtub_time"] = np.where((df_bathtub_obj["hit_relative_time"] > 5) & (df_bathtub_obj["hit_relative_time"] <= 95), True, False)
    df_bathtub_obj =  df_bathtub_obj.groupby("data_addr", as_index=False).aggregate({"is_bathtub_time": ["any"]})
    df_bathtub_obj.columns = df_bathtub_obj.columns.map(''.join)
    df_bathtub_obj = df_bathtub_obj.rename(columns={"is_bathtub_timeany": "is_bathtub_obj"})
    df_bathtub_obj["is_bathtub_obj"] = ~df_bathtub_obj["is_bathtub_obj"]
    is_bathtub_mask = df_bathtub_obj["is_bathtub_obj"] == True
    # convert the data into a histogram
    bin_edges = np.linspace(0, 100, 1001)
    bin_edges[0] -= 1000
    bin_edges[-1] += 1000
    hit_hist, bins = np.histogram(np.array(df[lifetime_mask]["hit_relative_time"]), bins=bin_edges)
    bin_edges = np.linspace(0, endtime, 1001)
    bin_edges[0] -= 10000
    bin_edges[-1] += 10000
    lifetime_hist, bins = np.histogram(np.array(df["lifetime"]), bins=bin_edges)
    realtime_hist, bins = np.histogram(np.array(df["alloc_time"] + df["hit_absolute_time"]), bins=bin_edges)
    return_data = {
        "short_lifetime_obj_num" : int(df["caller_objects_num"].iloc[0] - long_lifetime_obj_num),
        "long_lifetime_obj_num" : int(long_lifetime_obj_num),
        "bathtub_obj_num" : len(df_bathtub_obj[is_bathtub_mask]),
        "caller_obj_num" : int(df["caller_objects_num"].iloc[0]),
        "hit_hist" : hit_hist.tolist(),
        "lifetime_hist" : lifetime_hist.tolist(),
        "realtime_hist" : realtime_hist.tolist()
    }

    return return_data

def process_score_data(score_data):
    global_data = {
        "total_short_lifetime_obj_num" : 0,
        "total_long_lifetime_obj_num" : 0,
        "total_bathtub_obj_num" : 0,
        "total_obj_num" : 0,
        "total_hit_hist" : [],
        "total_lifetime_hist" : [],
        "total_realtime_hist" : []
    }
    
    for data in score_data.values():
        global_data["total_short_lifetime_obj_num"] += data["data"]["short_lifetime_obj_num"]
        global_data["total_long_lifetime_obj_num"] += data["data"]["long_lifetime_obj_num"]
        global_data["total_bathtub_obj_num"] += data["data"]["bathtub_obj_num"]
        global_data["total_obj_num"] += data["data"]["caller_obj_num"]
        global_data["total_hit_hist"].append(data["data"]["hit_hist"])
        global_data["total_lifetime_hist"].append(data["data"]["lifetime_hist"])
        global_data["total_realtime_hist"].append(data["data"]["realtime_hist"])
    
    zipped_hist = zip(*global_data["total_hit_hist"])
    global_data["total_hit_hist"] = [sum(group) for group in zipped_hist]
    zipped_hist = zip(*global_data["total_lifetime_hist"])
    global_data["total_lifetime_hist"] = [sum(group) for group in zipped_hist]
    zipped_hist = zip(*global_data["total_realtime_hist"])
    global_data["total_realtime_hist"] = [sum(group) for group in zipped_hist]

    return global_data

def judge_malloc(score_data, process_score_data_func, record_score_global_data_func, calc_func):
    path = "./result_picture/score/"
    if not Path(path).exists():
        os.makedirs(path)
    with open(f"./result_picture/score/score_data.json", "w") as file:
        score_data_str_keys = {str(k): v for k, v in score_data.items()}
        json.dump(score_data_str_keys, file)
    global_data = process_score_data_func(score_data)
    record_score_global_data_func(global_data)
    # print("global_data", global_data)
    scores = []
    for data in score_data.values():
        data["score"] = calc_func(data["data"], global_data)
        scores.append(data["score"])

    scores.sort()
    index = int(len(scores) * ((100 - args.cold_propotion) / 100.0))
    judge_score = list(scores[index])

    # retain cold_propotion of the amount.
    # judge_score = list(np.percentile(scores, 100 - args.cold_propotion, axis=0,  method='lower'))
    # print("judge", judge_score)
    for data in score_data.values():
        if data["score"] >= judge_score:
            data["is_cold_flag"] = True
            classify_image(data["source_path"], data["name"], data["target_path"], True)
        else:
            data["is_cold_flag"] = False
            
        with open(data["source_path"] + "/" + data["name"] + "_score.json", "w") as file:
            json.dump({"score": data["score"]}, file)

    return judge_score

def event_moment_init():
    global event_moment
    with open("./event_moment.txt", "r") as f:
        while True:
            moment = f.readline()
            if len(moment) == 0:
                break
            event_moment.append(float(moment))

def main():
    global endtime, args
    with open("./result/endtime", "r") as f:
        endtime = float(f.readline())
    
    if args.already_have_score_data == True:
        with open("./result_picture/score/score_data.json", "r") as file:
            score_data = json.load(file)
        with open("./result_picture/score/unsampled_allocs.json", "r") as file:
            unsampled_allocs = json.load(file)
        judge_score = judge_malloc(score_data, process_score_data, record_score_global_data, calc_score)
        record_judge_result(score_data, judge_score)
        record_all_allocs(score_data, unsampled_allocs)
        return

    fileresult_names = {}
    fileresult_unsampled_names = {}
    fileresult_myaf = {}
    pids = {}
    score_data = {}
    unsampled_allocs = {}
    if args.use_import_calc_method:
        score_data2 = {}

    all_data = os.listdir("./result")
    #print(all_data)
    for data in all_data:
        if re.search(r'\d', data) is not None: 
            pid = int(''.join(re.findall(r'\d+', data)), 10)
            if "result_not_be_sampled" in data:
                fileresult_unsampled_names[pid] = "./result/" + data
            elif "myaf" in data:
                fileresult_myaf[pid] = "./result/" + data
                pids[pid] = True
            else:
                all_chunks = os.listdir("./result/" + data)
                fileresult_names[pid] = []
                for chunk in all_chunks:
                    fileresult_names[pid].append("./result/" + data + "/" + chunk)

    # initialize event moment
    event_moment_init()

    # for every pid have files myaf
    for pid in pids:
        # these dirs are used to sort result image
        unsampled_dir_path = "./result_picture/" + str(pid) + "unsampled"
        sampled_dir_path = "./result_picture/" + str(pid)
        coldmalloc_dir_path = "./result_picture/" + str(pid) + "cold"
        dir_paths = [unsampled_dir_path, sampled_dir_path, coldmalloc_dir_path]
        if args.use_import_calc_method:
            coldmalloc_dir_path2 = "./result_picture/" + str(pid) + "cold2"
            dir_paths.append(coldmalloc_dir_path2)
        for dir_path in dir_paths:
            if not Path(dir_path).exists():
                os.makedirs(dir_path)

        # open myaf for every alloc and free information            
        df_myaf = pd.read_csv(fileresult_myaf[pid], dtype=dtype)
        df_myaf = pd.DataFrame(df_myaf)        
        # I temporarily rename the column avoid to get it wrong
        df_myaf = df_myaf.rename(columns={"generation": "lifetime"})

        df_myaf["lifetime_objsize_product"] = df_myaf["lifetime"].clip(lower=0) * df_myaf["size"]
        df_myaf_total_size =  df_myaf.groupby("caller_addr", as_index=False).aggregate({
            "lifetime_objsize_product": ["sum"],
            "size": ["sum"]
        })
        df_myaf_total_size.columns = df_myaf_total_size.columns.map(''.join)
        df_myaf_total_size = df_myaf_total_size.rename(columns={
            "sizesum": "total_alloc_size"
        })

        # In this pid, if all the objects alloced from some malloc have no any event(cachemiss)
        # then we output some picture with the information for these mallocs and these mallocs'obj  
        if fileresult_unsampled_names.get(pid) is not None:
            
            df_not = pd.read_csv(fileresult_unsampled_names[pid], dtype=dtype)
            df_not = pd.DataFrame(df_not)

            print("\n")
            print(str(pid) + " not be sampled : ", len(df_not))
            record_size_with_no_event(pid, df_not)

            # for every malloc, we save the picture shows that the lifetime and size of all objs in this malloc
            index = 0
            for caller_addr in df_not["caller_addr"]:
                print("no event", index, hex(caller_addr))
                mask = df_myaf["caller_addr"] == caller_addr
                record_objs_with_no_event(df_myaf[mask], unsampled_dir_path + "/" + str(index) + "_" + str(hex(caller_addr)))
                
                mask = df_myaf_total_size["caller_addr"] == caller_addr
                unsampled_allocs[(pid, caller_addr)] = {
                    "alloc_size" : int(df_myaf_total_size[mask]["total_alloc_size"].iloc[0]),
                    "lifetime_objsize_product" : float(df_myaf_total_size[mask]["lifetime_objsize_productsum"].iloc[0])
                }
                index += 1
        
        # In this pid, if one of the objects alloced from the malloc have a event(cachemiss)
        # then we output some picture with the information for these mallocs and mallocs' obj  
        if (fileresult_names.get(pid) is not None) and (fileresult_myaf.get(pid) is not None):        
            ## i simply concat all the chunks as a templily way 
            if len(fileresult_names[pid]) == 1:
                df = pd.read_csv(fileresult_names[pid][0], dtype=dtype)
                df = pd.DataFrame(df)
            else:
                df_chunks = []
                for chunk in fileresult_names[pid]:
                    df = pd.read_csv(chunk, dtype=dtype)
                    df = pd.DataFrame(df)
                    df_chunks.append(df)
                df = pd.concat(df_chunks, axis=0)

            # drop error
            # df.drop_duplicates(subset=["hit_time"], keep=False, inplace=True)
            
            # I temporarily rename the column avoid to get it wrong
            df = df.rename(columns={"interval_time": "lifetime"})
            # add another column
            df["hit_absolute_time"] = df["hit_time"] - df["alloc_time"]

            # group the data by caller addr and count some information 
            indicate = df.groupby("caller_addr_str", as_index=False).aggregate({
                # just use a arbitrary column to count how many rows we group 
                "size": ["count"],
                # number of how many objs
                "caller_objects_num": ["mean"],
                # total size alloced by every malloc
                "caller_total_alloc_size": ["mean"],
                # max obj lifetime
                "lifetime": ["max"]
            })
            indicate.columns = indicate.columns.map(''.join)
            indicate = indicate.rename(columns={
                "sizecount": "count_of_hits",
                "caller_objects_nummean": "count_of_objs",
                "caller_total_alloc_sizemean" : "total_alloc_size"
            })

            # record some information
            # allocs_info.classify["sampled"].count = len(indicate)
            # allocs_info.classify["sampled"].total_hits = len(df)
            # print(str(pid) + " sample num : ", allocs_info.classify["sampled"].count)

            # make pictures with every malloc address 
            for i in range(len(indicate)):
                if i > CONTINUE_NUM:
                    continue
                per_caller_info = indicate.iloc[i:i + 1, :]
                print("\nmalloc " + str(i) + "\n", per_caller_info)

                caller_addr = int(per_caller_info["caller_addr_str"].to_string(index=False), 16)
                mask = df["lifetime"] > LIFE_TIME_THRESHOLD
                mask2 = df["caller_addr_str"].isin(per_caller_info["caller_addr_str"])
                mask3 = df_myaf["caller_addr"].isin([caller_addr])
                mask4 = df_myaf[mask3]["lifetime"] >= LIFE_TIME_THRESHOLD

                # get savepath
                picture_name = re.sub(r'\s+', '_', per_caller_info["caller_addr_str"].to_string())
                savepath = sampled_dir_path + "/" + picture_name

                # get interval data or processing data
                interval_data = {}
                if args.already_have_interval_data:
                    all_data = os.listdir(sampled_dir_path)
                    for data in all_data:
                        if "interval_data" in data and picture_name in data and data.endswith(".json"):
                            with open(sampled_dir_path + '/' + data, 'r') as file:
                                interval_data = json.load(file)
                else:
                    if args.just_show_obj_similarity:
                        if (float(per_caller_info["lifetimemax"].to_string(index=False)) < LIFE_TIME_THRESHOLD) or \
                            (float(per_caller_info["count_of_objs"].to_string(index=False)) < OBJ_SIMILARITY_SELECTNUM):
                            continue
                    statistics(df[mask2], df_myaf[mask3], filter_flag = False, savepath=savepath, interval_data=interval_data)
                
                record_malloc(df[mask2], df_myaf[mask3], df[mask & mask2], per_caller_info, 
                                long_lifetime_propotion=0, is_cold=None, cold_score=0, savepath=savepath)
                
                mask = df_myaf_total_size["caller_addr"] == caller_addr

                score_data[(pid, caller_addr)] = { 
                    "data" : prepare_score_data(df[mask2], endtime),
                    "source_path" : sampled_dir_path,
                    "name" : picture_name,
                    "target_path" : coldmalloc_dir_path,
                    "score" : 0,
                    "is_cold_flag" : False,
                    "alloc_size" : int(df_myaf_total_size[mask]["total_alloc_size"].iloc[0]),
                    "lifetime_objsize_product" : float(df_myaf_total_size[mask]["lifetime_objsize_productsum"].iloc[0])
                }
                if args.use_import_calc_method:
                    score_data2[(pid, caller_addr)] = {
                        "data" : prepare_score_data2(df[mask2], endtime),
                        "source_path" : sampled_dir_path,
                        "name" : picture_name,
                        "target_path" : coldmalloc_dir_path2,
                        "score" : 0,
                        "is_cold_flag" : False,
                        "alloc_size" : int(df_myaf_total_size[mask]["total_alloc_size"].iloc[0]),
                        "lifetime_objsize_product" : float(df_myaf_total_size[mask]["lifetime_objsize_productsum"].iloc[0])
                    }
                
        # # remove the empty dir
        # for dir_path in dir_paths:
        #     try:
        #         os.rmdir(dir_path)
        #     except:
        #         None

    judge_score = judge_malloc(score_data, process_score_data, record_score_global_data, calc_score)
    record_judge_result(score_data, judge_score)
    if args.use_import_calc_method:
        judge_score = judge_malloc(score_data2, process_score_data2, record_score_global_data2, calc_score2)
        record_judge_result(score_data, judge_score)

    record_all_allocs(score_data, unsampled_allocs)
    with open( "./result_picture/score/unsampled_allocs.json", 'w') as file:
        unsampled_allocs_str_keys = {str(k): v for k, v in unsampled_allocs.items()}
        json.dump(unsampled_allocs_str_keys, file)
    

if __name__ == "__main__":
    # Turn off the automatic using scientific notation at axis lable
    plt.rcParams['axes.formatter.useoffset'] = False

    parser = argparse.ArgumentParser(
        usage="python3 ./data_show\n\
               --already_have_interval_data [False]\n\
               --already_have_score_data [False]\n\
               --cold_propotion [10]\n\
               --debug [False]\n\
               --just_show_obj_similarity [False]\n\
               --use_import_calc_method [False]\n"
    )
    parser.add_argument('--already_have_interval_data', type=bool, default=False, help="[True / False]")
    parser.add_argument('--already_have_score_data', type=bool, default=False, help="[True / False]")
    parser.add_argument('--cold_propotion', type=int, default=10, help="[0 ~ 100]")
    parser.add_argument('--debug', type=bool, default=False, help="[True / False]")
    parser.add_argument('--just_show_obj_similarity', type=bool, default=False, help="[True / False]")
    parser.add_argument('--use_import_calc_method', type=bool, default=False, help="[True / False]")
    args = parser.parse_args()
    
    if args.use_import_calc_method:
        from calc_score import calc_score as calc_score2
        from calc_score import prepare_score_data as prepare_score_data2
        from calc_score import process_score_data as process_score_data2
        from calc_score import record_score_global_data as record_score_global_data2

    main()
