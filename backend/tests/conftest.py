from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app.models.schemas import DailyRecord
from app.services.monitoring import MonitoringService
from app.storage.repository import SQLiteRepository


@pytest.fixture
def service(tmp_path: Path):
    return MonitoringService(SQLiteRepository(tmp_path / "isolated-test.sqlite"))


def unit_record(day: str, value: int = 17) -> DailyRecord:
    """Deterministic test-only record; it is written only to pytest's temporary DB."""
    return DailyRecord(
        basis_date=day,
        basis_timezone="Asia/Seoul",
        value=value,
        unit="건",
        source="unit-test-only",
        source_timestamp=None,
        fetched_at_kst=datetime(2026, 1, 1, 12, tzinfo=ZoneInfo("Asia/Seoul")),
        data_origin="real",
    )
