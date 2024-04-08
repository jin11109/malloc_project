import os
import re
import matplotlib.pyplot as plt
import seaborn as sns

all_file_names = os.listdir("./")
#print(all_data)

for file_name in all_file_names:
    if "script" not in file_name and ".log" not in file_name:
        continue
    periods = []

    with open(file_name, "r") as script:
        print("file =", file_name)
        while True:
            data = script.readline()
            if len(data) == 0:
                break
            temp = data.strip()
            info = re.split(r'\s+', temp) # slip data by space
            index = 0
            while info[index].isdigit() is not True:
                index += 1

            #script_time = float(info[index + 1][0: len(info[index + 1]) - 1])
            period = int(info[index + 2], 10)
            #script_pid = int(info[index], 10)
            #data_addr = int(info[index + 4], 16)
            periods.append(period)

    #print(periods)
    #sns.swarmplot(x=periods)
    print("avg periods :", sum(periods) / len(periods))
    #sns.catplot(x=periods)
    sns.violinplot(x=periods, inner="point")
    plt.show()