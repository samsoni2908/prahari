"""PRAHARI Model-A Runtime Loader & Safe Inference Service.

Task 28 & 29 Contract:
1. RUNTIME MUST NEVER TRAIN:
   - Zero model.fit() or preprocessor.fit() during startup or inference.
   - Strict read-only artifact consumption.
2. Explicit Availability States:
   - approved artifact found & valid -> MODEL_AVAILABLE
   - artifact missing -> MODEL_UNAVAILABLE (ARTIFACT_MISSING)
   - artifact corrupt -> MODEL_UNAVAILABLE (ARTIFACT_CORRUPT)
   - wrong feature version -> MODEL_UNAVAILABLE (FEATURE_VERSION_MISMATCH)
   - wrong target version -> MODEL_UNAVAILABLE (TARGET_VERSION_MISMATCH)
3. Zero Fallback Rule:
   - NEVER fallback to legacy hardcoded probabilities (e.g. 0.12).
   - NEVER return fake LOW risk when model is unavailable.
   - When unavailable, probability is None, predicted_class is None, score is None, band is MODEL_UNAVAILABLE.
4. Role-Scoped Operational Output:
   - Operational information only.
   - Strictly NO clinical or mental health terminology.
   - Strictly NO private wellbeing data.
"""

from pathlib import Path
import json
import math
from typing import Any, Dict, List, Optional, Tuple, Union
import joblib
import numpy as np
import pandas as pd

from app.ml.artifact_contract import (
    DEFAULT_ARTIFACT_PATH,
    DEFAULT_MANIFEST_PATH,
    FEATURE_SPEC_VERSION,
    TARGET_VERSION,
    compute_file_sha256,
)
from app.ml.confidence import calculate_feature_completeness, compute_operational_confidence
from app.ml.explain import explain_operational_prediction
from app.ml.features_hr import FEATURE_SET_B
from app.ml.risk_score import (
    DEFAULT_TAU_HIGH,
    DEFAULT_TAU_MED,
    execute_operational_pipeline,
)

STATUS_AVAILABLE = "MODEL_AVAILABLE"
STATUS_UNAVAILABLE = "MODEL_UNAVAILABLE"
APPROVED_ARTIFACT_SHA256 = "2e540b4ca0c3db9cf32b7601ac23319ead74db5c18ac5fd7c466b2ef4ae290b9"


