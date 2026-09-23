"""
File location in project: agents/priority_explainer_agent.py
    python .\\agents\\priority_explainer_agent.py
"""

import json
import os
import sys

import numpy as np
import pandas as pd
import joblib
import shap


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DATA_DIR = "data/model_ready"
MODEL_DIR = "model/saved_models"
CORRELATED_ALERTS_PATH = f"{DATA_DIR}/correlated_alert_stream.csv"
OUTPUT_PATH = f"{DATA_DIR}/prioritized_alert_stream.csv"
KNOWLEDGE_BASE_PATH = "knowledge_base/known_campaigns.json"

SEVERITY_TABLE = {
    "BENIGN": "None",
    "PortScan": "Medium",
    "FTP-Patator": "High",
    "SSH-Patator": "High",
    "Web Attack - Brute Force": "High",
    "Web Attack - XSS": "High",
    "Web Attack - SQL Injection": "Critical",
    "DoS Hulk": "High",
    "DoS GoldenEye": "High",
    "DoS Slowloris": "High",
    "DoS SlowHTTPTest": "High",
    "Heartbleed": "Critical",
    "DDoS": "Critical",
    "Botnet": "Critical",
    "Infiltration": "Critical",
}

SEVERITY_TO_SCORE = {
    "None": 0.0,
    "Medium": 0.4,
    "High": 0.7,
    "Critical": 1.0,
}

W_SEVERITY = 0.5
W_CONFIDENCE = 0.3
W_FREQUENCY = 0.2

FREQUENCY_LOG_CAP = 10

PRIORITY_BUCKETS = [
    (80, "Critical"),
    (60, "High"),
    (40, "Medium"),
    (0, "Low"),
]


def severity_score(attack_type):
    label = SEVERITY_TABLE.get(attack_type, "Medium")
    return SEVERITY_TO_SCORE[label], label


def frequency_norm(count):
    capped = min(count, FREQUENCY_LOG_CAP)
    return np.log1p(capped) / np.log1p(FREQUENCY_LOG_CAP)


def bucket_priority(score):
    for threshold, label in PRIORITY_BUCKETS:
        if score >= threshold:
            return label
    return "Low"


class PriorityExplainerAgent:
    def __init__(self):
        print("[PriorityExplainerAgent] Loading Random Forest model for SHAP ...")
        self.rf = joblib.load(f"{MODEL_DIR}/random_forest_model.joblib")

        with open(f"{DATA_DIR}/feature_names.json") as f:
            self.feature_names = json.load(f)
        with open(f"{DATA_DIR}/label_mapping.json") as f:
            self.label_mapping = json.load(f)
        self.idx_to_name = {v: k for k, v in self.label_mapping.items()}

        print("[PriorityExplainerAgent] Loading knowledge base for severity lookups ...")
        with open(KNOWLEDGE_BASE_PATH) as f:
            knowledge_base = json.load(f)
        self.pattern_severity_by_name = {
            entry["name"]: entry.get("typical_severity", "Medium") for entry in knowledge_base
        }

        print("[PriorityExplainerAgent] Building SHAP TreeExplainer ...")
        self.explainer = shap.TreeExplainer(self.rf)

        print("[PriorityExplainerAgent] Ready.")

    def explain(self, feature_row, predicted_class, top_n=5):

        X = np.asarray(feature_row).reshape(1, -1)
        shap_values = self.explainer.shap_values(X)

        class_idx = self.label_mapping[predicted_class]

        if isinstance(shap_values, list):
            class_shap = shap_values[class_idx][0]
        elif shap_values.ndim == 3:
            class_shap = shap_values[0, :, class_idx]
        else:
            class_shap = shap_values[0]

        feature_impacts = list(zip(self.feature_names, class_shap))
        feature_impacts.sort(key=lambda x: abs(x[1]), reverse=True)

        return [
            {"feature": f, "shap_value": float(v)}
            for f, v in feature_impacts[:top_n]
        ]

    def score_alert(self, predicted_class, confidence, group_size,
                     matched_known_pattern=None):

        own_score, own_label = severity_score(predicted_class)

        if matched_known_pattern is not None:
            pattern_score = SEVERITY_TO_SCORE.get(
                matched_known_pattern.get("typical_severity", "Medium"), 0.4
            )
            effective_score = max(own_score, pattern_score)
        else:
            effective_score = own_score

        freq_score = frequency_norm(group_size)

        priority = 100 * (
            W_SEVERITY * effective_score
            + W_CONFIDENCE * confidence
            + W_FREQUENCY * freq_score
        )
        priority = round(min(priority, 100.0), 2)
        bucket = bucket_priority(priority)

        return {
            "priority_score": priority,
            "priority_bucket": bucket,
            "effective_severity_score": effective_score,
            "own_severity_label": own_label,
        }


def run_demo():
    print("Loading correlated alert stream ...")
    alerts_df = pd.read_csv(CORRELATED_ALERTS_PATH)
    print(f"  Loaded {len(alerts_df)} alerts")

    print("Loading X_test for SHAP lookups ...")
    X_test = np.load(f"{DATA_DIR}/X_test.npy")

    agent = PriorityExplainerAgent()

    group_sizes = alerts_df["correlation_group_id"].value_counts().to_dict()

    results = []
    for _, alert in alerts_df.iterrows():
        group_id = alert.get("correlation_group_id")
        group_size = group_sizes.get(group_id, 1) if pd.notna(group_id) else 1

        matched_pattern = None
        if pd.notna(alert.get("matched_known_pattern")):
            pattern_name = alert["matched_known_pattern"]
            matched_pattern = {
                "campaign_name": pattern_name,
                "typical_severity": agent.pattern_severity_by_name.get(pattern_name, "Medium"),
            }

        score_result = agent.score_alert(
            predicted_class=alert["predicted_class"],
            confidence=alert["confidence"],
            group_size=group_size,
            matched_known_pattern=matched_pattern,
        )

        row_idx = int(alert["row_index"])
        explanation = agent.explain(
            X_test[row_idx], alert["predicted_class"], top_n=5
        )

        results.append({
            **alert.to_dict(),
            **score_result,
            "top_contributing_features": json.dumps(explanation),
        })

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values("priority_score", ascending=False)

    print("\n--- Priority bucket distribution ---")
    print(results_df["priority_bucket"].value_counts())

    print("\n--- Top 5 highest-priority alerts ---")
    print(results_df[[
        "alert_id", "predicted_class", "confidence", "priority_score",
        "priority_bucket", "is_correlated_campaign"
    ]].head(5).to_string(index=False))

    print("\n--- Example explanation (top priority alert) ---")
    top_alert = results_df.iloc[0]
    print(f"Alert: {top_alert['alert_id']}  ({top_alert['predicted_class']})")
    for item in json.loads(top_alert["top_contributing_features"]):
        print(f"  {item['feature']:30s} SHAP={item['shap_value']:+.4f}")

    results_df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved prioritized alert stream to: {OUTPUT_PATH}")

    return results_df


if __name__ == "__main__":
    run_demo()
