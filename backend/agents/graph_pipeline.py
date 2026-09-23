"""
File location in project: agents/graph_pipeline.py
    python -m agents.graph_pipeline
"""

import os
import random
import sqlite3
import uuid
from datetime import datetime
from typing import Optional, TypedDict

import agents.detection_agent

import numpy as np
import pandas as pd
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from langgraph.checkpoint.sqlite import SqliteSaver
from langsmith import traceable

GRAPH_CHECKPOINT_DIR = "data/escalation"
GRAPH_CHECKPOINT_PATH = f"{GRAPH_CHECKPOINT_DIR}/graph_checkpoints.sqlite"


def _random_synthetic_ip(prefix: str) -> str:
    return f"{prefix}.{random.randint(1, 254)}.{random.randint(1, 254)}"


class AriaState(TypedDict, total=False):
    row_index: int
    source_ip: Optional[str]
    commit: bool

    alert_id: str
    destination_ip: str
    timestamp: str
    history_sequence: list

    predicted_class: str
    confidence: float
    class_probabilities: dict

    is_correlated_campaign: bool
    correlation_group_id: Optional[str]
    group_size: int
    kill_chain_stages_seen: Optional[str]
    matched_known_pattern: Optional[str]
    matched_pattern_similarity: Optional[float]

    priority: dict
    explanation: list

    description: str
    is_novel: bool
    best_similarity: float
    best_match_name: Optional[str]
    should_escalate: bool

    human_approved: Optional[bool]


