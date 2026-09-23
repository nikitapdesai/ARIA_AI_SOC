"""
File location in project: api/schemas.py
"""

from typing import Optional

from pydantic import BaseModel, Field


class LiveAnalyzeRequest(BaseModel):
    row_index: Optional[int] = Field(
        default=None,
        description="Specific X_test row to analyze. Omit for a random row.",
    )
    source_ip: Optional[str] = Field(
        default=None,
        description=(
            "Synthetic source IP to attribute this flow to. If it matches "
            "a recent alert's source_ip, the Correlation Agent may group "
            "them into a campaign. Omit for a fresh, isolated source."
        ),
    )
    commit: bool = Field(
        default=False,
        description=(
            "If true, persist this analysis: append to the prioritized "
            "alert stream and run real escalation (incident log + "
            "knowledge base growth). If false (default), it's a dry run."
        ),
    )


class LiveReviewRequest(BaseModel):
    approved: bool = Field(
        description=(
            "Analyst decision on a pending 'pending_review' result from "
            "POST /api/live/analyze: whether to add the novel campaign "
            "pattern to the knowledge base. Either way the incident "
            "itself still gets logged -- this only decides KB growth."
        ),
    )
