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

def compare_reusedist(two_reuse_distance, one_reuse_distance):
    thresholds = [0, 5000, 10000, 15000, 20000, 25000, 30000, 35000, 40000]

    data = []
    for threshold in thresholds:
        count1 = np.sum(one_reuse_distance >= threshold)
        count2 = np.sum(two_reuse_distance >= threshold)
        data.append({"Threshold": threshold, "Count": count1, "Type": "Original"})
        data.append({"Threshold": threshold, "Count": count2, "Type": "Split to Cold and Other"})

    df = pd.DataFrame(data)
    fig, axs = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={'bottom': 0.3, 'top': 0.9})
    plt.subplots_adjust(wspace=0.3)
    sns.lineplot(data=df, x="Threshold", y="Count", hue="Type", ax=axs[0], markers=True, style="Type")
    axs[0].set_yscale('log')
    axs[0].set_title('Page fault between split cold objects \nor not with defferent threshold')
    axs[0].set_ylabel('Number of page fault')
    axs[0].set_xlabel('Threshold')
    plt.savefig("./compare_reusedist")
    plt.close(fig)

    max_value = max(np.max(two_reuse_distance), np.max(one_reuse_distance))
    bin_edges = np.arange(0, max_value + 2, 1)
    count1_hist, _ = np.histogram(one_reuse_distance, bins=bin_edges)
    count2_hist, _ = np.histogram(two_reuse_distance, bins=bin_edges)
    cumulative_count1 = np.cumsum(count1_hist[::-1])[::-1]
    cumulative_count2 = np.cumsum(count2_hist[::-1])[::-1]
    variation_raw = []
    reduction_percentage = []
    end_of_cum = -1
    index = 0
    for count1, count2 in zip(cumulative_count1, cumulative_count2):
        variation_raw.append(count2 - count1)
        if count1 != 0:
            reduction_percentage.append(round((count2 - count1) / count1 * 100, 3) * -1)
        if count1 == 0 or count2 == 0:
            if end_of_cum == -1:
                end_of_cum = index
            reduction_percentage.append(0)
        index += 1

    x_data = []
    index = 0
    end_of_x = len(bin_edges[0 : -(max_value - end_of_cum) - 1])
    for i in bin_edges[0 : -(max_value - end_of_cum) - 1]:
        index += 1
        mem_pressure = abs((max_value - i) / max_value * 100)
        # Don't consider the data smaller than 5% memory persure
        if mem_pressure < 5:
            end_of_x = index - 1
            break
        x_data.append(mem_pressure)
    fig, axs = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={'bottom': 0.3, 'top': 0.9})
    sns.lineplot(x=x_data, y=reduction_percentage[0 : end_of_x], ax=axs[1])
    plt.axhline(0, color='gray', linestyle='--', linewidth=1)
    axs[1].text(x_data[0] + 2, reduction_percentage[0] + 8, f'({x_data[0]}%, {reduction_percentage[0]}%)', fontsize=10, color='darkblue', ha='right')
    axs[1].plot(x_data[0], reduction_percentage[0], 'o', color='darkblue')
    axs[1].set_xticks(range(0, 100 + 1, 10))
    axs[1].axhline(0, color='gray', linestyle='--', linewidth=1)
    axs[1].set_title('The reduction of page faults after separating cold ma-calllers\nfrom other ma-callers under different memory pressure')
    axs[1].set_ylabel('Reduction of page faults(%)')
    axs[1].set_xlabel('Memory pressure(%)')
    plt.savefig("./compare_reusedist_pagefault")
    plt.close(fig)

def main():
    two_mallocs_result = input('input two mallocs result dir path\n')
    one_malooc_reault = input('input one malloc result dir path\n')
    with open(two_mallocs_result + '/cold_reuse_distance_space.json', 'r') as file:
        two_reuse_distance = json.load(file)
    with open(two_mallocs_result + '/other_reuse_distance_space.json', 'r') as file:
        two_reuse_distance.extend(json.load(file))
    with open(one_malooc_reault + '/other_reuse_distance_space.json', 'r') as file:
        one_reuse_distance = json.load(file)

    two_reuse_distance = np.array(two_reuse_distance)
    one_reuse_distance = np.array(one_reuse_distance)
    compare_reusedist(two_reuse_distance, one_reuse_distance)

if __name__ == "__main__":
    plt.rcParams["axes.formatter.useoffset"] = False
    main()
