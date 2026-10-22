"""Source-authoritative WSI and prior-only history using existing algorithms."""
import uuid
from dataclasses import asdict
from datetime import timedelta
from sqlalchemy import insert, select
from app.analytics.baseline import compute_personal_baseline
from app.analytics.ewma import compute_ewma_trend
from app.analytics.wsi_source_adapter import WsiSourceAdapter
from app.repositories.detection_repository import TABLES


class OperationalAnalyticsService:
    def __init__(self, repository, peer_cache=None):
        self.repo = repository
        self.peer_cache = peer_cache if peer_cache is not None else {}

    def peer(self, person, cutoff, current, policy):
        import hashlib
        import json
        import math
        import sklearn
        from app.analytics.peer_anomaly import detect_peer_anomalies
        unavailable = {"status": "NOT_COMPUTED", "anomaly_strength": None, "reason": "PEER_POLICY_UNAVAILABLE"}
        values = policy["values"]
        keys = ("peer.min_valid_members", "peer.iforest.n_estimators", "peer.iforest.max_samples",
            "peer.iforest.max_features", "peer.iforest.contamination", "peer.iforest.random_state",
            "peer.iforest.n_jobs", "peer.iforest.library_version", "peer.preprocessing_version")
        if not all(key in values for key in keys):
            return unavailable
        minimum = values["peer.min_valid_members"]
        trees, jobs, seed = (values["peer.iforest." + key] for key in ("n_estimators", "n_jobs", "random_state"))
        if (any(isinstance(x, bool) or not isinstance(x, int) for x in (minimum, trees, jobs, seed))
                or minimum < 2 or trees < 1 or jobs < 1
                or values["peer.iforest.library_version"] != sklearn.__version__
                or values["peer.preprocessing_version"] != "operational-peer-raw-v1"):
            return {**unavailable, "reason": "PEER_POLICY_INCOMPATIBLE"}
        data = self.repo.wsi_sources(person["unit_id"], cutoff)
        member = next((p for p in data["personnel"] if p["id"] == person["id"]), None)
        if member is None or not member.get("role_title"):
            return {**unavailable, "reason": "OPERATIONAL_ROLE_UNAVAILABLE"}
        candidates = sorted([p for p in data["personnel"] if p.get("role_title") == member["role_title"]
            and p["unit_id"] == person["unit_id"] and p["status"] == "ACTIVE"], key=lambda p: p["pseudo_id"])
        cohort, matrix = [], []
        for candidate in candidates:
            metric = current if candidate["id"] == person["id"] else WsiSourceAdapter(self.repo).build(candidate["id"], candidate["unit_id"], cutoff)
            if metric["status"] == "VALID" and metric["policy_version"] == current["policy_version"]:
                cohort.append(str(candidate["id"]))
                matrix.append(metric["peer_vector"])
        if len(cohort) < minimum or str(person["id"]) not in cohort:
            return {**unavailable, "status": "PEER_COHORT_INSUFFICIENT", "reason": "ELIGIBLE_COHORT_INSUFFICIENT", "cohort_size": len(cohort)}
        samples = values["peer.iforest.max_samples"]
        features = values["peer.iforest.max_features"]
        contamination = values["peer.iforest.contamination"]
        def bounded(value, ceiling):
            return not isinstance(value, bool) and ((isinstance(value, int) and 1 <= value <= ceiling)
                or (isinstance(value, float) and math.isfinite(value) and 0 < value <= 1))
        if (not bounded(samples, len(cohort)) or not bounded(features, 5)
                or not isinstance(contamination, (int, float)) or isinstance(contamination, bool)
                or not math.isfinite(contamination) or not 0 < contamination <= .5):
            return {**unavailable, "reason": "INVALID_PEER_POLICY"}
        cohort_hash = hashlib.sha256(json.dumps([cohort, matrix, current["source_hash"], policy["content_hash"]],
            separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if cohort_hash not in self.peer_cache:
            self.peer_cache[cohort_hash] = detect_peer_anomalies(matrix, cohort, contamination=contamination,
                n_estimators=trees, random_state=seed, min_cohort_size=minimum,
                max_samples=samples, max_features=features, n_jobs=jobs)
        return {**self.peer_cache[cohort_hash][str(person["id"])], "cohort_size": len(cohort),
            "cohort_hash": cohort_hash, "policy_version": policy["version"]}

    def calculate(self, person, cutoff):
        current = WsiSourceAdapter(self.repo).build(person["id"], person["unit_id"], cutoff)
        output = {"wsi": current, "baseline": {"status": "BASELINE_UNAVAILABLE", "z_score": None,
            "reason": "REQUIRED_POLICY_OR_CURRENT_INPUT_UNAVAILABLE"},
            "trend": {"status": "NOT_COMPUTED", "trend": None, "current_ewma": None,
                "reason": "REQUIRED_POLICY_OR_CURRENT_INPUT_UNAVAILABLE"},
            "peer": {"status": "NOT_COMPUTED", "anomaly_strength": None,
                "reason": "PEER_POLICY_OR_COHORT_UNAVAILABLE"}}
        if current["status"] != "VALID":
            return output
        policy = self.repo.wsi_policy(cutoff)
        values = policy["values"]
        output["peer"] = self.peer(person, cutoff, current, policy)
        history_keys = ("baseline.lookback_days", "baseline.min_valid_observations",
            "trend.min_valid_observations", "trend.stability_tolerance", "ewma.lambda")
        if not all(key in values for key in history_keys):
            return output
        lookback = values["baseline.lookback_days"]
        minimum = values["baseline.min_valid_observations"]
        segment = values["trend.min_valid_observations"]
        tolerance = values["trend.stability_tolerance"]
        import math
        if (any(isinstance(value, bool) or not isinstance(value, int) for value in (lookback, minimum, segment))
                or not 1 <= minimum <= lookback <= 3660 or segment < 2
                or not isinstance(tolerance, (int, float)) or not math.isfinite(tolerance) or tolerance < 0
                or values["ewma.lambda"] != .30):
            output["baseline"]["reason"] = "INVALID_HISTORY_POLICY"
            output["trend"]["reason"] = "INVALID_HISTORY_POLICY"
            return output
        # Recompute unrounded historical scores from immutable certified sources;
        # the two-decimal legacy persistence column never becomes baseline truth.
        series = []
        for index in range(lookback, 0, -1):
            prior = WsiSourceAdapter(self.repo).build(person["id"], person["unit_id"], cutoff - timedelta(days=index))
            series.append(prior.get("unrounded_value") if prior["status"] == "VALID"
                and prior["policy_version"] == current["policy_version"] else None)
        output["baseline"] = asdict(compute_personal_baseline(series,
            current["unrounded_value"], min_observations=minimum))
        output["trend"] = asdict(compute_ewma_trend([*series, current["unrounded_value"]],
            lambda_param=values["ewma.lambda"], min_segment_length=segment, stability_tolerance=tolerance))
        return output

    def process(self, person, cutoff, actor=None):
        result = self.calculate(person, cutoff)
        wsi = result["wsi"]
        if wsi["status"] != "VALID":
            self.repo.audit("WSI_SOURCE_UNAVAILABLE", actor, cutoff,
                reason=wsi["reason_codes"][0], source_hash=wsi["source_hash"],
                personnel_id=person["id"], availability=wsi["status"])
            return result
        snapshots = TABLES["wsi_snapshots"]
        identity = uuid.uuid5(uuid.NAMESPACE_URL, f"prahari:wsi:{person['id']}:{cutoff}:{wsi['policy_version']}:{wsi['source_hash']}")
        existing = self.repo.connection.execute(select(snapshots.c.id).where(snapshots.c.id == identity)).first()
        if not existing:
            columns = {key.lower() + "_component": value["value"] for key, value in wsi["components"].items()}
            self.repo.connection.execute(insert(snapshots).values(id=identity,
                personnel_id=person["id"], unit_id=person["unit_id"], snapshot_date=cutoff,
                wsi_score=wsi["value"], policy_version=wsi["policy_version"], **columns))
            self.repo.audit("WSI_SOURCE_CERTIFIED", actor, cutoff,
                source_hash=wsi["source_hash"], personnel_id=person["id"], availability="VALID")
        return result
