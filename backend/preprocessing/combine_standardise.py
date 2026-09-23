"""
File location in project: preprocessing/combine_and_standardize.py
"""

import pandas as pd
import numpy as np


PROCESSED_DIR = "data/processed"

CLEANED_FILES = [
    "monday_cleaned.csv",
    "tuesday_cleaned.csv",
    "wednesday_cleaned.csv",
    "thursday_morning_webattacks_cleaned.csv",
    "thursday_afternoon_infiltration_cleaned.csv",
    "friday_morning_cleaned.csv",
    "friday_afternoon_portscan_cleaned.csv",
    "friday_afternoon_ddos_cleaned.csv",
]

OUTPUT_PATH = f"{PROCESSED_DIR}/combined_cleaned.csv"


def standardize_labels(df):

    df["Label"] = df["Label"].astype(str).str.strip()

    df["Label"] = df["Label"].str.replace(
        "Web Attack \ufffd ", "Web Attack - ", regex=False
    )
    df["Label"] = df["Label"].str.replace(
        "Web Attack ï¿½ ", "Web Attack - ", regex=False
    )

    label_map = {
        "Web Attack - Brute Force": "Web Attack - Brute Force",
        "Web Attack - XSS": "Web Attack - XSS",
        "Web Attack - Sql Injection": "Web Attack - SQL Injection",
        "DoS slowloris": "DoS Slowloris",
        "DoS Slowhttptest": "DoS SlowHTTPTest",
        "DoS Hulk": "DoS Hulk",
        "DoS GoldenEye": "DoS GoldenEye",
        "Heartbleed": "Heartbleed",
        "FTP-Patator": "FTP-Patator",
        "SSH-Patator": "SSH-Patator",
        "PortScan": "PortScan",
        "DDoS": "DDoS",
        "Bot": "Botnet",
        "Infiltration": "Infiltration",
        "BENIGN": "BENIGN",
    }

    df["Label"] = df["Label"].replace(label_map)

    return df


def combine_and_standardize():
    all_dfs = []

    for filename in CLEANED_FILES:
        path = f"{PROCESSED_DIR}/{filename}"
        print(f"Loading {filename} ...")
        df = pd.read_csv(path)
        print(f"  shape: {df.shape}")
        all_dfs.append(df)

    print("\nCombining all files ...")
    combined = pd.concat(all_dfs, ignore_index=True)
    print(f"Combined shape before standardization: {combined.shape}")

    print("\nLabel distribution BEFORE standardization:")
    print(combined["Label"].value_counts())

    combined = standardize_labels(combined)

    print("\nLabel distribution AFTER standardization:")
    print(combined["Label"].value_counts())

    total_after = combined["Label"].value_counts().sum()
    assert total_after == combined.shape[0], (
        "Row count mismatch after standardization -- investigate before continuing."
    )

    combined.to_csv(OUTPUT_PATH, index=False)
    print(f"\nCombined + standardized dataset saved to: {OUTPUT_PATH}")
    print(f"Final shape: {combined.shape}")

    return combined


if __name__ == "__main__":
    combine_and_standardize()
