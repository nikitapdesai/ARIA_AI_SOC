"""
File location in project: api/state.py
"""

import json
import os

from agents.detection_agent import DetectionAgent

import numpy as np
import pandas as pd

from agents.correlation_agent import CorrelationAgent
from agents.escalation_agent import EscalationAgent
from agents.priority_explainer_agent import PriorityExplainerAgent
from agents.graph_pipeline import build_graph

DATA_DIR = "data/model_ready"
PRIORITIZED_ALERTS_PATH = f"{DATA_DIR}/prioritized_alert_stream.csv"
CORRELATED_ALERTS_PATH = f"{DATA_DIR}/correlated_alert_stream.csv"
INCIDENT_LOG_PATH = "data/escalation/incident_log.json"
KNOWLEDGE_BASE_PATH = "knowledge_base/known_campaigns.json"


class AppState:
    """Loaded once at API startup, stored on app.state.aria."""

    def __init__(self):
        print("[api] Loading Detection Agent ...")
        self.detection_agent = DetectionAgent()

        print("[api] Loading Correlation Agent ...")
        self.correlation_agent = CorrelationAgent()

        print("[api] Loading Priority-Explainer Agent ...")
        self.priority_agent = PriorityExplainerAgent()

        print("[api] Loading Escalation Agent ...")
        self.escalation_agent = EscalationAgent()

        with open(f"{DATA_DIR}/label_mapping.json") as f:
            self.label_mapping = json.load(f)
        self.idx_to_name = {v: k for k, v in self.label_mapping.items()}

        print("[api] Loading X_test / y_test for live analysis ...")
        self.X_test = np.load(f"{DATA_DIR}/X_test.npy")
        self.y_test = np.load(f"{DATA_DIR}/y_test.npy")

        print("[api] Building LangGraph pipeline (live analysis) ...")
        self.graph = build_graph(self)

        print("[api] Ready.")


    def load_prioritized_alerts(self) -> pd.DataFrame:
        if not os.path.exists(PRIORITIZED_ALERTS_PATH):
            return pd.DataFrame()
        df = pd.read_csv(PRIORITIZED_ALERTS_PATH)
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed")
        return df

    def load_incident_log(self) -> list:
        if not os.path.exists(INCIDENT_LOG_PATH):
            return []
        with open(INCIDENT_LOG_PATH) as f:
            return json.load(f)

    def load_knowledge_base(self) -> list:
        if not os.path.exists(KNOWLEDGE_BASE_PATH):
            return []
        with open(KNOWLEDGE_BASE_PATH) as f:
            return json.load(f)
