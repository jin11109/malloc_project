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
import threading
import bisect
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean
from scipy.stats import wasserstein_distance

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
    "alloc_type" : str
}

thread_flag = True
picture_size = (10, 8)
dpi = 100
endtime = -1
debug = True
lifetime_threshold = 100
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
    standard_hist_avg = standard_hist.copy() / float(malloc_info["caller_objects_nummean"].to_string(index = False))

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
def record_objs(obj_sizes, statistics_hits, statistics_lifetime, no_event_objs, filter_flag, savepath, filter_save_path):
    global lifetime_threshold

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
        if i < lifetime_threshold:
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
                + "\n" + f"|  Number of objects with lifetime < {lifetime_threshold} : " +  str(number_of_short_lifetime)\
                + "\n" + f"|  Number of Objects with lifetime >= {lifetime_threshold} : " + str(number_of_total_objs - number_of_short_lifetime) \
                + "\n" + "|  Number of objects with times of hit is 0 : " + str(number_of_zreo_hit) \
                + "\n" + "|  Number of objects with times of hit is between 1~10 : " + str(number_of_hit_between_1_10) \
                + "\n" + "|  Number of objects with times of hit is > 10 : " + str(number_of_total_objs - number_of_hit_between_1_10 - number_of_zreo_hit) \
                + "\n" + f"|  Porpotion of long lifetime objects (lifetime >= {lifetime_threshold}): " + str((1 - number_of_short_lifetime / number_of_total_objs) * 100) + "%"
    fig.text(0.2, 0.2,  obj_info, ha='left', va='top', fontsize=10, color='blue')
    fig.savefig(savepath + "_all_obj")
    if filter_flag:
        fig.savefig(filter_save_path + "_all_obj")
    plt.close(fig)

    # for objs don't have any event
    if len(no_event_objs) == 0:
        return
    
    no_event_obj_lifetime = no_event_objs["generation"]
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
    number_of_no_event_objs_shortlifetime = len(no_event_objs[no_event_objs["generation"] < lifetime_threshold])
    number_of_no_event_objs_smallsize = len(no_event_objs[no_event_objs["size"] < 64])
    obj_info = "malloc objects information" \
                + "\n" + "|  Number of tatal no event objects : " + str(number_of_total_no_event_objs) \
                + "\n" + f"|  Number of no event objects with lifetime < {lifetime_threshold} : " +  str(number_of_no_event_objs_shortlifetime)\
                + "\n" + f"|  Number of no event Objects with lifetime >= {lifetime_threshold} : " + str(number_of_total_no_event_objs - number_of_no_event_objs_shortlifetime) \
                + "\n" + "|  Number of no event objects with size < 64 : " + str(number_of_no_event_objs_smallsize) \
                + "\n" + "|  Number of no event objects with size >= 64 : " + str(number_of_total_no_event_objs - number_of_no_event_objs_smallsize) \
                + "\n" + "|  " + str()
    fig.text(0.2, 0.2,  obj_info, ha='left', va='top', fontsize=10, color='blue')
    fig.savefig(savepath + "_noevent_obj")
    if filter_flag:
        fig.savefig(filter_save_path + "_noevent_obj")
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
def record_internal(intervals, intervals_128kfilter, obj_sizes, obj_sizes_128kfilter, filter_flag, savepath, filter_save_path):
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
    if filter_flag:
        fig.savefig(filter_save_path + "_all_interval")
    plt.close(fig)

# save the picture shows that the real hit itme of all objs alloced from this malloc,
# and if there is a time of important event we already recorded in ./event_moment.txt,
# highlight these time to the realtime picture
def record_malloc_with_realtime(df, filter_flag, savepath, filter_save_path):
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
    axs[0].set_xlabel('Real Timing of Sampling Hits Across Generations (seconds)')
    axs[0].set_ylabel('Number of Sampling Hits')
    for moment in event_moment:
        axs[0].axvline(x=moment, color='green', linestyle='--')

    plt.savefig(savepath + '_realtime')
    if filter_flag:
        plt.savefig(filter_save_path + '_realtime')
    plt.close(fig)

