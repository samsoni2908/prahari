"""Isolated PostgreSQL 16 Stage-3 proofs, no retained writes or app login."""
import json
import hashlib
import asyncio
import math
import os
import tempfile
import unittest
import uuid
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, insert, select, update, text, event
from sqlalchemy.engine import make_url
from app.config import settings
from app.repositories.detection_repository import DetectionRepository, TABLES
from app.analytics.operational_feature_adapter import OperationalFeatureAdapter, FAMILIES, POLICY, source_hash, row_key
from app.services.operational_attention_service import OperationalAttentionService, FAMILY
from app.ml.features_hr import FEATURE_SET_B
from app.ml.runtime_loader import model_a_runtime, ModelARuntimeLoader
from app.analytics.operational_scheduler import OperationalScheduler, completed_day_run

DB="prahari_test_stage3_20261018"
CUTOFF=date(2026,3,15)
PROOFS=[]


class FixedLoader:
    status="MODEL_AVAILABLE"
    def __init__(self,band="HIGH"):
        self.band=band
    def predict_operational_attention(self,features):
        assert tuple(features)==tuple(FEATURE_SET_B) and len(features)==15
        if self.band=="UNAVAILABLE":
            return {"availability_status":"MODEL_UNAVAILABLE"}
        return {"availability_status":"MODEL_AVAILABLE","calibrated_probability":0.2 if self.band=="HIGH" else 0.1,
                "operational_strain_score":75.0 if self.band=="HIGH" else 50.0,
                "operational_attention_band":self.band,"predicted_class":int(self.band=="HIGH"),
                "top_operational_drivers":[]}


class DetectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_settings_urls = settings.DATABASE_URL, settings.DATABASE_URL_SYNC
        source=make_url(os.environ.get("PRAHARI_TEST_DATABASE_URL", settings.DATABASE_URL_SYNC)).set(drivername="postgresql")
        cls.url=source.set(database=DB)
        assert cls.url.host in {"postgres", "localhost", "127.0.0.1"} and cls.url.database==DB and DB.startswith("prahari_test_")
        cls.engine=create_engine(cls.url,hide_parameters=True)
        with cls.engine.connect() as c:
            assert c.execute(text("SELECT current_database()")).scalar_one()==DB
            assert int(c.execute(text("SELECT current_setting('server_version_num')")).scalar_one())//10000==16
            tables=c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")).all()
            if tables:
                assert len(tables)==32 and c.execute(text("SELECT version_num FROM alembic_version")).scalars().all()==["e26186_stage2_schema"], "Refusing incompatible disposable DB"
        old=settings.DATABASE_URL_SYNC
        settings.DATABASE_URL=cls.url.set(drivername="postgresql+asyncpg").render_as_string(hide_password=False)
        try:
            settings.DATABASE_URL_SYNC=cls.url.render_as_string(hide_password=False)
            command.upgrade(Config(str(Path(__file__).resolve().parents[1] / "alembic.ini")),"e26186_stage2_schema")
        finally:
            settings.DATABASE_URL_SYNC=old
        # Application imports below must bind only this exact disposable runtime.
        settings.DATABASE_URL_SYNC=cls.url.render_as_string(hide_password=False)
        settings.DATABASE_URL=cls.url.set(drivername="postgresql+asyncpg").render_as_string(hide_password=False)
        import app.db.session
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        if not hasattr(cls, "_orig_async_engine"):
            cls._orig_async_engine = app.db.session.engine
            cls._orig_async_session_local = app.db.session.AsyncSessionLocal
        app.db.session.engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            hide_parameters=True,
            future=True,
            pool_pre_ping=True,
        )
        app.db.session.AsyncSessionLocal = async_sessionmaker(
            bind=app.db.session.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        import app.security.deps
        if not hasattr(cls, "_orig_deps_session_local"):
            cls._orig_deps_session_local = app.security.deps.AsyncSessionLocal
        app.security.deps.AsyncSessionLocal = app.db.session.AsyncSessionLocal
        def reject_private(conn,cursor,statement,parameters,context,executemany):
            lowered=statement.lower()
            if any(word in lowered for word in ("wellbeing_private","wellbeing_results","wellbeing_consent")):
                raise AssertionError("Private table queried by detection")
        event.listen(cls.engine,"before_cursor_execute",reject_private)

    @classmethod
    def tearDownClass(cls):
        settings.DATABASE_URL, settings.DATABASE_URL_SYNC = cls._orig_settings_urls
        if hasattr(cls, "_orig_async_engine"):
            import app.db.session
            app.db.session.engine = cls._orig_async_engine
            app.db.session.AsyncSessionLocal = cls._orig_async_session_local
        if hasattr(cls, "_orig_deps_session_local"):
            import app.security.deps
            app.security.deps.AsyncSessionLocal = cls._orig_deps_session_local

    def setUp(self):
        self.unit,self.admin=uuid.uuid4(),uuid.uuid4()
        self.people=[uuid.uuid4() for _ in range(5)]
        self.actor={"user_id":str(self.admin),"role":"ADMIN"}
        with self.engine.begin() as c:
            c.execute(insert(TABLES["units"]).values(id=self.unit,unit_code=str(self.unit),unit_name="Synthetic proof",unit_type="TEST",sanctioned_strength=5))
            c.execute(insert(TABLES["users"]).values(id=self.admin,username=str(self.admin),password_hash="test-only",role="ADMIN"))
            for i,pid in enumerate(self.people):
                c.execute(insert(TABLES["personnel"]).values(id=pid,personnel_code=str(pid),pseudo_id="SYN-"+str(pid),full_name="Private fixture name",unit_id=self.unit,rank_or_grade="TEST",role_title="TEST",status="ACTIVE"))
                c.execute(insert(TABLES["leave_records"]).values(id=uuid.uuid4(),personnel_id=pid,
                    leave_type="TEST",start_date=date(2025,12,18),end_date=date(2025,12,20),days=3,
                    status="COMPLETED",actual_start_date=date(2025,12,18),actual_end_date=date(2025,12,20)))
                c.execute(insert(TABLES["posting_history"]).values(id=uuid.uuid4(),personnel_id=pid,unit_id=self.unit,posting_start_date=date(2025,1,1),posting_type="TEST"))
                for j in range(90):
                    day=date(2026,1,1)+timedelta(days=j)
                    if j%7:
                        start=datetime.combine(day,datetime.min.time(),timezone.utc)+timedelta(hours=6)
                        hours=6+i*0.5+(j%3)*0.2
                        c.execute(insert(TABLES["duties"]).values(id=uuid.uuid4(),personnel_id=pid,unit_id=self.unit,duty_date=day,start_at=start,end_at=start+timedelta(hours=hours),hours=hours,duty_type="TEST",shift_type="DAY",is_night=(j%4==0)))
                    c.execute(insert(TABLES["rest_records"]).values(id=uuid.uuid4(),personnel_id=pid,record_date=day,rest_hours=12,rest_gap_hours=14,source="TEST",data_quality_status="VALID"))
            for j in range(90):
                day=date(2026,1,1)+timedelta(days=j)
                c.execute(insert(TABLES["staffing"]).values(id=uuid.uuid4(),unit_id=self.unit,record_date=day,sanctioned_strength=5,available_strength=5,required_strength=5))
        self.service=OperationalAttentionService(self.engine,FixedLoader())

    def certify(self,cutoff=CUTOFF,changes=None):
        with self.engine.begin() as c:
            repo=DetectionRepository(c)
            data=repo.sources(self.unit,cutoff)
            manifest={"policy":POLICY,"cutoff":cutoff.isoformat(),"source_hash":source_hash(data),"families":sorted(FAMILIES),"unknown_gaps":0,
                      "complete_days":{str(p):[(cutoff-timedelta(days=i)).isoformat() for i in range(1,58)] for p in self.people},
                      "known_at":{name+"."+row_key(row):"2025-12-01T00:00:00+00:00" for name,rows in data.items() for row in rows}}
            for name,rows in data.items():
                for row in rows:
                    completed=row["end_at"] if name=="duties" else datetime.combine(row["record_date"]+timedelta(days=1),datetime.min.time(),timezone.utc) if name=="rest_records" else None
                    if completed is not None:
                        manifest["known_at"][name+"."+row_key(row)]=completed.isoformat()
            if changes:
                manifest.update(changes)
            key=f"analytics.coverage.{self.unit}.{cutoff.isoformat()}"
            existing=c.execute(select(TABLES["policy_config"].c.id).where(TABLES["policy_config"].c.policy_key==key)).scalar_one_or_none()
            if existing:
                c.execute(update(TABLES["policy_config"]).where(TABLES["policy_config"].c.id==existing).values(policy_value_json=manifest))
            else:
                c.execute(insert(TABLES["policy_config"]).values(id=uuid.uuid4(),policy_key=key,policy_value_json=manifest,version=POLICY,updated_by_user_id=self.admin,effective_from=datetime(2025,1,1,tzinfo=timezone.utc)))
            # Explicit test-only WSI policy and independent coverage evidence.
            # These fixtures exercise the new mandatory WSI gate, not a mocked score.
            policy=TABLES["policy_config"]
            if not c.execute(select(policy.c.id).where(policy.c.policy_key=="analytics.wsi")).first():
                values={"wsi.d.reference_hours":56,"wsi.r.reference_hours":12,
                    "wsi.c.reference_days":7,"wsi.l.reference_days":60,"wsi.h.reference_intensity":5}
                digest=hashlib.sha256(json.dumps(values,sort_keys=True,separators=(",",":")).encode()).hexdigest()
                c.execute(insert(policy).values(id=uuid.uuid4(),policy_key="analytics.wsi",version="TEST_WSI_V1",
                    policy_value_json={"activation_status":"ACTIVE","values":values,"content_hash":digest},
                    updated_by_user_id=self.admin,effective_from=datetime(2025,1,1,tzinfo=timezone.utc),
                    created_at=datetime(2025,1,1,tzinfo=timezone.utc)))
            wsi_data=repo.wsi_sources(self.unit,cutoff)
            wsi_manifest={**manifest,"source_hash":source_hash(wsi_data),
                "known_at":{name+"."+row_key(row):datetime.combine(cutoff,datetime.min.time(),timezone.utc).isoformat()
                    for name,rows in wsi_data.items() for row in rows},
                "leave_completion_history_complete":{str(p):True for p in self.people}}
            wsi_key=f"analytics.wsi.coverage.{self.unit}.{cutoff.isoformat()}"
            wsi_existing=c.execute(select(policy.c.id).where(policy.c.policy_key==wsi_key)).scalar_one_or_none()
            if wsi_existing:
                c.execute(update(policy).where(policy.c.id==wsi_existing).values(policy_value_json=wsi_manifest))
            else:
                c.execute(insert(policy).values(id=uuid.uuid4(),policy_key=wsi_key,version=POLICY,
                    policy_value_json=wsi_manifest,updated_by_user_id=self.admin))
        return manifest

    def run_day(self,day=CUTOFF,service=None,**kw):
        return (service or self.service).run(day,actor=self.actor,unit_id=self.unit,**kw)

    def count(self,table):
        with self.engine.connect() as c:
            t=TABLES[table]
            return c.execute(select(t.c.id).where(t.c.personnel_id.in_(self.people))).all()

    def test_real_e2e_exact_vector_and_no_training(self):
        self.certify()
        with self.engine.connect() as c:
            result=OperationalFeatureAdapter(DetectionRepository(c)).build(self.people[0],self.unit,CUTOFF)
        self.assertEqual(result.status,"VALID")
        self.assertEqual(result.feature_names,tuple(FEATURE_SET_B))
        self.assertEqual(len(result.feature_vector),15)
        self.assertTrue(all(math.isfinite(x) for x in result.feature_vector))
        for altered in (replace(result, feature_names=tuple(reversed(result.feature_names))),
                        replace(result, feature_vector=result.feature_vector[:-1]),
                        replace(result, feature_vector=result.feature_vector+(1.0,)),
                        replace(result, feature_vector=(float("inf"),)+result.feature_vector[1:])):
            with self.assertRaises(ValueError):
                altered.as_features()
        self.assertFalse(hasattr(model_a_runtime.artifact["preprocessor"], "fit"))
        self.assertFalse(hasattr(model_a_runtime.artifact["calibrator"], "fit"))
        # Install failing sentinels after proving fitting is absent; any attempted
        # runtime training still fails this real database/inference flow.
        with patch.object(type(model_a_runtime.artifact["preprocessor"]),"fit",create=True,side_effect=AssertionError("runtime training")),patch.object(type(model_a_runtime.artifact["calibrator"]),"fit",create=True,side_effect=AssertionError("runtime training")):
            run=self.run_day(service=OperationalAttentionService(self.engine,model_a_runtime))
        self.assertEqual(run["valid"],5)
        self.assertEqual(run["failed"],0)
        with self.engine.connect() as c:
            rows=DetectionRepository(c).governed(self.people[0],CUTOFF)
            self.assertEqual(len(rows),1)
            row=rows[0]
            self.assertIsNone(row["wellbeing_probability"])
            self.assertIsNone(row["combined_probability"])
            self.assertEqual(row["training_data_version"],"v2.1-frozen-prototype")
            PROOFS.append({"cutoff":str(CUTOFF),"features":list(result.feature_names),"vector_size":15,"probability":str(row["hr_probability"]),"band":row["risk_level"],"status":result.status})
        self.run_day(service=OperationalAttentionService(self.engine,model_a_runtime))
        self.assertEqual(len(self.count("model_outputs")),5)

    def test_high_sustain_replay_open_ack_cooldown_concurrency(self):
        self.certify()
        self.assertEqual(self.run_day()["alerts_created"],0)
        next_day=CUTOFF+timedelta(days=1)
        self.certify(next_day)
        with ThreadPoolExecutor(max_workers=2) as pool:
            runs=list(pool.map(lambda _:self.run_day(next_day),range(2)))
        self.assertEqual(sum(r["alerts_created"] for r in runs),5)
        self.assertEqual(len(self.count("alerts")),5)
        self.assertEqual(self.run_day(next_day)["alerts_created"],0)
        with self.engine.begin() as c:
            c.execute(update(TABLES["alerts"]).where(TABLES["alerts"].c.personnel_id.in_(self.people)).values(status="ACKNOWLEDGED"))
        d2=next_day+timedelta(days=1)
        self.certify(d2)
        self.assertEqual(self.run_day(d2)["alerts_created"],0)
        with self.engine.begin() as c:
            c.execute(update(TABLES["alerts"]).where(TABLES["alerts"].c.personnel_id.in_(self.people)).values(status="RESOLVED",resolved_at=datetime.now(timezone.utc)))
        d3=d2+timedelta(days=1)
        self.certify(d3)
        self.assertEqual(self.run_day(d3)["alerts_created"],0)
        d7=next_day+timedelta(days=6)
        self.certify(d7)
        self.assertEqual(self.run_day(d7)["alerts_created"],0)
        d8=next_day+timedelta(days=7)
        self.certify(d8)
        self.assertEqual(self.run_day(d8)["alerts_created"],5)
        self.assertEqual(len(self.count("alerts")),10)

    def test_real_artifact_high_progression(self):
        # Controlled disposable operational exposure; no score/label fabrication.
        with self.engine.begin() as c:
            for i,pid in enumerate(self.people):
                c.execute(text("UPDATE duties SET hours=:hours,start_at=date_trunc('day',start_at)+interval '2 hours',end_at=date_trunc('day',start_at)+interval '2 hours'+(:hours*interval '1 hour'),is_night=true,shift_type='NIGHT' WHERE personnel_id=:pid AND duty_date>=:start"),
                    {"hours":12+i*.2,"pid":pid,"start":CUTOFF-timedelta(days=30)})
                rest=TABLES["rest_records"]
                c.execute(update(rest).where(rest.c.personnel_id==pid,rest.c.record_date>=CUTOFF-timedelta(days=30)).values(rest_hours=4,rest_gap_hours=6))
            c.execute(update(TABLES["staffing"]).where(TABLES["staffing"].c.unit_id==self.unit).values(available_strength=2))
        real=OperationalAttentionService(self.engine,model_a_runtime)
        self.certify()
        first=self.run_day(service=real)
        self.assertEqual(first["valid"],5)
        self.assertEqual(first["alerts_created"],0)
        with self.engine.connect() as c:
            row=DetectionRepository(c).governed(self.people[0],CUTOFF)[0]
            self.assertEqual(row["risk_level"],"HIGH")
            PROOFS.append({"cutoff":str(CUTOFF),"probability":str(row["hr_probability"]),"band":"HIGH","real_artifact":True})
        second=CUTOFF+timedelta(days=1)
        self.certify(second)
        progressed=self.run_day(second,service=real)
        self.assertEqual(progressed["alerts_created"],5)
        self.assertEqual(self.run_day(second,service=real)["alerts_created"],0)
        self.assertEqual(len(self.count("alerts")),5)

    def test_missing_wsi_breaks_high_sustain_and_job_availability(self):
        self.certify()
        self.assertEqual(self.run_day()["valid"], 5)
        next_day = CUTOFF + timedelta(days=1)
        self.certify(next_day)
        with self.engine.begin() as c:
            policy = TABLES["policy_config"]
            c.execute(policy.delete().where(policy.c.policy_key == f"analytics.wsi.coverage.{self.unit}.{next_day}"))
        result = self.run_day(next_day)
        self.assertEqual(result["valid"], 0)
        self.assertEqual(result["unavailable"], 5)
        self.assertEqual(result["alerts_created"], 0)
        projected = self.service.project({"role":"COMMANDER", "unit_id":str(self.unit)}, next_day)
        self.assertTrue(all(item["attention_band"] is None for item in projected["items"]))
        third_day = next_day + timedelta(days=1)
        self.certify(third_day)
        self.assertEqual(self.run_day(third_day)["alerts_created"], 0)

    def test_medium_visible_and_unavailable_break(self):
        self.certify()
        medium=OperationalAttentionService(self.engine,FixedLoader("MEDIUM"))
        self.assertEqual(self.run_day(service=medium)["alerts_created"],0)
        actor={"role":"COMMANDER","unit_id":str(self.unit)}
        self.assertTrue(all(i["attention_band"]=="MEDIUM" for i in medium.project(actor,CUTOFF)["items"]))
        next_day=CUTOFF+timedelta(days=1)
        self.assertEqual(self.run_day(next_day)["unavailable"],5)
        self.certify(next_day+timedelta(days=1))
        self.assertEqual(self.run_day(next_day+timedelta(days=1))["alerts_created"],0)
        projected=self.service.project(actor,next_day)
        self.assertTrue(all(i["status"]=="NOT_COMPUTED" and i["attention_band"] is None for i in projected["items"]))

    def test_coverage_cutoff_private_exclusion_missing_and_nonfinite(self):
        self.certify()
        with self.engine.connect() as c:
            repo=DetectionRepository(c)
            adapter=OperationalFeatureAdapter(repo)
            initial=adapter.build(self.people[0],self.unit,CUTOFF)
            self.assertEqual(initial.status,"VALID")
            self.assertTrue(all(row["duty_date"] < CUTOFF for row in repo.sources(self.unit,CUTOFF)["duties"]))
        self.certify(changes={"unknown_gaps":1})
        self.assertEqual(self.run_day()["unavailable"],5)
        self.assertEqual(len(self.count("model_outputs")),0)
        self.certify()
        with self.engine.begin() as c:
            t=TABLES["rest_records"]
            c.execute(update(t).where(t.c.personnel_id==self.people[0],t.c.record_date==CUTOFF-timedelta(days=1)).values(rest_hours=-1))
        self.certify()
        with self.engine.connect() as c:
            result=OperationalFeatureAdapter(DetectionRepository(c)).build(self.people[0],self.unit,CUTOFF)
        self.assertEqual(result.status,"COMPUTATION_ERROR")
        isolated=self.run_day()
        self.assertEqual(isolated["unavailable"],1)
        self.assertEqual(isolated["valid"],4)
        self.certify(changes={"known_at":{}})
        self.assertEqual(self.run_day()["unavailable"],5)

    def test_loader_and_feature_count_order(self):
        self.assertEqual(model_a_runtime.status,"MODEL_AVAILABLE")
        missing=ModelARuntimeLoader(Path(tempfile.gettempdir()) / "stage3_missing_c933aabc.joblib")
        self.assertEqual(missing.status,"MODEL_UNAVAILABLE")
        with tempfile.TemporaryDirectory(prefix="prahari_stage3_", dir=Path(__file__).resolve().parent) as test_dir:
            bad=Path(test_dir) / "invalid.joblib"
            bad.write_bytes(b"not-the-approved-artifact")
            self.assertEqual(ModelARuntimeLoader(bad).status,"MODEL_UNAVAILABLE")
        for features in ({k:1.0 for k in FEATURE_SET_B[:-1]},{**dict.fromkeys(FEATURE_SET_B,1.0),"extra":1.0},{**dict.fromkeys(FEATURE_SET_B,1.0),FEATURE_SET_B[0]:float("nan")}):
            prediction=model_a_runtime.predict_operational_attention(features)
            self.assertEqual(prediction["availability_status"],"MODEL_UNAVAILABLE")
            self.assertIsNone(prediction["calibrated_probability"])

    def test_truthful_source_and_model_unavailability(self):
        self.certify()
        missing=ModelARuntimeLoader(Path(tempfile.gettempdir()) / "stage3_missing_c933aabc.joblib")
        run=self.run_day(service=OperationalAttentionService(self.engine,missing))
        self.assertEqual(run["unavailable"],5)
        self.assertEqual(len(self.count("model_outputs")),0)
        view=self.service.project({"role":"PERSONNEL","personnel_id":str(self.people[0])},CUTOFF)
        self.assertEqual(view["items"][0]["status"],"MODEL_UNAVAILABLE")
        self.assertIsNone(view["items"][0]["attention_band"])
        with self.engine.begin() as c:
            t=TABLES["rest_records"]
            c.execute(update(t).where(t.c.personnel_id==self.people[0],t.c.record_date==CUTOFF-timedelta(days=1)).values(record_date=CUTOFF+timedelta(days=90)))
        with self.engine.connect() as c:
            result=OperationalFeatureAdapter(DetectionRepository(c)).build(self.people[0],self.unit,CUTOFF)
            self.assertEqual(result.status,"DATA_STALE")
        self.certify()
        with self.engine.connect() as c:
            result=OperationalFeatureAdapter(DetectionRepository(c)).build(self.people[0],self.unit,CUTOFF)
            self.assertEqual(result.status,"REST_DATA_MISSING")
        with self.engine.begin() as c:
            c.execute(update(TABLES["personnel"]).where(TABLES["personnel"].c.id==self.people[0]).values(rank_or_grade="DIFFERENT"))
        self.certify()
        with self.engine.connect() as c:
            result=OperationalFeatureAdapter(DetectionRepository(c)).build(self.people[0],self.unit,CUTOFF)
            self.assertEqual(result.status,"PEER_COHORT_INSUFFICIENT")

    def test_failure_isolation_and_safe_audit(self):
        self.certify()
        bad=self.people[0]
        class OneBrokenAdapter(OperationalFeatureAdapter):
            def build(inner,pid,unit,cutoff):
                if pid==bad:
                    raise ValueError("never log sensitive fixture text")
                return super().build(pid,unit,cutoff)
        run=self.run_day(service=OperationalAttentionService(self.engine,FixedLoader(),OneBrokenAdapter))
        self.assertEqual(run["failed"],1)
        self.assertEqual(run["valid"],4)
        with self.engine.connect() as c:
            a=TABLES["audit_events"]
            meta=c.execute(select(a.c.metadata_json).where(a.c.resource_type=="OPERATIONAL_DETECTION")).scalars().all()
        self.assertNotIn("sensitive",json.dumps(meta))
        self.assertNotIn("wellbeing",json.dumps(meta))

    def test_role_scope_legacy_and_manual_idempotency(self):
        self.certify()
        with self.engine.begin() as c:
            c.execute(insert(TABLES["model_outputs"]).values(id=uuid.uuid4(),personnel_id=self.people[0],prediction_date=CUTOFF,target_name="target_leave_anomaly",hr_probability=0.9,risk_score=99,risk_level="HIGH",model_name="Legacy",model_version="old",feature_set_version="old"))
        first=self.run_day(request_key="stage3-key-123")
        self.assertEqual(self.run_day(request_key="stage3-key-123"),first)
        with self.assertRaises(ValueError):
            self.run_day(CUTOFF+timedelta(days=1),request_key="stage3-key-123")
        commander={"role":"COMMANDER","unit_id":str(self.unit)}
        welfare={"role":"WELFARE_OFFICER","unit_id":str(self.unit)}
        for actor in (commander,welfare):
            result=self.service.project(actor,CUTOFF)
            self.assertEqual(len(result["items"]),5)
            self.assertNotIn("full_name",json.dumps(result))
            self.assertNotIn("personnel_code",json.dumps(result))
            self.assertNotIn("wellbeing",json.dumps(result))
            self.assertNotIn("request_text",json.dumps(result))
        own=self.service.project({"role":"PERSONNEL","personnel_id":str(self.people[0])},CUTOFF)
        self.assertEqual(len(own["items"]),1)
        self.assertEqual(own["items"][0]["pseudo_id"],"SYN-"+str(self.people[0]))
        self.assertFalse(self.service.project({"role":"COMMANDER","unit_id":str(uuid.uuid4())})["items"])
        self.assertNotIn("items",self.service.project(self.actor))
        with self.assertRaises(PermissionError):
            self.service.run(CUTOFF,actor=commander)
        page=self.service.project(commander,CUTOFF,limit=2)
        self.assertEqual(len(page["items"]),2)
        self.assertIsNotNone(page["next_cursor"])
        self.assertEqual(len(self.service.project(commander,CUTOFF,limit=2,cursor=page["next_cursor"])["items"]),2)
        with self.engine.connect() as c:
            original=DetectionRepository(c).governed(self.people[0],CUTOFF)[0]
        with self.engine.begin() as c:
            t=TABLES["rest_records"]
            c.execute(update(t).where(t.c.personnel_id==self.people[0],t.c.record_date==CUTOFF-timedelta(days=1)).values(rest_hours=11))
        self.certify()
        self.assertEqual(self.run_day()["unavailable"],5)
        with self.engine.connect() as c:
            preserved=DetectionRepository(c).governed(self.people[0],CUTOFF)[0]
        self.assertEqual(preserved["id"],original["id"])
        self.assertEqual(preserved["explanation_json"]["source_hash"],original["explanation_json"]["source_hash"])

    def test_scheduler_single_owner_and_no_startup_processing(self):
        service=self.service
        with patch.object(service,"run",side_effect=AssertionError("startup backlog")):
            first=OperationalScheduler(self.engine,service)
            second=OperationalScheduler(self.engine,service)
            try:
                self.assertTrue(first.start())
                self.assertFalse(second.start())
                job=first.scheduler.get_job("operational_completed_day")
                self.assertEqual(str(job.trigger.timezone),"UTC")
                self.assertIn("hour='0'",str(job.trigger))
                self.assertIn("minute='15'",str(job.trigger))
            finally:
                second.stop()
                first.stop()
        with patch.object(service,"run",return_value={"ok":True}) as run:
            self.assertEqual(completed_day_run(service),{"ok":True})
            run.assert_called_once_with(datetime.now(timezone.utc).date(),mode="SCHEDULED")

    def test_api_auth_role_scope_csrf_and_governance(self):
        self.certify()
        import httpx
        from app.main import app
        from app.security.jwt import create_access_token
        from app.db.session import engine as async_engine
        self.assertEqual(async_engine.url.database,DB)
        self.assertIn(async_engine.url.host,{"postgres", "localhost", "127.0.0.1"})
        credentials={}
        with self.engine.begin() as c:
            for role in ("PERSONNEL","COMMANDER","WELFARE_OFFICER","ADMIN"):
                uid=self.admin if role=="ADMIN" else uuid.uuid4()
                if role!="ADMIN":
                    c.execute(insert(TABLES["users"]).values(id=uid,username=str(uid),password_hash="test-only",role=role,
                        unit_id=self.unit,personnel_id=self.people[0] if role=="PERSONNEL" else None))
                jti=uuid.uuid4()
                c.execute(insert(TABLES["auth_sessions"]).values(
                    id=uuid.uuid4(),user_id=uid,jti=jti,
                    refresh_secret_hash="dummy_hash",
                    expires_at=datetime.now(timezone.utc)+timedelta(hours=1),
                    last_seen_at=datetime.now(timezone.utc)
                ))
                credentials[role]=create_access_token(
                    subject="fixture",
                    role=role,
                    user_id=str(uid),
                    session_jti=str(jti),
                    unit_id=str(self.unit) if role != "ADMIN" else None,
                    personnel_id=str(self.people[0]) if role=="PERSONNEL" else None,
                )
        async def proof():
            try:
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
                    self.assertEqual((await client.get("/api/v1/operational/attention")).status_code,401)
                    request={"cutoff":str(CUTOFF),"unit_id":str(self.unit)}
                    for role in ("PERSONNEL","COMMANDER","WELFARE_OFFICER"):
                        r=await client.post("/api/v1/admin/operational-runs",json=request,headers={"Authorization":"Bearer "+credentials[role],"Idempotency-Key":"api-key-123"})
                        self.assertEqual(r.status_code,403)
                    client.cookies.set("prahari_session",credentials["ADMIN"])
                    csrf=await client.post("/api/v1/admin/operational-runs",json=request,headers={"Idempotency-Key":"api-key-123"})
                    self.assertEqual(csrf.status_code,403)
                    client.cookies.clear()
                    admin_headers={"Authorization":"Bearer "+credentials["ADMIN"],"Idempotency-Key":"api-key-123"}
                    run=await client.post("/api/v1/admin/operational-runs",json=request,headers=admin_headers)
                    self.assertEqual(run.status_code,200,run.text)
                    self.assertEqual(run.json()["valid"],5)
                    self.assertEqual((await client.post("/api/v1/admin/operational-runs",json=request,headers=admin_headers)).json(),run.json())
                    for role in credentials:
                        projected=await client.get("/api/v1/operational/attention",params={"cutoff":str(CUTOFF)},headers={"Authorization":"Bearer "+credentials[role]})
                        self.assertEqual(projected.status_code,200)
                        payload=projected.json()
                        self.assertNotIn("Private fixture name",json.dumps(payload))
                        self.assertNotIn("personnel_code",json.dumps(payload))
                        self.assertNotIn("wellbeing",json.dumps(payload))
                        if role=="ADMIN":
                            self.assertNotIn("items",payload)
                        else:
                            self.assertEqual(len(payload["items"]),1 if role=="PERSONNEL" else 5)
                        if role=="COMMANDER":
                            detail=await client.get("/api/v1/commander/strain-card/"+str(self.people[0]),headers={"Authorization":"Bearer "+credentials[role]})
                            self.assertEqual(detail.status_code,200)
                            self.assertEqual(detail.json()["prediction"]["status"],"VALID")
                            self.assertIsNotNone(detail.json()["prediction"]["risk_probability"])
            finally:
                await async_engine.dispose()
        asyncio.run(proof())


if __name__=="__main__":
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(DetectionTests)
    outcome=unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"tests":outcome.testsRun,"failures":len(outcome.failures),"errors":len(outcome.errors),"skipped":len(outcome.skipped),"e2e":PROOFS}))
    raise SystemExit(not outcome.wasSuccessful())
