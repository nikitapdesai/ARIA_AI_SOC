"""
File location in project: agents/correlation_agent.py
Correlation Agent -- Agent 2 of 4 in the SOC Alert Prioritizer pipeline.
    python .\\agents\\correlation_agent.py
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime

import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

KNOWLEDGE_BASE_DIR = "knowledge_base"
KNOWN_CAMPAIGNS_PATH = f"{KNOWLEDGE_BASE_DIR}/known_campaigns.json"
ALERT_STREAM_PATH = "data/model_ready/simulated_alert_stream.csv"

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

TIME_WINDOW_MINUTES = 30
MIN_GROUP_SIZE_FOR_CAMPAIGN = 2

KILL_CHAIN_STAGES = {
    "reconnaissance": ["PortScan"],
    "credential_access": ["FTP-Patator", "SSH-Patator", "Web Attack - Brute Force"],
    "impact": ["Infiltration", "Botnet", "DoS Hulk", "DoS GoldenEye", "DoS Slowloris",
               "DoS SlowHTTPTest", "DDoS", "Heartbleed", "Web Attack - XSS",
               "Web Attack - SQL Injection"],
}


def attack_to_stage(attack_type):
    for stage, types in KILL_CHAIN_STAGES.items():
        if attack_type in types:
            return stage
    return "unknown"


class CorrelationAgent:
    def __init__(self):
        print("[CorrelationAgent] Loading embedding model ...")
        self.embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)

        print("[CorrelationAgent] Loading known campaign knowledge base ...")
        with open(KNOWN_CAMPAIGNS_PATH) as f:
            self.known_campaigns = json.load(f)

        self._build_faiss_index()
        print("[CorrelationAgent] Ready.")

    def _build_faiss_index(self):
        descriptions = [c["description"] for c in self.known_campaigns]
        embeddings = self.embedder.encode(descriptions, normalize_embeddings=True)
        embeddings = np.asarray(embeddings, dtype="float32")

        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)
        self.embedding_dim = dim

    def _describe_alert(self, alert_row):

        return f"{alert_row['predicted_class']} attack detected with confidence {alert_row['confidence']:.2f}"

    def _describe_group(self, group_df):

        sequence = " then ".join(group_df.sort_values("timestamp")["predicted_class"].tolist())
        return f"Sequence of attacks from same source: {sequence}"

    def retrieve_similar_known_pattern(self, description, top_k=1):
        query_embedding = self.embedder.encode([description], normalize_embeddings=True)
        query_embedding = np.asarray(query_embedding, dtype="float32")

        similarities, indices = self.index.search(query_embedding, top_k)

        results = []
        for sim, idx in zip(similarities[0], indices[0]):
            if idx == -1:
                continue
            match = self.known_campaigns[idx]
            results.append({
                "campaign_name": match["name"],
                "similarity": float(sim),
                "typical_severity": match["typical_severity"],
                "mitre_tactics": match.get("mitre_tactics", []),
            })
        return results

    def correlate(self, alerts_df):

        df = alerts_df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        df["correlation_group_id"] = None
        df["is_correlated_campaign"] = False
        df["kill_chain_stages_seen"] = None
        df["matched_known_pattern"] = None
        df["matched_pattern_similarity"] = None

        group_counter = 1

        for source_ip, source_group in df.groupby("source_ip"):
            source_group = source_group.sort_values("timestamp")

            if len(source_group) < MIN_GROUP_SIZE_FOR_CAMPAIGN:
                continue

            cluster_start_time = None
            current_cluster_indices = []
            clusters = []

            for idx, row in source_group.iterrows():
                if cluster_start_time is None:
                    cluster_start_time = row["timestamp"]
                    current_cluster_indices = [idx]
                    continue

                gap_minutes = (row["timestamp"] - cluster_start_time).total_seconds() / 60.0
                if gap_minutes <= TIME_WINDOW_MINUTES:
                    current_cluster_indices.append(idx)
                else:
                    clusters.append(current_cluster_indices)
                    cluster_start_time = row["timestamp"]
                    current_cluster_indices = [idx]

            if current_cluster_indices:
                clusters.append(current_cluster_indices)

            for cluster_indices in clusters:
                if len(cluster_indices) < MIN_GROUP_SIZE_FOR_CAMPAIGN:
                    continue

                group_df = df.loc[cluster_indices]
                stages_seen = sorted(set(
                    attack_to_stage(t) for t in group_df["predicted_class"]
                ))

                is_campaign = len(stages_seen) >= 2

                group_id = f"CORR-{group_counter:04d}"
                group_counter += 1

                df.loc[cluster_indices, "correlation_group_id"] = group_id
                df.loc[cluster_indices, "is_correlated_campaign"] = is_campaign
                df.loc[cluster_indices, "kill_chain_stages_seen"] = ", ".join(stages_seen)

                if is_campaign:
                    description = self._describe_group(group_df)
                    matches = self.retrieve_similar_known_pattern(description, top_k=1)
                    if matches:
                        df.loc[cluster_indices, "matched_known_pattern"] = matches[0]["campaign_name"]
                        df.loc[cluster_indices, "matched_pattern_similarity"] = matches[0]["similarity"]

        return df


def run_demo():
    print("Loading simulated alert stream ...")
    alerts_df = pd.read_csv(ALERT_STREAM_PATH)
    print(f"  Loaded {len(alerts_df)} alerts")

    agent = CorrelationAgent()

    print("\nRunning correlation ...")
    correlated_df = agent.correlate(alerts_df)

    n_campaigns = correlated_df[correlated_df["is_correlated_campaign"]]["correlation_group_id"].nunique()
    n_campaign_alerts = correlated_df["is_correlated_campaign"].sum()

    print(f"\nCorrelated campaigns detected: {n_campaigns}")
    print(f"Alerts flagged as part of a campaign: {n_campaign_alerts} / {len(correlated_df)}")

    print("\n--- Sample correlated campaign ---")
    campaign_ids = correlated_df[correlated_df["is_correlated_campaign"]]["correlation_group_id"].unique()
    if len(campaign_ids) > 0:
        sample_group = correlated_df[correlated_df["correlation_group_id"] == campaign_ids[0]]
        print(sample_group[[
            "alert_id", "timestamp", "source_ip", "predicted_class",
            "confidence", "kill_chain_stages_seen", "matched_known_pattern",
            "matched_pattern_similarity"
        ]].to_string(index=False))

    output_path = "data/model_ready/correlated_alert_stream.csv"
    correlated_df.to_csv(output_path, index=False)
    print(f"\nSaved correlated alert stream to: {output_path}")

    return correlated_df


if __name__ == "__main__":
    run_demo()