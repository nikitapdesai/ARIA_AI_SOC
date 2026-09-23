"""
File location in project: preprocessing/inspect_raw_files.py
    python .\\preprocessing\\inspect_raw_files.py
"""

import os

RAW_DIR = "data/raw"


def inspect_raw_files():
    if not os.path.isdir(RAW_DIR):
        print(f"Directory not found: {RAW_DIR}")
        return

    files = sorted(os.listdir(RAW_DIR))
    csv_files = [f for f in files if f.lower().endswith(".csv")]

    if not csv_files:
        print(f"No CSV files found in {RAW_DIR}")
        return

    print(f"Found {len(csv_files)} CSV file(s) in {RAW_DIR}:\n")
    for f in csv_files:
        full_path = os.path.join(RAW_DIR, f)
        size_mb = os.path.getsize(full_path) / (1024 * 1024)
        print(f"  {f}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    inspect_raw_files()
