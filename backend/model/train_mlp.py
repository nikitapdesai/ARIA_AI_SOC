"""
File location in project: model/train_mlp.py
    python .\\model\\train_mlp.py
"""

import json
import os

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

import pandas as pd

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
)


DATA_DIR = "data/model_ready"
OUTPUT_MODEL_DIR = "model/saved_models"

USE_SMOTE_DATA = False

OUTPUT_REPORTS_DIR = "outputs/mlp_smote" if USE_SMOTE_DATA else "outputs/mlp"

MAX_CLASS_WEIGHT = 15.0

RANDOM_STATE = 42
VALIDATION_SPLIT = 0.1
EPOCHS = 30
BATCH_SIZE = 512


def load_prepared_data():
    suffix = "_smote" if USE_SMOTE_DATA else ""
    print(f"Loading prepared data from {DATA_DIR}/ (X_train{suffix}.npy) ...")
    X_train = np.load(f"{DATA_DIR}/X_train{suffix}.npy")
    X_test = np.load(f"{DATA_DIR}/X_test.npy")
    y_train = np.load(f"{DATA_DIR}/y_train{suffix}.npy")
    y_test = np.load(f"{DATA_DIR}/y_test.npy")

    with open(f"{DATA_DIR}/label_mapping.json") as f:
        label_mapping = json.load(f)

    if USE_SMOTE_DATA:
        from sklearn.utils.class_weight import compute_class_weight
        classes = np.unique(y_train)
        weights = compute_class_weight(class_weight="balanced", classes=classes, y=y_train)
        raw_class_weights = {int(c): float(w) for c, w in zip(classes, weights)}
        print("  Recomputed class weights from SMOTE-augmented training labels.")
    else:
        with open(f"{DATA_DIR}/class_weights.json") as f:
            raw_class_weights = json.load(f)
        raw_class_weights = {int(k): v for k, v in raw_class_weights.items()}

    print(f"  X_train: {X_train.shape}   y_train: {y_train.shape}")
    print(f"  X_test:  {X_test.shape}   y_test:  {y_test.shape}")
    print(f"  Classes: {len(label_mapping)}")

    return X_train, X_test, y_train, y_test, label_mapping, raw_class_weights


def cap_class_weights(class_weights, max_weight=MAX_CLASS_WEIGHT):
    print(f"\n--- Capping class weights at {max_weight} ---")
    capped = {}
    for cls_idx, weight in class_weights.items():
        capped_weight = min(weight, max_weight)
        capped[cls_idx] = capped_weight
        if capped_weight != weight:
            print(f"  class {cls_idx}: {weight:.2f} -> {capped_weight:.2f} (capped)")
    return capped


def build_mlp(input_dim, num_classes):
    model = keras.Sequential([
        layers.Input(shape=(input_dim,)),

        layers.Dense(128),
        layers.BatchNormalization(),
        layers.ReLU(),
        layers.Dropout(0.3),

        layers.Dense(64),
        layers.BatchNormalization(),
        layers.ReLU(),
        layers.Dropout(0.3),

        layers.Dense(num_classes, activation="softmax"),
    ])

    model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    return model


def evaluate_model(model, X_test, y_test, label_mapping, output_dir):
    print("\n--- Evaluating on held-out test set ---")

    idx_to_name = {v: k for k, v in label_mapping.items()}
    class_names = [idx_to_name[i] for i in range(len(idx_to_name))]

    y_pred_proba = model.predict(X_test, batch_size=BATCH_SIZE, verbose=0)
    y_pred = np.argmax(y_pred_proba, axis=1)

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


def train_mlp():
    tf.random.set_seed(RANDOM_STATE)

    X_train, X_test, y_train, y_test, label_mapping, raw_class_weights = load_prepared_data()
    class_weights = cap_class_weights(raw_class_weights)

    num_classes = len(label_mapping)
    input_dim = X_train.shape[1]

    print(f"\n--- Building MLP (input_dim={input_dim}, num_classes={num_classes}) ---")
    model = build_mlp(input_dim, num_classes)
    model.summary()

    early_stopping = keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=5,
        restore_best_weights=True,
    )

    print(f"\n--- Training (epochs={EPOCHS}, batch_size={BATCH_SIZE}) ---")
    history = model.fit(
        X_train, y_train,
        validation_split=VALIDATION_SPLIT,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        class_weight=class_weights,
        callbacks=[early_stopping],
        verbose=1,
    )

    os.makedirs(OUTPUT_REPORTS_DIR, exist_ok=True)
    history_dict = {k: [float(v) for v in vals] for k, vals in history.history.items()}
    with open(f"{OUTPUT_REPORTS_DIR}/training_history.json", "w") as f:
        json.dump(history_dict, f, indent=2)

    evaluate_model(model, X_test, y_test, label_mapping, OUTPUT_REPORTS_DIR)

    os.makedirs(OUTPUT_MODEL_DIR, exist_ok=True)
    model_suffix = "_smote" if USE_SMOTE_DATA else ""
    model_path = f"{OUTPUT_MODEL_DIR}/mlp_model{model_suffix}.keras"
    model.save(model_path)
    print(f"\nModel saved to: {model_path}")

    return model, history


if __name__ == "__main__":
    train_mlp()