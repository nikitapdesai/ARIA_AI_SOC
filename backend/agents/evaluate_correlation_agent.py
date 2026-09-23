"""
File location in project: agents/evaluate_correlation_agent.py
    python .\\agents\\evaluate_correlation_agent.py
"""

import pandas as pd
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    confusion_matrix, adjusted_rand_score,
)


CORRELATED_ALERTS_PATH = "data/model_ready/correlated_alert_stream.csv"


def evaluate():
    print(f"Loading {CORRELATED_ALERTS_PATH} ...")
    df = pd.read_csv(CORRELATED_ALERTS_PATH)
    print(f"  {len(df)} alerts loaded")

    y_true = df["simulated_campaign_id"].notna().astype(int)
    y_pred = df["is_correlated_campaign"].astype(bool).astype(int)

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    cm = confusion_matrix(y_true, y_pred)

    print("\n--- Binary campaign detection (is this alert part of a campaign?) ---")
    print(f"  Ground truth positives (simulated campaign members): {y_true.sum()}")
    print(f"  Predicted positives (flagged as correlated campaign): {y_pred.sum()}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1-score:  {f1:.4f}")
    print(f"\n  Confusion matrix:")
    print(f"                    Predicted: Not Campaign   Predicted: Campaign")
    print(f"  Actual: Not Campaign      {cm[0][0]:>10}              {cm[0][1]:>10}")
    print(f"  Actual: Campaign          {cm[1][0]:>10}              {cm[1][1]:>10}")

    df["_true_group"] = df["simulated_campaign_id"].fillna(
        pd.Series([f"ISOLATED_TRUE_{i}" for i in df.index], index=df.index)
    )
    df["_pred_group"] = df["correlation_group_id"].fillna(
        pd.Series([f"ISOLATED_PRED_{i}" for i in df.index], index=df.index)
    )

    ari = adjusted_rand_score(df["_true_group"], df["_pred_group"])

    print(f"\n--- Clustering quality ---")
    print(f"  Adjusted Rand Index (grouping agreement): {ari:.4f}")
    print(f"  (1.0 = perfect agreement with ground-truth groupings, "
          f"0.0 = random chance level)")

    print(f"\n--- Per-campaign detection breakdown ---")
    true_campaigns = df[df["simulated_campaign_id"].notna()].groupby("simulated_campaign_id")

    fully_detected = 0
    partially_detected = 0
    missed = 0

    for camp_id, camp_alerts in true_campaigns:
        pred_groups_in_campaign = camp_alerts["correlation_group_id"].dropna().unique()
        flagged_as_campaign = camp_alerts["is_correlated_campaign"].any()

        if not flagged_as_campaign:
            missed += 1
        elif len(pred_groups_in_campaign) == 1 and camp_alerts["is_correlated_campaign"].all():
            fully_detected += 1
        else:
            partially_detected += 1

    total_true_campaigns = len(true_campaigns)
    print(f"  Total true simulated campaigns: {total_true_campaigns}")
    print(f"  Fully detected as one coherent group: {fully_detected}")
    print(f"  Partially detected (some alerts missed/split): {partially_detected}")
    print(f"  Completely missed: {missed}")

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "ari": ari,
        "fully_detected": fully_detected,
        "partially_detected": partially_detected,
        "missed": missed,
        "total_true_campaigns": total_true_campaigns,
    }


if __name__ == "__main__":
    evaluate()