import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv("./result.csv")

df["std"] = (df["count"] - df["count"].mean()) / df["count"].std()
print(df)
print("count sum", df["count"].sum())

plt.figure()
#sns.lineplot(data=df, x="std", y="std")
sns.kdeplot(data=df, x="std")

plt.show()
