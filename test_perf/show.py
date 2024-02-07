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

    plt.figure()
    sns.lineplot(data=df, x="time", y="count_log2_porpotion", hue="bin")

    plt.show()
        


