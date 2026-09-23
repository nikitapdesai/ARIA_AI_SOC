"""
File location in project: preprocessing/apply_smote.py
    python .\\preprocessing\\apply_smote.py
"""

import json

import numpy as np
from imblearn.over_sampling import SMOTE


DATA_DIR = "data/model_ready"

TARGET_COUNTS = {
    "Botnet": 5000,
    "Web Attack - Brute Force": 3000,
    "Web Attack - XSS": 2000,
    "Web Attack - SQL Injection": 500,
}

RANDOM_STATE = 42


def apply_smote():
    print(f"Loading training data from {DATA_DIR}/ ...")
    X_train = np.load(f"{DATA_DIR}/X_train.npy")
    y_train = np.load(f"{DATA_DIR}/y_train.npy")

    with open(f"{DATA_DIR}/label_mapping.json") as f:
        label_mapping = json.load(f)
    name_to_idx = {k: v for k, v in label_mapping.items()}
    idx_to_name = {v: k for k, v in label_mapping.items()}

    print(f"  X_train: {X_train.shape}   y_train: {y_train.shape}")

    print("\n--- Class counts BEFORE SMOTE ---")
    unique, counts = np.unique(y_train, return_counts=True)
    before_counts = dict(zip(unique, counts))
    for idx in sorted(before_counts):
        print(f"  {idx_to_name[idx]:30s} {before_counts[idx]}")

    sampling_strategy = {}
    for class_name, target_count in TARGET_COUNTS.items():
        class_idx = name_to_idx[class_name]
        current_count = before_counts.get(class_idx, 0)
        if target_count > current_count:
            sampling_strategy[class_idx] = target_count
        else:
            print(f"\n  Skipping '{class_name}': target {target_count} <= current {current_count}")

    print(f"\n--- Applying SMOTE (k_neighbors=5) ---")
    print(f"  Targeting: {[idx_to_name[i] for i in sampling_strategy]}")

    smote = SMOTE(
        sampling_strategy=sampling_strategy,
        k_neighbors=5,
        random_state=RANDOM_STATE,
    )
    X_train_smote, y_train_smote = smote.fit_resample(X_train, y_train)

    print(f"\n--- Class counts AFTER SMOTE ---")
    unique_after, counts_after = np.unique(y_train_smote, return_counts=True)
    after_counts = dict(zip(unique_after, counts_after))
    for idx in sorted(after_counts):
        before = before_counts.get(idx, 0)
        after = after_counts[idx]
        marker = "  <-- oversampled" if after > before else ""
        print(f"  {idx_to_name[idx]:30s} {before:>8} -> {after:>8}{marker}")

    print(f"\nTotal training samples: {X_train.shape[0]} -> {X_train_smote.shape[0]}")

    np.save(f"{DATA_DIR}/X_train_smote.npy", X_train_smote)
    np.save(f"{DATA_DIR}/y_train_smote.npy", y_train_smote)
    print(f"\nSaved: {DATA_DIR}/X_train_smote.npy")
    print(f"Saved: {DATA_DIR}/y_train_smote.npy")
    print("\nNote: X_test.npy / y_test.npy are UNCHANGED -- evaluation stays fair.")


if __name__ == "__main__":
    apply_smote()