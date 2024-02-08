import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np

all_file = os.listdir("./")

for file in all_file:
    if "result" not in file or ".csv" not in file:
        continue
    
    print(file)
    df = pd.read_csv(file)
    print(df)

    fig = plt.figure()    
    for i in range(0, 4):
        plt.plot(df[df["bin"] == i]["time"], df[df["bin"] == i]["theoretic_porpotion"], color='gray', alpha=0.5, linestyle='dashed', linewidth=2)
    
    sns.lineplot(data=df, x="time", y="porpotion", hue="bin", palette = sns.color_palette("mako_r", 6))    
    plt.yscale('log')

    plt.show()
        


