"""Aggregate cells and complementary totals must not disclose small groups."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid
from datetime import date

import pytest

from app.services.commander_service import CommanderService


@pytest.mark.asyncio
@pytest.mark.parametrize("scores,suppressed", [([10] * 3, True), ([10] * 5 + [80], True), ([10] * 5 + [80] * 5, False)])
async def test_unit_partition_suppression(scores, suppressed, monkeypatch):
    monkeypatch.setattr("app.services.commander_service.settings.AGGREGATION_FLOOR", 5)
    unit = SimpleNamespace(id=uuid.uuid4(), unit_code="TEST", unit_name="Synthetic unit", unit_type="DEMO", location_label="Demo", sanctioned_strength=20)
    unit_repo = AsyncMock()
    unit_repo.get_by_id.return_value = unit
    unit_repo.get_latest_staffing.return_value = None
    analytics = AsyncMock()
    analytics.get_latest_unit_wsi_snapshots.return_value = [
        SimpleNamespace(personnel_id=uuid.uuid4(), wsi_score=score, **{name + "_component": score for name in "drcnlhs"}) for score in scores
    ]
    analytics.get_active_alerts_by_unit.return_value = []
    service = CommanderService(unit_repo, AsyncMock(), analytics, AsyncMock(), AsyncMock())
    response = await service.get_unit_overview(unit.id)
    assert response["aggregation_status"] == ("SUPPRESSED" if suppressed else "VALID")
    if suppressed:
        assert all(response["kpis"][name] is None for name in ("total_personnel", "avg_wsi", "low_risk_count", "medium_risk_count", "high_risk_count"))
        assert all(bucket["count"] is None for bucket in response["distribution"])
        assert all(driver["value"] is None for driver in response["drivers"])
    else:
        assert response["kpis"]["total_personnel"] == len(scores)
        assert [bucket["count"] for bucket in response["distribution"]] == [5, 0, 5]


@pytest.mark.asyncio
async def test_unit_risk_trends_returns_only_privacy_safe_daily_means(monkeypatch):
    monkeypatch.setattr("app.services.commander_service.settings.AGGREGATION_FLOOR", 5)
    unit_id = uuid.uuid4()
    visible_day = date(2026, 10, 18)
    suppressed_day = date(2026, 10, 19)
    analytics = AsyncMock()
    analytics.get_unit_wsi_history.return_value = [
        *[
            SimpleNamespace(
                personnel_id=uuid.uuid4(), snapshot_date=visible_day, wsi_score=score
            )
            for score in (40, 50, 60, 70, 80)
        ],
        *[
            SimpleNamespace(
                personnel_id=uuid.uuid4(), snapshot_date=suppressed_day, wsi_score=score
            )
            for score in (20, 30, 40, 50)
        ],
    ]
    service = CommanderService(AsyncMock(), AsyncMock(), analytics, AsyncMock(), AsyncMock())

    result = await service.get_unit_risk_trends(unit_id)

    assert result == [{
        "date": visible_day.isoformat(),
        "mean_wsi": 60.0,
        "eligible_personnel": 5,
        "status": "VALID",
    }]
