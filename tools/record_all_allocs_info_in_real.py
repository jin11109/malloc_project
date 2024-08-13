import os
import re
import pandas as pd
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import seaborn as sns

class Alloc:
    def __init__(self, alloc_temper):
        self.total_alloc_size = 0
        self.lifetime_objsize_product = 0
        self.count = 0
        self.total_hits = 0
        self.temper = alloc_temper

class Allocs_info:
    def __init__(self, pid):
        self.pid = pid
        # "cold", "other" are include in "sampled" 
        self.classification = ["cold", "unsampled", "other", "sampled"]
        self.classify = {}
        for i in self.classification:
            self.classify[i] = Alloc(i)
    
    def count_alloc_sum(self):
        temp = 0
        for i in self.classification:
            if i != "sampled":
                temp += self.classify[i].count
        return temp

    def total_alloc_size_sum(self):
        temp = 0
        for i in self.classification:
            if i != "sampled":
                temp += self.classify[i].total_alloc_size
        return temp
    
    def lifetime_objsize_product_sum(self):
        temp = 0
        for i in self.classification:
            if i != "sampled":
                temp += self.classify[i].lifetime_objsize_product
        return temp

dtype = {
    "pid_in_drcachesim" : int,
    "pid_real" : int,
    "alloc_index_in_drcachesim" : int,
    "alloc_addr_in_drcachesim" : str,
    "alloc_addr_real" : str,
    "alloc_index_real" : int,
    "temperature" : str,
    "mark" : str,
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

def record_allocs(allocs_info):
    fig, axs = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={'bottom': 0.3, 'top': 0.9})
    plt.subplots_adjust(wspace=0.3)

    classifications = ["cold", "other", "unsampled"]
    rename_label = {
        "cold" : "cold ma-callers",
        "other" : "other ma-callers",
        "unsampled" : "ma-callers have no data"
    }
    labels = []
    titles = []
    data = []

    count_alloc_sum = allocs_info.count_alloc_sum()
    total_alloc_size_sum = allocs_info.total_alloc_size_sum()
    lifetime_objsize_product_sum = allocs_info.lifetime_objsize_product_sum()
    for classification in classifications:
        data.append(allocs_info.classify[classification].count / count_alloc_sum * 100)
        titles.append("count of ma-callers")
        labels.append(rename_label[classification])

        data.append(allocs_info.classify[classification].total_alloc_size / total_alloc_size_sum * 100)
        titles.append("total alloc size\nof ma-callers")
        labels.append(rename_label[classification])

        data.append(allocs_info.classify[classification].lifetime_objsize_product / lifetime_objsize_product_sum * 100)
        #titles.append("production of\nlifetime and objs size")
        titles.append("memory occupation")
        labels.append(rename_label[classification])

    sns.barplot(x=titles, y=data, hue=labels, ax=axs[0], estimator=sum, errorbar=None, palette=sns.color_palette("deep"))
    axs[0].set_ylabel("propotion(%)")
    #axs[0].bar_label(axs[0].containers[0])
    for container in axs[0].containers:
        labels = [f"{float(v.get_height()):.2f}%" for v in container]
        axs[0].bar_label(container, labels=labels)

    mallocs_info = f"allocs information (pid : {allocs_info.pid})"\
        + "\n" + "|  count of allocs : " + f"cold({allocs_info.classify['cold'].count}),  unsampled({allocs_info.classify['unsampled'].count}),  other({allocs_info.classify['other'].count})" \
        + "\n" + "|  total alloc size : " + f"cold({allocs_info.classify['cold'].total_alloc_size}),  unsampled({allocs_info.classify['unsampled'].total_alloc_size}),  other({allocs_info.classify['other'].total_alloc_size})" \
        + "\n" + "|  production of lifetime and objs size : " + f"cold({allocs_info.classify['cold'].lifetime_objsize_product:.2f}),  unsampled({allocs_info.classify['unsampled'].lifetime_objsize_product:.2f}),  other({allocs_info.classify['other'].lifetime_objsize_product:.2f})" 
    
    fig.text(0.2, 0.2,  mallocs_info, ha='left', va='top', fontsize=10, color='blue')

    plt.savefig(f"./{allocs_info.pid}all_allocs")
    plt.close(fig)

