"""Production Model-A must start and infer without importing any offline package."""
import subprocess
import sys


def test_application_and_frozen_inference_without_tools():
    code = '''
import importlib.abc
import sys
class RejectTools(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "tools" or fullname.startswith("tools."):
            raise AssertionError("Runtime imported offline package: " + fullname)
sys.meta_path.insert(0, RejectTools())
from app.main import app
from app.ml.runtime_loader import model_a_runtime
from app.ml.features_hr import FEATURE_SET_B
assert model_a_runtime.status == "MODEL_AVAILABLE", model_a_runtime.status_reason
result = model_a_runtime.predict_operational_attention({name: 15.0 for name in FEATURE_SET_B})
assert result["availability_status"] == "MODEL_AVAILABLE"
assert 0 <= result["calibrated_probability"] <= 1
assert app.openapi()["paths"]
assert not any(name == "tools" or name.startswith("tools.") for name in sys.modules)
'''
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_frozen_runtime_estimators_cannot_train():
    from app.ml.runtime_loader import model_a_runtime
    from tools.training.calibrate import GovernedCalibrator
    from tools.training.preprocessing import GovernedPreprocessor

    assert model_a_runtime.status == "MODEL_AVAILABLE"
    for name in ("preprocessor", "calibrator"):
        estimator = model_a_runtime.artifact[name]
        assert not hasattr(estimator, "fit")
        assert not hasattr(estimator, "save")
    assert callable(GovernedPreprocessor.fit)
    assert callable(GovernedCalibrator.fit)