# save the picture shows that absolute/relative hit time and lifetime of all objs alloed from this malloc
def record_malloc(pid, df_abs, df_lifetime, df_rel, per_caller_info, all_hits_count, number_of_unsampled_malloc, number_of_sampled_malloc, long_lifetime_propotion, filter_flag, savepath, filter_save_path):
    global lifetime_threshold, alloc_type_mapping
    
    fig, axs = plt.subplots(1, 3, figsize=(14, 5), gridspec_kw={'bottom': 0.3, 'top': 0.9}) # bottom and top is percentage 
    plt.subplots_adjust(wspace=0.3)
    # absolute time
    sns.histplot(x=df_abs["hit_absolute_time"], ax=axs[0], bins=100)
    axs[0].set_title('Sampling Hits Count for Malloc Objects')
    axs[0].set_xlabel('Timing of Sampling Hits Across Generations (seconds)')
    axs[0].set_ylabel('Number of Sampling Hits')

    # life time
    sns.histplot(x=df_lifetime["generation"], ax=axs[2], bins=100)
    axs[2].set_title('Generation Lengths of Malloc Objects')
    axs[2].set_xlabel('Generation Lengths (seconds)')
    axs[2].set_ylabel('Number of Malloc Objects')

    # relatine time
    rel_bins = np.linspace(-3, 103, 101)
    sns.histplot(x=df_rel["hit_relative_time"], ax=axs[1], bins=rel_bins)
    axs[1].set_title('Sampling Hits Count for Malloc Objects')
    axs[1].set_xlabel('Timing of Sampling Hits Across Generations (%)')
    axs[1].set_ylabel('Number of Sampling Hits')
    #axs[1].set_xlim(-3, 103)
    
    # add some information to picture
    alloc_type = alloc_type_mapping[df_lifetime["alloc_type"].iloc[0]]
    malloc_info = "alloc information (type "+  alloc_type + ")" \
        + "\n" + "|  malloc address : " + per_caller_info["caller_addr_str"].to_string(index=False) \
        + "\n" + "|  Sampling Hits Count of malloc Objects : " + per_caller_info["sizecount"].to_string(index=False) \
        + "\n" + "|  Size of All Allocated Spaces by this malloc: " + per_caller_info["caller_total_alloc_sizemean"].to_string(index=False) \
        + "\n" + "|  Number of Objects Allocated by this malloc : " + per_caller_info["caller_objects_nummean"].to_string(index=False) \
        + "\n" + f"|  Propotion of Long Lifetime Objects (lifetime >= {lifetime_threshold}) : " + str(long_lifetime_propotion * 100) + "%"
    other_info = "Information about this experiment" \
        + "\n" + "|  All Sampling Hits Count of malloc Objects for PID " + str(pid) + " : " + str(all_hits_count) \
        + "\n" + "|  Count of Unsampled mallocs for PID " + str(pid) + " : " + str(number_of_unsampled_malloc)\
        + "\n" + "|  Count of sampled mallocs for PID " + str(pid) + " : " + str(number_of_sampled_malloc)\

    fig.text(0.2, 0.2,  malloc_info, ha='left', va='top', fontsize=10, color='blue')
    fig.text(0.6, 0.2, other_info, ha='left', va='top', fontsize=10, color='blue')

    plt.savefig(savepath)
    if filter_flag:
        plt.savefig(filter_save_path)
    plt.close(fig)

    record_malloc_with_realtime(df_abs, filter_flag, savepath, filter_save_path)

# save the picture shows that the lifetime and size of each objs alloced from this malloc
def record_objs_with_no_event(df_myaf, savepath):
    global lifetime_threshold

    number_of_total_objs = len(df_myaf)
    number_of_small_size = len(df_myaf[df_myaf["size"] <= 64])
    number_of_short_lifetime = len(df_myaf[df_myaf["generation"] < lifetime_threshold])

    # print(number_of_short_lifetime, number_of_small_size, number_of_total_objs)

    fig, axs = plt.subplots(1, 2, figsize=(14, 7), gridspec_kw={'bottom': 0.3, 'top': 0.9})
    sns.histplot(x=df_myaf["generation"], ax=axs[0], bins=100)
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
                + "\n" + f"|  Number of objects with lifetime < {lifetime_threshold} : " +  str(number_of_short_lifetime)\
                + "\n" + f"|  Number of Objects with lifetime >= {lifetime_threshold} : " + str(number_of_total_objs - number_of_short_lifetime) \
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

