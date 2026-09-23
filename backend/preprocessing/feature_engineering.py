"""
File location in project: preprocessing/feature_engineering.py
    python .\\preprocessing\\feature_engineering.py
"""

import pandas as pd
import numpy as np
import joblib
import json
import os

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.utils.class_weight import compute_class_weight


INPUT_PATH = "data/processed/combined_cleaned.csv"
OUTPUT_DIR = "data/model_ready"

CONSTANT_COLUMNS = [
    "Bwd PSH Flags",
    "Bwd URG Flags",
    "Fwd Avg Bytes/Bulk",
    "Fwd Avg Packets/Bulk",
    "Fwd Avg Bulk Rate",
    "Bwd Avg Bytes/Bulk",
    "Bwd Avg Packets/Bulk",
    "Bwd Avg Bulk Rate",
]

DUPLICATE_COLUMNS = [
    "Fwd Header Length.1",
]

CORRELATION_THRESHOLD = 0.95
RANDOM_STATE = 42
TEST_SIZE = 0.2


def drop_constant_and_duplicate_columns(df):
    print("\n--- Dropping constant columns ---")
    existing_constant = [c for c in CONSTANT_COLUMNS if c in df.columns]
    print(f"  Dropping: {existing_constant}")
    df = df.drop(columns=existing_constant)

    print("--- Dropping known duplicate columns ---")
    existing_dupes = [c for c in DUPLICATE_COLUMNS if c in df.columns]
    print(f"  Dropping: {existing_dupes}")
    df = df.drop(columns=existing_dupes)

    return df


def drop_correlated_columns(df, label_col="Label"):
    print(f"\n--- Dropping redundant correlated columns (|corr| > {CORRELATION_THRESHOLD}) ---")

    numeric_df = df.drop(columns=[label_col])
    corr_matrix = numeric_df.corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))

    to_drop = set()
    dropped_because_of = {}

    for col in upper.columns:
        if col in to_drop:
            continue
        correlated_with_col = upper.index[upper[col] > CORRELATION_THRESHOLD].tolist()
        for row in correlated_with_col:
            if row not in to_drop:
                to_drop.add(row)
                dropped_because_of[row] = col

    print(f"  Total columns dropped: {len(to_drop)}")
    for dropped_col, kept_col in sorted(dropped_because_of.items()):
        print(f"    dropped '{dropped_col}'  (redundant with kept '{kept_col}')")

    df = df.drop(columns=list(to_drop))
    return df, dropped_because_of


def feature_engineering():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Loading {INPUT_PATH} ...")
    df = pd.read_csv(INPUT_PATH)
    print(f"Initial shape: {df.shape}")

    df = drop_constant_and_duplicate_columns(df)
    print(f"Shape after dropping constant/duplicate columns: {df.shape}")

    df, dropped_corr_info = drop_correlated_columns(df, label_col="Label")
    print(f"Shape after dropping correlated columns: {df.shape}")

    X = df.drop(columns=["Label"])
    y = df["Label"]
    feature_names = X.columns.tolist()
    print(f"\nFinal feature count: {len(feature_names)}")

    print("\n--- Encoding labels ---")
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    label_mapping = {
        str(cls): int(idx) for idx, cls in enumerate(label_encoder.classes_)
    }
    print("  Label mapping:")
    for cls, idx in label_mapping.items():
        print(f"    {idx:2d} -> {cls}")

    print(f"\n--- Splitting train/test (test_size={TEST_SIZE}, stratified) ---")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded,
        test_size=TEST_SIZE,
        stratify=y_encoded,
        random_state=RANDOM_STATE,
    )
    print(f"  Train shape: {X_train.shape}")
    print(f"  Test shape:  {X_test.shape}")

    print("\n--- Scaling features (fit on train only) ---")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print("\n--- Computing class weights (from training labels only) ---")
    classes = np.unique(y_train)
    weights = compute_class_weight(
        class_weight="balanced",
        classes=classes,
        y=y_train,
    )
    class_weight_dict = {int(c): float(w) for c, w in zip(classes, weights)}
    print("  Class weights:")
    for cls_idx, weight in sorted(class_weight_dict.items()):
        cls_name = label_encoder.inverse_transform([cls_idx])[0]
        print(f"    {cls_idx:2d} ({cls_name:30s}) weight = {weight:.4f}")

    print(f"\n--- Saving artifacts to {OUTPUT_DIR}/ ---")

    np.save(f"{OUTPUT_DIR}/X_train.npy", X_train_scaled)
    np.save(f"{OUTPUT_DIR}/X_test.npy", X_test_scaled)
    np.save(f"{OUTPUT_DIR}/y_train.npy", y_train)
    np.save(f"{OUTPUT_DIR}/y_test.npy", y_test)

    joblib.dump(scaler, f"{OUTPUT_DIR}/scaler.joblib")
    joblib.dump(label_encoder, f"{OUTPUT_DIR}/label_encoder.joblib")

    with open(f"{OUTPUT_DIR}/feature_names.json", "w") as f:
        json.dump(feature_names, f, indent=2)

    with open(f"{OUTPUT_DIR}/label_mapping.json", "w") as f:
        json.dump(label_mapping, f, indent=2)

    with open(f"{OUTPUT_DIR}/class_weights.json", "w") as f:
        json.dump(class_weight_dict, f, indent=2)

    with open(f"{OUTPUT_DIR}/dropped_correlated_columns.json", "w") as f:
        json.dump(dropped_corr_info, f, indent=2)

    print("  Saved: X_train.npy, X_test.npy, y_train.npy, y_test.npy")
    print("  Saved: scaler.joblib, label_encoder.joblib")
    print("  Saved: feature_names.json, label_mapping.json")
    print("  Saved: class_weights.json, dropped_correlated_columns.json")

    print("\nFeature engineering complete.")
    print(f"Final feature count: {len(feature_names)}")
    print(f"Train samples: {X_train_scaled.shape[0]}  Test samples: {X_test_scaled.shape[0]}")


if __name__ == "__main__":
    feature_engineering()