def main():
    addr_table_path = input("input alloc addr table path\n")
    result_path = input("input result path\n")

    myafs_path = {}

    all_datas = os.listdir(result_path)
    for data in all_datas:
        if data.endswith(".csv") and "myaf" in data:
            pid = int(''.join(re.findall(r'\d+', data)), 10)
            myafs_path[pid] = result_path + "/" +  data

    df_allocs_addr_table = pd.read_csv(addr_table_path, dtype=dtype)
    df_allocs_addr_table = pd.DataFrame(df_allocs_addr_table)
    df_allocs_addr_table["alloc_addr_real_decimal"] = df_allocs_addr_table['alloc_addr_real'].apply(lambda x: int(x, 16))
    for pid in myafs_path:
        allocs_info = Allocs_info(pid)

        df_myaf = pd.read_csv(myafs_path[pid], dtype=dtype)
        df_myaf = pd.DataFrame(df_myaf)
        # I temporarily rename the column avoid to get it wrong
        df_myaf = df_myaf.rename(columns={"generation": "lifetime"})
        df_myaf["lifetime_objsize_product"] = df_myaf["lifetime"].clip(lower=0) * df_myaf["size"]

        total_alloc = len(df_myaf.groupby("caller_addr", as_index=False))
        total_lifetime_objsize_product = df_myaf["lifetime_objsize_product"].sum()
        total_alloc_size = df_myaf["size"].sum()

        mask = df_allocs_addr_table["pid_real"] == pid
        temper_cold_mask = df_allocs_addr_table["temperature"] == "cold"
        temper_unsampled_mask = df_allocs_addr_table["temperature"] == "unsampled"
        temper_cold_mask2 = df_myaf["caller_addr"].isin(df_allocs_addr_table[mask & temper_cold_mask]["alloc_addr_real_decimal"])
        temper_unsampled_mask2 = df_myaf["caller_addr"].isin(df_allocs_addr_table[mask & temper_unsampled_mask]["alloc_addr_real_decimal"])
        
        # record "cold" information
        df_cold = df_myaf.copy()
        df_cold = df_cold[temper_cold_mask2]
        allocs_info.classify["cold"].count = len(df_cold.groupby("caller_addr", as_index=False))
        allocs_info.classify["cold"].lifetime_objsize_product = df_cold["lifetime_objsize_product"].sum()
        allocs_info.classify["cold"].total_alloc_size = df_cold["size"].sum()

        # record "unsampled" information
        df_unsampled = df_myaf.copy()
        df_unsampled = df_unsampled[temper_unsampled_mask2]
        allocs_info.classify["unsampled"].count = len(df_unsampled.groupby("caller_addr", as_index=False))
        allocs_info.classify["unsampled"].lifetime_objsize_product = df_unsampled["lifetime_objsize_product"].sum()
        allocs_info.classify["unsampled"].total_alloc_size = df_unsampled["size"].sum()

        # record "other" information
        allocs_info.classify["other"].count = total_alloc \
            - allocs_info.classify["unsampled"].count \
            - allocs_info.classify["cold"].count
        allocs_info.classify["other"].lifetime_objsize_product = total_lifetime_objsize_product \
            - allocs_info.classify["unsampled"].lifetime_objsize_product \
            - allocs_info.classify["cold"].lifetime_objsize_product
        allocs_info.classify["other"].total_alloc_size = total_alloc_size \
            - allocs_info.classify["unsampled"].total_alloc_size \
            - allocs_info.classify["cold"].total_alloc_size

        record_allocs(allocs_info)


if __name__ == "__main__":
    # Turn off the automatic using scientific notation at axis lable
    plt.rcParams['axes.formatter.useoffset'] = False
    
    main()