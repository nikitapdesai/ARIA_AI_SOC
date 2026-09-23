"""File location in project: api/routers/alerts.py"""

import json
import math

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _clean_records(df: pd.DataFrame) -> list:
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].astype(str)
    records = df.to_dict(orient="records")
    for row in records:
        for k, v in row.items():
            if isinstance(v, float) and math.isnan(v):
                row[k] = None
    return records


@router.get("")
def list_alerts(
    request: Request,
    bucket: list[str] | None = Query(default=None),
    attack_type: list[str] | None = Query(default=None),
    campaign_only: bool = False,
    limit: int = 200,
    offset: int = 0,
):
    state = request.app.state.aria
    df = state.load_prioritized_alerts()
    if df.empty:
        return {"total": 0, "alerts": []}

    if bucket:
        df = df[df["priority_bucket"].isin(bucket)]
    if attack_type:
        df = df[df["predicted_class"].isin(attack_type)]
    if campaign_only:
        df = df[df["is_correlated_campaign"] == True]

    df = df.sort_values("priority_score", ascending=False)
    total = len(df)
    page = df.iloc[offset : offset + limit]

    display_cols = [
        "alert_id", "timestamp", "source_ip", "destination_ip", "predicted_class",
        "confidence", "priority_score", "priority_bucket", "is_correlated_campaign",
        "correlation_group_id", "matched_known_pattern",
    ]
    display_cols = [c for c in display_cols if c in page.columns]

    return {"total": total, "alerts": _clean_records(page[display_cols])}


@router.get("/{alert_id}")
def get_alert_detail(alert_id: str, request: Request):
    state = request.app.state.aria
    df = state.load_prioritized_alerts()
    match = df[df["alert_id"] == alert_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    row = match.iloc[0]
    record = _clean_records(match)[0]

    explanation = []
    if pd.notna(row.get("top_contributing_features")):
        try:
            explanation = json.loads(row["top_contributing_features"])
        except (TypeError, ValueError):
            explanation = []
    record["top_contributing_features"] = explanation

    return record


@router.get("/meta/attack-types")
def list_attack_types(request: Request):
    state = request.app.state.aria
    df = state.load_prioritized_alerts()
    if df.empty:
        return []
    return sorted(df["predicted_class"].unique().tolist())
