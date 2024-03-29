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
    "generation" : float
}

thread_flag = True
picture_size = (10, 8)
dpi = 100
endtime = -1

def DTW(df_per_malloc, save_path, malloc_info):
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

        #obj_performance_hist /= standard[-1]
        #sampled_standard = np.random.choice(standard, size=len(obj_performance), replace=True)
        #normalized_standard = standard / standard[-1]
        #sampled_normalized_standard = np.random.choice(standard, size=len(obj_performance_hist), replace=True)
        
        #print(standard_hist)
        #print(standard_hist.shape)
        #print(obj_performance_hist)
        #print(obj_performance_hist.shape)

        #distance1, path1 = fastdtw(standard_hist, obj_performance_hist, dist=2)
        #distance2, path2 = fastdtw(standard_hist_resize, obj_performance_hist, dist=2)
        distance1 = wasserstein_distance(x_axis, x_axis, standard_hist, obj_performance_hist)
        distance2 = wasserstein_distance(x_axis, x_axis, standard_hist_resize, obj_performance_hist)

        normalized_distance1 = distance1 / (len(obj_performance))
        normalized_distance2 = distance2 / (len(obj_performance))

        # save the picture of objects performance diagram
        if len(obj_performance) > 0:
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

            fig.savefig(save_path + "_dtw" + str(index))
            plt.close(fig)
        
        dtws.append(distance1)
        normalized_dtws.append(normalized_distance1)
        sampled_dtws.append(distance2)
        sampled_normalized_dtws.append(normalized_distance2)
        hit_count.append(len(obj_performance))
        

    fig, axs = plt.subplots(2, 2, figsize=(14, 14), gridspec_kw={'bottom': 0.2, 'top': 0.9})
    sns.histplot(x=hit_count, y=dtws, ax=axs[0][0], cbar=True)
    sns.histplot(x=hit_count, y=normalized_dtws, ax=axs[0][1], cbar=True)
    sns.histplot(x=hit_count, y=sampled_dtws, ax=axs[1][0], cbar=True)
    #print(sampled_normalized_dtws, len(sampled_normalized_dtws))
    #print(hit_count, len(hit_count))
    sns.histplot(x=hit_count, y=sampled_normalized_dtws, ax=axs[1][1], cbar=True)

    fig.savefig(save_path + "_all_dtws")
    plt.close(fig)

    #print("DTW :", distance)
    #print("path :", path)
    print("\n\n\n")


def hit_interval(df_per_malloc, save_path, malloc_info, df_myaf):
    global endtime
    print(df_per_malloc)
    print("df myaf")
    print(df_myaf)

    malloc_objs_df = df_per_malloc.groupby("data_addr", as_index=False).size()
    malloc_objs = malloc_objs_df["data_addr"].to_dict()

    # data and information
    intervals = []
    intervals_128kfilter = []
    obj_sizes = []
    obj_sizes_128kfilter = []

    # for every objects
    for index in malloc_objs:
        obj = malloc_objs[index]
        print(index, obj)
        #print(df_per_malloc)

        mask = df_per_malloc["data_addr"] == obj
        obj_performance = df_per_malloc[mask]["hit_absolute_time"].to_numpy().tolist()
        #obj_alloc_time = float(df_per_malloc[mask]["alloc_time"].iloc[0: 1].to_string(index = False))
        #print(df_per_malloc[mask])
        obj_life_time = float(df_per_malloc[mask]["interval_time"].iloc[0: 1].to_string(index = False))
        obj_size = int(df_per_malloc[mask]["size"].iloc[0: 1].to_string(index = False), 10)
        obj_performance.append(obj_life_time)
        print("objper", obj_performance)

        # insert size
        obj_sizes.append(obj_size)
        if obj_size <= 128 * 1024:
            obj_sizes_128kfilter.append(obj_size)

        last_time = -100
        obj_performance.sort()
        for hit_time in obj_performance:
            #print(obj_alloc_time, obj_free_time)
            if last_time == -100:
                interval = hit_time
            else:
                interval = hit_time - last_time
            
            intervals.append(interval)
            if obj_size <= 128 * 1024:
                intervals_128kfilter.append(interval)
            last_time = hit_time

    # add objects data which not been sampled
    mask = ~df_myaf["data_addr"].isin(malloc_objs_df["data_addr"])
    mask_128ksize = df_myaf["size"] <= 128 * 1024
    for index, obj_info in df_myaf[mask].iterrows():
        intervals.append(float(obj_info["generation"]))
        obj_sizes.append(float(obj_info["size"]))
    for index, obj_info in df_myaf[mask & mask_128ksize].iterrows():
        intervals_128kfilter.append(float(obj_info["generation"]))
        obj_sizes_128kfilter.append(float(obj_info["size"]))

    #print("intervals:", intervals)
    #print("\n")
    #print(intervals_128kfilter)
    #print("\n\n\n")
            

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
    fig.savefig(save_path + "_interval")
    plt.close(fig)



