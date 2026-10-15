from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import (
    DailyRecord,
    DataOrigin,
    FailureState,
    LatestView,
    MonitoringStatus,
    RecoveryResponse,
)
from app.services.monitoring import MonitoringService
from app.services.replay import ReplayService
from app.services.animal_api import ProviderError, collect_snapshot
from app.storage.factory import create_repository


router = APIRouter(prefix="/api")
KST = ZoneInfo("Asia/Seoul")
replay_service = ReplayService()


def get_service() -> MonitoringService:
    return MonitoringService(create_repository())


@router.get("/status", response_model=MonitoringStatus)
def status(service: MonitoringService = Depends(get_service)):
    return service.repository.get_status()


@router.get("/latest", response_model=LatestView)
def latest(service: MonitoringService = Depends(get_service)):
    return service.latest_view()


@router.get("/daily-records", response_model=list[DailyRecord])
def daily_records(service: MonitoringService = Depends(get_service)):
    return service.repository.list_records()


@router.get("/replay/package")
async def replay_package():
    return replay_service.verify_package()


@router.get("/replay/state")
async def replay_state():
    return replay_service.snapshot()


@router.post("/replay/reset")
async def replay_reset():
    return replay_service.reset()


@router.post("/replay/fixtures/{fixture_id}")
async def replay_fixture(fixture_id: str):
    try:
        return replay_service.run_fixture(fixture_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/replay/recover")
async def replay_recover():
    state = replay_service.snapshot()
    if not state["status"] or state["status"]["freshness"] != "stale":
        raise HTTPException(status_code=409, detail="합성 실패 상태에서만 fixture 복구를 재생할 수 있습니다.")
    try:
        return replay_service.run_fixture("T04-RECOVER-D2")
    except (ValueError, RuntimeError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/test/recover", response_model=RecoveryResponse)
async def recover(service: MonitoringService = Depends(get_service)):
    current = service.repository.get_status()
    last_good = service.repository.latest_real_record()
    if current.status.value != "FAILED":
        raise HTTPException(status_code=409, detail="복구할 실패 상태가 없습니다.")
    try:
        record = await collect_snapshot(datetime.now(KST).date())
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ProviderError as error:
        service.record_failure(FailureState(
            type=error.failure_type,
            code=error.code,
            message=error.message,
            http_status=error.http_status,
            occurred_at=datetime.now(KST),
            data_origin=DataOrigin.REAL,
        ))
        raise HTTPException(status_code=502, detail=error.message) from error
    saved = service.record_success(record)
    return RecoveryResponse(
        status=service.repository.get_status().status,
        saved_record=saved,
        current_latest_available=True,
        message="새 실제 데이터 수집 후 복구했습니다.",
    )


@router.post("/collect", response_model=DailyRecord)
async def collect(basis_date: date, service: MonitoringService = Depends(get_service)):
    if basis_date != datetime.now(KST).date():
        raise HTTPException(status_code=400, detail="유기동물 API는 과거 시점 조회를 지원하지 않아 오늘 날짜 스냅샷만 저장할 수 있습니다.")
    return await _collect_and_save(service)


@router.post("/collect/today", response_model=DailyRecord)
async def collect_today(service: MonitoringService = Depends(get_service)):
    return await _collect_and_save(service)


async def _collect_and_save(service: MonitoringService) -> DailyRecord:
    try:
        record = await collect_snapshot(datetime.now(KST).date())
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ProviderError as error:
        service.record_failure(FailureState(
            type=error.failure_type,
            code=error.code,
            message=error.message,
            http_status=error.http_status,
            occurred_at=datetime.now(KST),
            data_origin=DataOrigin.REAL,
        ))
        raise HTTPException(status_code=502, detail=error.message) from error
    return service.record_success(record)
