"""Stage 4B Comprehensive Test Suite: BALANCE, Scenarios, Hard Constraints, Human Decisions & APIs.

Targeting disposable DB: prahari_stage4a_upgrade_20261005.
Retained DB 'prahari' remains 100% READ-ONLY and untouched.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import os
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from fastapi import HTTPException, Request

from app.main import app
from app.db.session import get_db
from app.security.deps import get_current_user, get_db_with_rls
from app.security.jwt import create_access_token
from app.planning.adapter import PlanningSourceAdapter
from app.planning.validator import validate_plan_with_evidence
from app.planning.optimizer import (
    DeterministicBalanceOptimizer,
    ScheduleMetrics,
    get_lexicographic_score,
)
from app.planning.comparison import compute_scenario_comparison
from app.planning.revision import compute_expected_revision
from app.models import (
    Approval,
    AvailabilityInterval,
    Deployment,
    LeaveRecord,
    Personnel,
    PolicyConfig,
    RosterAssignment,
    RosterScenario,
    ScenarioChange,
    ShiftRequirement,
    Training,
    Unit,
    User,
)
from app.repositories.audit_repository import AuditRepository
from app.repositories.scenario_repository import ScenarioRepository
from app.repositories.unit_repository import UnitRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.personnel_repository import PersonnelRepository
from app.services.scenario_service import ScenarioService, format_scenario_response

# Constants for Stage 4B Test
TEST_DB_URL = os.environ.get(
    "PRAHARI_TEST_DATABASE_URL",
    "postgresql+asyncpg://prahari_app:prahari_dev_password@127.0.0.1:5432/prahari_test_isolated",
)
_test_identity = make_url(TEST_DB_URL)
if (_test_identity.host not in {"127.0.0.1", "localhost", "postgres"}
        or not (_test_identity.database or "").startswith("prahari_test_")):
    raise RuntimeError("Stage workflow tests require a local disposable prahari_test_ database")
DEMO_UNIT_ID = uuid.UUID("e09b8af8-d4b9-c3c1-bc35-89ed1a295ca2")
DEMO_CUTOFF = datetime(2026, 5, 14, 0, 0, 0, tzinfo=timezone.utc)
CANONICAL_SOURCE_HASH = "98248f3ddab2e4b7801ea5f10f797fa115f1398ddba5c4867e56132bb20515aa"

DEMO_COMMANDER_USER_ID = uuid.UUID("fc032c1c-5af3-134a-8304-354f6e788abb")
DEMO_WELFARE_USER_ID = uuid.UUID("1a9571fd-f5b3-c291-b038-21d8bb15ee82")
CROSS_UNIT_COMMANDER_USER_ID = uuid.UUID("d5cce8ef-c1c4-02ef-27a4-387f336a572b")  # from another unit
DEMO_PERSONNEL_USER_ID = uuid.UUID("db564f18-9220-479c-2088-b7adcb367438")
DEMO_ADMIN_USER_ID = uuid.UUID("d34e7c6b-5d68-10b8-efc5-c7c26ae3a66b")


@pytest_asyncio.fixture
async def disposable_session():
    """Provides an isolated AsyncSession bound to the disposable database."""
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool, future=True)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_01_planning_source_adapter_hash_and_counts(disposable_session: AsyncSession):
    """Test planning adapter reproduces canonical hash and correct counts from DB."""
    snapshot = await PlanningSourceAdapter.load_snapshot_async(
        session=disposable_session,
        unit_id=DEMO_UNIT_ID,
        cutoff=DEMO_CUTOFF,
    )

    assert snapshot.is_valid is True
    assert snapshot.source_hash == CANONICAL_SOURCE_HASH
    assert len(snapshot.shift_requirements) == 28
    assert len(snapshot.current_assignments) == 126
    assert len(snapshot.availability_intervals) == 48
    assert len(snapshot.personnel) == 32
    assert snapshot.policy_version in ("BALANCE_SYNTHETIC_DEMO_POLICY_V1", "BALANCE_POLICY_V1")
    assert len(snapshot.policy_hash) == 64


@pytest.mark.asyncio
async def test_02_all_12_hard_constraints_baseline_feasible(disposable_session: AsyncSession):
    """Test all 12 hard constraints against baseline plan returning FEASIBLE."""
    snapshot = await PlanningSourceAdapter.load_snapshot_async(
        session=disposable_session,
        unit_id=DEMO_UNIT_ID,
        cutoff=DEMO_CUTOFF,
    )
    pseudo_map = {p["id"]: p["pseudo_id"] for p in snapshot.personnel}

    val = validate_plan_with_evidence(
        shifts=snapshot.shift_requirements,
        assignments=snapshot.current_assignments,
        availability=snapshot.availability_intervals,
        person_skills=snapshot.person_skills,
        unit_personnel=snapshot.personnel_ids,
        personnel_pseudo_map=pseudo_map,
        approved_leaves=snapshot.approved_leaves,
        trainings=snapshot.trainings,
        deployments=snapshot.deployments,
        prior_duties=snapshot.prior_duties,
        window_start=DEMO_CUTOFF,
        window_end=DEMO_CUTOFF + timedelta(days=14),
    )

    assert val["all_hard_constraints_satisfied"] is True
    assert val["status"] == "FEASIBLE"
    assert len(val["constraints"]) == 12

    # Check evidence for each constraint
    expected_codes = [
        "C01_REQUIRED_COVERAGE",
        "C02_SKILL_COVERAGE",
        "C03_ELIGIBILITY",
        "C04_AVAILABILITY",
        "C05_LEAVE_RESTRICTIONS",
        "C06_TRAINING_RESTRICTIONS",
        "C07_DEPLOYMENT_RESTRICTIONS",
        "C08_NO_OVERLAPS",
        "C09_LOCKED_ASSIGNMENTS",
        "C10_MIN_REST_8H",
        "C11_MAX_DUTY_60H_7D",
        "C12_MAX_CONSECUTIVE_DAYS_6D",
    ]
    for c in expected_codes:
        assert c in val["constraints"]
        ev = val["constraints"][c]
        assert ev["status"] == "PASS"


@pytest.mark.asyncio
async def test_03_constraint_violations_individual_evidence(disposable_session: AsyncSession):
    """Test negative cases for individual constraint violations."""
    snapshot = await PlanningSourceAdapter.load_snapshot_async(
        session=disposable_session,
        unit_id=DEMO_UNIT_ID,
        cutoff=DEMO_CUTOFF,
    )
    pseudo_map = {p["id"]: p["pseudo_id"] for p in snapshot.personnel}
    w_start = DEMO_CUTOFF
    w_end = DEMO_CUTOFF + timedelta(days=14)

    # 1. C01 failure: Under-allocation (drop an assignment)
    dropped = snapshot.current_assignments[1:]
    val1 = validate_plan_with_evidence(
        shifts=snapshot.shift_requirements,
        assignments=dropped,
        availability=snapshot.availability_intervals,
        person_skills=snapshot.person_skills,
        unit_personnel=snapshot.personnel_ids,
        personnel_pseudo_map=pseudo_map,
        approved_leaves=snapshot.approved_leaves,
        trainings=snapshot.trainings,
        deployments=snapshot.deployments,
        prior_duties=snapshot.prior_duties,
        window_start=w_start,
        window_end=w_end,
    )
    assert val1["all_hard_constraints_satisfied"] is False
    assert val1["constraints"]["C01_REQUIRED_COVERAGE"]["status"] == "FAIL"

    # 2. C01 minimum coverage semantics:
    # Under-coverage: assigned < required_count -> FAIL
    # Exact coverage: assigned == required_count -> PASS
    # Over-coverage:  assigned > required_count -> PASS for C01
    first_shift = dict(snapshot.shift_requirements[0])
    s_id = uuid.UUID(str(first_shift["id"]))
    req_cnt = first_shift["required_count"]
    s_assigns = [a for a in snapshot.current_assignments if uuid.UUID(str(a["shift_id"])) == s_id]
    other_assigns = [a for a in snapshot.current_assignments if uuid.UUID(str(a["shift_id"])) != s_id]

    # Case A: assigned < required_count -> FAIL
    under_assigns = other_assigns + s_assigns[:req_cnt - 1]
    val_under = validate_plan_with_evidence(
        shifts=snapshot.shift_requirements,
        assignments=under_assigns,
        availability=snapshot.availability_intervals,
        person_skills=snapshot.person_skills,
        unit_personnel=snapshot.personnel_ids,
        personnel_pseudo_map=pseudo_map,
        approved_leaves=snapshot.approved_leaves,
        trainings=snapshot.trainings,
        deployments=snapshot.deployments,
        prior_duties=snapshot.prior_duties,
        window_start=w_start,
        window_end=w_end,
    )
    assert val_under["constraints"]["C01_REQUIRED_COVERAGE"]["status"] == "FAIL"

    # Case B: assigned == required_count -> PASS
    exact_assigns = other_assigns + s_assigns[:req_cnt]
    val_exact = validate_plan_with_evidence(
        shifts=snapshot.shift_requirements,
        assignments=exact_assigns,
        availability=snapshot.availability_intervals,
        person_skills=snapshot.person_skills,
        unit_personnel=snapshot.personnel_ids,
        personnel_pseudo_map=pseudo_map,
        approved_leaves=snapshot.approved_leaves,
        trainings=snapshot.trainings,
        deployments=snapshot.deployments,
        prior_duties=snapshot.prior_duties,
        window_start=w_start,
        window_end=w_end,
    )
    assert val_exact["constraints"]["C01_REQUIRED_COVERAGE"]["status"] == "PASS"

    # Case C: assigned > required_count -> PASS for C01
    assigned_pids_s = {uuid.UUID(str(a["personnel_id"])) for a in s_assigns}
    available_pids = [pid for pid in snapshot.personnel_ids if pid not in assigned_pids_s]
    if available_pids:
        over_assigns = list(exact_assigns) + [{
            "id": uuid.uuid4(),
            "shift_id": s_id,
            "personnel_id": available_pids[0],
            "is_locked": False,
            "source_revision": "test",
        }]
        val_over = validate_plan_with_evidence(
            shifts=snapshot.shift_requirements,
            assignments=over_assigns,
            availability=snapshot.availability_intervals,
            person_skills=snapshot.person_skills,
            unit_personnel=snapshot.personnel_ids,
            personnel_pseudo_map=pseudo_map,
            approved_leaves=snapshot.approved_leaves,
            trainings=snapshot.trainings,
            deployments=snapshot.deployments,
            prior_duties=snapshot.prior_duties,
            window_start=w_start,
            window_end=w_end,
        )
        assert val_over["constraints"]["C01_REQUIRED_COVERAGE"]["status"] == "PASS"

    # 3. C03 failure: Non-unit personnel assigned
    fake_pid = uuid.uuid4()
    bad_unit_assign = [dict(a) for a in snapshot.current_assignments]
    bad_unit_assign[0]["personnel_id"] = fake_pid
    val3 = validate_plan_with_evidence(
        shifts=snapshot.shift_requirements,
        assignments=bad_unit_assign,
        availability=snapshot.availability_intervals,
        person_skills=snapshot.person_skills,
        unit_personnel=snapshot.personnel_ids,
        personnel_pseudo_map=pseudo_map,
        approved_leaves=snapshot.approved_leaves,
        trainings=snapshot.trainings,
        deployments=snapshot.deployments,
        prior_duties=snapshot.prior_duties,
        window_start=w_start,
        window_end=w_end,
    )
    assert val3["all_hard_constraints_satisfied"] is False
    assert val3["constraints"]["C03_ELIGIBILITY"]["status"] == "FAIL"


@pytest.mark.asyncio
async def test_04_deterministic_optimizer_and_incumbent_preservation(disposable_session: AsyncSession):
    """Test deterministic optimizer produces identical runs and preserves locked assignments."""
    snapshot = await PlanningSourceAdapter.load_snapshot_async(
        session=disposable_session,
        unit_id=DEMO_UNIT_ID,
        cutoff=DEMO_CUTOFF,
    )

    opt = DeterministicBalanceOptimizer()
    run1 = opt.optimize(snapshot)
    run2 = opt.optimize(snapshot)

    # 1. Determinism
    assert run1["status"] == "FEASIBLE"
    assert run2["status"] == "FEASIBLE"
    assert run1["proposed_assignments"] == run2["proposed_assignments"]
    assert run1["changes"] == run2["changes"]
    assert run1["before_metrics"] == run2["before_metrics"]
    assert run1["after_metrics"] == run2["after_metrics"]

    # 2. Commitment preservation (locked Day 0 & Day 1 assignments)
    locked_pairs = {
        (str(a["shift_id"]), str(a["personnel_id"]))
        for a in snapshot.current_assignments
        if a.get("is_locked")
    }
    assert len(locked_pairs) > 0

    proposed_pairs = {
        (str(a["shift_id"]), str(a["personnel_id"]))
        for a in run1["proposed_assignments"]
    }
    for lp in locked_pairs:
        assert lp in proposed_pairs, f"Locked assignment {lp} was violated!"

    # 3. Soft objectives verification (Lexicographical)
    before_m = ScheduleMetrics.from_dict(run1["before_metrics"])
    after_m = ScheduleMetrics.from_dict(run1["after_metrics"])
    score_before = opt.get_lexicographic_score(before_m)
    score_after = opt.get_lexicographic_score(after_m)
    assert score_after <= score_before, "Incumbent did not preserve or improve lexicographical score"


@pytest.mark.asyncio
async def test_05_schedule_comparison_truthful_wsi_null(disposable_session: AsyncSession):
    """Test comparative analysis preserves explicit NULL for projected WSI."""
    snapshot = await PlanningSourceAdapter.load_snapshot_async(
        session=disposable_session,
        unit_id=DEMO_UNIT_ID,
        cutoff=DEMO_CUTOFF,
    )
    opt = DeterministicBalanceOptimizer()
    res = opt.optimize(snapshot)

    comp = compute_scenario_comparison(
        before_metrics=res["before_metrics"],
        after_metrics=res["after_metrics"],
        changes=res["changes"],
    )

    # Workload & recovery changes are computed
    assert "workload" in comp
    assert "recovery" in comp
    assert "disruption" in comp

    # CRITICAL: WSI must be explicitly NOT COMPUTED / NULL
    assert comp["wsi"]["projected_wsi"] is None
    assert comp["wsi"]["projected_wsi_status"] == "PROJECTION_NOT_COMPUTED"


@pytest.mark.asyncio
async def test_06_revision_token_format_and_sensitivity():
    """Test expected_revision token format and sensitivity to protected content changes."""
    sid = uuid.uuid4()
    uid = uuid.uuid4()
    cuid = uuid.uuid4()
    now = datetime(2026, 5, 14, 0, 0, 0, tzinfo=timezone.utc)
    base_kwargs = {
        "scenario_id": sid,
        "unit_id": uid,
        "creator_user_id": cuid,
        "scenario_version": 1,
        "parent_id": None,
        "planning_window": {"start_at": "2026-05-14T00:00:00+00:00", "end_at": "2026-05-28T00:00:00+00:00"},
        "source_hash": CANONICAL_SOURCE_HASH,
        "policy_hash": "p1",
        "status": "FEASIBLE",
        "current_snapshot_json": {"assignments": [{"id": "a1", "personnel_id": "p1"}]},
        "proposed_snapshot_json": {"assignments": [{"id": "a1", "personnel_id": "p2"}]},
        "before_metrics_json": {"night_duties": 4},
        "after_metrics_json": {"night_duties": 2},
        "constraint_results_json": {"all_satisfied": True},
        "optimizer_method": "DETERMINISTIC_LEXICOGRAPHICAL_SWAP_V1",
        "created_at": now,
        "latest_approval_id": None,
    }

    base_rev = compute_expected_revision(**base_kwargs)
    assert base_rev.startswith("rev-sha256-")
    assert len(base_rev) == 75

    # 1. Proposed assignment change -> changes token
    mod_prop = dict(base_kwargs, proposed_snapshot_json={"assignments": [{"id": "a1", "personnel_id": "p3"}]})
    assert compute_expected_revision(**mod_prop) != base_rev

    # 2. Current assignment snapshot change -> changes token
    mod_curr = dict(base_kwargs, current_snapshot_json={"assignments": [{"id": "a1", "personnel_id": "p4"}]})
    assert compute_expected_revision(**mod_curr) != base_rev

    # 3. Planning window change -> changes token
    mod_win = dict(base_kwargs, planning_window={"start_at": "2026-05-15T00:00:00+00:00", "end_at": "2026-05-29T00:00:00+00:00"})
    assert compute_expected_revision(**mod_win) != base_rev

    # 4. Constraint result change -> changes token
    mod_con = dict(base_kwargs, constraint_results_json={"all_satisfied": False})
    assert compute_expected_revision(**mod_con) != base_rev

    # 5. Optimizer execution evidence change -> changes token
    mod_opt = dict(base_kwargs, optimizer_method="HEURISTIC_SWAP_V2")
    assert compute_expected_revision(**mod_opt) != base_rev

    # 6. Source hash change -> changes token
    mod_src = dict(base_kwargs, source_hash="altered_source_hash_123")
    assert compute_expected_revision(**mod_src) != base_rev

    # 7. Policy hash change -> changes token
    mod_pol = dict(base_kwargs, policy_hash="altered_policy_hash_456")
    assert compute_expected_revision(**mod_pol) != base_rev

    # 8. Workflow status change -> changes token
    mod_sta = dict(base_kwargs, status="APPROVED")
    assert compute_expected_revision(**mod_sta) != base_rev

    # 9. Latest decision identity change -> changes token
    mod_dec = dict(base_kwargs, latest_approval_id=uuid.uuid4())
    assert compute_expected_revision(**mod_dec) != base_rev

    # 10. Created at change -> changes token
    mod_cre = dict(base_kwargs, created_at=now + timedelta(seconds=1))
    assert compute_expected_revision(**mod_cre) != base_rev


@pytest.mark.asyncio
async def test_07_scenario_service_idempotent_creation(disposable_session: AsyncSession):
    """Test scenario creation with Idempotency-Key returns safe replay without duplicates."""
    scenario_repo = ScenarioRepository(disposable_session)
    unit_repo = UnitRepository(disposable_session)
    analytics_repo = AnalyticsRepository(disposable_session)
    personnel_repo = PersonnelRepository(disposable_session)
    audit_repo = AuditRepository(disposable_session)

    svc = ScenarioService(
        scenario_repo=scenario_repo,
        unit_repo=unit_repo,
        analytics_repo=analytics_repo,
        personnel_repo=personnel_repo,
        audit_repo=audit_repo,
    )

    idem_key = f"test-key-{uuid.uuid4()}"
    scen_name = f"Test Balance {uuid.uuid4()}"

    res1 = await svc.create_what_if_scenario(
        unit_id=DEMO_UNIT_ID,
        created_by_user_id=DEMO_COMMANDER_USER_ID,
        scenario_name=scen_name,
        cutoff=DEMO_CUTOFF,
        idempotency_key=idem_key,
    )
    await disposable_session.commit()

    # Replay identical request
    res2 = await svc.create_what_if_scenario(
        unit_id=DEMO_UNIT_ID,
        created_by_user_id=DEMO_COMMANDER_USER_ID,
        scenario_name=scen_name,
        cutoff=DEMO_CUTOFF,
        idempotency_key=idem_key,
    )

    assert res1["id"] == res2["id"]
    assert res1["expected_revision"] == res2["expected_revision"]
    assert res2.get("replay_safe") is True

    # Verify authoritative audit receipt exists in audit_events
    key_hash = hashlib.sha256(idem_key.strip().encode("utf-8")).hexdigest()
    receipt = await audit_repo.find_create_receipt_by_idempotency_hash(DEMO_UNIT_ID, key_hash)
    assert receipt is not None
    assert receipt.resource_id == uuid.UUID(res1["id"])
    assert receipt.metadata_json.get("idempotency_key_hash") == key_hash
    assert receipt.metadata_json.get("unit_id") == str(DEMO_UNIT_ID)

    # CRITICAL: Verify raw Idempotency-Key is NEVER stored
    assert idem_key not in (receipt.metadata_json or {})
    assert idem_key not in (receipt.reason or "")
    assert idem_key not in (receipt.action or "")
    assert not any(idem_key in str(v) for v in (receipt.metadata_json or {}).values())

    # Replay with different payload must fail with 409 Conflict
    with pytest.raises(HTTPException) as exc:
        await svc.create_what_if_scenario(
            unit_id=DEMO_UNIT_ID,
            created_by_user_id=DEMO_COMMANDER_USER_ID,
            scenario_name="Different Name Collision Test",
            cutoff=DEMO_CUTOFF,
            idempotency_key=idem_key,
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_07b_concurrent_create_idempotency():
    """Verify concurrent CREATE calls with identical key serialize and do not duplicate scenarios."""
    import asyncio

    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool, future=True)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    concurrent_key = f"conc-create-key-{uuid.uuid4()}"
    scen_title = f"Concurrent Create Scenario {uuid.uuid4()}"

    async def create_worker(worker_id: int):
        async with session_factory() as session:
            session.info["actor"] = {
                "user_id": str(DEMO_COMMANDER_USER_ID),
                "role": "COMMANDER",
                "unit_id": str(DEMO_UNIT_ID),
            }
            svc = ScenarioService(
                scenario_repo=ScenarioRepository(session),
                unit_repo=UnitRepository(session),
                analytics_repo=AnalyticsRepository(session),
                personnel_repo=PersonnelRepository(session),
                audit_repo=AuditRepository(session),
            )
            res = await svc.create_what_if_scenario(
                unit_id=DEMO_UNIT_ID,
                created_by_user_id=DEMO_COMMANDER_USER_ID,
                scenario_name=scen_title,
                cutoff=DEMO_CUTOFF,
                idempotency_key=concurrent_key,
            )
            await session.commit()
            return res

    results = await asyncio.gather(create_worker(1), create_worker(2))
    assert results[0]["id"] == results[1]["id"]
    # One created, the other safely replayed from audit receipt
    assert any(r.get("replay_safe") is True for r in results)

    # Verify exactly ONE scenario row was created in DB
    async with session_factory() as verify_session:
        scen_count = await verify_session.scalar(
            select(text("count(*)")).select_from(RosterScenario).where(RosterScenario.scenario_name == scen_title)
        )
        assert scen_count == 1

    await engine.dispose()


@pytest.mark.asyncio
async def test_08_decision_workflow_accept_and_source_immutability(disposable_session: AsyncSession):
    """Test ACCEPT decision requires FEASIBLE (rejects DRAFT), creates approval, and leaves roster unmutated."""
    scenario_repo = ScenarioRepository(disposable_session)
    unit_repo = UnitRepository(disposable_session)
    analytics_repo = AnalyticsRepository(disposable_session)
    personnel_repo = PersonnelRepository(disposable_session)
    audit_repo = AuditRepository(disposable_session)

    svc = ScenarioService(
        scenario_repo=scenario_repo,
        unit_repo=unit_repo,
        analytics_repo=analytics_repo,
        personnel_repo=personnel_repo,
        audit_repo=audit_repo,
    )

    disposable_session.info["actor"] = {
        "user_id": str(DEMO_COMMANDER_USER_ID),
        "role": "COMMANDER",
        "unit_id": str(DEMO_UNIT_ID),
    }

    # Count published roster records at baseline
    count_assign_before = await disposable_session.scalar(
        select(text("count(*)")).select_from(RosterAssignment)
    )
    count_shift_before = await disposable_session.scalar(
        select(text("count(*)")).select_from(ShiftRequirement)
    )
    assert count_assign_before == 126
    assert count_shift_before == 28

    # --- PART 1: DRAFT + ACCEPT MUST BE REJECTED ---
    draft_scen = await svc.create_what_if_scenario(
        unit_id=DEMO_UNIT_ID,
        created_by_user_id=DEMO_WELFARE_USER_ID,
        scenario_name="Welfare Draft Scenario",
        cutoff=DEMO_CUTOFF,
        is_welfare_draft=True,
    )
    await disposable_session.commit()
    assert draft_scen["status"] == "DRAFT"
    draft_id = uuid.UUID(draft_scen["id"])

    # Commander attempts to ACCEPT a DRAFT scenario -> MUST BE REJECTED
    with pytest.raises(HTTPException) as exc_draft:
        await svc.record_decision(
            scenario_id=draft_id,
            user_id=DEMO_COMMANDER_USER_ID,
            decision="ACCEPT",
            reason="Commander mistakenly attempting to accept draft directly",
        )
    assert exc_draft.value.status_code == 409
    assert "FEASIBLE" in str(exc_draft.value.detail)

    # Commander attempts to REJECT a DRAFT scenario -> MUST BE REJECTED (409)
    with pytest.raises(HTTPException) as exc_draft_rej:
        await svc.record_decision(
            scenario_id=draft_id,
            user_id=DEMO_COMMANDER_USER_ID,
            decision="REJECT",
            reason="Commander attempting to reject draft directly without evaluation",
        )
    assert exc_draft_rej.value.status_code == 409
    assert "DRAFT" in str(exc_draft_rej.value.detail) or "evaluated" in str(exc_draft_rej.value.detail)

    # Verify no approval inserted for draft scenario
    approvals_for_draft = await disposable_session.scalar(
        select(text("count(*)")).select_from(Approval).where(Approval.scenario_id == draft_id)
    )
    assert approvals_for_draft == 0

    # Verify scenario remains in DRAFT status
    scen_recheck = await svc.scenario_repo.get_by_id(draft_id)
    assert scen_recheck.status == "DRAFT"

    # Verify published roster remains unmutated
    count_assign_mid = await disposable_session.scalar(
        select(text("count(*)")).select_from(RosterAssignment)
    )
    assert count_assign_mid == 126

    # --- PART 2: FEASIBLE + ACCEPT SUCCEEDS ---
    scen_res = await svc.create_what_if_scenario(
        unit_id=DEMO_UNIT_ID,
        created_by_user_id=DEMO_COMMANDER_USER_ID,
        scenario_name="Feasible Acceptance Test Scenario",
        cutoff=DEMO_CUTOFF,
        is_welfare_draft=False,
    )
    await disposable_session.commit()
    assert scen_res["status"] == "FEASIBLE"
    scen_id = uuid.UUID(scen_res["id"])
    expected_rev = scen_res["expected_revision"]

    # Stale revision denial test -> 409
    with pytest.raises(HTTPException) as exc_stale:
        await svc.record_decision(
            scenario_id=scen_id,
            user_id=DEMO_COMMANDER_USER_ID,
            decision="ACCEPT",
            reason="Operational duty workload leveling across squads",
            expected_revision="rev-sha256-invalidstale000000000000000000000000000000000000000000000000000000",
        )
    assert exc_stale.value.status_code == 409
    assert "STALE_REVISION" in exc_stale.value.detail

    # Valid ACCEPT decision with Idempotency-Key
    accept_idem_key = f"accept-key-{uuid.uuid4()}"
    dec_res = await svc.record_decision(
        scenario_id=scen_id,
        user_id=DEMO_COMMANDER_USER_ID,
        decision="ACCEPT",
        reason="Operational duty workload leveling across squads",
        expected_revision=expected_rev,
        idempotency_key=accept_idem_key,
    )
    await disposable_session.commit()

    assert dec_res["decision"] == "ACCEPT"
    assert dec_res["status"] == "APPROVED"

    # Verify approval was inserted
    approvals_for_scen = await disposable_session.scalar(
        select(text("count(*)")).select_from(Approval).where(Approval.scenario_id == scen_id)
    )
    assert approvals_for_scen == 1

    # CRITICAL: Verify published roster records are 100% UNCHANGED
    count_assign_after = await disposable_session.scalar(
        select(text("count(*)")).select_from(RosterAssignment)
    )
    assert count_assign_after == 126

    # Idempotent replay of identical ACCEPT with same Idempotency-Key
    replay_res = await svc.record_decision(
        scenario_id=scen_id,
        user_id=DEMO_COMMANDER_USER_ID,
        decision="ACCEPT",
        reason="Operational duty workload leveling across squads",
        expected_revision=expected_rev,
        idempotency_key=accept_idem_key,
    )
    assert replay_res["replay_safe"] is True
    assert replay_res["approval_id"] == dec_res["approval_id"]

    # Collision: same Idempotency-Key with different reason -> 409
    with pytest.raises(HTTPException) as exc_accept_col:
        await svc.record_decision(
            scenario_id=scen_id,
            user_id=DEMO_COMMANDER_USER_ID,
            decision="ACCEPT",
            reason="Different reason attempting collision",
            expected_revision=expected_rev,
            idempotency_key=accept_idem_key,
        )
    assert exc_accept_col.value.status_code == 409


@pytest.mark.asyncio
async def test_09_decision_workflow_modify_and_reject(disposable_session: AsyncSession):
    """Test REJECT and MODIFY decisions with audit receipt idempotency and concurrency."""
    scenario_repo = ScenarioRepository(disposable_session)
    unit_repo = UnitRepository(disposable_session)
    analytics_repo = AnalyticsRepository(disposable_session)
    personnel_repo = PersonnelRepository(disposable_session)
    audit_repo = AuditRepository(disposable_session)

    svc = ScenarioService(
        scenario_repo=scenario_repo,
        unit_repo=unit_repo,
        analytics_repo=analytics_repo,
        personnel_repo=personnel_repo,
        audit_repo=audit_repo,
    )

    disposable_session.info["actor"] = {
        "user_id": str(DEMO_COMMANDER_USER_ID),
        "role": "COMMANDER",
        "unit_id": str(DEMO_UNIT_ID),
    }

    # --- A. REJECT with Idempotency-Key & Replay ---
    scen_a = await svc.create_what_if_scenario(
        unit_id=DEMO_UNIT_ID,
        created_by_user_id=DEMO_COMMANDER_USER_ID,
        scenario_name="To Reject Scenario",
        cutoff=DEMO_CUTOFF,
    )
    await disposable_session.commit()
    rej_key = f"rej-key-{uuid.uuid4()}"
    rej_res = await svc.record_decision(
        scenario_id=uuid.UUID(scen_a["id"]),
        user_id=DEMO_COMMANDER_USER_ID,
        decision="REJECT",
        reason="Operational requirements changed due to upcoming training rotation",
        idempotency_key=rej_key,
    )
    await disposable_session.commit()
    assert rej_res["decision"] == "REJECT"
    assert rej_res["status"] == "REJECTED"

    # Replay REJECT with same key
    rej_replay = await svc.record_decision(
        scenario_id=uuid.UUID(scen_a["id"]),
        user_id=DEMO_COMMANDER_USER_ID,
        decision="REJECT",
        reason="Operational requirements changed due to upcoming training rotation",
        idempotency_key=rej_key,
    )
    assert rej_replay.get("replay_safe") is True

    # Collision REJECT with different reason -> 409
    with pytest.raises(HTTPException) as exc_rej_col:
        await svc.record_decision(
            scenario_id=uuid.UUID(scen_a["id"]),
            user_id=DEMO_COMMANDER_USER_ID,
            decision="REJECT",
            reason="Different reason collision test",
            idempotency_key=rej_key,
        )
    assert exc_rej_col.value.status_code == 409

    # --- B. MODIFY with Idempotency-Key & Replay ---
    scen_b = await svc.create_what_if_scenario(
        unit_id=DEMO_UNIT_ID,
        created_by_user_id=DEMO_COMMANDER_USER_ID,
        scenario_name="Parent Modify Scenario",
        cutoff=DEMO_CUTOFF,
    )
    await disposable_session.commit()
    mod_key = f"mod-key-{uuid.uuid4()}"
    mod_res = await svc.record_decision(
        scenario_id=uuid.UUID(scen_b["id"]),
        user_id=DEMO_COMMANDER_USER_ID,
        decision="MODIFY",
        reason="Modify coverage requirements for post-exercise recovery",
        idempotency_key=mod_key,
        target_reduction_percent=20,
    )
    await disposable_session.commit()

    assert mod_res["decision"] == "MODIFY"
    assert mod_res["parent_status"] == "SUPERSEDED"
    assert "child_scenario" in mod_res
    child = mod_res["child_scenario"]
    assert child["parent_id"] == scen_b["id"]
    assert child["scenario_version"] == 2

    # Replay MODIFY with same key -> returns safe replay with same child scenario
    mod_replay = await svc.record_decision(
        scenario_id=uuid.UUID(scen_b["id"]),
        user_id=DEMO_COMMANDER_USER_ID,
        decision="MODIFY",
        reason="Modify coverage requirements for post-exercise recovery",
        idempotency_key=mod_key,
        target_reduction_percent=20,
    )
    assert mod_replay.get("replay_safe") is True
    assert mod_replay["child_scenario"]["id"] == child["id"]


@pytest.mark.asyncio
async def test_10_role_security_and_welfare_draft(disposable_session: AsyncSession):
    """Test role security: Welfare drafts only; Commander decides; Personnel/Admin forbidden."""
    scenario_repo = ScenarioRepository(disposable_session)
    unit_repo = UnitRepository(disposable_session)
    analytics_repo = AnalyticsRepository(disposable_session)
    personnel_repo = PersonnelRepository(disposable_session)
    audit_repo = AuditRepository(disposable_session)

    svc = ScenarioService(
        scenario_repo=scenario_repo,
        unit_repo=unit_repo,
        analytics_repo=analytics_repo,
        personnel_repo=personnel_repo,
        audit_repo=audit_repo,
    )

    # 1. Welfare Officer creates draft scenario
    disposable_session.info["actor"] = {
        "user_id": str(DEMO_WELFARE_USER_ID),
        "role": "WELFARE_OFFICER",
        "unit_id": str(DEMO_UNIT_ID),
    }

    welfare_draft = await svc.create_what_if_scenario(
        unit_id=DEMO_UNIT_ID,
        created_by_user_id=DEMO_WELFARE_USER_ID,
        scenario_name="Welfare Workload Suggestion",
        cutoff=DEMO_CUTOFF,
        is_welfare_draft=True,
    )
    await disposable_session.commit()

    assert welfare_draft["status"] == "DRAFT"
    welfare_scen_id = uuid.UUID(welfare_draft["id"])

    # 2. Welfare Officer CANNOT decide (ACCEPT / REJECT / MODIFY)
    with pytest.raises(HTTPException) as exc_wel_dec:
        await svc.record_decision(
            scenario_id=welfare_scen_id,
            user_id=DEMO_WELFARE_USER_ID,
            decision="ACCEPT",
            reason="Welfare officer cannot decide",
        )
    assert exc_wel_dec.value.status_code == 403

    # 3. Commander CANNOT accept Welfare draft scenario directly (FEASIBLE only)
    disposable_session.info["actor"] = {
        "user_id": str(DEMO_COMMANDER_USER_ID),
        "role": "COMMANDER",
        "unit_id": str(DEMO_UNIT_ID),
    }
    with pytest.raises(HTTPException) as exc_draft_acc:
        await svc.record_decision(
            scenario_id=welfare_scen_id,
            user_id=DEMO_COMMANDER_USER_ID,
            decision="ACCEPT",
            reason="Commander cannot accept unreviewed draft directly",
        )
    assert exc_draft_acc.value.status_code == 409
    assert "FEASIBLE" in str(exc_draft_acc.value.detail)

    # 3b. Commander CANNOT reject Welfare draft scenario directly (must be evaluated first)
    with pytest.raises(HTTPException) as exc_draft_rej:
        await svc.record_decision(
            scenario_id=welfare_scen_id,
            user_id=DEMO_COMMANDER_USER_ID,
            decision="REJECT",
            reason="Commander cannot reject unreviewed draft directly",
        )
    assert exc_draft_rej.value.status_code == 409
    assert "DRAFT" in str(exc_draft_rej.value.detail) or "evaluated" in str(exc_draft_rej.value.detail)

    # Verify no approval inserted for draft scenario
    approvals_for_draft = await disposable_session.scalar(
        select(text("count(*)")).select_from(Approval).where(Approval.scenario_id == welfare_scen_id)
    )
    assert approvals_for_draft == 0

    # 4. Cross-unit Commander CANNOT decide
    disposable_session.info["actor"] = {
        "user_id": str(CROSS_UNIT_COMMANDER_USER_ID),
        "role": "COMMANDER",
        "unit_id": "299dab9b-a61c-08c0-863c-91340adf9b97",  # Different unit U01
    }
    with pytest.raises(HTTPException) as exc_cross:
        await svc.record_decision(
            scenario_id=welfare_scen_id,
            user_id=CROSS_UNIT_COMMANDER_USER_ID,
            decision="REJECT",
            reason="Cross unit decision should fail",
        )
    assert exc_cross.value.status_code in (403, 404)


@pytest.mark.asyncio
async def test_11_pseudonymous_privacy_projections(disposable_session: AsyncSession):
    """Test scenario responses contain pseudonyms and zero raw names, codes, or wellbeing data."""
    scenario_repo = ScenarioRepository(disposable_session)
    unit_repo = UnitRepository(disposable_session)
    analytics_repo = AnalyticsRepository(disposable_session)
    personnel_repo = PersonnelRepository(disposable_session)
    audit_repo = AuditRepository(disposable_session)

    svc = ScenarioService(
        scenario_repo=scenario_repo,
        unit_repo=unit_repo,
        analytics_repo=analytics_repo,
        personnel_repo=personnel_repo,
        audit_repo=audit_repo,
    )

    scen = await svc.create_what_if_scenario(
        unit_id=DEMO_UNIT_ID,
        created_by_user_id=DEMO_COMMANDER_USER_ID,
        scenario_name="Privacy Inspection Scenario",
        cutoff=DEMO_CUTOFF,
    )
    await disposable_session.commit()

    # Verify root fields
    forbidden_keys = {"full_name", "personnel_code", "raw_answers", "wellbeing_score", "phq9", "gad7"}
    assert not any(k in scen for k in forbidden_keys)

    # Verify changes
    for ch in scen.get("changes", []):
        assert "personnel_pseudo_id" in ch
        assert ch["personnel_pseudo_id"].startswith(("PS-", "PRH-")) or len(ch["personnel_pseudo_id"]) in (8, 12)
        # Ensure raw personnel_id is not present in from_value or to_value
        assert "personnel_id" not in ch.get("from_value", {})
        assert "personnel_id" not in ch.get("to_value", {})
        assert not any(k in ch for k in forbidden_keys)


@pytest.mark.asyncio
async def test_12_commander_and_welfare_api_endpoints():
    """Test HTTP API endpoints with dependency override on disposable DB."""
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool, future=True)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async def override_get_db(request: Request):
        async with session_factory() as session:
            session.info["actor"] = getattr(request.state, "actor", None)
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def override_get_current_user(request: Request):
        auth = request.headers.get("Authorization", "")
        if "commander" in auth:
            actor = {
                "user_id": str(DEMO_COMMANDER_USER_ID),
                "sub": str(DEMO_COMMANDER_USER_ID),
                "username": "demo_commander",
                "role": "COMMANDER",
                "unit_id": str(DEMO_UNIT_ID),
                "personnel_id": None,
                "jti": str(uuid.uuid4()),
            }
        elif "welfare" in auth:
            actor = {
                "user_id": str(DEMO_WELFARE_USER_ID),
                "sub": str(DEMO_WELFARE_USER_ID),
                "username": "welfare_u02",
                "role": "WELFARE_OFFICER",
                "unit_id": str(DEMO_UNIT_ID),
                "personnel_id": None,
                "jti": str(uuid.uuid4()),
            }
        elif "personnel" in auth:
            actor = {
                "user_id": str(DEMO_PERSONNEL_USER_ID),
                "sub": str(DEMO_PERSONNEL_USER_ID),
                "username": "demo_personnel",
                "role": "PERSONNEL",
                "unit_id": str(DEMO_UNIT_ID),
                "personnel_id": str(uuid.uuid4()),
                "jti": str(uuid.uuid4()),
            }
        else:
            raise HTTPException(401, "Invalid authentication session")
        request.state.actor = actor
        return actor

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_with_rls] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            cmd_headers = {"Authorization": "Bearer commander"}
            welfare_headers = {"Authorization": "Bearer welfare"}
            personnel_headers = {"Authorization": "Bearer personnel"}

            # 1. Commander creates scenario via POST /api/v1/commander/scenarios
            idem_key = f"api-test-{uuid.uuid4()}"
            res_c = await client.post(
                "/api/v1/commander/scenarios",
                    json={"unit_id": str(DEMO_UNIT_ID), "scenario_name": "API Commander Scenario", "cutoff": DEMO_CUTOFF.isoformat()},
                headers={**cmd_headers, "Idempotency-Key": idem_key},
            )
            assert res_c.status_code == 200, f"res_c failed with {res_c.status_code}: {res_c.text}"
            scen_data = res_c.json()
            scen_id = scen_data["id"]
            expected_rev = scen_data["expected_revision"]

            # 2. Commander gets scenario detail via GET /api/v1/commander/scenarios/{id}
            res_get = await client.get(f"/api/v1/commander/scenarios/{scen_id}", headers=cmd_headers)
            assert res_get.status_code == 200
            assert res_get.json()["id"] == scen_id

            # 3. Commander gets comparison via GET /api/v1/commander/scenarios/{id}/comparison
            res_comp = await client.get(f"/api/v1/commander/scenarios/{scen_id}/comparison", headers=cmd_headers)
            assert res_comp.status_code == 200
            comp_body = res_comp.json()
            assert "workload" in comp_body
            assert comp_body["wsi"]["projected_wsi"] is None

            # 4. Commander decides with stale revision -> 409
            res_stale = await client.post(
                f"/api/v1/commander/scenarios/{scen_id}/decide",
                json={
                    "decision": "ACCEPT",
                    "reason": "Leveling roster duties across sections",
                    "expected_revision": "rev-sha256-invalid00000000000000000000000000000000000000000000000000000000",
                },
                headers=cmd_headers,
            )
            assert res_stale.status_code == 409

            # 5. Commander decides with valid revision -> 200
            res_accept = await client.post(
                f"/api/v1/commander/scenarios/{scen_id}/decide",
                json={
                    "decision": "ACCEPT",
                    "reason": "Leveling roster duties across sections",
                    "expected_revision": expected_rev,
                },
                headers=cmd_headers,
            )
            assert res_accept.status_code == 200
            assert res_accept.json()["status"] == "APPROVED"

            # 6. Welfare drafts scenario via POST /api/v1/welfare/scenarios/draft -> 200
            res_draft = await client.post(
                "/api/v1/welfare/scenarios/draft",
                json={"unit_id": str(DEMO_UNIT_ID), "scenario_name": "API Welfare Draft"},
                headers=welfare_headers,
            )
            assert res_draft.status_code == 200
            assert res_draft.json()["status"] == "DRAFT"
            draft_id = res_draft.json()["id"]

            # 6b. Commander attempts to ACCEPT a DRAFT scenario -> 409 Conflict (FEASIBLE only)
            res_cmd_accept_draft = await client.post(
                f"/api/v1/commander/scenarios/{draft_id}/decide",
                json={
                    "decision": "ACCEPT",
                    "reason": "Commander mistakenly attempting to accept draft directly",
                    "expected_revision": res_draft.json()["expected_revision"],
                },
                headers=cmd_headers,
            )
            assert res_cmd_accept_draft.status_code == 409
            assert res_cmd_accept_draft.json()["error"]["code"] == "CONFLICT"

            # 6c. Commander attempts to REJECT a DRAFT scenario -> 409 Conflict (must be evaluated first)
            res_cmd_reject_draft = await client.post(
                f"/api/v1/commander/scenarios/{draft_id}/decide",
                json={
                    "decision": "REJECT",
                    "reason": "Commander mistakenly attempting to reject draft directly",
                    "expected_revision": res_draft.json()["expected_revision"],
                },
                headers=cmd_headers,
            )
            assert res_cmd_reject_draft.status_code == 409
            assert res_cmd_reject_draft.json()["error"]["code"] == "CONFLICT"

            # 7. Welfare cannot decide -> 403 Forbidden
            res_w_dec = await client.post(
                f"/api/v1/commander/scenarios/{draft_id}/decide",
                json={"decision": "ACCEPT", "reason": "Welfare trying to accept"},
                headers=welfare_headers,
            )
            assert res_w_dec.status_code == 403

            # 8. Personnel cannot create or decide scenarios -> 403 Forbidden
            res_p_create = await client.post(
                "/api/v1/commander/scenarios",
                json={"unit_id": str(DEMO_UNIT_ID), "scenario_name": "Personnel forbidden"},
                headers=personnel_headers,
            )
            assert res_p_create.status_code == 403

            res_p_draft = await client.post(
                "/api/v1/welfare/scenarios/draft",
                json={"unit_id": str(DEMO_UNIT_ID), "scenario_name": "Personnel forbidden draft"},
                headers=personnel_headers,
            )
            assert res_p_draft.status_code == 403

    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_db_with_rls, None)
        app.dependency_overrides.pop(get_current_user, None)
        await engine.dispose()


@pytest.mark.asyncio
async def test_13_concurrent_terminal_decisions():
    """Verify concurrent terminal decision attempts are serialized by advisory lock and produce exactly one winner."""
    import asyncio

    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool, future=True)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # 1. Create a feasible scenario
    async with session_factory() as session:
        session.info["actor"] = {
            "user_id": str(DEMO_COMMANDER_USER_ID),
            "role": "COMMANDER",
            "unit_id": str(DEMO_UNIT_ID),
        }
        svc = ScenarioService(
            scenario_repo=ScenarioRepository(session),
            unit_repo=UnitRepository(session),
            analytics_repo=AnalyticsRepository(session),
            personnel_repo=PersonnelRepository(session),
            audit_repo=AuditRepository(session),
        )
        scen = await svc.create_what_if_scenario(
            unit_id=DEMO_UNIT_ID,
            created_by_user_id=DEMO_COMMANDER_USER_ID,
            scenario_name="Concurrency Race Test Scenario",
            cutoff=DEMO_CUTOFF,
        )
        await session.commit()
        scen_id = uuid.UUID(scen["id"])
        expected_rev = scen["expected_revision"]

    # 2. Define two concurrent deciders with distinct sessions and different idempotency keys
    async def decide_worker(worker_id: int):
        async with session_factory() as worker_session:
            worker_session.info["actor"] = {
                "user_id": str(DEMO_COMMANDER_USER_ID),
                "role": "COMMANDER",
                "unit_id": str(DEMO_UNIT_ID),
            }
            worker_svc = ScenarioService(
                scenario_repo=ScenarioRepository(worker_session),
                unit_repo=UnitRepository(worker_session),
                analytics_repo=AnalyticsRepository(worker_session),
                personnel_repo=PersonnelRepository(worker_session),
                audit_repo=AuditRepository(worker_session),
            )
            try:
                res = await worker_svc.record_decision(
                    scenario_id=scen_id,
                    user_id=DEMO_COMMANDER_USER_ID,
                    decision="ACCEPT",
                    reason=f"Concurrent accept attempt from worker {worker_id}",
                    expected_revision=expected_rev,
                    idempotency_key=f"conc-key-worker-{worker_id}-{uuid.uuid4()}",
                )
                await worker_session.commit()
                return {"status": "SUCCESS", "res": res}
            except HTTPException as e:
                await worker_session.rollback()
                return {"status": "HTTPException", "status_code": e.status_code, "detail": e.detail}
            except Exception as e:
                await worker_session.rollback()
                return {"status": "EXCEPTION", "error": str(e)}

    # 3. Launch concurrently
    results = await asyncio.gather(decide_worker(1), decide_worker(2))

    # 4. Verify exactly one succeeded (200 / APPROVED) and one failed with 409 Conflict
    successes = [r for r in results if r["status"] == "SUCCESS"]
    conflicts = [r for r in results if r["status"] == "HTTPException" and r["status_code"] == 409]

    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}: {results}"
    assert len(conflicts) == 1, f"Expected exactly 1 409 conflict, got {len(conflicts)}: {results}"
    assert "FEASIBLE" in conflicts[0]["detail"] or "terminal" in str(conflicts[0]["detail"]).lower()

    # 5. Verify exactly one approval was persisted in database
    async with session_factory() as verify_session:
        app_count = await verify_session.scalar(
            select(text("count(*)")).select_from(Approval).where(Approval.scenario_id == scen_id)
        )
        assert app_count == 1

        # Published roster count remains unmutated (126)
        r_count = await verify_session.scalar(
            select(text("count(*)")).select_from(RosterAssignment)
        )
        assert r_count == 126

    await engine.dispose()
