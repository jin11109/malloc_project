import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv("./result.csv")

print(df)
print("count sum", df["count"].sum())

plt.figure()
sns.histplot(x=df["data_index"], weights=df["count"], bins=100)

plt.show()