def build_graph(app_state):

    @traceable(name="detect", run_type="chain")
    def detect_node(s: AriaState) -> dict:
        X_row = app_state.X_test[s["row_index"]: s["row_index"] + 1]
        mlp_probs = app_state.detection_agent.mlp.predict(X_row, verbose=0)
        rf_probs = app_state.detection_agent.rf.predict_proba(X_row)
        meta_X = np.hstack([mlp_probs, rf_probs])
        ensemble_probs = app_state.detection_agent.meta_model.predict_proba(meta_X)[0]

        predicted_idx = int(np.argmax(ensemble_probs))
        predicted_class = app_state.idx_to_name[predicted_idx]
        confidence = float(ensemble_probs[predicted_idx])

        alert_id = f"LIVE-{uuid.uuid4().hex[:8]}"
        resolved_source_ip = s.get("source_ip") or _random_synthetic_ip("10.0")
        destination_ip = _random_synthetic_ip("192.168")

        return {
            "alert_id": alert_id,
            "source_ip": resolved_source_ip,
            "destination_ip": destination_ip,
            "predicted_class": predicted_class,
            "confidence": confidence,
            "class_probabilities": {
                app_state.idx_to_name[i]: float(p) for i, p in enumerate(ensemble_probs)
            },
        }

    @traceable(name="correlate", run_type="chain")
    def correlate_node(s: AriaState) -> dict:
        from api.state import CORRELATED_ALERTS_PATH

        history_df = pd.DataFrame()
        if os.path.exists(CORRELATED_ALERTS_PATH):
            history_df = pd.read_csv(CORRELATED_ALERTS_PATH)
            history_df["timestamp"] = pd.to_datetime(history_df["timestamp"], format="mixed")
            history_df = history_df[history_df["source_ip"] == s["source_ip"]].tail(10)

        if not history_df.empty:
            now = history_df["timestamp"].max() + pd.Timedelta(seconds=random.randint(10, 180))
        else:
            now = datetime.now()

        new_row = {
            "alert_id": s["alert_id"],
            "row_index": s["row_index"],
            "timestamp": now,
            "source_ip": s["source_ip"],
            "predicted_class": s["predicted_class"],
            "confidence": s["confidence"],
        }

        combined = pd.concat(
            [history_df[["alert_id", "timestamp", "source_ip", "predicted_class", "confidence"]],
             pd.DataFrame([new_row])],
            ignore_index=True,
        ) if not history_df.empty else pd.DataFrame([new_row])

        correlated = app_state.correlation_agent.correlate(combined)
        row = correlated[correlated["alert_id"] == s["alert_id"]].iloc[0]

        is_campaign = bool(row["is_correlated_campaign"])
        group_id = row["correlation_group_id"]
        group_size = (
            int((correlated["correlation_group_id"] == group_id).sum())
            if pd.notna(group_id) else 1
        )

        return {
            "timestamp": now.isoformat(),
            "history_sequence": combined.sort_values("timestamp")["predicted_class"].tolist(),
            "is_correlated_campaign": is_campaign,
            "correlation_group_id": group_id if pd.notna(group_id) else None,
            "group_size": group_size,
            "kill_chain_stages_seen": row["kill_chain_stages_seen"] if pd.notna(row["kill_chain_stages_seen"]) else None,
            "matched_known_pattern": row["matched_known_pattern"] if pd.notna(row["matched_known_pattern"]) else None,
            "matched_pattern_similarity": (
                float(row["matched_pattern_similarity"]) if pd.notna(row["matched_pattern_similarity"]) else None
            ),
        }

    @traceable(name="prioritize_explain", run_type="chain")
    def prioritize_node(s: AriaState) -> dict:
        matched_pattern = None
        if s.get("matched_known_pattern"):
            matched_pattern = {
                "campaign_name": s["matched_known_pattern"],
                "typical_severity": app_state.priority_agent.pattern_severity_by_name.get(
                    s["matched_known_pattern"], "Medium"
                ),
            }

        score = app_state.priority_agent.score_alert(
            predicted_class=s["predicted_class"],
            confidence=s["confidence"],
            group_size=s["group_size"],
            matched_known_pattern=matched_pattern,
        )
        score = {k: (float(v) if isinstance(v, np.floating) else v) for k, v in score.items()}

        explanation = app_state.priority_agent.explain(
            app_state.X_test[s["row_index"]], s["predicted_class"], top_n=5
        )
        return {"priority": score, "explanation": explanation}

    @traceable(name="novelty_check", run_type="chain")
    def novelty_node(s: AriaState) -> dict:
        description = (
            f"{s['predicted_class']} attack detected with confidence {s['confidence']:.2f}"
            if not s["is_correlated_campaign"]
            else f"Sequence of attacks from same source: {' then '.join(s['history_sequence'])}"
        )
        is_novel, best_sim, best_match = app_state.escalation_agent.check_novelty(description)
        should_escalate = s["priority"]["priority_bucket"] == "Critical" or s["is_correlated_campaign"]

        return {
            "description": description,
            "is_novel": is_novel,
            "best_similarity": best_sim,
            "best_match_name": best_match,
            "should_escalate": should_escalate,
        }

    def review_node(s: AriaState) -> dict:
        decision = interrupt({
            "reason": "novel_campaign_pattern",
            "alert_id": s["alert_id"],
            "predicted_class": s["predicted_class"],
            "description": s["description"],
            "best_existing_match": s["best_match_name"],
            "similarity": s["best_similarity"],
        })
        return {"human_approved": bool(decision.get("approved", False))}

    @traceable(name="kb_update", run_type="chain")
    def kb_update_node(s: AriaState) -> dict:
        stages = s["kill_chain_stages_seen"].split(", ") if s.get("kill_chain_stages_seen") else []
        app_state.escalation_agent.add_learned_pattern(
            s["description"], stages, s["priority"]["own_severity_label"]
        )
        return {}

    @traceable(name="log_incident", run_type="chain")
    def log_incident_node(s: AriaState) -> dict:
        from api.state import INCIDENT_LOG_PATH
        import json

        alert_series = pd.Series({
            "alert_id": s["alert_id"],
            "predicted_class": s["predicted_class"],
            "source_ip": s["source_ip"],
            "priority_score": s["priority"]["priority_score"],
        })
        app_state.escalation_agent.log_incident(
            incident_type="correlated_campaign" if s["is_correlated_campaign"] else "isolated_critical",
            alerts=alert_series,
        )
        with open(INCIDENT_LOG_PATH, "w") as f:
            json.dump(app_state.escalation_agent.incident_log, f, indent=2)
        return {}

    def route_after_novelty(s: AriaState):
        if not s.get("commit") or not s["should_escalate"]:
            return END
        return "review" if s["is_novel"] else "log_incident"

    def route_after_review(s: AriaState):
        return "kb_update" if s.get("human_approved") else "log_incident"

    g = StateGraph(AriaState)
    g.add_node("detect", detect_node)
    g.add_node("correlate", correlate_node)
    g.add_node("prioritize_explain", prioritize_node)
    g.add_node("novelty_check", novelty_node)
    g.add_node("review", review_node)
    g.add_node("kb_update", kb_update_node)
    g.add_node("log_incident", log_incident_node)

    g.add_edge(START, "detect")
    g.add_edge("detect", "correlate")
    g.add_edge("correlate", "prioritize_explain")
    g.add_edge("prioritize_explain", "novelty_check")
    g.add_conditional_edges("novelty_check", route_after_novelty, ["review", "log_incident", END])
    g.add_conditional_edges("review", route_after_review, ["kb_update", "log_incident"])
    g.add_edge("kb_update", "log_incident")
    g.add_edge("log_incident", END)

    os.makedirs(GRAPH_CHECKPOINT_DIR, exist_ok=True)
    conn = sqlite3.connect(GRAPH_CHECKPOINT_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    return g.compile(checkpointer=checkpointer)


def result_from_state(state_values: dict) -> dict:
    """Shapes a completed (non-interrupted) graph state back into the
    same response shape api/routers/live.py's callers already expect."""
    return {
        "alert_id": state_values["alert_id"],
        "row_index": state_values["row_index"],
        "timestamp": state_values["timestamp"],
        "source_ip": state_values["source_ip"],
        "destination_ip": state_values["destination_ip"],
        "detection": {
            "predicted_class": state_values["predicted_class"],
            "confidence": state_values["confidence"],
            "class_probabilities": state_values["class_probabilities"],
        },
        "correlation": {
            "is_correlated_campaign": state_values["is_correlated_campaign"],
            "correlation_group_id": state_values.get("correlation_group_id"),
            "group_size": state_values["group_size"],
            "kill_chain_stages_seen": state_values.get("kill_chain_stages_seen"),
            "matched_known_pattern": state_values.get("matched_known_pattern"),
            "matched_pattern_similarity": state_values.get("matched_pattern_similarity"),
        },
        "priority": state_values["priority"],
        "explanation": state_values["explanation"],
        "escalation": {
            "should_escalate": state_values["should_escalate"],
            "is_novel_pattern": state_values["is_novel"],
            "novelty_best_similarity": state_values["best_similarity"],
            "novelty_best_match": state_values["best_match_name"],
            "human_approved": state_values.get("human_approved"),
        },
    }


if __name__ == "__main__":
    print("Building graph pipeline (loading all 4 agents) ...")
    from api.state import AppState

    app_state = AppState()
    graph = build_graph(app_state)

    row_index = random.randint(0, len(app_state.X_test) - 1)
    config = {"configurable": {"thread_id": f"smoke-test-{uuid.uuid4().hex[:8]}"}}

    result = graph.invoke({"row_index": row_index, "source_ip": None, "commit": False}, config=config)

    if "__interrupt__" in result:
        print("\nGraph paused for human review:")
        print(result["__interrupt__"])
        print("\nResuming with approved=True ...")
        from langgraph.types import Command
        result = graph.invoke(Command(resume={"approved": True}), config=config)

    print("\nFinal state:")
    for k, v in result_from_state(result).items():
        print(f"  {k}: {v}")
