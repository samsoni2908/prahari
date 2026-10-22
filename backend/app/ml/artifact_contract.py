"""Read-only Model-A artifact locations, versions and hashing; no training dependencies."""
import hashlib
from pathlib import Path

ARTIFACT_VERSION = "1.0.0"
TARGET_VERSION = "v2.1-approved-leave-lifecycle"
FEATURE_SPEC_VERSION = "v2.1-SetB-15ops"
DEFAULT_ARTIFACT_PATH = Path(__file__).resolve().parent / "saved/model_a_governed_artifact.joblib"
DEFAULT_MANIFEST_PATH = Path(__file__).resolve().parent / "saved/model_a_governed_manifest.json"


def compute_file_sha256(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as stream:
        while chunk := stream.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()
