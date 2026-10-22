"""Operational alert projections exclude identities, internal evidence and private data."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

AlertState = Literal["OPEN", "ACKNOWLEDGED", "RESOLVED"]


class AlertView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    alert_type: str
    severity: Literal["HIGH"]
    status: AlertState
    message: str
    created_at: datetime
    resolved_at: datetime | None
    revision: str


class AlertPage(BaseModel):
    items: list[AlertView]
    next_cursor: str | None


class AlertAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    reason_code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z][A-Z0-9_]*$")
