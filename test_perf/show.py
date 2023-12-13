import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv("./result.csv")
plt.figure()
sns.histplot(data=df, x="time", kde=True)
plt.figure()
sns.kdeplot(data=df, x="time")
plt.show()