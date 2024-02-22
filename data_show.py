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

thread_flag = True
picture_size = (10, 8)
dpi = 100

def query(df_rel, df_abs, indicate):
    global thread_flag
    all_df = {
        "rel" : df_rel,
        "abs" : df_abs
    }
    while thread_flag:
        dftype = input("rel or abs (or enter to skip): ")
        if all_df.get(dftype) is None:
            break
        caller_addr_str = input("caller address : ")
        #try:
        if True:
            if dftype == "abs":
                fig = plt.figure(figsize=picture_size, dpi=dpi)
                plt.title(dftype + "_" + caller_addr_str)
                mask = all_df[dftype]["caller_addr_str"] == caller_addr_str
                df_temp = all_df[dftype][mask]
                print(df_temp)
                sns.histplot(x=df_temp["hit_absolute_time"], kde=True, line_kws={"linewidth" : 5}, bins=100)

                mask2 = indicate["caller_addr_str"] == caller_addr_str
                print(indicate[mask2])

                fig.show()

            elif dftype == "rel":
                fig = plt.figure(figsize=picture_size, dpi=dpi)
                plt.title(dftype + "_" + caller_addr_str + " (discard interval small than 1s)")
                mask = all_df[dftype]["caller_addr_str"] == caller_addr_str
                df_temp = all_df[dftype][mask]
                print(df_temp)
                sns.histplot(x=df_temp["hit_relative_time"], kde=True, line_kws={"linewidth" : 5}, bins=100)

                mask2 = indicate["caller_addr_str"] == caller_addr_str
                print(indicate[mask2])

                fig.show()

            else:
                continue
        #except:
        #    print("input error")
                

def show_diagram():
    fileresult_names = {}
    fileresult_notsampled_names = {}
    fileresult_myaf = {}
    pids = {}
    all_data = os.listdir("./result")
    #print(all_data)
    for data in all_data:
        pid = int(''.join(re.findall(r'\d+', data)), 10)
        pids[pid] = True
        if "result_not_be_sampled" in data:
            fileresult_notsampled_names[pid] = "./result/" + data
        elif "myaf" in data:
            fileresult_myaf[pid] = "./result/" + data
        else:
            fileresult_names[pid] = "./result/" + data

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
            
            # make pictures with all caller 
            for i in range(min(10, number_of_sampled_malloc)):
                per_caller_info = indicate.iloc[i:i + 1, :]
                print(per_caller_info)
                mask2 = df["caller_addr_str"].isin(per_caller_info["caller_addr_str"])
                mask3 = df_myaf["caller_addr"].isin([int(per_caller_info["caller_addr_str"].to_string(index=False), 16)])

                fig, axs = plt.subplots(1, 3, figsize=(14, 5), gridspec_kw={'bottom': 0.3, 'top': 0.9}) # bottom and top is percentage 
                plt.subplots_adjust(wspace=0.3)
                # absolute time
                df_temp = df[mask2]
                sns.histplot(x=df_temp["hit_absolute_time"], ax=axs[0], bins=100)
                axs[0].set_title('Sampling Hits Count for Malloc Objects')
                axs[0].set_xlabel('Timing of Sampling Hits Across Generations (seconds)')
                axs[0].set_ylabel('Number of Sampling Hits')

                # free time
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

                # save picture
                picture_name = re.sub(r'\s+', '_', per_caller_info["caller_addr_str"].to_string())
                plt.savefig(dir_path + "/" + picture_name)
                plt.close(fig)

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
