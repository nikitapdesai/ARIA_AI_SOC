"""
File location in project: agents/escalation_agent.py

Escalation Agent -- Agent 4 of 4 in the SOC Alert Prioritizer
pipeline.
    python .\\agents\\escalation_agent.py
"""

import json
import os
import sys
from datetime import datetime

import pandas as pd
from sentence_transformers import SentenceTransformer, util


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DATA_DIR = "data/model_ready"
PRIORITIZED_ALERTS_PATH = f"{DATA_DIR}/prioritized_alert_stream.csv"

KNOWLEDGE_BASE_PATH = "knowledge_base/known_campaigns.json"
INCIDENT_LOG_DIR = "data/escalation"
INCIDENT_LOG_PATH = f"{INCIDENT_LOG_DIR}/incident_log.json"

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

NOVELTY_THRESHOLD = 0.85


def should_escalate(priority_bucket, is_correlated_campaign):
    return priority_bucket == "Critical" or bool(is_correlated_campaign)


STAGE_TO_MITRE = {
    "reconnaissance": "TA0043 Reconnaissance",
    "credential_access": "TA0006 Credential Access",
    "impact": "TA0040 Impact",
}


class EscalationAgent:
    def __init__(self):
        print("[EscalationAgent] Loading embedding model (for novelty checks) ...")
        self.embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)

        print("[EscalationAgent] Loading knowledge base ...")
        with open(KNOWLEDGE_BASE_PATH) as f:
            self.knowledge_base = json.load(f)
        self._refresh_kb_embeddings()

        print("[EscalationAgent] Loading existing incident log (if any) ...")
        os.makedirs(INCIDENT_LOG_DIR, exist_ok=True)
        if os.path.exists(INCIDENT_LOG_PATH):
            with open(INCIDENT_LOG_PATH) as f:
                self.incident_log = json.load(f)
        else:
            self.incident_log = []

        self.next_incident_id = len(self.incident_log) + 1
        print(f"[EscalationAgent] Ready. {len(self.incident_log)} existing incidents loaded, "
              f"{len(self.knowledge_base)} known patterns loaded.")

    def _refresh_kb_embeddings(self):

        descriptions = [c["description"] for c in self.knowledge_base]
        if descriptions:
            self.kb_embeddings = self.embedder.encode(descriptions, convert_to_tensor=True)
        else:
            self.kb_embeddings = None

    def check_novelty(self, description):
        if self.kb_embeddings is None:
            return True, 0.0, None

        query_embedding = self.embedder.encode(description, convert_to_tensor=True)
        similarities = util.cos_sim(query_embedding, self.kb_embeddings)[0]

        best_idx = int(similarities.argmax())
        best_sim = float(similarities[best_idx])
        best_name = self.knowledge_base[best_idx]["name"]

        is_novel = best_sim < NOVELTY_THRESHOLD
        return is_novel, best_sim, best_name

    def add_learned_pattern(self, description, stages_seen, severity_label):
        mitre_tactics = [
            STAGE_TO_MITRE[s] for s in stages_seen if s in STAGE_TO_MITRE
        ]
        new_entry = {
            "name": f"Learned Pattern - {' + '.join(stages_seen)}",
            "description": description,
            "typical_severity": severity_label,
            "mitre_tactics": mitre_tactics,
            "learned_at": datetime.now().isoformat(),
            "source": "escalation_agent_auto_learned",
        }
        self.knowledge_base.append(new_entry)
        self._refresh_kb_embeddings()

        with open(KNOWLEDGE_BASE_PATH, "w") as f:
            json.dump(self.knowledge_base, f, indent=2)

        print(f"  [KB GROWTH] Added new pattern: '{new_entry['name']}'")
        return new_entry

    def log_incident(self, incident_type, alerts, extra_fields=None):
        incident = {
            "incident_id": f"INC-{self.next_incident_id:05d}",
            "logged_at": datetime.now().isoformat(),
            "incident_type": incident_type,
            "alert_ids": alerts["alert_id"].tolist() if hasattr(alerts, "columns") else [alerts["alert_id"]],
            "predicted_classes": (
                alerts["predicted_class"].tolist() if hasattr(alerts, "columns")
                else [alerts["predicted_class"]]
            ),
            "source_ip": (
                alerts["source_ip"].iloc[0] if hasattr(alerts, "columns")
                else alerts["source_ip"]
            ),
            "max_priority_score": (
                float(alerts["priority_score"].max()) if hasattr(alerts, "columns")
                else float(alerts["priority_score"])
            ),
        }
        if extra_fields:
            incident.update(extra_fields)

        self.incident_log.append(incident)
        self.next_incident_id += 1
        return incident

    def process(self, prioritized_df):
        print("\n--- Processing alerts for escalation ---")

        escalated_isolated = 0
        escalated_campaigns = 0
        new_patterns_learned = 0

        campaign_groups = prioritized_df[
            prioritized_df["is_correlated_campaign"] == True
        ].groupby("correlation_group_id")

        for group_id, group_df in campaign_groups:
            if not should_escalate(group_df["priority_bucket"].iloc[0], True):
                continue

            stages_str = group_df["kill_chain_stages_seen"].iloc[0]
            stages_seen = [s.strip() for s in str(stages_str).split(",")] if pd.notna(stages_str) else []

            matched_pattern = group_df["matched_known_pattern"].iloc[0]
            matched_similarity = group_df["matched_pattern_similarity"].iloc[0]

            sequence = " then ".join(group_df.sort_values("timestamp")["predicted_class"].tolist())
            description = f"Sequence of attacks from same source: {sequence}"

            is_novel, best_sim, best_match_name = self.check_novelty(description)

            learned_pattern = None
            if is_novel:
                severity_label = group_df["own_severity_label"].mode().iloc[0]
                learned_pattern = self.add_learned_pattern(description, stages_seen, severity_label)
                new_patterns_learned += 1

            self.log_incident(
                incident_type="correlated_campaign",
                alerts=group_df,
                extra_fields={
                    "correlation_group_id": group_id,
                    "kill_chain_stages_seen": stages_str,
                    "matched_known_pattern_at_detection_time": matched_pattern,
                    "matched_similarity_at_detection_time": (
                        float(matched_similarity) if pd.notna(matched_similarity) else None
                    ),
                    "novelty_check_best_similarity": best_sim,
                    "novelty_check_best_match": best_match_name,
                    "new_pattern_learned": learned_pattern["name"] if learned_pattern else None,
                },
            )
            escalated_campaigns += 1

        isolated_critical = prioritized_df[
            (prioritized_df["is_correlated_campaign"] != True)
            & (prioritized_df["priority_bucket"] == "Critical")
        ]

        for _, alert in isolated_critical.iterrows():
            self.log_incident(incident_type="isolated_critical", alerts=alert)
            escalated_isolated += 1

        with open(INCIDENT_LOG_PATH, "w") as f:
            json.dump(self.incident_log, f, indent=2)

        print(f"\nEscalated correlated campaigns: {escalated_campaigns}")
        print(f"Escalated isolated critical alerts: {escalated_isolated}")
        print(f"New patterns learned into knowledge base: {new_patterns_learned}")
        print(f"Total incidents in log (all-time): {len(self.incident_log)}")
        print(f"\nSaved incident log to: {INCIDENT_LOG_PATH}")
        print(f"Knowledge base now has {len(self.knowledge_base)} total patterns.")


def run_demo():
    print("Loading prioritized alert stream ...")
    prioritized_df = pd.read_csv(PRIORITIZED_ALERTS_PATH)
    print(f"  Loaded {len(prioritized_df)} alerts")

    agent = EscalationAgent()
    agent.process(prioritized_df)


if __name__ == "__main__":
    run_demo()