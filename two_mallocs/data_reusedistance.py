import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("agg")
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re
import json

PAGE_SIZE = 4096

def calculate_reuse_distances(df):
    cold_reuse_distances = []
    other_reuse_distances = []
    last_seen = {}

    for index, row in df.iterrows():
        key = (row["page"], row["pid"])
        if key in last_seen:
            distance = index - last_seen[key]
            if row["is_cold"]:
                cold_reuse_distances.append(distance)
            else:
                other_reuse_distances.append(distance)
        last_seen[key] = index

    return [cold_reuse_distances, other_reuse_distances]

def output(distance_counts, distances, savepath):
    fig, axs = plt.subplots(1, 1, figsize=(14, 10), gridspec_kw={"bottom": 0.3, "top": 0.9})
    # sns.barplot(x=distances, y=distance_counts)
    sns.histplot(x=distances, weights=distance_counts, ax=axs, bins=250)
    axs.set_title("Page Reuse Distance Frequency Chart")
    axs.set_ylabel("Reference Count")
    axs.set_xlabel("Reuse Distance")
    axs.set_yscale("log")
    
    obj_info = "malloc objects information" \
                + "\n" + "|  " + str()
    
    fig.text(0.2, 0.2,  obj_info, ha="left", va="top", fontsize=10, color="blue")
    
    fig.savefig("./result_picture/" + savepath)
    plt.close(fig)

    with open("./result_picture/" + savepath + ".json", 'w') as file:
        json.dump({"distance_counts" : distance_counts.tolist(), "distances" : distances.tolist()}, file)

def main():
    all_data = os.listdir("./data")
    alloc_logs = {}
    for data in all_data:
        if "mya_" in data:
            pid = int("".join(re.findall(r"\d+", data)), 10)
            alloc_logs[pid] = "./data/" + data

    all_df_mya = []
    for pid in alloc_logs:
        df_mya = pd.read_csv(alloc_logs[pid])
        df_mya["page"] = df_mya["data_addr"].apply(lambda x: x // PAGE_SIZE)
        df_mya["pid"] = pid
        all_df_mya.append(df_mya)
    df_mya = pd.concat(all_df_mya, axis=0)

    df = pd.read_csv("./data/cachemisses.csv")
    df["page"] = df["addr"].apply(lambda x: int(x, 16) // PAGE_SIZE)

    merged_df = df.merge(df_mya, on=['page', 'pid'], how='left', indicator=True)
    df["is_cold"] = merged_df['_merge'] == 'both'

    cold_reuse_distances, other_reuse_distances = calculate_reuse_distances(df)

    cold_distance_counts = np.bincount(cold_reuse_distances)
    cold_distances = np.arange(len(cold_distance_counts))
    output(cold_distance_counts, cold_distances, "cold_reusedist")

    other_distance_counts = np.bincount(other_reuse_distances)
    other_distances = np.arange(len(other_distance_counts))
    output(other_distance_counts, other_distances, "other_reusedist")

if __name__ == "__main__":
    plt.rcParams["axes.formatter.useoffset"] = False
    main()
