"""One transactional operational path for manual and scheduled processing."""
import math
import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, select, insert, desc, and_, text
from app.analytics.operational_feature_adapter import OperationalFeatureAdapter
from app.repositories.detection_repository import DetectionRepository, TABLES, TARGET, MODEL_VERSION, FEATURE_VERSION, TRAINING_VERSION
from app.ml.runtime_loader import model_a_runtime, APPROVED_ARTIFACT_SHA256
from app.services.operational_analytics_service import OperationalAnalyticsService
from app.analytics.attention import evaluate_attention

POLICY = "OPERATIONAL_ATTENTION_POLICY_V1_SYNTHETIC_DEMO"
FAMILY = "OPERATIONAL_MODEL_A_HIGH"


class OperationalAttentionService:
    def __init__(self, engine, loader=None, adapter_class=OperationalFeatureAdapter):
        self.engine = engine
        self.loader = loader if loader is not None else model_a_runtime
        self.adapter_class = adapter_class

    def run(self, cutoff, actor=None, mode="HISTORICAL", unit_id=None, request_key=None):
        if request_key is None:
            return self._run(cutoff,actor,mode,unit_id)
        if mode != "HISTORICAL" or not actor or actor.get("role") != "ADMIN":
            raise PermissionError("GOVERNANCE_ROLE_REQUIRED")
        key_hash=hashlib.sha256((actor["user_id"]+":"+request_key).encode()).hexdigest()
        payload_hash=hashlib.sha256(json.dumps([cutoff.isoformat(),str(unit_id)],separators=(",",":")).encode()).hexdigest()
        lock=int(key_hash[:15],16)
        with self.engine.connect() as owner:
            owner.execute(text("SELECT pg_advisory_lock(:key)"),{"key":lock})
            owner.commit()
            try:
                audit=TABLES["audit_events"]
                receipt=owner.execute(select(audit.c.metadata_json).where(
                    audit.c.action=="OPERATIONAL_MANUAL_RECEIPT",
                    audit.c.actor_user_id==uuid.UUID(actor["user_id"]),
                    audit.c.metadata_json["request_key_hash"].astext==key_hash,
                )).scalar_one_or_none()
                owner.commit()
                if receipt:
                    if receipt["request_hash"] != payload_hash:
                        raise ValueError("IDEMPOTENCY_CONFLICT")
                    return {"cutoff":cutoff.isoformat(),"mode":mode,**{k:receipt[k] for k in ("processed","valid","unavailable","failed","alerts_created","alerts_suppressed")}}
                result=self._run(cutoff,actor,mode,unit_id)
                with self.engine.begin() as c:
                    DetectionRepository(c).audit("OPERATIONAL_MANUAL_RECEIPT",actor,cutoff,counts=result,
                                                request_key_hash=key_hash,request_hash=payload_hash)
                return result
            finally:
                owner.execute(text("SELECT pg_advisory_unlock(:key)"),{"key":lock})
                owner.commit()

    def _run(self, cutoff, actor=None, mode="HISTORICAL", unit_id=None):
        if mode not in ("HISTORICAL", "SCHEDULED"):
            raise ValueError("INVALID_RUN_MODE")
        if mode == "HISTORICAL" and (not actor or actor.get("role") != "ADMIN"):
            raise PermissionError("GOVERNANCE_ROLE_REQUIRED")
        if mode == "SCHEDULED" and cutoff != datetime.now(timezone.utc).date():
            raise ValueError("SCHEDULED_COMPLETED_DAY_REQUIRED")
        if cutoff > datetime.now(timezone.utc).date():
            raise ValueError("FUTURE_CUTOFF")
        counts = dict.fromkeys(("processed","valid","unavailable","failed","alerts_created","alerts_suppressed"),0)
        peer_cache = {}
        with self.engine.connect() as c:
            people = DetectionRepository(c).people(unit_id)
        for person in people:
            counts["processed"] += 1
            checkpoint={k:counts[k] for k in ("valid","unavailable","alerts_created","alerts_suppressed")}
            try:
                with self.engine.begin() as c:
                    repo = DetectionRepository(c)
                    repo.lock_person(person["id"])
                    analytics = OperationalAnalyticsService(repo, peer_cache).process(person, cutoff, actor)
                    result = self.adapter_class(repo).build(person["id"],person["unit_id"],cutoff)
                    if result.status != "VALID":
                        repo.audit("OPERATIONAL_PERSON_UNAVAILABLE", actor,cutoff,reason=result.reason_codes[0],
                                   source_hash=result.source_hash,personnel_id=person["id"],availability=result.status)
                        counts["unavailable"] += 1
                        continue
                    existing = repo.governed(person["id"],cutoff)
                    if len(existing) > 1:
                        raise ValueError("GOVERNED_IDENTITY_CONFLICT")
                    if existing:
                        output = existing[0]
                        if output["explanation_json"].get("source_hash") != result.source_hash or output["explanation_json"].get("artifact_hash") != APPROVED_ARTIFACT_SHA256:
                            repo.audit("OPERATIONAL_PERSON_UNAVAILABLE",actor,cutoff,reason="SOURCE_CHANGED",
                                       personnel_id=person["id"],availability="DATA_STALE")
                            counts["unavailable"] += 1
                            continue
                    else:
                        prediction = self.loader.predict_operational_attention(result.as_features())
                        if prediction["availability_status"] != "MODEL_AVAILABLE":
                            repo.audit("OPERATIONAL_PERSON_UNAVAILABLE",actor,cutoff,reason="MODEL_UNAVAILABLE",
                                       personnel_id=person["id"],availability="MODEL_UNAVAILABLE")
                            counts["unavailable"] += 1
                            continue
                        probability = prediction["calibrated_probability"]
                        score = prediction["operational_strain_score"]
                        band = prediction["operational_attention_band"]
                        if probability is None or score is None or not math.isfinite(probability) or not 0 <= probability <= 1 or not math.isfinite(score) or not 0 <= score <= 100 or band not in ("LOW","MEDIUM","HIGH"):
                            raise ValueError("INVALID_INFERENCE")
                        evidence = {"governance":"MODEL_A_FINAL_LOCKED","artifact_hash":APPROVED_ARTIFACT_SHA256,
                                    "target_contract":"v2.1-approved-leave-lifecycle","source_hash":result.source_hash,
                                    "coverage_policy":"SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO",
                                    "attention_policy":POLICY,"availability":"VALID",
                                    "drivers":prediction.get("top_operational_drivers",[])[:4]}
                        output = dict(id=uuid.uuid4(),personnel_id=person["id"],prediction_date=cutoff,target_name=TARGET,
                                      hr_probability=probability,wellbeing_probability=None,combined_probability=None,
                                      risk_score=score,risk_level=band,predicted_class=prediction["predicted_class"],
                                      model_name="Model-A (Operational Workload & Recovery Decision Support)",
                                      model_version=MODEL_VERSION,feature_set_version=FEATURE_VERSION,
                                      training_data_version=TRAINING_VERSION,data_completeness=100,explanation_json=evidence,
                                      created_at=datetime.now(timezone.utc))
                        c.execute(insert(TABLES["model_outputs"]).values(**output))
                    attention = evaluate_attention(analytics, output)
                    repo.audit("OPERATIONAL_ATTENTION_EVALUATED", actor, cutoff,
                        reason=attention["reason_codes"][0] if attention["reason_codes"] else None,
                        source_hash=analytics["wsi"]["source_hash"], personnel_id=person["id"], availability=attention["status"])
                    emitted = self.attention(repo, person, cutoff, output, actor, analytics)
                    counts["valid" if attention["status"] == "VALID" else "unavailable"] += 1
                    counts["alerts_created"] += int(emitted)
                    counts["alerts_suppressed"] += int(output["risk_level"] == "HIGH" and not emitted)
            except Exception as error:
                # A commit failure must not count rolled-back effects as successful.
                counts.update(checkpoint)
                counts["failed"] += 1
                # Failure detail is a bounded reason code, never raw DB/feature payload.
                with self.engine.begin() as c:
                    DetectionRepository(c).audit("OPERATIONAL_PERSON_FAILURE",actor,cutoff,
                         reason="COMPUTATION_ERROR",personnel_id=person["id"],availability="COMPUTATION_ERROR")
        with self.engine.begin() as c:
            repo = DetectionRepository(c)
            repo.audit("OPERATIONAL_MANUAL_BATCH" if mode=="HISTORICAL" else "OPERATIONAL_SCHEDULED_BATCH",actor,cutoff,counts=counts)
            if counts["failed"]:
                repo.audit("OPERATIONAL_PARTIAL_FAILURE",actor,cutoff,counts=counts,reason="PARTIAL_BATCH_FAILURE")
        return {"cutoff":cutoff.isoformat(),"mode":mode,**counts}

    def attention(self, repo, person, cutoff, output, actor, analytics=None):
        analytics = analytics or OperationalAnalyticsService(repo).calculate(person, cutoff)
        current = evaluate_attention(analytics, output)
        if current["status"] != "VALID" or current["band"] != "HIGH":
            return False
        previous = repo.governed(person["id"],cutoff-timedelta(days=1))
        if len(previous)!=1:
            return False
        preceding = evaluate_attention(OperationalAnalyticsService(repo).calculate(person, cutoff-timedelta(days=1)), previous[0])
        if preceding["status"] != "VALID" or preceding["band"] != "HIGH":
            return False
        a = TABLES["audit_events"]
        breaks = repo.connection.execute(select(a.c.created_at).where(
            a.c.resource_id==person["id"],
            a.c.action.in_(("OPERATIONAL_PERSON_UNAVAILABLE","OPERATIONAL_PERSON_FAILURE")),
            a.c.metadata_json["cutoff"].astext.in_((cutoff.isoformat(),(cutoff-timedelta(days=1)).isoformat())),
        )).first()
        if breaks:
            return False
        alerts, outputs = TABLES["alerts"], TABLES["model_outputs"]
        # Same parent row lock owns replay, cross-policy family suppression and cooldown.
        history = repo.connection.execute(select(alerts,outputs.c.prediction_date.label("emission_cutoff")).outerjoin(
            outputs, alerts.c.source_id==outputs.c.id).where(alerts.c.personnel_id==person["id"],alerts.c.alert_type==FAMILY)
            .order_by(alerts.c.created_at.desc(),alerts.c.id)).mappings().all()
        if any(row["status"] in ("OPEN","ACKNOWLEDGED") for row in history):
            return False
        if any(cutoff < (row["emission_cutoff"] or row["created_at"].date()) + timedelta(days=7) for row in history):
            return False
        key = f"{person['id']}:{FAMILY}:{POLICY}:{cutoff.isoformat()}"
        if repo.connection.execute(select(alerts.c.id).where(alerts.c.dedupe_key==key)).first():
            return False
        alert_id = uuid.uuid4()
        repo.connection.execute(insert(alerts).values(id=alert_id,personnel_id=person["id"],unit_id=person["unit_id"],
             alert_type=FAMILY,severity="HIGH",source_type="MODEL_A",source_id=output["id"],status="OPEN",
             dedupe_key=key,message="Sustained elevated operational workload/recovery attention.",
             created_at=datetime.now(timezone.utc)))
        repo.audit("OPERATIONAL_ALERT_CREATED",actor,cutoff,source_hash=output["explanation_json"]["source_hash"],personnel_id=person["id"])
        return True

    def project(self, actor, cutoff=None, limit=50, cursor=None):
        role = actor.get("role")
        if role not in ("PERSONNEL","COMMANDER","WELFARE_OFFICER","ADMIN"):
            raise PermissionError("ROLE_REQUIRED")
        if role=="PERSONNEL" and not actor.get("personnel_id"):
            raise PermissionError("PERSONNEL_SCOPE_REQUIRED")
        if role in ("COMMANDER","WELFARE_OFFICER") and not actor.get("unit_id"):
            raise PermissionError("UNIT_SCOPE_REQUIRED")
        with self.engine.begin() as c:
            repo = DetectionRepository(c)
            if role=="ADMIN":
                # Governance counts only; never an individual welfare projection.
                return {"model_version":MODEL_VERSION,"feature_set_version":FEATURE_VERSION,
                        "model_status":self.loader.status,"scheduler_cadence":"00:15 UTC",
                        "security":"APPLICATION_AUTHORIZATION_AND_QUERY_SCOPING"}
            people = repo.people(uuid.UUID(actor["unit_id"])) if role!="PERSONNEL" else repo.rows(
                "personnel", TABLES["personnel"].c.id==uuid.UUID(actor["personnel_id"]))
            people.sort(key=lambda p:p["id"])
            if cursor:
                people=[p for p in people if p["id"]>uuid.UUID(str(cursor))]
            items=[]
            for person in people[:limit]:
                effective_cutoff = cutoff or datetime.now(timezone.utc).date()
                rows=repo.governed(person["id"],effective_cutoff)
                latest=rows[0] if rows else None
                a=TABLES["audit_events"]
                failure_query=select(a.c.metadata_json,a.c.created_at).where(
                    a.c.resource_id==person["id"],a.c.action.in_(("OPERATIONAL_PERSON_UNAVAILABLE","OPERATIONAL_PERSON_FAILURE"))
                )
                failure_query=failure_query.where(a.c.metadata_json["cutoff"].astext==effective_cutoff.isoformat())
                failure=c.execute(failure_query.order_by(a.c.created_at.desc()).limit(1)).mappings().first()
                stale = failure and (not latest or failure["created_at"] > latest["created_at"])
                analytics = OperationalAnalyticsService(repo).calculate(person, effective_cutoff)
                attention = evaluate_attention(analytics, latest if not stale else None)
                item={"pseudo_id":person["pseudo_id"],"status":attention["status"],
                      "cutoff":latest["prediction_date"].isoformat() if latest and not stale else failure["metadata_json"].get("cutoff") if failure else None,
                      "probability":float(latest["hr_probability"]) if latest and not stale else None,
                      "score":float(latest["risk_score"]) if latest and not stale else None,
                      "attention_band":attention["band"], "attention":attention,
                      "analytics":analytics, "model_a_status":"VALID" if latest and not stale else "MODEL_UNAVAILABLE"}
                items.append(item)
            return {"items":items,"next_cursor":str(people[limit-1]["id"]) if len(people)>limit else None}
