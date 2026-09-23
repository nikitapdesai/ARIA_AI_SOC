"""
File location in project: model/train_ensemble.py
    python .\\model\\train_ensemble.py
"""

import json
import os

import numpy as np
import tensorflow as tf
from tensorflow import keras

import pandas as pd
import joblib

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
)


DATA_DIR = "data/model_ready"
MODEL_DIR = "model/saved_models"
OUTPUT_REPORTS_DIR = "outputs/ensemble"

RANDOM_STATE = 42
STACK_SPLIT_SIZE = 0.5


def load_base_models_and_data():
    print("Loading base models ...")
    mlp = keras.models.load_model(f"{MODEL_DIR}/mlp_model.keras")
    rf = joblib.load(f"{MODEL_DIR}/random_forest_model.joblib")

    print(f"Loading prepared data from {DATA_DIR}/ ...")
    X_test = np.load(f"{DATA_DIR}/X_test.npy")
    y_test = np.load(f"{DATA_DIR}/y_test.npy")

    with open(f"{DATA_DIR}/label_mapping.json") as f:
        label_mapping = json.load(f)

    print(f"  X_test: {X_test.shape}   y_test: {y_test.shape}")

    return mlp, rf, X_test, y_test, label_mapping


def get_base_model_probs(mlp, rf, X):
    mlp_probs = mlp.predict(X, batch_size=512, verbose=0)
    rf_probs = rf.predict_proba(X)
    return mlp_probs, rf_probs


def evaluate_predictions(y_true, y_pred, y_pred_proba, label_mapping, output_dir, model_label):
    idx_to_name = {v: k for k, v in label_mapping.items()}
    class_names = [idx_to_name[i] for i in range(len(idx_to_name))]

    report_dict = classification_report(
        y_true, y_pred,
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )
    report_str = classification_report(
        y_true, y_pred,
        target_names=class_names,
        zero_division=0,
    )
    print(f"\n--- {model_label} evaluation ---")
    print(report_str)

    try:
        roc_auc = roc_auc_score(
            y_true, y_pred_proba,
            multi_class="ovr",
            average="macro",
        )
        print(f"Macro ROC-AUC (one-vs-rest): {roc_auc:.4f}")
    except ValueError as e:
        roc_auc = None
        print(f"ROC-AUC could not be computed: {e}")

    cm = confusion_matrix(y_true, y_pred)
    cm_df = pd.DataFrame(cm, index=class_names, columns=class_names)

    os.makedirs(output_dir, exist_ok=True)
    with open(f"{output_dir}/classification_report.json", "w") as f:
        json.dump(report_dict, f, indent=2)
    with open(f"{output_dir}/classification_report.txt", "w") as f:
        f.write(report_str)
        if roc_auc is not None:
            f.write(f"\nMacro ROC-AUC (one-vs-rest): {roc_auc:.4f}\n")
    cm_df.to_csv(f"{output_dir}/confusion_matrix.csv")

    print(f"Saved evaluation artifacts to {output_dir}/")

    return report_dict, roc_auc


def train_ensemble():
    mlp, rf, X_test, y_test, label_mapping = load_base_models_and_data()

    print(f"\n--- Splitting test set for stacking (stack_fit / final_eval, {STACK_SPLIT_SIZE}) ---")
    X_stack_fit, X_final_eval, y_stack_fit, y_final_eval = train_test_split(
        X_test, y_test,
        test_size=STACK_SPLIT_SIZE,
        stratify=y_test,
        random_state=RANDOM_STATE,
    )
    print(f"  stack_fit:  {X_stack_fit.shape}")
    print(f"  final_eval: {X_final_eval.shape}")

    print("\n--- Generating base model probabilities on stack_fit ---")
    mlp_probs_fit, rf_probs_fit = get_base_model_probs(mlp, rf, X_stack_fit)

    meta_X_fit = np.hstack([mlp_probs_fit, rf_probs_fit])

    print("\n--- Training meta-model (Logistic Regression) ---")
    meta_model = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        random_state=RANDOM_STATE,
    )
    meta_model.fit(meta_X_fit, y_stack_fit)

    print("\n--- Generating base model probabilities on final_eval ---")
    mlp_probs_eval, rf_probs_eval = get_base_model_probs(mlp, rf, X_final_eval)
    meta_X_eval = np.hstack([mlp_probs_eval, rf_probs_eval])

    ensemble_probs = meta_model.predict_proba(meta_X_eval)
    ensemble_pred = meta_model.predict(meta_X_eval)

    mlp_pred_eval = np.argmax(mlp_probs_eval, axis=1)
    rf_pred_eval = np.argmax(rf_probs_eval, axis=1)

    evaluate_predictions(
        y_final_eval, mlp_pred_eval, mlp_probs_eval,
        label_mapping, f"{OUTPUT_REPORTS_DIR}/mlp_on_final_eval", "MLP alone (final_eval slice)"
    )
    evaluate_predictions(
        y_final_eval, rf_pred_eval, rf_probs_eval,
        label_mapping, f"{OUTPUT_REPORTS_DIR}/rf_on_final_eval", "Random Forest alone (final_eval slice)"
    )
    ensemble_report, ensemble_auc = evaluate_predictions(
        y_final_eval, ensemble_pred, ensemble_probs,
        label_mapping, f"{OUTPUT_REPORTS_DIR}/stacked_ensemble", "Stacked Ensemble"
    )

    os.makedirs(MODEL_DIR, exist_ok=True)
    meta_model_path = f"{MODEL_DIR}/ensemble_meta_model.joblib"
    joblib.dump(meta_model, meta_model_path)
    print(f"\nMeta-model saved to: {meta_model_path}")

    print("\n=== SUMMARY: macro avg F1-score comparison (same final_eval slice) ===")
    print(f"  Ensemble macro F1: {ensemble_report['macro avg']['f1-score']:.4f}")

    return meta_model, ensemble_report


if __name__ == "__main__":
    train_ensemble()