# statistics interval hit time and some information, then call other funcs to save pictures
def statistics(df_per_malloc, df_myaf, filter_flag, savepath, filter_save_path):
    global endtime, lifetime_threshold
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
    statistics_lifetime = []

    dir_flag = True
    if not Path(savepath + "_obj").exists():
        os.makedirs(savepath + "_obj")
    # for every objects calculate the interval hit time
    for index in malloc_objs:
        # record the object hit interval
        obj_interval = []
        # get data
        obj = malloc_objs[index]
        print("    ", index, obj)
        #print(df_per_malloc)

        mask = df_per_malloc["data_addr"] == obj
        obj_performance = df_per_malloc[mask]["hit_absolute_time"].to_numpy().tolist()
        
        obj_life_time = float(df_per_malloc[mask]["interval_time"].iloc[0: 1].to_string(index = False))
        obj_size = int(df_per_malloc[mask]["size"].iloc[0: 1].to_string(index = False), 10)
        obj_performance_without_lifetime = obj_performance
        obj_performance.append(obj_life_time)
        obj_addr = hex(int(df_per_malloc[mask]["data_addr"].iloc[0: 1].to_string(index = False), 10))
        obj_alloctime = float(df_per_malloc[mask]["alloc_time"].iloc[0: 1].to_string(index = False))
        obj_freetime = float(df_per_malloc[mask]["free_time"].iloc[0: 1].to_string(index = False))
        
        # insert size
        obj_sizes.append(obj_size)
        if obj_size <= 128 * 1024:
            obj_sizes_128kfilter.append(obj_size)

        is_first = True
        last_time = -100000
        obj_performance.sort()
        for hit_time in obj_performance:
            #print(obj_alloc_time, obj_free_time)
            if is_first:
                interval = hit_time
                is_first = False
            else:
                interval = hit_time - last_time
            
            # record ineterval data
            obj_interval.append(interval)
            intervals.append(interval)
            if obj_size <= 128 * 1024:
                intervals_128kfilter.append(interval)
            
            last_time = hit_time

        # record other information
        if len(obj_performance) > 100 or (filter_flag and len(malloc_objs) < 1000):
            record_obj(obj_life_time, obj_size, obj_interval, obj_performance_without_lifetime, obj_alloctime, obj_freetime, savepath + "_obj/", obj_addr, index)
            dir_flag = False

        statistics_hits.append(len(obj_performance_without_lifetime))

    if dir_flag:
        os.rmdir(savepath + "_obj")

    # statistics some information
    
    # mask for objs which do not have any event
    mask = ~df_myaf["data_addr"].isin(malloc_objs_df["data_addr"])
    # mask for objs' size bigger then 128k 
    mask_128ksize = df_myaf["size"] <= 128 * 1024

    intervals += df_myaf[mask]["generation"].to_numpy().tolist()
    intervals_128kfilter += df_myaf[mask & mask_128ksize]["generation"].to_numpy().tolist()
    obj_sizes = df_myaf["size"].to_numpy().tolist()
    obj_sizes_128kfilter = df_myaf[mask_128ksize]["size"].to_numpy().tolist()
    statistics_hits += [0] * len(df_myaf[mask])
    statistics_lifetime = df_myaf["generation"].to_numpy().tolist()
    # objs have no event
    no_event_objs = df_myaf[mask]
    
    record_internal(intervals, intervals_128kfilter, obj_sizes, obj_sizes_128kfilter, filter_flag, savepath, filter_save_path)
    record_objs(obj_sizes, statistics_hits, statistics_lifetime, no_event_objs, filter_flag, savepath, filter_save_path)
    
def event_moment_init():
    global event_momentwith 
    with open("./event_moment.txt", "r") as f:
        while True:
            moment = f.readline()
            if len(moment) == 0:
                break
            event_moment.append(float(moment))

