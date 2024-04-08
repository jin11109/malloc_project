import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

all_file = os.listdir("./")
#print(all_data)

for file in all_file:
    if "result" not in file or ".csv" not in file:
        continue
    
    print(file)
    df = pd.read_csv(file)

    print(df)
    print("count sum", df["count"].sum())

    plt.figure()
    sns.histplot(x=df["data_index"], weights=df["count"], bins=100)

    plt.show()
        


