"""
File location in project: preprocessing/inspect_combined.py
    python .\\preprocessing\\inspect_combined.py
"""

import pandas as pd
import numpy as np

INPUT_PATH = "data/processed/combined_cleaned.csv"


def inspect_combined():
    print(f"Loading {INPUT_PATH} ...")
    df = pd.read_csv(INPUT_PATH)
    print(f"Shape: {df.shape}\n")

    print("=" * 60)
    print("COLUMN NAMES AND DTYPES")
    print("=" * 60)
    for col in df.columns:
        print(f"  {col:35s} {df[col].dtype}")

    print("\n" + "=" * 60)
    print("POTENTIAL IDENTITY / LEAKAGE COLUMNS (manual review needed)")
    print("=" * 60)
    suspect_keywords = ["ip", "flow id", "timestamp", "port", "id"]
    suspects = [
        col for col in df.columns
        if any(kw in col.lower() for kw in suspect_keywords)
    ]
    for col in suspects:
        print(f"  {col}  (sample values: {df[col].unique()[:3]})")

    print("\n" + "=" * 60)
    print("CONSTANT OR NEAR-CONSTANT COLUMNS (nunique <= 1)")
    print("=" * 60)
    numeric_df = df.select_dtypes(include=[np.number])
    constant_cols = [col for col in numeric_df.columns if numeric_df[col].nunique() <= 1]
    if constant_cols:
        for col in constant_cols:
            print(f"  {col}  (unique value: {numeric_df[col].unique()})")
    else:
        print("  None found.")

    print("\n" + "=" * 60)
    print("MISSING / INFINITE VALUE CHECK (should be 0 after cleaning)")
    print("=" * 60)
    missing_total = df.isna().sum().sum()
    inf_total = np.isinf(numeric_df).sum().sum()
    print(f"  Missing values: {missing_total}")
    print(f"  Infinite values: {inf_total}")

    print("\n" + "=" * 60)
    print("LABEL DISTRIBUTION")
    print("=" * 60)
    print(df["Label"].value_counts())
    print(f"\n  Total classes: {df['Label'].nunique()}")

    print("\n" + "=" * 60)
    print("HIGHLY CORRELATED FEATURE PAIRS (|corr| > 0.95)")
    print("=" * 60)
    corr_matrix = numeric_df.corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    high_corr_pairs = [
        (col, row, upper.loc[row, col])
        for col in upper.columns
        for row in upper.index
        if pd.notna(upper.loc[row, col]) and upper.loc[row, col] > 0.95
    ]
    print(f"  Found {len(high_corr_pairs)} pairs with |corr| > 0.95")
    for col, row, val in high_corr_pairs[:20]:
        print(f"  {row}  <->  {col}   corr={val:.3f}")
    if len(high_corr_pairs) > 20:
        print(f"  ... and {len(high_corr_pairs) - 20} more (truncated)")


if __name__ == "__main__":
    inspect_combined()