def main():
    global endtime, lifetime_threshold

    fileresult_names = {}
    fileresult_notsampled_names = {}
    fileresult_myaf = {}
    pids = {}
    all_data = os.listdir("./result")
    #print(all_data)
    for data in all_data:
        if re.search(r'\d', data) is not None: 
            pid = int(''.join(re.findall(r'\d+', data)), 10)
            if "result_not_be_sampled" in data:
                fileresult_notsampled_names[pid] = "./result/" + data
            elif "myaf" in data:
                fileresult_myaf[pid] = "./result/" + data
                pids[pid] = True
            else:
                all_chunks = os.listdir("./result/" + data)
                fileresult_names[pid] = []
                for chunk in all_chunks:
                    fileresult_names[pid].append("./result/" + data + "/" + chunk)
    with open("./result/endtime", "r") as f:
        endtime = float(f.readline())

    # initialize event moment
    event_moment_init()

    # for every pid have files myaf
    for pid in pids:
        # open myaf for every alloc and free information            
        df_myaf = pd.read_csv(fileresult_myaf[pid], dtype=dtype)
        df_myaf = pd.DataFrame(df_myaf)        

        number_of_unsampled_malloc = 0
        
        # In this pid, if all the objects alloced from some malloc have no any event(cachemiss)
        # then we output some picture with the information for these mallocs and these mallocs'obj  
        if fileresult_notsampled_names.get(pid) is not None:
            # put result picture into this dir
            dir_path = "./result_picture/" + str(pid) + "noevent"
            if not Path(dir_path).exists():
                os.makedirs(dir_path)
            
            df_not = pd.read_csv(fileresult_notsampled_names[pid], dtype=dtype)
            df_not = pd.DataFrame(df_not)

            print("\n")
            number_of_unsampled_malloc = len(df_not.copy())
            print(str(pid) + " not be sampled : ", number_of_unsampled_malloc)
            record_size_with_no_event(pid, df_not)

            # for every malloc, we save the picture shows that the lifetime and size of all objs in this malloc
            index = 0
            for caller_addr in df_not["caller_addr"]:
                print("no event", index, hex(caller_addr))
                mask = df_myaf["caller_addr"] == caller_addr
                record_objs_with_no_event(df_myaf[mask], dir_path + "/" + str(index) + "_" + str(hex(caller_addr)))
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
                "interval_time": ["max"]
            })
            indicate.columns = indicate.columns.map(''.join)
            
            # record some information
            number_of_sampled_malloc = len(indicate)
            all_hits_count = len(df)
            print(str(pid) + " sample num : ", number_of_sampled_malloc)

            # put result picture into this dir
            dir_path = "./result_picture/" + str(pid)
            if not Path(dir_path).exists():
                os.makedirs(dir_path)
            filter_dir_path = "./result_picture/" + str(pid) + "filter"
            if not Path(filter_dir_path).exists():
                os.makedirs(filter_dir_path)

            # make pictures with every malloc address 
            for i in range(number_of_sampled_malloc):
                per_caller_info = indicate.iloc[i:i + 1, :]
                print("\nmalloc " + str(i) + "\n", per_caller_info)
    
                mask = df["interval_time"] > lifetime_threshold
                mask2 = df["caller_addr_str"].isin(per_caller_info["caller_addr_str"])
                mask3 = df_myaf["caller_addr"].isin([int(per_caller_info["caller_addr_str"].to_string(index=False), 16)])
                mask4 = df_myaf[mask3]["generation"] >= lifetime_threshold
                
                # for filter 
                # only consider the malloc whitch number of objs is more than 5
                condition1 = float(per_caller_info["caller_objects_nummean"].to_string(index=False)) > 5
                # only consider the malloc whitch max lifetime of objs in this malloc is >= 100 second  
                condition2 = float(per_caller_info["interval_timemax"].to_string(index=False)) >= lifetime_threshold
                # only consider the malloc whitch propotion of long lifetime objs bigger than 50% 
                long_lifetime_propotion = len(df_myaf[mask3 & mask4]) / float(per_caller_info["caller_objects_nummean"].to_string(index=False))
                condition3 = long_lifetime_propotion > 0.5
                filter_flag = condition1 and condition2 and condition3

                # get savepath
                picture_name = re.sub(r'\s+', '_', per_caller_info["caller_addr_str"].to_string())
                savepath = dir_path + "/" + picture_name
                filter_savepath = filter_dir_path + "/" + picture_name
                
                record_malloc(pid, df[mask2], df_myaf[mask3], df[mask & mask2], per_caller_info, all_hits_count, number_of_unsampled_malloc, 
                              number_of_sampled_malloc, long_lifetime_propotion, filter_flag, savepath, filter_savepath)

                statistics(df[mask2], df_myaf[mask3], filter_flag, savepath, filter_savepath)  
                
                # calculate DTW
                #DTW(df[mask2], dir_path + "/" + picture_name, per_caller_info) 

if __name__ == "__main__":
    main()