def show_diagram():
    global endtime

    fileresult_names = {}
    fileresult_notsampled_names = {}
    fileresult_myaf = {}
    pids = {}
    all_data = os.listdir("./result")
    #print(all_data)
    for data in all_data:
        if re.search(r'\d', data) is not None: 
            pid = int(''.join(re.findall(r'\d+', data)), 10)
            pids[pid] = True
            if "result_not_be_sampled" in data:
                fileresult_notsampled_names[pid] = "./result/" + data
            elif "myaf" in data:
                fileresult_myaf[pid] = "./result/" + data
            else:
                fileresult_names[pid] = "./result/" + data
    with open("./result/endtime", "r") as f:
        endtime = float(f.readline())

    
    for pid in pids:
        flag = False
        number_of_unsampled_malloc = 0
        if fileresult_notsampled_names.get(pid) is not None:
            df_not = pd.read_csv(fileresult_notsampled_names[pid], dtype=dtype)
            df_not = pd.DataFrame(df_not)

            df_not = df_not.sort_values("caller_total_alloc_size", ascending=False)
            indicate = df_not.head(50)
            
            print("\n")
            number_of_unsampled_malloc = len(df_not)
            print(str(pid) + " not be sampled : ", number_of_unsampled_malloc)

            fig = plt.figure(figsize=picture_size, dpi=dpi)
            plt.title('sample not hit pid=' + str(pid))
            sns.barplot(data=indicate, x="caller_total_alloc_size", y="caller_addr_str")
            plt.savefig("./result_picture/" + str(pid) + "_sample_not_hit" + ".png")

        if (fileresult_names.get(pid) is not None) and (fileresult_myaf.get(pid) is not None):       
            # open files
            df = pd.read_csv(fileresult_names[pid], dtype=dtype)
            df_myaf = pd.read_csv(fileresult_myaf[pid], dtype=dtype)
            df = pd.DataFrame(df)
            df_myaf = pd.DataFrame(df_myaf)
            flag = True

            # drop error
            df.drop_duplicates(subset=["hit_time"], keep=False, inplace=True)

            # add another column
            df["hit_absolute_time"] = df["hit_time"] - df["alloc_time"]
            
            # discard the too small interval time between malloc and free 
            mask = df["interval_time"] > 3

            # group the data by caller addr and count some information 
            indicate = df.groupby("caller_addr_str", as_index=False).aggregate({
                "size": ["count"], 
                "caller_objects_num": ["mean"], 
                "caller_total_alloc_size": ["mean"]
            })
            indicate.columns = indicate.columns.map(''.join)
            
            # record some information
            number_of_sampled_malloc = len(indicate)
            all_hits_count = len(df)
            print(str(pid) + " sample num : ", number_of_sampled_malloc)

            # put per caller picture into this dir
            dir_path = "./result_picture/" + str(pid)
            if not Path(dir_path).exists():
                os.makedirs(dir_path)
            
            # make pictures with every malloc address 
            for i in range(number_of_sampled_malloc):
                per_caller_info = indicate.iloc[i:i + 1, :]
                print(per_caller_info)
                
                mask2 = df["caller_addr_str"].isin(per_caller_info["caller_addr_str"])
                mask3 = df_myaf["caller_addr"].isin([int(per_caller_info["caller_addr_str"].to_string(index=False), 16)])
                
                ###
                fig, axs = plt.subplots(1, 3, figsize=(14, 5), gridspec_kw={'bottom': 0.3, 'top': 0.9}) # bottom and top is percentage 
                plt.subplots_adjust(wspace=0.3)
                # absolute time
                df_temp = df[mask2]
                sns.histplot(x=df_temp["hit_absolute_time"], ax=axs[0], bins=100)
                axs[0].set_title('Sampling Hits Count for Malloc Objects')
                axs[0].set_xlabel('Timing of Sampling Hits Across Generations (seconds)')
                axs[0].set_ylabel('Number of Sampling Hits')

                # life time
                dfmyaf_temp = df_myaf[mask3]
                sns.histplot(x=dfmyaf_temp["generation"], ax=axs[2], bins=100)
                axs[2].set_title('Generation Lengths of Malloc Objects')
                axs[2].set_xlabel('Generation Lengths (seconds)')
                axs[2].set_ylabel('Number of Malloc Objects')

                # relatine time
                df_temp = df[mask & mask2]
                rel_bins = np.linspace(-3, 103, 101)
                sns.histplot(x=df_temp["hit_relative_time"], ax=axs[1], bins=rel_bins)
                axs[1].set_title('Sampling Hits Count for Malloc Objects')
                axs[1].set_xlabel('Timing of Sampling Hits Across Generations (%)')
                axs[1].set_ylabel('Number of Sampling Hits')
                #axs[1].set_xlim(-3, 103)
                
                # add some information to picture
                malloc_info = "malloc information" \
                    + "\n" + "|  malloc address : " + per_caller_info["caller_addr_str"].to_string(index=False) \
                    + "\n" + "|  Sampling Hits Count of malloc Objects : " + per_caller_info["sizecount"].to_string(index=False) \
                    + "\n" + "|  Size of All Allocated Spaces by this malloc: " + per_caller_info["caller_total_alloc_sizemean"].to_string(index=False) \
                    + "\n" + "|  Number of Objects Allocated by this malloc : " + per_caller_info["caller_objects_nummean"].to_string(index=False)
                other_info = "Information about this experiment" \
                    + "\n" + "|  All Sampling Hits Count of malloc Objects for PID " + str(pid) + " : " + str(all_hits_count) \
                    + "\n" + "|  Count of Unsampled mallocs for PID " + str(pid) + " : " + str(number_of_unsampled_malloc)\
                    + "\n" + "|  Count of sampled mallocs for PID " + str(pid) + " : " + str(number_of_sampled_malloc)\

                fig.text(0.2, 0.2,  malloc_info, ha='left', va='top', fontsize=10, color='blue')
                fig.text(0.6, 0.2, other_info, ha='left', va='top', fontsize=10, color='blue')

                ###
                # save picture
                picture_name = re.sub(r'\s+', '_', per_caller_info["caller_addr_str"].to_string())
                plt.savefig(dir_path + "/" + picture_name)
                plt.close(fig)
                

                # calculate DTW
                DTW(df[mask2], dir_path + "/" + picture_name, per_caller_info) 

                # calculate hit interval
                hit_interval(df[mask2], dir_path + "/" + picture_name, per_caller_info, df_myaf[mask3])
            

        """        
            # choose witch to display
            #indicate = indicate.sort_values("sizesize", ascending=False)
            #indicate = indicate.sort_values("sizecount", ascending=False)
            indicate = indicate.head(50)
            #indicate = indicate.iloc[1:51, :]
            print(indicate)

            # mask 
            mask2 = df["caller_addr_str"].isin(indicate["caller_addr_str"])

            # relative time df and absolute time df
            df_rel = df[mask & mask2]
            df_abs = df[mask2]

            # hit relative time histplot diagram
            plt.figure(figsize=picture_size, dpi=dpi)
            plt.title('hit relative time(%) (discard interval small than 1s) pid=' + str(pid))
            sns.histplot(x=df_rel["hit_relative_time"], y=df_rel["caller_addr_str"], legend=True, cbar=True, bins=100) 
            plt.savefig('./result_picture/' + str(pid) + '_relative_time' + ".png")

            # hit absolute time histplot diagram
            plt.figure(figsize=picture_size, dpi=dpi)
            plt.title('hit absolute time(seconds) pid=' + str(pid))
            sns.histplot(x=df_abs["hit_absolute_time"], y=df_abs["caller_addr_str"], legend=True, cbar=True, bins=100)
            plt.savefig('./result_picture/' + str(pid) + '_absolute_time' + ".png")

            # free absolute time histplot diagram
            plt.figure(figsize=picture_size, dpi=dpi)
            plt.title('free absolute time(seconds) pid=' + str(pid))
            sns.histplot(x=df_abs["interval_time"], y=df_abs["caller_addr_str"], legend=True, cbar=True, bins=100)
            plt.savefig('./result_picture/' + str(pid) + '_free_absolute_time' + ".png")

            # information bar diagram
            g = sns.PairGrid(
                data=indicate,
                x_vars=["sizecount", "caller_total_alloc_sizemean"],
                y_vars=["caller_addr_str"],
                height=picture_size[0] / 1.5,
                aspect=1
            )
            g.map(sns.barplot, color="#00E3E3")
            g.set(title="info")
            plt.savefig("./result_picture/" + str(pid) + "_info" + ".png", bbox_inches='tight')

        plt.ion()
        plt.show()
        if flag:
            query(df_rel, df_abs, indicate)
        else:
            input("press enter to skip")
        plt.close("all")

        """
if __name__ == "__main__":
    show_diagram()
