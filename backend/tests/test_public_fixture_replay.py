from pathlib import Path

import pytest

from app.services.replay import ReplayService
from conftest import unit_record


FAILURES = {
    "T04-TIMEOUT": "timeout",
    "T04-AUTH-401": "auth",
    "T04-RATE-429": "rate_limit",
    "T04-OFFLINE": "offline",
    "T04-SCHEMA-BREAK": "schema_error",
}


@pytest.fixture
def replay():
    root = Path(__file__).resolve().parents[2] / "assets" / "studio-task-assets" / "t04-real-information-board"
    return ReplayService(root)


def prepare_baseline(replay):
    replay.reset()
    first = replay.run_fixture("T04-NORMAL-D1-A")
    second = replay.run_fixture("T04-NORMAL-D1-B")
    assert len(first["daily_readings"]) == 1
    assert len(second["daily_readings"]) == 1
    assert second["daily_readings"][0]["record_id"] == first["daily_readings"][0]["record_id"]
    assert second["daily_readings"][0]["normalized_value"] == 105
    return second


def test_public_asset_manifest_hashes_match(replay):
    report = replay.verify_package()
    assert report["package_id"] == "aleph-t04-real-information-board-public-contract-v2"
    assert report["checked_file_count"] == 17
    assert report["integrity_ok"] is True


def test_default_replay_service_resolves_course_asset_location():
    assert ReplayService().verify_package()["integrity_ok"] is True


def test_normal_d2_adds_one_day_and_computes_delta(replay):
    prepare_baseline(replay)
    state = replay.run_fixture("T04-NORMAL-D2")
    assert state["status"] == {"freshness": "fresh", "error_code": "none"}
    assert len(state["daily_readings"]) == 2
    assert state["last_delta"] == 15
    assert state["current_reading"]["normalized_value"] == 120


@pytest.mark.parametrize(("fixture_id", "error_code"), FAILURES.items())
def test_each_failure_keeps_last_good_and_marks_it_stale(replay, fixture_id, error_code):
    before = prepare_baseline(replay)
    state = replay.run_fixture(fixture_id)
    assert state["status"] == {"freshness": "stale", "error_code": error_code}
    assert len(state["daily_readings"]) == 1
    assert state["daily_readings"][0]["normalized_value"] == 105
    assert state["daily_readings"][0]["record_id"] == before["daily_readings"][0]["record_id"]
    assert state["current_reading"]["normalized_value"] == 105
    assert state["next_action_ko"]


def test_recovery_fixture_adds_exactly_one_next_day_record(replay):
    prepare_baseline(replay)
    replay.run_fixture("T04-TIMEOUT")
    recovered = replay.run_fixture("T04-RECOVER-D2")
    assert recovered["status"] == {"freshness": "fresh", "error_code": "none"}
    assert len(recovered["daily_readings"]) == 2
    assert recovered["daily_readings"][1]["record_date"] == "2026-08-25"
    assert recovered["daily_readings"][1]["normalized_value"] == 120
    assert recovered["last_delta"] == 15
    replay.run_fixture("T04-RECOVER-D2")
    assert len(replay.snapshot()["daily_readings"]) == 2


def test_replay_reset_only_clears_synthetic_state(replay, service):
    service.record_success(unit_record("2026-01-01", 44))
    prepare_baseline(replay)
    replay.reset()
    assert replay.snapshot()["daily_readings"] == []
    assert len(service.repository.list_records()) == 1
    assert service.repository.latest_real_record().value == 44
