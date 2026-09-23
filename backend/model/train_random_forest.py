"""
File location in project: model/train_random_forest.py
    python .\\model\\train_random_forest.py
"""

import json
import os

import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
)


DATA_DIR = "data/model_ready"
OUTPUT_MODEL_DIR = "model/saved_models"

USE_SMOTE_DATA = False

OUTPUT_REPORTS_DIR = "outputs/random_forest_smote" if USE_SMOTE_DATA else "outputs/random_forest"

RANDOM_STATE = 42

N_ESTIMATORS = 200
MAX_DEPTH = 20
N_JOBS = -1


def load_prepared_data():
    suffix = "_smote" if USE_SMOTE_DATA else ""
    print(f"Loading prepared data from {DATA_DIR}/ (X_train{suffix}.npy) ...")
    X_train = np.load(f"{DATA_DIR}/X_train{suffix}.npy")
    X_test = np.load(f"{DATA_DIR}/X_test.npy")
    y_train = np.load(f"{DATA_DIR}/y_train{suffix}.npy")
    y_test = np.load(f"{DATA_DIR}/y_test.npy")

    with open(f"{DATA_DIR}/label_mapping.json") as f:
        label_mapping = json.load(f)
    with open(f"{DATA_DIR}/feature_names.json") as f:
        feature_names = json.load(f)

    print(f"  X_train: {X_train.shape}   y_train: {y_train.shape}")
    print(f"  X_test:  {X_test.shape}   y_test:  {y_test.shape}")
    print(f"  Classes: {len(label_mapping)}")

    return X_train, X_test, y_train, y_test, label_mapping, feature_names


def evaluate_model(model, X_test, y_test, label_mapping, output_dir):
    print("\n--- Evaluating on held-out test set ---")

    idx_to_name = {v: k for k, v in label_mapping.items()}
    class_names = [idx_to_name[i] for i in range(len(idx_to_name))]

    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)

    report_dict = classification_report(
        y_test, y_pred,
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )
    report_str = classification_report(
        y_test, y_pred,
        target_names=class_names,
        zero_division=0,
    )
    print(report_str)

    try:
        roc_auc = roc_auc_score(
            y_test, y_pred_proba,
            multi_class="ovr",
            average="macro",
        )
        print(f"Macro ROC-AUC (one-vs-rest): {roc_auc:.4f}")
    except ValueError as e:
        roc_auc = None
        print(f"ROC-AUC could not be computed: {e}")

    cm = confusion_matrix(y_test, y_pred)
    cm_df = pd.DataFrame(cm, index=class_names, columns=class_names)

    os.makedirs(output_dir, exist_ok=True)
    with open(f"{output_dir}/classification_report.json", "w") as f:
        json.dump(report_dict, f, indent=2)
    with open(f"{output_dir}/classification_report.txt", "w") as f:
        f.write(report_str)
        if roc_auc is not None:
            f.write(f"\nMacro ROC-AUC (one-vs-rest): {roc_auc:.4f}\n")
    cm_df.to_csv(f"{output_dir}/confusion_matrix.csv")

    print(f"\nSaved evaluation artifacts to {output_dir}/")

    return report_dict, roc_auc, cm_df


def train_random_forest():
    X_train, X_test, y_train, y_test, label_mapping, feature_names = load_prepared_data()

    print(f"\n--- Building Random Forest (n_estimators={N_ESTIMATORS}, max_depth={MAX_DEPTH}) ---")
    model = RandomForestClassifier(
        n_estimators=N_ESTIMATORS,
        max_depth=MAX_DEPTH,
        class_weight="balanced_subsample",
        random_state=RANDOM_STATE,
        n_jobs=N_JOBS,
        verbose=1,
    )

    print("\n--- Training ---")
    model.fit(X_train, y_train)

    evaluate_model(model, X_test, y_test, label_mapping, OUTPUT_REPORTS_DIR)

    importances = model.feature_importances_
    importance_df = pd.DataFrame({
        "feature": feature_names,
        "importance": importances,
    }).sort_values("importance", ascending=False)

    os.makedirs(OUTPUT_REPORTS_DIR, exist_ok=True)
    importance_df.to_csv(f"{OUTPUT_REPORTS_DIR}/feature_importance.csv", index=False)
    print("\nTop 10 most important features:")
    print(importance_df.head(10).to_string(index=False))

    os.makedirs(OUTPUT_MODEL_DIR, exist_ok=True)
    model_path = f"{OUTPUT_MODEL_DIR}/random_forest_model.joblib"
    joblib.dump(model, model_path)
    print(f"\nModel saved to: {model_path}")

    return model


if __name__ == "__main__":
    train_random_forest()