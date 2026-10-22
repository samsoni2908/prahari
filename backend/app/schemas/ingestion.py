"""Bounded operational CSV intake; no private or derived datasets."""
from typing import Literal
from uuid import UUID
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

Dataset = Literal["duties", "rest_records", "leave_records", "deployments", "training", "staffing"]


class ImportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_type: Dataset
    csv_data: str = Field(min_length=1, max_length=2_000_000)
    source_timestamp: AwareDatetime


class ImportCommit(ImportInput):
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_revision: str = Field(pattern=r"^[a-f0-9]{64}$")


class RowError(BaseModel):
    row: int
    field: str
    code: str


class ImportValidation(BaseModel):
    id: UUID
    status: Literal["VALIDATED", "REJECTED"]
    dataset_type: Dataset
    checksum: str
    revision: str
    row_count: int
    errors: list[RowError]


class ImportResult(BaseModel):
    id: UUID
    status: Literal["COMMITTED"]
    dataset_type: Dataset
    row_count: int
    checksum: str
    source_timestamp: AwareDatetime
    analytics_status: Literal["NOT_COMPUTED"] = "NOT_COMPUTED"
