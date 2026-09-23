import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv(
    "../data/raw/Tuesday-WorkingHours.pcap_ISCX.csv"
)

df.columns = df.columns.str.strip()

print("=" * 60)
print("DATASET OVERVIEW")
print("=" * 60)

print("Shape:", df.shape)

print("\nNumber of features:", len(df.columns) - 1)

print("\nLabels:")
print(df["Label"].value_counts())

print("\nLabel percentages:")
print(df["Label"].value_counts(normalize=True) * 100)

print("\nMissing values:")
print(df.isnull().sum().sum())

print("\nDuplicate rows:")
print(df.duplicated().sum())

print("\nInfinite values:")
numeric_df = df.select_dtypes(include=np.number)
print(np.isinf(numeric_df).sum().sum())

plt.figure(figsize=(10, 6))

sns.countplot(
    data=df,
    x="Label"
)

plt.title("Attack Distribution - Tuesday Dataset")
plt.xlabel("Traffic Type")
plt.ylabel("Number of Records")

plt.xticks(rotation=20)

plt.tight_layout()
plt.show()
print("\nNumerical feature statistics:")
print(df.describe().T)