"""
File location in project: api/routers/live.py
"""

import asyncio
import json
import random
import uuid
from datetime import datetime

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langgraph.types import Command

import os

from agents.graph_pipeline import result_from_state
from api.schemas import LiveAnalyzeRequest, LiveReviewRequest
from api.state import CORRELATED_ALERTS_PATH, PRIORITIZED_ALERTS_PATH

router = APIRouter(prefix="/api/live", tags=["live"])


def _random_synthetic_ip(prefix: str) -> str:
    return f"{prefix}.{random.randint(1, 254)}.{random.randint(1, 254)}"


def _run_live_analysis(state, row_index: int | None, source_ip: str | None) -> dict:
    n_rows = len(state.X_test)
    if row_index is None:
        row_index = random.randint(0, n_rows - 1)
    elif not (0 <= row_index < n_rows):
        raise HTTPException(status_code=400, detail=f"row_index must be in [0, {n_rows})")

    X_row = state.X_test[row_index : row_index + 1]

    mlp_probs = state.detection_agent.mlp.predict(X_row, verbose=0)
    rf_probs = state.detection_agent.rf.predict_proba(X_row)
    meta_X = np.hstack([mlp_probs, rf_probs])
    ensemble_probs = state.detection_agent.meta_model.predict_proba(meta_X)[0]

    predicted_idx = int(np.argmax(ensemble_probs))
    predicted_class = state.idx_to_name[predicted_idx]
    confidence = float(ensemble_probs[predicted_idx])
    class_probabilities = {
        state.idx_to_name[i]: float(p) for i, p in enumerate(ensemble_probs)
    }

    alert_id = f"LIVE-{uuid.uuid4().hex[:8]}"
    resolved_source_ip = source_ip or _random_synthetic_ip("10.0")
    destination_ip = _random_synthetic_ip("192.168")

    history_df = pd.DataFrame()
    if os.path.exists(CORRELATED_ALERTS_PATH):
        history_df = pd.read_csv(CORRELATED_ALERTS_PATH)
        history_df["timestamp"] = pd.to_datetime(history_df["timestamp"], format="mixed")
        history_df = history_df[history_df["source_ip"] == resolved_source_ip].tail(10)

    if not history_df.empty:
        now = history_df["timestamp"].max() + pd.Timedelta(seconds=random.randint(10, 180))
    else:
        now = datetime.now()

    new_row = {
        "alert_id": alert_id,
        "row_index": row_index,
        "timestamp": now,
        "source_ip": resolved_source_ip,
        "destination_ip": destination_ip,
        "predicted_class": predicted_class,
        "confidence": confidence,
    }

    combined = pd.concat(
        [history_df[["alert_id", "timestamp", "source_ip", "predicted_class", "confidence"]], pd.DataFrame([new_row])],
        ignore_index=True,
    ) if not history_df.empty else pd.DataFrame([new_row])

    correlated = state.correlation_agent.correlate(combined)
    new_alert_row = correlated[correlated["alert_id"] == alert_id].iloc[0]

    is_correlated_campaign = bool(new_alert_row["is_correlated_campaign"])
    correlation_group_id = new_alert_row["correlation_group_id"]
    kill_chain_stages_seen = new_alert_row["kill_chain_stages_seen"]
    matched_known_pattern_name = new_alert_row["matched_known_pattern"]
    matched_pattern_similarity = new_alert_row["matched_pattern_similarity"]

    group_size = (
        int((correlated["correlation_group_id"] == correlation_group_id).sum())
        if pd.notna(correlation_group_id) else 1
    )

    matched_pattern = None
    if pd.notna(matched_known_pattern_name):
        matched_pattern = {
            "campaign_name": matched_known_pattern_name,
            "typical_severity": state.priority_agent.pattern_severity_by_name.get(
                matched_known_pattern_name, "Medium"
            ),
        }

    score_result = state.priority_agent.score_alert(
        predicted_class=predicted_class,
        confidence=confidence,
        group_size=group_size,
        matched_known_pattern=matched_pattern,
    )
    explanation = state.priority_agent.explain(state.X_test[row_index], predicted_class, top_n=5)

    description = (
        f"{predicted_class} attack detected with confidence {confidence:.2f}"
        if not is_correlated_campaign
        else f"Sequence of attacks from same source: {' then '.join(combined.sort_values('timestamp')['predicted_class'].tolist())}"
    )
    is_novel, best_similarity, best_match_name = state.escalation_agent.check_novelty(description)
    should_escalate = score_result["priority_bucket"] == "Critical" or is_correlated_campaign

    return {
        "alert_id": alert_id,
        "row_index": row_index,
        "timestamp": now.isoformat(),
        "source_ip": resolved_source_ip,
        "destination_ip": destination_ip,
        "detection": {
            "predicted_class": predicted_class,
            "confidence": confidence,
            "class_probabilities": class_probabilities,
        },
        "correlation": {
            "is_correlated_campaign": is_correlated_campaign,
            "correlation_group_id": correlation_group_id if pd.notna(correlation_group_id) else None,
            "group_size": group_size,
            "kill_chain_stages_seen": kill_chain_stages_seen if pd.notna(kill_chain_stages_seen) else None,
            "matched_known_pattern": matched_known_pattern_name if pd.notna(matched_known_pattern_name) else None,
            "matched_pattern_similarity": (
                float(matched_pattern_similarity) if pd.notna(matched_pattern_similarity) else None
            ),
        },
        "priority": score_result,
        "explanation": explanation,
        "escalation": {
            "should_escalate": should_escalate,
            "is_novel_pattern": is_novel,
            "novelty_best_similarity": best_similarity,
            "novelty_best_match": best_match_name,
        },
    }


