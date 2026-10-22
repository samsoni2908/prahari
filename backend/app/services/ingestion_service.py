"""Validate every row before atomically committing source rows and a safe receipt.

Validation stores only counts/hash/provenance in existing audit_events. Commit
resubmits the CSV, avoiding an unapproved payload/batch store. Imported sources
do not automatically certify coverage or fabricate successful analytics jobs.
"""
import csv
import hashlib
import io
import json
import uuid
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String
from sqlalchemy.exc import IntegrityError
from app.repositories.ingestion_repository import IngestionRepository, SOURCE_MODELS
from app.repositories.audit_repository import AuditRepository
from app.schemas.ingestion import ImportValidation, ImportResult, RowError


class IngestionService:
    def __init__(self, session):
        self.session = session
        self.repo = IngestionRepository(session)
        self.audit = AuditRepository(session)
        self.actor = session.info.get("actor") or {}

    def authorize(self):
        if self.actor.get("role") != "ADMIN":
            raise HTTPException(403, "ADMIN_REQUIRED")

    def identity(self, body):
        checksum = hashlib.sha256(body.csv_data.encode("utf-8")).hexdigest()
        revision = hashlib.sha256(json.dumps([body.dataset_type, checksum,
            body.source_timestamp.astimezone(timezone.utc).isoformat()], separators=(",", ":")).encode()).hexdigest()
        identifier = uuid.uuid5(uuid.NAMESPACE_URL, "prahari:import:" + self.actor["user_id"] + ":" + revision)
        return identifier, checksum, revision

    @staticmethod
    def convert(column, raw):
        if raw == "":
            if column.nullable:
                return None
            raise ValueError()
        kind = column.type
        if isinstance(kind, Boolean):
            if raw.lower() not in ("true", "false"):
                raise ValueError()
            return raw.lower() == "true"
        if isinstance(kind, DateTime):
            value = datetime.fromisoformat(raw)
            if value.tzinfo is None:
                raise ValueError()
            return value.astimezone(timezone.utc)
        if isinstance(kind, Date):
            return date.fromisoformat(raw)
        if isinstance(kind, Integer):
            return int(raw)
        if isinstance(kind, Numeric):
            value = Decimal(raw)
            if not value.is_finite():
                raise ValueError()
            return value
        if isinstance(kind, String):
            if kind.length and len(raw) > kind.length:
                raise ValueError()
            return raw
        return uuid.UUID(raw)

    async def inspect(self, body, replay=False):
        self.authorize()
        identifier, checksum, revision = self.identity(body)
        errors, rows, row_numbers = [], [], []
        def error(number, field, code):
            if len(errors) < 100:
                errors.append(RowError(row=number, field=field, code=code))
        if body.source_timestamp > datetime.now(timezone.utc):
            error(0, "source_timestamp", "FUTURE_SOURCE_TIMESTAMP")
        if len(body.csv_data.encode("utf-8")) > 2_000_000:
            error(0, "csv_data", "FILE_SIZE_EXCEEDED")
        model = SOURCE_MODELS[body.dataset_type]
        columns = {c.name:c for c in model.__table__.columns if c.name != "created_at"}
        required = {name for name, c in columns.items() if not c.nullable and name != "id"}
        reader = csv.DictReader(io.StringIO(body.csv_data.lstrip("\ufeff")), strict=True)
        try:
            headers = reader.fieldnames or []
        except csv.Error:
            headers = []
            error(0, "csv_data", "INVALID_CSV")
        if len(headers) != len(set(headers)) or set(headers) - set(columns) or required - set(headers):
            error(0, "headers", "INVALID_HEADERS")
        else:
            try:
                for number, raw in enumerate(reader, 2):
                    if number > 2001:
                        error(number, "rows", "ROW_LIMIT_EXCEEDED")
                        break
                    if None in raw or any(value is None for value in raw.values()):
                        error(number, "row", "INVALID_COLUMN_COUNT")
                        continue
                    row = {"id":uuid.uuid5(identifier, str(number))}
                    parse_failed = False
                    for name, value in raw.items():
                        try:
                            row[name] = self.convert(columns[name], value.strip())
                        except (ValueError, TypeError, ArithmeticError):
                            error(number, name, "INVALID_VALUE")
                            parse_failed = True
                    if parse_failed:
                        continue
                    self.check_values(body.dataset_type, row, number, error, body.source_timestamp)
                    rows.append(row)
                    row_numbers.append(number)
            except csv.Error:
                error(0, "csv_data", "INVALID_CSV")
        if not rows:
            error(0, "rows", "EMPTY_IMPORT")
        identifiers = [row["id"] for row in rows]
        if len(identifiers) != len(set(identifiers)):
            error(0, "id", "DUPLICATE_ID")
        # Authorization is scoped to one internally registered operational intake.
        self.session.info["actor"] = {**self.actor, "_operational_import":body.dataset_type}
        try:
            for name, column in columns.items():
                if not column.foreign_keys:
                    continue
                values = {r[name] for r in rows if r.get(name) is not None}
                valid = await self.repo.foreign_ids(column, values) if values else set()
                for number, row in zip(row_numbers, rows):
                    if row.get(name) is not None and row[name] not in valid:
                        error(number, name, "FOREIGN_KEY_NOT_FOUND")
            if not replay:
                existing = await self.repo.existing(body.dataset_type, identifiers)
                for number, row in zip(row_numbers, rows):
                    if row["id"] in existing or await self.repo.overlaps(body.dataset_type, row):
                        error(number, "row", "EXISTING_SOURCE_CONFLICT")
            # Detect intra-batch overlaps/duplicate daily reports before mutation.
            seen = []
            for number, row in zip(row_numbers, rows):
                for prior in seen:
                    kind = body.dataset_type
                    if kind == "duties" and prior["personnel_id"] == row["personnel_id"] and prior["start_at"] < row["end_at"] and row["start_at"] < prior["end_at"]:
                        error(number, "start_at", "OVERLAPPING_SOURCE")
                    elif kind in ("rest_records", "staffing"):
                        key = "personnel_id" if kind == "rest_records" else "unit_id"
                        if prior[key] == row[key] and prior["record_date"] == row["record_date"]:
                            error(number, "record_date", "DUPLICATE_DAILY_SOURCE")
                seen.append(row)
        finally:
            self.session.info["actor"] = self.actor
        result = ImportValidation(id=identifier, status="REJECTED" if errors else "VALIDATED",
            dataset_type=body.dataset_type, checksum=checksum, revision=revision, row_count=len(rows), errors=errors)
        return result, rows

    @staticmethod
    def check_values(kind, row, number, error, known_at):
        for name in ("hours", "days", "available_strength", "required_strength", "sanctioned_strength"):
            if row.get(name) is not None and row[name] < 0:
                error(number, name, "NEGATIVE_VALUE")
        if kind == "rest_records":
            if row["data_quality_status"] == "VALID" and (row.get("rest_hours") is None or row.get("rest_gap_hours") is None):
                error(number, "rest_hours", "VALID_REST_VALUES_REQUIRED")
            if row.get("rest_hours") is not None and not 0 <= row["rest_hours"] <= 24:
                error(number, "rest_hours", "INVALID_REST_HOURS")
            if row.get("rest_gap_hours") is not None and row["rest_gap_hours"] < 0:
                error(number, "rest_gap_hours", "INVALID_REST_GAP")
            if row["data_quality_status"] not in ("VALID", "MISSING", "DELAYED", "INVALID"):
                error(number, "data_quality_status", "INVALID_STATUS")
        if row.get("end_date") is not None and row["end_date"] < row["start_date"]:
            error(number, "end_date", "INVALID_DATE_RANGE")
        if kind == "duties" and (row["end_at"] <= row["start_at"] or
                abs(Decimal(str((row["end_at"]-row["start_at"]).total_seconds()/3600))-row["hours"]) > Decimal("0.01")
                or row["start_at"].date() != row["duty_date"]):
            error(number, "end_at", "INVALID_DUTY_INTERVAL")
        completion = row["end_at"] if kind=="duties" else None
        completed_date = row.get("record_date") if kind=="rest_records" and row["data_quality_status"]=="VALID" else row.get("end_date") if kind=="training" and row["status"]=="COMPLETED" else row.get("actual_end_date") if kind=="leave_records" else None
        if completed_date:
            completion=datetime.combine(completed_date+timedelta(days=1),datetime.min.time(),timezone.utc)
        if completion and completion>known_at:
            error(number,"source_timestamp","COMPLETION_NOT_KNOWN")
        if kind == "deployments" and row.get("intensity_level") is not None and not 1 <= row["intensity_level"] <= 5:
            error(number, "intensity_level", "INVALID_INTENSITY")
        if kind == "staffing" and row.get("coverage_percent") is not None:
            required = row["required_strength"]
            if required <= 0 or abs(row["coverage_percent"] - Decimal(100)*row["available_strength"]/required) > Decimal("0.01"):
                error(number, "coverage_percent", "INCONSISTENT_COVERAGE")
        if kind == "leave_records":
            for name, allowed in (("planning_classification", {"PLANNED", "UNPLANNED"}),
                ("disruption_type", {"CANCELLED", "DEFERRED", "RECALLED", "SHORTENED"}),
                ("disruption_initiator", {"SERVICE", "PERSONNEL"})):
                if row.get(name) is not None and row[name] not in allowed:
                    error(number, name, "INVALID_ENUM")
            if row.get("actual_start_date") and row.get("actual_end_date") and row["actual_end_date"] < row["actual_start_date"]:
                error(number, "actual_end_date", "INVALID_ACTUAL_DATE_RANGE")

    async def validate(self, body):
        result, _ = await self.inspect(body)
        await self.audit.log_event(None, None, "IMPORT_" + result.status, "operational_import", result.id,
            metadata={"source_hash":result.checksum, "expected_revision":result.revision,
                "dataset_type":body.dataset_type, "row_count":result.row_count,
                "source_timestamp":body.source_timestamp.isoformat()})
        return result

    async def commit(self, identifier, body, key):
        self.authorize()
        actual, checksum, revision = self.identity(body)
        if actual != identifier or checksum != body.checksum or revision != body.expected_revision:
            raise HTTPException(409, "IMPORT_REVISION_CONFLICT")
        await self.repo.lock(revision)
        prior = await self.repo.receipt(identifier, "IMPORT_COMMITTED")
        if prior:
            return ImportResult(id=identifier, status="COMMITTED", dataset_type=body.dataset_type,
                row_count=prior.metadata_json["row_count"], checksum=checksum, source_timestamp=body.source_timestamp)
        if not await self.repo.receipt(identifier, "IMPORT_VALIDATED", uuid.UUID(self.actor["user_id"])):
            raise HTTPException(409, "IMPORT_VALIDATION_REQUIRED")
        key_hash = hashlib.sha256((self.actor["user_id"]+":import:"+key).encode()).hexdigest()
        await self.repo.lock(key_hash)
        from sqlalchemy import select
        from app.models import AuditEvent
        collision = (await self.session.execute(select(AuditEvent.resource_id).where(
            AuditEvent.action == "IMPORT_COMMITTED", AuditEvent.actor_user_id == uuid.UUID(self.actor["user_id"]),
            AuditEvent.metadata_json["idempotency_key_hash"].astext == key_hash))).scalar_one_or_none()
        if collision and collision != identifier:
            raise HTTPException(409, "IDEMPOTENCY_CONFLICT")
        result, rows = await self.inspect(body)
        if result.errors:
            raise HTTPException(422, "IMPORT_REVALIDATION_FAILED")
        subjects=sorted({str(row.get("personnel_id") or row.get("unit_id")) for row in rows})
        for subject in subjects:
            await self.repo.lock(hashlib.sha256((body.dataset_type+":"+subject).encode()).hexdigest())
        result, rows=await self.inspect(body)
        if result.errors:
            raise HTTPException(422,"IMPORT_REVALIDATION_FAILED")
        self.session.info["actor"] = {**self.actor, "_operational_import":body.dataset_type}
        try:
            # Savepoint protects caller transaction even when the service is used
            # outside a request. Outer transaction commits source + receipt together.
            async with self.session.begin_nested():
                now = datetime.now(timezone.utc)
                self.session.add_all(SOURCE_MODELS[body.dataset_type](**row, created_at=now) for row in rows)
                await self.session.flush()
                await self.audit.log_event(None, None, "IMPORT_COMMITTED", "operational_import", identifier,
                    metadata={"source_hash":checksum, "expected_revision":revision,
                        "dataset_type":body.dataset_type, "row_count":len(rows),
                        "source_timestamp":body.source_timestamp.isoformat(), "idempotency_key_hash":key_hash})
        except IntegrityError:
            raise HTTPException(422, "IMPORT_CONSTRAINT_CONFLICT") from None
        finally:
            self.session.info["actor"] = self.actor
        return ImportResult(id=identifier, status="COMMITTED", dataset_type=body.dataset_type,
            row_count=len(rows), checksum=checksum, source_timestamp=body.source_timestamp)
