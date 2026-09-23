"""
File location in project: agents/detection_agent.py
Detection Agent -- Agent 1 of 4 in the SOC Alert Prioritizer pipeline.
"""

import json
import numpy as np
import joblib
from tensorflow import keras


DATA_DIR = "data/model_ready"
MODEL_DIR = "model/saved_models"


class DetectionAgent:
    def __init__(self):
        print("[DetectionAgent] Loading artifacts ...")

        self.scaler = joblib.load(f"{DATA_DIR}/scaler.joblib")
        self.label_encoder = joblib.load(f"{DATA_DIR}/label_encoder.joblib")

        with open(f"{DATA_DIR}/label_mapping.json") as f:
            self.label_mapping = json.load(f)
        self.idx_to_name = {v: k for k, v in self.label_mapping.items()}

        self.mlp = keras.models.load_model(f"{MODEL_DIR}/mlp_model.keras")
        self.rf = joblib.load(f"{MODEL_DIR}/random_forest_model.joblib")
        self.meta_model = joblib.load(f"{MODEL_DIR}/ensemble_meta_model.joblib")

        print("[DetectionAgent] Ready.")

    def predict(self, raw_feature_row):

        X = np.asarray(raw_feature_row).reshape(1, -1)
        X_scaled = self.scaler.transform(X)

        mlp_probs = self.mlp.predict(X_scaled, verbose=0)
        rf_probs = self.rf.predict_proba(X_scaled)

        meta_X = np.hstack([mlp_probs, rf_probs])
        ensemble_probs = self.meta_model.predict_proba(meta_X)[0]

        predicted_idx = int(np.argmax(ensemble_probs))
        predicted_class = self.idx_to_name[predicted_idx]
        confidence = float(ensemble_probs[predicted_idx])

        class_probabilities = {
            self.idx_to_name[i]: float(p) for i, p in enumerate(ensemble_probs)
        }

        return {
            "predicted_class": predicted_class,
            "confidence": confidence,
            "class_probabilities": class_probabilities,
        }

    def predict_batch(self, raw_feature_matrix):
        X = np.asarray(raw_feature_matrix)
        X_scaled = self.scaler.transform(X)

        mlp_probs = self.mlp.predict(X_scaled, verbose=0)
        rf_probs = self.rf.predict_proba(X_scaled)

        meta_X = np.hstack([mlp_probs, rf_probs])
        ensemble_probs = self.meta_model.predict_proba(meta_X)

        results = []
        for row_probs in ensemble_probs:
            predicted_idx = int(np.argmax(row_probs))
            results.append({
                "predicted_class": self.idx_to_name[predicted_idx],
                "confidence": float(row_probs[predicted_idx]),
                "class_probabilities": {
                    self.idx_to_name[i]: float(p) for i, p in enumerate(row_probs)
                },
            })
        return results


if __name__ == "__main__":
    print("Running Detection Agent smoke test ...")
    X_test = np.load(f"{DATA_DIR}/X_test.npy")
    with open(f"{DATA_DIR}/label_mapping.json") as f:
        label_mapping = json.load(f)
    idx_to_name = {v: k for k, v in label_mapping.items()}
    y_test = np.load(f"{DATA_DIR}/y_test.npy")

    agent = DetectionAgent()

    sample = X_test[:5]
    mlp_probs = agent.mlp.predict(sample, verbose=0)
    rf_probs = agent.rf.predict_proba(sample)
    meta_X = np.hstack([mlp_probs, rf_probs])
    ensemble_probs = agent.meta_model.predict_proba(meta_X)

    for i in range(5):
        pred_idx = int(np.argmax(ensemble_probs[i]))
        pred_name = idx_to_name[pred_idx]
        true_name = idx_to_name[int(y_test[i])]
        confidence = ensemble_probs[i][pred_idx]
        print(f"  True: {true_name:25s}  Predicted: {pred_name:25s}  Confidence: {confidence:.4f}")