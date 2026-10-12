from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.models.schemas import CollectionStatus, FailureType
from conftest import unit_record


@pytest.mark.parametrize("failure_type", list(FailureType))
def test_failure_replay_preserves_real_record_and_marks_latest_unavailable(service, failure_type):
    service.record_success(unit_record("2026-01-01"))
    before = service.repository.latest_real_record()

    status = service.replay_failure(failure_type)
    view = service.latest_view()

    assert status.status == CollectionStatus.FAILED
    assert status.current_latest_available is False
    assert view.current_latest is None
    assert view.last_known_good == before
    assert view.message == "현재 최신 데이터 확인 불가"
    assert len(service.repository.list_records()) == 1


def test_initial_state_does_not_claim_current_data(service):
    view = service.latest_view()
    assert view.status == CollectionStatus.UNINITIALIZED
    assert view.current_latest_available is False
    assert view.current_latest is None
    assert view.last_known_good is None


def test_normal_data_is_saved(service):
    saved = service.record_success(unit_record("2026-01-01"))
    assert saved.id is not None
    assert saved.data_origin == "real"
    assert service.repository.get_status().status == CollectionStatus.NORMAL


def test_same_basis_date_upserts_instead_of_duplicating(service):
    service.record_success(unit_record("2026-01-01", 17))
    service.record_success(unit_record("2026-01-01", 18))
    records = service.repository.list_records()
    assert len(records) == 1
    assert records[0].value == 18


def test_next_basis_date_creates_new_record(service):
    service.record_success(unit_record("2026-01-01"))
    service.record_success(unit_record("2026-01-02"))
    assert len(service.repository.list_records()) == 2


def test_recovery_requires_new_real_success_and_sets_recovered(service):
    service.record_success(unit_record("2026-01-01"))
    service.replay_failure(FailureType.TIMEOUT)
    new_record = unit_record("2026-01-02", 19)
    new_record.fetched_at_kst = datetime(2026, 1, 2, 12, tzinfo=ZoneInfo("Asia/Seoul"))

    service.record_success(new_record)
    view = service.latest_view()

    assert view.status == CollectionStatus.RECOVERED
    assert view.current_latest_available is True
    assert view.current_latest.basis_date.isoformat() == "2026-01-02"
    assert view.last_known_good == view.current_latest


def test_synthetic_record_cannot_be_promoted_to_success(service):
    record = unit_record("2026-01-01")
    record.data_origin = "synthetic"
    with pytest.raises(ValueError, match="data_origin=real"):
        service.record_success(record)


def test_synthetic_record_cannot_be_written_to_daily_storage(service):
    record = unit_record("2026-01-01")
    record.data_origin = "synthetic"
    with pytest.raises(ValueError, match="실제 수집값"):
        service.repository.upsert_daily_record(record)


def test_error_state_keeps_http_and_application_failure_fields_separate(service):
    state = service.replay_failure(FailureType.FORBIDDEN)
    assert state.failure.http_status == 403
    assert state.failure.type == FailureType.FORBIDDEN
    assert state.failure.code == "HTTP_403"
