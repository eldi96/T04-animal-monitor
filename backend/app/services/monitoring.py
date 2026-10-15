import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.models.schemas import (
    CollectionStatus,
    DailyRecord,
    FailureState,
    FailureType,
    LatestView,
    MonitoringStatus,
)
from app.storage.base import RecordRepository


KST = ZoneInfo("Asia/Seoul")


class MonitoringService:
    def __init__(self, repository: RecordRepository):
        self.repository = repository

    def record_success(self, record: DailyRecord) -> DailyRecord:
        if record.data_origin != "real":
            raise ValueError("정상 수집값은 data_origin=real 이어야 합니다.")
        saved = self.repository.upsert_daily_record(record)
        previous = self.repository.get_status()
        next_status = (
            CollectionStatus.RECOVERED
            if previous.status == CollectionStatus.FAILED
            else CollectionStatus.NORMAL
        )
        self.repository.set_status(
            MonitoringStatus(
                status=next_status,
                current_latest_available=True,
                last_successful_observed_at=record.fetched_at_kst,
                source=record.source,
                data_origin="real",
                message="실제 데이터 수집이 정상 완료되었습니다.",
            )
        )
        return saved

    def record_failure(self, failure: FailureState) -> MonitoringStatus:
        previous = self.repository.get_status()
        last_real = self.repository.latest_real_record()
        status = MonitoringStatus(
            status=CollectionStatus.FAILED,
            failure=failure,
            current_latest_available=False,
            last_successful_observed_at=(
                last_real.fetched_at_kst if last_real else previous.last_successful_observed_at
            ),
            source=last_real.source if last_real else previous.source,
            data_origin="real" if last_real else None,
            message="현재 최신 데이터 확인 불가",
        )
        self.repository.set_status(status)
        return status

    def replay_failure(self, failure_type: FailureType) -> MonitoringStatus:
        now = datetime.now(KST)
        fixture_names = {
            FailureType.TIMEOUT: "timeout.json",
            FailureType.AUTH_ERROR: "http_401.json",
            FailureType.FORBIDDEN: "http_403.json",
            FailureType.SERVER_ERROR: "http_500.json",
            FailureType.OFFLINE: "offline.json",
            FailureType.MALFORMED_RESPONSE: "malformed_response.json",
            FailureType.STALE_RESPONSE: "stale_response.json",
        }
        fixture_dir = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
        fixture = json.loads((fixture_dir / fixture_names[failure_type]).read_text(encoding="utf-8"))
        if fixture.get("data_origin") != "synthetic":
            raise ValueError("실패 재생 fixture는 data_origin=synthetic이어야 합니다.")
        messages = {
            FailureType.TIMEOUT: "외부 응답이 제한 시간 안에 도착하지 않았습니다.",
            FailureType.AUTH_ERROR: "인증 오류(401)가 재생되었습니다.",
            FailureType.FORBIDDEN: "접근 거부(403)가 재생되었습니다.",
            FailureType.SERVER_ERROR: "외부 서버 오류(500)가 재생되었습니다.",
            FailureType.OFFLINE: "오프라인 상태가 재생되었습니다.",
            FailureType.MALFORMED_RESPONSE: "응답 형식 오류가 재생되었습니다.",
            FailureType.STALE_RESPONSE: "오래된 응답이 재생되었습니다.",
        }
        failure = FailureState(
            type=failure_type,
            code=fixture["code"],
            message=messages[failure_type],
            http_status=fixture["http_status"],
            occurred_at=now,
            data_origin=fixture["data_origin"],
        )
        # Failure replay is synthetic and never writes a daily record.
        return self.record_failure(failure)

    def latest_view(self) -> LatestView:
        status = self.repository.get_status()
        last_good = self.repository.latest_real_record()
        current = last_good if status.current_latest_available and status.status in {
            CollectionStatus.NORMAL,
            CollectionStatus.RECOVERED,
        } else None
        return LatestView(
            status=status.status,
            current_latest=current,
            last_known_good=last_good,
            current_latest_available=status.current_latest_available,
            failure=status.failure,
            message=status.message,
        )
