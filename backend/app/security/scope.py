"""Request-scoped query predicates and write checks; no global role bypass."""

import uuid

from fastapi import HTTPException
from sqlalchemy import event, false, select, inspect
from sqlalchemy.orm import Session, with_loader_criteria

from app import models


def require_unit(actor, requested=None):
    if actor.get("role") not in ("COMMANDER", "WELFARE_OFFICER") or not actor.get("unit_id"):
        raise HTTPException(403, "Unit scope is not configured")
    unit = uuid.UUID(actor["unit_id"])
    if requested is not None and uuid.UUID(str(requested)) != unit:
        raise HTTPException(404, "Resource not found")
    return unit


def predicate(model, actor, queue=False):
    role = actor.get("role")
    uid = uuid.UUID(actor["user_id"])
    pid = uuid.UUID(actor["personnel_id"]) if actor.get("personnel_id") else None
    unit = uuid.UUID(actor["unit_id"]) if actor.get("unit_id") else None
    if model is models.Notification:
        return model.recipient_user_id == uid
    if model is models.WelfareCaseAction:
        if role == "PERSONNEL":
            return (model.visibility == "PERSONNEL") & model.case_id.in_(
                select(models.SupportRequest.id).where(models.SupportRequest.personnel_id == pid)
            ) if pid else false()
        if role == "WELFARE_OFFICER" and unit:
            return model.case_id.in_(select(models.SupportRequest.id).join(
                models.Personnel, models.Personnel.id == models.SupportRequest.personnel_id,
            ).where(models.Personnel.unit_id == unit, models.SupportRequest.assigned_to_user_id == uid))
        return false()
    if role == "ADMIN":
        operational = (models.Duty, models.RestRecord, models.LeaveRecord, models.Deployment, models.Training, models.Staffing)
        if actor.get("_operational_import") in {m.__tablename__ for m in operational} and model in operational:
            return True
        if model is models.SupportRequest and actor.get("_unit_transfer"):
            return model.personnel_id == uuid.UUID(actor["_unit_transfer"])
        return True if model in (models.User, models.Unit, models.Personnel, models.Skill, models.PersonSkill, models.PostingHistory, models.AuditEvent, models.PolicyConfig, models.AuthSession) else false()
    if model is models.User:
        return model.id == uid
    if model is models.AuthSession:
        return model.user_id == uid
    if model is models.AuditEvent:
        if role == "PERSONNEL" and pid:
            own_cases = select(models.SupportRequest.id).where(models.SupportRequest.personnel_id == pid)
            return (model.actor_user_id == uid) | (
                model.action.in_(("CASE_CONTENT_ACCESS", "CASE_IDENTITY_ACCESS"))
                & ((model.resource_id.in_(own_cases))
                   | ((model.resource_type == "personnel") & (model.resource_id == pid)))
            )
        return model.actor_user_id == uid
    if role == "PERSONNEL":
        if model is models.Personnel:
            return model.id == pid if pid else false()
        if model is models.Unit:
            return model.id.in_(select(models.Personnel.unit_id).where(models.Personnel.id == pid)) if pid else false()
        if hasattr(model, "personnel_id"):
            return model.personnel_id == pid if pid else false()
        return false()
    if role not in ("COMMANDER", "WELFARE_OFFICER") or not unit:
        return false()
    if model in (models.WellbeingPrivate, models.WellbeingResult, models.WellbeingConsent):
        # Existing generic consent cannot prove assessment/case/recipient sharing.
        return false()
    people = select(models.Personnel.id).where(models.Personnel.unit_id == unit)
    if model is models.SupportRequest:
        if role != "WELFARE_OFFICER":
            return false()
        scope = model.personnel_id.in_(people)
        claim = actor.get("_claim_case")
        if claim:
            # Internal single-case claim context; never supplied by token/input.
            return scope & (model.id == uuid.UUID(claim)) & ((model.assigned_to_user_id == uid) | model.assigned_to_user_id.is_(None))
        return scope if queue else scope & (model.assigned_to_user_id == uid)
    if model is models.Personnel:
        return model.unit_id == unit
    if model is models.Unit:
        return model.id == unit
    if model in (models.Skill, models.PolicyConfig):
        return True
    if hasattr(model, "unit_id"):
        return model.unit_id == unit
    if hasattr(model, "scenario_id"):
        return model.scenario_id.in_(select(models.RosterScenario.id).where(models.RosterScenario.unit_id == unit))
    if hasattr(model, "personnel_id"):
        return model.personnel_id.in_(people)
    return false()


@event.listens_for(Session, "do_orm_execute")
def scope_queries(state):
    actor = state.session.info.get("actor")
    if not actor:
        return
    # Protected writes must use entity changes so before_flush checks both
    # ownership and permitted transitions; bulk DML bypasses that hook.
    if state.is_update or state.is_delete or state.is_insert:
        raise HTTPException(403, "Bulk mutation is not permitted")
    queue = state.execution_options.get("welfare_queue", False)
    if queue:
        allowed = {"id", "pseudo_id", "request_type", "status", "created_at"}
        if any(column.name not in allowed for column in state.statement.selected_columns):
            raise HTTPException(403, "Invalid queue projection")
    for model in models.Base.registry.mappers:
        cls = model.class_
        state.statement = state.statement.options(with_loader_criteria(cls, predicate(cls, actor, queue), include_aliases=True))


