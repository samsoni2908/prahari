"""Certified raw-source normalization; policy values here are explicit test fixtures."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4
import pytest
from app.analytics.wsi_source_adapter import WsiSourceAdapter
from app.analytics.operational_feature_adapter import POLICY, source_hash, row_key


class Sources:
    def __init__(self, cutoff=date(2026, 9, 1)):
        self.person, self.unit = uuid4(), uuid4()
        self.cutoff = cutoff
        previous = self.cutoff - timedelta(days=1)
        self.data = {name: [] for name in ("personnel", "posting_history", "duties", "rest_records", "leave_records", "deployments", "staffing")}
        self.data["personnel"] = [{"id": self.person, "unit_id": self.unit, "status": "ACTIVE"}]
        self.data["posting_history"] = [{"id": uuid4(), "personnel_id": self.person, "unit_id": self.unit,
            "posting_start_date": date(2026, 1, 1), "posting_end_date": None}]
        for index in range(1, 8):
            day = self.cutoff - timedelta(days=index)
            start = datetime.combine(day, datetime.min.time(), timezone.utc) + timedelta(hours=8)
            self.data["duties"].append({"id": uuid4(), "personnel_id": self.person, "duty_date": day,
                "start_at": start, "end_at": start + timedelta(hours=8), "hours": 8, "is_night": False})
            self.data["rest_records"].append({"id": uuid4(), "personnel_id": self.person, "record_date": day,
                "rest_hours": 8, "source": "DERIVED_FROM_DUTY", "data_quality_status": "VALID"})
            self.data["staffing"].append({"id": uuid4(), "unit_id": self.unit, "record_date": day,
                "available_strength": 8, "required_strength": 10})
        self.data["leave_records"] = [{"id": uuid4(), "personnel_id": self.person,
            "actual_start_date": date(2026, 7, 1), "actual_end_date": date(2026, 7, 3)}]
        self.manifest = {"policy": POLICY, "cutoff": self.cutoff.isoformat(), "families": list(self.data),
            "unknown_gaps": 0, "known_at": {}, "complete_days": {str(self.person): [(self.cutoff-timedelta(days=i)).isoformat() for i in range(1, 31)]},
            "leave_completion_history_complete": {str(self.person): True}, "completed_intervals": {}}
        self.policy = {"version": "TEST_NORMALIZATION_V1", "effective_from": "2026-01-01T00:00:00+00:00",
            "known_at": "2026-01-01T00:00:00+00:00", "effective_until": None,
            "values": {"wsi.d.reference_hours": 56, "wsi.r.reference_hours": 12,
                "wsi.c.reference_days": 7, "wsi.l.reference_days": 60, "wsi.h.reference_intensity": 5}}
        self.certify()

    def certify(self):
        at = datetime.combine(self.cutoff, datetime.min.time(), timezone.utc).isoformat()
        self.manifest["known_at"] = {name + "." + row_key(row): at for name, rows in self.data.items() for row in rows}
        self.manifest["source_hash"] = source_hash(self.data)

    def wsi_manifest(self, unit, cutoff):
        return self.manifest
    def wsi_policy(self, cutoff):
        return self.policy
    def wsi_sources(self, unit, cutoff):
        return self.data
    def result(self):
        return WsiSourceAdapter(self).build(self.person, self.unit, self.cutoff)


def test_authoritative_wsi_success_deterministic_and_no_defaults():
    source = Sources()
    first = source.result()
    assert first == source.result()
    assert first["status"] == "VALID" and first["freshness"] == "CURRENT_AT_CUTOFF"
    # D=100,R=100/3,C=100,N=0,L=60/60*100,H=0,S=20.
    assert first["value"] == pytest.approx(57.67)
    assert first["coverage"] == {"required_days": 30, "observed_days": 30}
    assert first["components"]["L"]["value"] == 100
    del source.policy["values"]["wsi.d.reference_hours"]
    missing = source.result()
    assert missing["value"] is None and missing["status"] == "NOT_COMPUTED"


@pytest.mark.parametrize("fault, expected", [
    ("missing", "NOT_COMPUTED"), ("stale", "DATA_STALE"), ("partial", "INSUFFICIENT_HISTORY"),
    ("future_knowledge", "INSUFFICIENT_HISTORY"), ("rest_missing", "REST_DATA_MISSING"),
    ("changed", "DATA_STALE"), ("invalid_rest", "COMPUTATION_ERROR"),
    ("planned_leave", "NOT_COMPUTED"),
])
def test_unavailable_sources_never_promote_historical_score(fault, expected):
    source = Sources()
    if fault == "missing":
        source.manifest = None
    elif fault == "stale":
        source.manifest["cutoff"] = "2026-08-31"
    elif fault == "partial":
        source.manifest["complete_days"][str(source.person)].pop()
    elif fault == "future_knowledge":
        key = next(iter(source.manifest["known_at"]))
        source.manifest["known_at"][key] = "2026-09-02T00:00:00+00:00"
    elif fault == "rest_missing":
        source.data["rest_records"].pop()
        source.certify()
    elif fault == "changed":
        source.data["staffing"][0]["available_strength"] = 9
    elif fault == "invalid_rest":
        source.data["rest_records"][0]["rest_hours"] = -1
        source.certify()
    elif fault == "planned_leave":
        source.data["leave_records"][0]["actual_end_date"] = None
        source.certify()
    result = source.result()
    assert result["status"] == expected and result["value"] is None
    assert result["freshness"] == "UNAVAILABLE"


def test_governed_peer_cohort_fits_once_and_never_widens():
    import hashlib
    import json
    import sklearn
    from unittest.mock import patch
    from app.services.operational_analytics_service import OperationalAnalyticsService
    from app.analytics.peer_anomaly import detect_peer_anomalies
    source = Sources()
    original = deepcopy(source.data)
    for index in range(5):
        identifier = source.person if index == 0 else uuid4()
        if index == 0:
            source.data["personnel"][0].update(role_title="SERVICE_ROLE", pseudo_id="TEST-0")
            continue
        for family in ("personnel", "posting_history", "duties", "rest_records", "leave_records"):
            for prior in original[family]:
                row = deepcopy(prior)
                if family == "personnel":
                    row.update(id=identifier, role_title="SERVICE_ROLE", pseudo_id="TEST-" + str(index))
                else:
                    row.update(id=uuid4(), personnel_id=identifier)
                if family == "duties":
                    row["hours"] += index
                    row["end_at"] += timedelta(hours=index)
                source.data[family].append(row)
        source.manifest["complete_days"][str(identifier)] = list(source.manifest["complete_days"][str(source.person)])
        source.manifest["leave_completion_history_complete"][str(identifier)] = True
    values = source.policy["values"]
    values.update({"peer.min_valid_members": 5, "peer.iforest.n_estimators": 20,
        "peer.iforest.max_samples": 1.0, "peer.iforest.max_features": 1.0,
        "peer.iforest.contamination": .2, "peer.iforest.random_state": 26186,
        "peer.iforest.n_jobs": 1, "peer.iforest.library_version": sklearn.__version__,
        "peer.preprocessing_version": "operational-peer-raw-v1"})
    source.policy["content_hash"] = hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    source.certify()
    service = OperationalAnalyticsService(source)
    with patch("app.analytics.peer_anomaly.detect_peer_anomalies", wraps=detect_peer_anomalies) as fit:
        first = service.calculate({"id": source.person, "unit_id": source.unit}, source.cutoff)
        second = service.calculate({"id": source.data["personnel"][1]["id"], "unit_id": source.unit}, source.cutoff)
        assert first["peer"]["status"] == second["peer"]["status"] == "VALID"
        assert first["peer"]["cohort_size"] == 5 and first["peer"]["anomaly_strength"] > 0
        assert fit.call_count == 1
    source.data["personnel"][1]["role_title"] = "OTHER_SERVICE_ROLE"
    source.certify()
    sparse = service.calculate({"id": source.person, "unit_id": source.unit}, source.cutoff)
    assert sparse["peer"]["status"] == "PEER_COHORT_INSUFFICIENT"
    assert sparse["peer"]["anomaly_strength"] is None
