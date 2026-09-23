"""File location in project: api/routers/overview.py"""

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/overview", tags=["overview"])


@router.get("")
def get_overview(request: Request):
    state = request.app.state.aria
    alerts_df = state.load_prioritized_alerts()
    incident_log = state.load_incident_log()
    knowledge_base = state.load_knowledge_base()

    if alerts_df.empty:
        bucket_counts = {}
        n_campaigns = 0
    else:
        bucket_counts = alerts_df["priority_bucket"].value_counts().to_dict()
        n_campaigns = int(
            alerts_df[alerts_df["is_correlated_campaign"] == True]["correlation_group_id"].nunique()
        )

    n_learned = sum(1 for k in knowledge_base if k.get("source") == "escalation_agent_auto_learned")

    return {
        "total_alerts": int(len(alerts_df)),
        "bucket_counts": {
            "Critical": int(bucket_counts.get("Critical", 0)),
            "High": int(bucket_counts.get("High", 0)),
            "Medium": int(bucket_counts.get("Medium", 0)),
            "Low": int(bucket_counts.get("Low", 0)),
        },
        "correlated_campaigns": n_campaigns,
        "incident_log": {
            "total": len(incident_log),
            "correlated_campaigns": sum(
                1 for i in incident_log if i["incident_type"] == "correlated_campaign"
            ),
            "isolated_critical": sum(
                1 for i in incident_log if i["incident_type"] == "isolated_critical"
            ),
        },
        "knowledge_base": {
            "total_patterns": len(knowledge_base),
            "auto_learned": n_learned,
        },
    }
