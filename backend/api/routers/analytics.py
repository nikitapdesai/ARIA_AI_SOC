"""File location in project: api/routers/analytics.py"""

import pandas as pd
from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("")
def get_analytics(request: Request):
    state = request.app.state.aria
    df = state.load_prioritized_alerts()
    if df.empty:
        return {
            "alerts_over_time": [], "attack_type_distribution": [],
            "top_sources": [], "severity_by_attack_type": [], "pattern_matches": [],
        }

    time_df = df.set_index("timestamp").resample("30min").size().reset_index()
    time_df.columns = ["timestamp", "count"]
    alerts_over_time = [
        {"timestamp": ts.isoformat(), "count": int(c)}
        for ts, c in zip(time_df["timestamp"], time_df["count"])
    ]

    attack_counts = df["predicted_class"].value_counts()
    attack_type_distribution = [
        {"attack_type": k, "count": int(v)} for k, v in attack_counts.items()
    ]

    top_sources = df["source_ip"].value_counts().head(10)
    top_sources_list = [{"source_ip": k, "count": int(v)} for k, v in top_sources.items()]

    severity_pivot = (
        df.groupby(["predicted_class", "priority_bucket"], observed=True)
        .size()
        .reset_index(name="count")
    )
    severity_by_attack_type = [
        {"attack_type": r["predicted_class"], "bucket": r["priority_bucket"], "count": int(r["count"])}
        for _, r in severity_pivot.iterrows()
    ]

    matched = df[df["matched_known_pattern"].notna()]
    pattern_counts = matched["matched_known_pattern"].value_counts()
    pattern_matches = [{"pattern": k, "count": int(v)} for k, v in pattern_counts.items()]

    return {
        "alerts_over_time": alerts_over_time,
        "attack_type_distribution": attack_type_distribution,
        "top_sources": top_sources_list,
        "severity_by_attack_type": severity_by_attack_type,
        "pattern_matches": pattern_matches,
    }
