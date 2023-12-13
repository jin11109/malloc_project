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
                fig = plt.figure()
                plt.title(dftype + "_" + caller_addr_str)
                mask = all_df[dftype]["caller_addr_str"] == caller_addr_str
                df_temp = all_df[dftype][mask]
                print(df_temp)
                sns.histplot(x=df_temp["hit_absolute_time"], kde=True, line_kws={"linewidth" : 5}, bins=100)

                mask2 = indicate["caller_addr_str"] == caller_addr_str
                print(indicate[mask2])

                fig.show()

            elif dftype == "rel":
                fig = plt.figure()
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
    pids = {}
    all_data = os.listdir("./result")
    #print(all_data)
    for data in all_data:
        pid = int(''.join(re.findall(r'\d+', data)), 10)
        pids[pid] = True
        if "result_not_be_sampled" in data:
            fileresult_notsampled_names[pid] = "./result/" + data
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
        "total_size" : int
    }
    
    for pid in pids:
        flag = False
        if fileresult_notsampled_names.get(pid) is not None:
            df_not = pd.read_csv(fileresult_notsampled_names[pid], dtype=dtype)
            df_not = pd.DataFrame(df_not)

            df_not = df_not.sort_values("total_size", ascending=False)
            indicate = df_not.head(50)
            
            print("\n")
            print(str(pid) + " not be sample : ", len(df_not))

            fig = plt.figure()
            plt.title('sample not hit pid=' + str(pid))
            sns.barplot(data=indicate, x="total_size", y="caller_addr_str")


        if fileresult_names.get(pid) is not None:       
            df = pd.read_csv(fileresult_names[pid], dtype=dtype)
            df = pd.DataFrame(df)
            flag = True

            # drop error
            df.drop_duplicates(subset=["hit_time"], keep=False, inplace=True)

            df["hit_absolute_time"] = df["hit_time"] - df["alloc_time"]
            
            mask = df["interval_time"] > 1
            
            #indicate = df.groupby("caller_addr_str", as_index=True).size().reset_index().rename(columns={0: 'size'})
            #indicate = df[mask].groupby("caller_addr_str", as_index=False).aggregate({"size": ["sum", "size"]})
            indicate = df.groupby("caller_addr_str", as_index=False).aggregate({"size": ["sum", "count"]})
            indicate.columns = indicate.columns.map(''.join)
            print(str(pid) + " smaple num : ", len(indicate))
            #indicate = indicate.sort_values("sizesize", ascending=False)
            indicate = indicate.sort_values("sizecount", ascending=False)
            indicate = indicate.head(50)
            print(indicate)

            mask2 = df["caller_addr_str"].isin(indicate["caller_addr_str"])

            # hit relative time histplot diagram
            plt.figure()
            plt.title('hit relative time(%) (discard interval small than 1s) pid=' + str(pid))
            df_rel = df[mask & mask2]
            sns.histplot(x=df_rel["hit_relative_time"], y=df_rel["caller_addr_str"], legend=True, cbar=True, bins=100) 
            
            # hit absolute time histplot diagram
            plt.figure()
            plt.title('hit absolute time(seconds) pid=' + str(pid))
            df_abs = df[mask2]
            sns.histplot(x=df_abs["hit_absolute_time"], y=df_abs["caller_addr_str"], legend=True, cbar=True, bins=100)

            # free absolute time histplot diagram
            plt.figure()
            plt.title('free absolute time(seconds) pid=' + str(pid))
            sns.histplot(x=df_abs["interval_time"], y=df_abs["caller_addr_str"], legend=True, cbar=True, bins=100)


            # information bar diagram
            g = sns.PairGrid(
                data=indicate,
                x_vars=["sizecount", "sizesum"],
                y_vars=["caller_addr_str"]
            )
            g.map(sns.barplot, color="#00E3E3")
            g.set(title="info")

        """
        global thread_flag
        task_thread = threading.Thread(target=query, args=(df_rel, df_abs))
        thread_flag = True
        task_thread.start()
        """
        plt.ion()
        plt.show()
        if flag:
            query(df_rel, df_abs, indicate)
        else:
            input("press enter to skip")
        plt.close("all")
        #plt.ioff()
        #thread_flag = False
        #task_thread.join()

if __name__ == "__main__":
    show_diagram()
