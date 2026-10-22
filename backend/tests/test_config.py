import pytest
from pydantic import ValidationError

from app.api.admin import CreateUserRequest
from app.config import settings


def test_settings_loaded():
    assert settings.PROJECT_NAME == "PRAHARI"
    assert settings.SYNTHETIC_DATA_SEED == 26186
    assert settings.AGGREGATION_FLOOR >= 5


def test_wsi_weights_sum_to_one():
    total_weight = (
        settings.WSI_WEIGHT_D
        + settings.WSI_WEIGHT_R
        + settings.WSI_WEIGHT_C
        + settings.WSI_WEIGHT_N
        + settings.WSI_WEIGHT_L
        + settings.WSI_WEIGHT_H
        + settings.WSI_WEIGHT_S
    )
    assert round(total_weight, 4) == 1.0000


def test_wsi_reference_benchmark():
    # Locked benchmark from AGENTS.md, database.md, rules.md:
    # D=78, R=85, C=90, N=80, L=70, H=65, S=40 -> WSI = 77.50
    d, r, c, n, l, h, s = 78, 85, 90, 80, 70, 65, 40
    calculated_wsi = (
        settings.WSI_WEIGHT_D * d
        + settings.WSI_WEIGHT_R * r
        + settings.WSI_WEIGHT_C * c
        + settings.WSI_WEIGHT_N * n
        + settings.WSI_WEIGHT_L * l
        + settings.WSI_WEIGHT_H * h
        + settings.WSI_WEIGHT_S * s
    )
    assert round(calculated_wsi, 2) == 77.50


def test_admin_account_creation_rejects_short_passwords():
    with pytest.raises(ValidationError):
        CreateUserRequest(username="prepared-user", password="too-short", role="PERSONNEL")
