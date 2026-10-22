"""Identity-only purpose-scoped search and explicit human case intake."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class NamedSearch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    field: Literal["name", "service_code", "pseudo_id"]
    query: str = Field(min_length=3, max_length=150)
    purpose_reason: str = Field(min_length=5, max_length=500)
    limit: int = Field(default=20, ge=1, le=50)


class NamedIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    full_name: str
    personnel_code: str
    pseudo_id: str


class NamedSearchResult(BaseModel):
    items: list[NamedIdentity]
    next_cursor: None = None


class OpenCase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    personnel_id: UUID
    request_type: Literal["LEAVE_ASSISTANCE", "STRESS_FATIGUE", "MEDICAL_HEALTH", "FAMILY_PERSONAL"]
    priority: Literal["NORMAL", "URGENT"] = "NORMAL"
    personnel_visible_reason: str = Field(min_length=10, max_length=2000)


class OpenedCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    status: Literal["ASSIGNED"]
    assigned_to_me: Literal[True]
    created_at: datetime
