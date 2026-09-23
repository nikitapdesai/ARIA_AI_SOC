"""
File location in project: preprocessing/clean_data.py

"""

import pandas as pd
import numpy as np


def clean_file(input_filename, output_filename, encoding="utf-8"):

    input_path = f"data/raw/{input_filename}"
    output_path = f"data/processed/{output_filename}"

    print(f"\n--- Cleaning {input_filename} (encoding={encoding}) ---")

    df = pd.read_csv(input_path, encoding=encoding)
    print(f"Original shape: {df.shape}")

    df.columns = df.columns.str.strip()
    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    missing = df.isna().sum().sum()
    print(f"Missing values: {missing}")
    df.dropna(inplace=True)
    print(f"After removing missing values: {df.shape}")

    before = df.shape[0]
    df.drop_duplicates(inplace=True)
    print(f"Duplicates removed: {before - df.shape[0]}")
    print(f"Shape after removing duplicates: {df.shape}")

    print("Final label distribution:")
    print(df["Label"].value_counts())

    df.to_csv(output_path, index=False)
    print(f"Cleaned dataset saved to: {output_path}")

    return df


if __name__ == "__main__":
    files_to_clean = {
        "Monday-WorkingHours.pcap_ISCX.csv":
            ("monday_cleaned.csv", "utf-8"),
        "Tuesday-WorkingHours.pcap_ISCX.csv":
            ("tuesday_cleaned.csv", "utf-8"),
        "Wednesday-workingHours.pcap_ISCX.csv":
            ("wednesday_cleaned.csv", "utf-8"),
        "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv":
            ("thursday_morning_webattacks_cleaned.csv", "utf-8"),
        "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv":
            ("thursday_afternoon_infiltration_cleaned.csv", "utf-8"),
        "Friday-WorkingHours-Morning.pcap_ISCX.csv":
            ("friday_morning_cleaned.csv", "utf-8"),
        "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv":
            ("friday_afternoon_portscan_cleaned.csv", "utf-8"),
        "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv":
            ("friday_afternoon_ddos_cleaned.csv", "utf-8"),
    }

    files_to_run = ["Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv"]

    for raw_file in files_to_run:
        cleaned_file, file_encoding = files_to_clean[raw_file]
        clean_file(raw_file, cleaned_file, encoding=file_encoding)
