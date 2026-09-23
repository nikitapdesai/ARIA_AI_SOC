"""File location in project: api/routers/incidents.py"""

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("")
def list_incidents(request: Request, limit: int = 100, offset: int = 0):
    state = request.app.state.aria
    log = state.load_incident_log()
    log_sorted = sorted(log, key=lambda i: i.get("logged_at", ""), reverse=True)
    return {"total": len(log_sorted), "incidents": log_sorted[offset : offset + limit]}


@router.get("/{incident_id}")
def get_incident(incident_id: str, request: Request):
    state = request.app.state.aria
    log = state.load_incident_log()
    for incident in log:
        if incident.get("incident_id") == incident_id:
            return incident
    raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