@event.listens_for(Session, "before_flush")
def scope_writes(session, flush_context, instances):
    actor = session.info.get("actor")
    if not actor:
        return
    for record in session.new | session.dirty | session.deleted:
        model = type(record)
        if model is models.AuditEvent:
            if record not in session.new or record.actor_user_id != uuid.UUID(actor["user_id"]) or record.actor_role != actor["role"]:
                raise HTTPException(403, "Audit records are append-only")
            continue
        if model is models.WelfareCaseAction:
            if record not in session.new or actor["role"] != "WELFARE_OFFICER":
                raise HTTPException(403, "Case actions are officer append-only")
            unit = require_unit(actor)
            claiming = actor.get("_claim_case") == str(record.case_id) and record.action_type == "ASSIGN"
            owned = session.execute(select(models.SupportRequest.id).join(
                models.Personnel, models.Personnel.id == models.SupportRequest.personnel_id,
            ).where(models.SupportRequest.id == record.case_id,
                    (models.SupportRequest.assigned_to_user_id.is_(None) if claiming else
                     models.SupportRequest.assigned_to_user_id == uuid.UUID(actor["user_id"])),
                    models.Personnel.unit_id == unit)).first()
            if owned is None or record.actor_user_id != uuid.UUID(actor["user_id"]):
                raise HTTPException(404, "Case not found")
            continue
        if model is models.Notification:
            if record in session.new:
                if not session.info.get("_notification_event"):
                    raise HTTPException(403, "Notification event required")
            elif (record in session.deleted or record.recipient_user_id != uuid.UUID(actor["user_id"])
                  or any(change.key != "read_at" for change in inspect(record).attrs
                         if change.history.has_changes())):
                raise HTTPException(403, "Only own notification read state may change")
            continue
        if record not in session.new:
            # Check persisted ownership before accepting any changed binding.
            mapper = inspect(model)
            identity = inspect(record).identity
            owned = session.execute(select(*mapper.primary_key).where(
                *(column == value for column, value in zip(mapper.primary_key, identity)),
                predicate(model, actor),
            )).first()
            if owned is None:
                raise HTTPException(404, "Resource not found")
        role = actor["role"]
        if role == "ADMIN":
            operational = (models.Duty, models.RestRecord, models.LeaveRecord, models.Deployment, models.Training, models.Staffing)
            if model in operational and actor.get("_operational_import") == model.__tablename__:
                if record not in session.new:
                    raise HTTPException(403, "Source import cannot overwrite or delete history")
                continue
            if model is models.SupportRequest and actor.get("_unit_transfer") == str(record.personnel_id):
                if (record.assigned_to_user_id is not None
                        or (inspect(record).attrs.status.history.has_changes()
                            and record.status != "WITHDRAWN")):
                    raise HTTPException(403, "Unit transfer may only withdraw or unassign cases")
                continue
            if model not in (models.User, models.Unit, models.Personnel, models.Skill, models.PersonSkill, models.PostingHistory, models.PolicyConfig, models.AuthSession):
                raise HTTPException(403, "Operation not permitted")
        elif role == "PERSONNEL":
            if model is models.AuthSession and record.user_id == uuid.UUID(actor["user_id"]):
                continue
            if model not in (models.WellbeingConsent, models.WellbeingPrivate, models.SupportRequest) or record.personnel_id != uuid.UUID(actor["personnel_id"]):
                raise HTTPException(403, "Operation not permitted")
        else:
            if model is models.AuthSession and record.user_id == uuid.UUID(actor["user_id"]):
                continue
            require_unit(actor)
            if model is models.Alert:
                changed = {attribute.key for attribute in inspect(record).attrs if attribute.history.has_changes()}
                old = inspect(record).attrs.status.history.deleted
                if (record in session.new or record in session.deleted
                        or record.source_type != "MODEL_A" or record.severity != "HIGH"
                        or changed - {"status", "resolved_at"}
                        or not old or old[0] not in ("OPEN", "ACKNOWLEDGED")
                        or record.status not in ("ACKNOWLEDGED", "RESOLVED")
                        or (old[0] == "ACKNOWLEDGED" and record.status != "RESOLVED")
                        or (record.status == "RESOLVED" and record.resolved_at is None)):
                    raise HTTPException(403, "Only human operational alert review is permitted")
                require_unit(actor, record.unit_id)
                continue
            if role == "COMMANDER":
                permitted = (models.RosterScenario, models.ScenarioChange, models.Approval, models.ScenarioImplementation, models.Outcome)
            elif role == "WELFARE_OFFICER":
                permitted = (models.SupportRequest, models.RosterScenario, models.ScenarioChange)
            else:
                permitted = ()
            if model not in permitted:
                raise HTTPException(403, "Operation not permitted")
            if model is models.SupportRequest:
                person = session.execute(select(models.Personnel).where(models.Personnel.id == record.personnel_id)).scalar_one_or_none()
                reassignment = actor.get("_reassign_case") == str(record.id)
                if not person or (not reassignment and record.assigned_to_user_id != uuid.UUID(actor["user_id"])):
                    raise HTTPException(404, "Resource not found")
            elif hasattr(record, "unit_id"):
                require_unit(actor, record.unit_id)
            else:
                scenario = session.execute(select(models.RosterScenario).where(models.RosterScenario.id == record.scenario_id)).scalar_one_or_none()
                if not scenario:
                    raise HTTPException(404, "Resource not found")
                if model is models.ScenarioChange:
                    person = session.execute(select(models.Personnel.id).where(models.Personnel.id == record.personnel_id)).first()
                    if not person:
                        raise HTTPException(404, "Resource not found")