class ModelARuntimeLoader:
    """Governed runtime loader and inference orchestrator for Model-A."""

    def __init__(self, artifact_path: Optional[Union[str, Path]] = None, auto_load: bool = True):
        self.artifact_path = Path(artifact_path) if artifact_path else DEFAULT_ARTIFACT_PATH
        self.artifact: Optional[Dict[str, Any]] = None
        self.status: str = STATUS_UNAVAILABLE
        self.status_reason: str = "INITIALIZING"
        self.artifact_hash: Optional[str] = None

        if auto_load:
            self.load()

    def load(self, enforce_hash: bool = False, expected_hash: Optional[str] = None) -> bool:
        """
        Loads the governed artifact from disk and validates compatibility.
        Runtime MUST NEVER train: returns False and sets status=MODEL_UNAVAILABLE upon any issue.
        """
        if not self.artifact_path.exists():
            self.status = STATUS_UNAVAILABLE
            self.status_reason = f"ARTIFACT_MISSING: Path not found {self.artifact_path}"
            self.artifact = None
            return False

        try:
            actual_hash = compute_file_sha256(self.artifact_path)
            self.artifact_hash = actual_hash

            if actual_hash != APPROVED_ARTIFACT_SHA256:
                self.status = STATUS_UNAVAILABLE
                self.status_reason = "ARTIFACT_CORRUPT: Approved artifact checksum mismatch"
                self.artifact = None
                return False

            if enforce_hash and expected_hash:
                if actual_hash.lower() != expected_hash.lower():
                    self.status = STATUS_UNAVAILABLE
                    self.status_reason = f"ARTIFACT_CORRUPT: Checksum mismatch (expected {expected_hash}, got {actual_hash})"
                    self.artifact = None
                    return False

            raw_loaded = joblib.load(self.artifact_path)
            if not isinstance(raw_loaded, dict):
                self.status = STATUS_UNAVAILABLE
                self.status_reason = "ARTIFACT_CORRUPT: Loaded object is not a dictionary"
                self.artifact = None
                return False

            manifest = json.loads(DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8"))
            expected = {
                "model_name": "Model-A (Operational Workload & Recovery Decision Support)",
                "model_version": "1.0.0", "target_name": "next_30d_leave_anomaly",
                "target_version": TARGET_VERSION, "feature_spec_version": FEATURE_SPEC_VERSION,
            }
            if any(manifest.get(k) != v or raw_loaded.get(k) != v for k,v in expected.items()) or manifest.get("artifact_sha256") != APPROVED_ARTIFACT_SHA256 or manifest.get("feature_count") != 15 or manifest.get("feature_names") != list(FEATURE_SET_B) or manifest.get("validation_cohort_provenance", {}).get("generator_version") != "v2.1-frozen-prototype":
                self.status = STATUS_UNAVAILABLE
                self.status_reason = "MANIFEST_CONTRACT_MISMATCH"
                self.artifact = None
                return False
            calibration_policy = {"tau_high": 0.15, "tau_med": 0.075, "safety_floors_mode": "PASS_THROUGH"}
            if any(raw_loaded.get("threshold_policy", {}).get(k) != v or manifest.get("threshold_policy", {}).get(k) != v for k, v in calibration_policy.items()):
                self.status = STATUS_UNAVAILABLE
                self.status_reason = "CALIBRATION_CONTRACT_MISMATCH"
                self.artifact = None
                return False

            # Verify target version
            art_target_ver = raw_loaded.get("target_version")
            if art_target_ver != TARGET_VERSION:
                self.status = STATUS_UNAVAILABLE
                self.status_reason = (
                    f"TARGET_VERSION_MISMATCH: Artifact has '{art_target_ver}', expected '{TARGET_VERSION}'"
                )
                self.artifact = None
                return False

            # Verify feature spec version and list
            art_feat_ver = raw_loaded.get("feature_spec_version")
            if art_feat_ver != FEATURE_SPEC_VERSION:
                self.status = STATUS_UNAVAILABLE
                self.status_reason = (
                    f"FEATURE_VERSION_MISMATCH: Artifact has '{art_feat_ver}', expected '{FEATURE_SPEC_VERSION}'"
                )
                self.artifact = None
                return False

            art_features = raw_loaded.get("feature_names", [])
            if list(art_features) != list(FEATURE_SET_B):
                self.status = STATUS_UNAVAILABLE
                self.status_reason = "FEATURE_ALLOWLIST_MISMATCH: Feature order or composition does not match contract"
                self.artifact = None
                return False

            # Verify preprocessor and calibrator instances
            prep = raw_loaded.get("preprocessor")
            calib = raw_loaded.get("calibrator")
            if prep is None or not getattr(prep, "is_fitted_", False):
                self.status = STATUS_UNAVAILABLE
                self.status_reason = "ARTIFACT_CORRUPT: Preprocessor missing or un-fitted"
                self.artifact = None
                return False

            # The frozen transform appends six missingness indicators internally.
            # The supervised runtime INPUT contract remains exactly 15 features.
            if list(getattr(prep, "expected_features", [])) != list(FEATURE_SET_B):
                self.status = STATUS_UNAVAILABLE
                self.status_reason = "PREPROCESSING_CONTRACT_MISMATCH"
                self.artifact = None
                return False

            if calib is None or not getattr(calib, "is_fitted_", False):
                self.status = STATUS_UNAVAILABLE
                self.status_reason = "ARTIFACT_CORRUPT: Calibrator missing or un-fitted"
                self.artifact = None
                return False

            # All validations passed
            self.artifact = raw_loaded
            self.status = STATUS_AVAILABLE
            self.status_reason = "VALID_APPROVED_ARTIFACT_LOADED"
            return True

        except Exception as exc:
            self.status = STATUS_UNAVAILABLE
            self.status_reason = f"ARTIFACT_CORRUPT: Exception loading artifact: {exc}"
            self.artifact = None
            return False

    def predict_operational_attention(
        self,
        feature_dict: Dict[str, Any],
        prior_scores: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end governed runtime inference for a single personnel operational vector.

        Returns truthful operational dictionary. If model is unavailable, probabilities and scores
        are strictly None, never falling back to legacy hardcoded values.
        """
        invalid_features = set(feature_dict) != set(FEATURE_SET_B) or len(feature_dict) != 15
        try:
            invalid_features = invalid_features or any(not math.isfinite(float(feature_dict[k])) for k in FEATURE_SET_B)
        except (KeyError, TypeError, ValueError):
            invalid_features = True
        if self.status != STATUS_AVAILABLE or self.artifact is None or invalid_features:
            return {
                "availability_status": STATUS_UNAVAILABLE,
                "availability_reason": "FEATURE_CONTRACT_MISMATCH" if invalid_features else self.status_reason,
                "calibrated_probability": None,
                "predicted_class": None,
                "raw_operational_score": None,
                "operational_strain_score": None,
                "operational_attention_band": STATUS_UNAVAILABLE,
                "operational_trend": STATUS_UNAVAILABLE,
                "primary_driver": None,
                "top_operational_drivers": [],
                "protective_factors": [],
                "confidence_score": 0.0,
                "confidence_descriptor": "UNAVAILABLE",
                "model_version": None,
            }

        preprocessor = self.artifact["preprocessor"]
        calibrator = self.artifact["calibrator"]
        feature_names = self.artifact["feature_names"]
        policy = self.artifact.get("threshold_policy", {})
        tau_high = policy.get("tau_high", DEFAULT_TAU_HIGH)
        tau_med = policy.get("tau_med", DEFAULT_TAU_MED)

        # 1. Construct single-row DataFrame with expected feature ordering
        df_row = pd.DataFrame([[feature_dict[k] for k in feature_names]], columns=feature_names)

        # 2. Transform via persisted preprocessor
        X_scaled = preprocessor.transform(df_row)

        # 3. Predict calibrated probability
        cal_probs = calibrator.predict_proba(X_scaled)[0]
        prob_pos = float(cal_probs[1])
        predicted_class = int(prob_pos >= tau_high)

        # 4. Pipeline: 0â€“100 operational score, safety floors (pass-through), trend, band
        pipe_res = execute_operational_pipeline(
            calibrated_prob=prob_pos,
            prior_scores=prior_scores,
            tau_high=tau_high,
            tau_med=tau_med,
        )

        # 5. Explanations: linear direct contributions
        # Extract base LogisticRegression coefficients
        base_lr = getattr(calibrator.calibrated_classifier_.estimator, "named_steps", {}).get(
            "classifier", getattr(calibrator.calibrated_classifier_, "estimator", None)
        )
        if hasattr(base_lr, "coef_"):
            coefs = base_lr.coef_[0]
        else:
            # Fallback if wrapped in calibrator ensemble
            first_est = calibrator.calibrated_classifier_.calibrated_classifiers_[0].estimator
            coefs = first_est.coef_[0]

        explain_res = explain_operational_prediction(
            feature_names=feature_names,
            scaled_feature_values=X_scaled[0],
            coefficients=coefs,
            raw_feature_values=feature_dict,
            top_k=4,
        )

        # 6. Epistemological Confidence
        completeness = calculate_feature_completeness(feature_dict, feature_names)
        conf_score, conf_desc, conf_bd = compute_operational_confidence(
            data_completeness=completeness,
            model_availability=1.0,
            calibration_reliability=0.97,  # 1.0 - ECE (0.0279) ~ 0.972
        )

        return {
            "availability_status": STATUS_AVAILABLE,
            "availability_reason": self.status_reason,
            "calibrated_probability": round(prob_pos, 4),
            "predicted_class": predicted_class,
            "decision_threshold": tau_high,
            "raw_operational_score": pipe_res["raw_operational_score"],
            "operational_strain_score": pipe_res["final_operational_score"],
            "operational_attention_band": pipe_res["operational_band"],
            "operational_trend": pipe_res["operational_trend"],
            "safety_floors_applied": pipe_res["safety_floors_applied"],
            "primary_driver": explain_res["primary_driver"],
            "top_operational_drivers": explain_res["top_drivers"],
            "protective_factors": explain_res["protective_factors"],
            "confidence_score": conf_score,
            "confidence_descriptor": conf_desc,
            "model_version": self.artifact["model_version"],
            "target_version": self.artifact["target_version"],
        }


# Global singleton instance for backend services
model_a_runtime = ModelARuntimeLoader(auto_load=True)
