"""
File location in project: utils/alert_simulator.py

Bridge component between the Detection Agent and the Correlation
Agent.

    python .\\utils\\alert_simulator.py
"""

import json
import os
import random
import sys
from datetime import datetime, timedelta

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents.detection_agent import DetectionAgent

import pandas as pd


DATA_DIR = "data/model_ready"
OUTPUT_PATH = "data/model_ready/simulated_alert_stream.csv"

RANDOM_STATE = 42
N_ALERTS_TO_SIMULATE = 2000
CAMPAIGN_FRACTION = 0.35
CAMPAIGN_LENGTH_RANGE = (2, 4)
CAMPAIGN_TIME_GAP_SECONDS = (10, 180)

KILL_CHAIN_STAGES = [
    ["PortScan"],
    ["FTP-Patator", "SSH-Patator", "Web Attack - Brute Force"],
    ["Infiltration", "Botnet", "DoS Hulk", "DDoS"],
]


def simulate_alert_stream():
    random.seed(RANDOM_STATE)
    np.random.seed(RANDOM_STATE)

    print("Loading Detection Agent and test data ...")

    X_test = np.load(f"{DATA_DIR}/X_test.npy")
    y_test = np.load(f"{DATA_DIR}/y_test.npy")
    with open(f"{DATA_DIR}/label_mapping.json") as f:
        label_mapping = json.load(f)
    idx_to_name = {v: k for k, v in label_mapping.items()}

    agent = DetectionAgent()

    sample_idx = np.random.choice(len(X_test), size=N_ALERTS_TO_SIMULATE, replace=False)
    X_sample = X_test[sample_idx]
    y_sample = y_test[sample_idx]

    print(f"Generating predictions for {N_ALERTS_TO_SIMULATE} sampled flows ...")
    mlp_probs = agent.mlp.predict(X_sample, verbose=0)
    rf_probs = agent.rf.predict_proba(X_sample)
    meta_X = np.hstack([mlp_probs, rf_probs])
    ensemble_probs = agent.meta_model.predict_proba(meta_X)

    predictions = []
    for i in range(N_ALERTS_TO_SIMULATE):
        pred_idx = int(np.argmax(ensemble_probs[i]))
        predictions.append({
            "row_index": int(sample_idx[i]),
            "true_class": idx_to_name[int(y_sample[i])],
            "predicted_class": idx_to_name[pred_idx],
            "confidence": float(ensemble_probs[i][pred_idx]),
        })

    attack_predictions = [p for p in predictions if p["predicted_class"] != "BENIGN"]
    print(f"  {len(attack_predictions)} of {N_ALERTS_TO_SIMULATE} predicted as attacks")

    alerts = []
    alert_id_counter = 1
    base_time = datetime(2026, 8, 12, 9, 0, 0)

    remaining = attack_predictions.copy()
    random.shuffle(remaining)

    n_campaign_alerts = int(len(remaining) * CAMPAIGN_FRACTION)
    campaign_pool = remaining[:n_campaign_alerts]
    isolated_pool = remaining[n_campaign_alerts:]

    campaign_counter = 1
    i = 0
    while i < len(campaign_pool):
        campaign_len = random.randint(*CAMPAIGN_LENGTH_RANGE)
        chunk = campaign_pool[i:i + campaign_len]
        i += campaign_len
        if not chunk:
            continue

        source_id = f"10.0.{random.randint(1,254)}.{random.randint(1,254)}"
        dest_id = f"192.168.{random.randint(1,254)}.{random.randint(1,254)}"
        campaign_id = f"CAMP-{campaign_counter:04d}"
        campaign_counter += 1

        current_time = base_time + timedelta(
            seconds=random.randint(0, 3600 * 6)
        )

        for pred in chunk:
            alerts.append({
                "alert_id": f"ALERT-{alert_id_counter:05d}",
                "row_index": pred["row_index"],
                "timestamp": current_time.isoformat(),
                "source_ip": source_id,
                "destination_ip": dest_id,
                "predicted_class": pred["predicted_class"],
                "true_class": pred["true_class"],
                "confidence": pred["confidence"],
                "simulated_campaign_id": campaign_id,
            })
            alert_id_counter += 1
            current_time += timedelta(
                seconds=random.randint(*CAMPAIGN_TIME_GAP_SECONDS)
            )

    for pred in isolated_pool:
        source_id = f"10.0.{random.randint(1,254)}.{random.randint(1,254)}"
        dest_id = f"192.168.{random.randint(1,254)}.{random.randint(1,254)}"
        alert_time = base_time + timedelta(seconds=random.randint(0, 3600 * 6))

        alerts.append({
            "alert_id": f"ALERT-{alert_id_counter:05d}",
            "row_index": pred["row_index"],
            "timestamp": alert_time.isoformat(),
            "source_ip": source_id,
            "destination_ip": dest_id,
            "predicted_class": pred["predicted_class"],
            "true_class": pred["true_class"],
            "confidence": pred["confidence"],
            "simulated_campaign_id": None,
        })
        alert_id_counter += 1

    alerts_df = pd.DataFrame(alerts).sort_values("timestamp").reset_index(drop=True)

    print(f"\nTotal simulated alerts: {len(alerts_df)}")
    print(f"  In simulated campaigns: {alerts_df['simulated_campaign_id'].notna().sum()}")
    print(f"  Isolated: {alerts_df['simulated_campaign_id'].isna().sum()}")
    print(f"  Unique simulated campaigns: {alerts_df['simulated_campaign_id'].nunique()}")

    alerts_df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved simulated alert stream to: {OUTPUT_PATH}")

    return alerts_df


if __name__ == "__main__":
    simulate_alert_stream()