@router.post("/analyze")
def analyze_live(payload: LiveAnalyzeRequest, request: Request):
    state = request.app.state.aria

    n_rows = len(state.X_test)
    row_index = payload.row_index
    if row_index is None:
        row_index = random.randint(0, n_rows - 1)
    elif not (0 <= row_index < n_rows):
        raise HTTPException(status_code=400, detail=f"row_index must be in [0, {n_rows})")

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    graph_result = state.graph.invoke(
        {"row_index": row_index, "source_ip": payload.source_ip, "commit": payload.commit},
        config=config,
    )

    result = result_from_state(graph_result)

    if payload.commit:
        _persist_alert_row(state, result)

    if "__interrupt__" in graph_result:
        return {"status": "pending_review", "thread_id": thread_id, **result}

    return {"status": "complete", "thread_id": thread_id, **result}


@router.post("/review/{thread_id}")
def submit_review(thread_id: str, payload: LiveReviewRequest, request: Request):
    """Resumes a graph run that paused at the human-review checkpoint
    (see agents/graph_pipeline.py's review_node) with the analyst's
    approve/reject decision. Approving writes the new pattern into
    knowledge_base/known_campaigns.json; either way, the incident
    itself still gets logged."""
    state = request.app.state.aria
    config = {"configurable": {"thread_id": thread_id}}

    snapshot = state.graph.get_state(config)
    if not snapshot.next:
        raise HTTPException(
            status_code=400,
            detail=f"No pending review for thread_id={thread_id!r} (already resolved, or never paused).",
        )

    graph_result = state.graph.invoke(Command(resume={"approved": payload.approved}), config=config)
    result = result_from_state(graph_result)
    return {"status": "complete", "thread_id": thread_id, **result}


def _persist_alert_row(state, result: dict):
    """Appends the analyzed alert to the persisted alert stream CSVs.
    Runs once, from /analyze, regardless of whether the escalation/KB
    decision is still pending human review -- this only records that
    the flow happened; incident-log and knowledge-base writes are the
    graph's job (agents/graph_pipeline.py's log_incident_node /
    kb_update_node), not this function's."""
    row = {
        "alert_id": result["alert_id"],
        "row_index": result["row_index"],
        "timestamp": result["timestamp"],
        "source_ip": result["source_ip"],
        "destination_ip": result["destination_ip"],
        "predicted_class": result["detection"]["predicted_class"],
        "confidence": result["detection"]["confidence"],
        "true_class": state.idx_to_name[int(state.y_test[result["row_index"]])],
        "simulated_campaign_id": None,
        "correlation_group_id": result["correlation"]["correlation_group_id"],
        "is_correlated_campaign": result["correlation"]["is_correlated_campaign"],
        "kill_chain_stages_seen": result["correlation"]["kill_chain_stages_seen"],
        "matched_known_pattern": result["correlation"]["matched_known_pattern"],
        "matched_pattern_similarity": result["correlation"]["matched_pattern_similarity"],
        "priority_score": result["priority"]["priority_score"],
        "priority_bucket": result["priority"]["priority_bucket"],
        "effective_severity_score": result["priority"]["effective_severity_score"],
        "own_severity_label": result["priority"]["own_severity_label"],
        "top_contributing_features": json.dumps(result["explanation"]),
    }

    df = state.load_prioritized_alerts()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(PRIORITIZED_ALERTS_PATH, index=False)

    correlated_cols = [
        "alert_id", "row_index", "timestamp", "source_ip", "destination_ip",
        "predicted_class", "true_class", "confidence", "simulated_campaign_id",
        "correlation_group_id", "is_correlated_campaign", "kill_chain_stages_seen",
        "matched_known_pattern", "matched_pattern_similarity",
    ]
    correlated_row = {k: row[k] for k in correlated_cols}
    if os.path.exists(CORRELATED_ALERTS_PATH):
        correlated_df = pd.read_csv(CORRELATED_ALERTS_PATH)
        correlated_df = pd.concat([correlated_df, pd.DataFrame([correlated_row])], ignore_index=True)
    else:
        correlated_df = pd.DataFrame([correlated_row])
    correlated_df.to_csv(CORRELATED_ALERTS_PATH, index=False)


@router.get("/stream")
async def stream_live_alerts(request: Request):
    state = request.app.state.aria

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                result = _run_live_analysis(state, row_index=None, source_ip=None)
                yield f"data: {json.dumps(result)}\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'error': str(exc)})}\n\n"
            await asyncio.sleep(3.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
