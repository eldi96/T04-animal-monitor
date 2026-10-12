from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CollectionStatus(StrEnum):
    UNINITIALIZED = "UNINITIALIZED"
    NORMAL = "NORMAL"
    FAILED = "FAILED"
    RECOVERED = "RECOVERED"


class FailureType(StrEnum):
    TIMEOUT = "TIMEOUT"
    AUTH_ERROR = "AUTH_ERROR"
    FORBIDDEN = "FORBIDDEN"
    SERVER_ERROR = "SERVER_ERROR"
    OFFLINE = "OFFLINE"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    STALE_RESPONSE = "STALE_RESPONSE"


class DataOrigin(StrEnum):
    REAL = "real"
    SYNTHETIC = "synthetic"


class DailyRecord(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: Optional[int] = None
    basis_date: date
    basis_timezone: str = Field(default="Asia/Seoul", pattern="^Asia/Seoul$")
    value: int = Field(ge=0)
    source_value: Optional[int] = Field(default=None, ge=0)
    district_counts: Optional[dict[str, int]] = None
    species_counts: Optional[dict[str, int]] = None
    status_counts: Optional[dict[str, int]] = None
    weekly_registration_counts: Optional[dict[str, int]] = None
    weekly_district_counts: Optional[dict[str, int]] = None
    weekly_species_counts: Optional[dict[str, int]] = None
    weekly_status_counts: Optional[dict[str, int]] = None
    recent_7_day_registration_counts: Optional[dict[str, int]] = None
    unit: str
    source: str
    source_timestamp: Optional[datetime] = None
    fetched_at_kst: datetime
    data_origin: DataOrigin
    error_code: Optional[str] = None
    created_at: Optional[datetime] = None

    @field_validator("fetched_at_kst")
    @classmethod
    def fetched_time_must_be_kst(cls, value: datetime) -> datetime:
        if value.utcoffset() != timedelta(hours=9):
            raise ValueError("fetched_at_kst는 Asia/Seoul(+09:00) 시각이어야 합니다.")
        return value

    @model_validator(mode="after")
    def aggregates_must_match_value(self):
        for label, counts in (("district_counts", self.district_counts), ("species_counts", self.species_counts), ("status_counts", self.status_counts)):
            if counts is not None and (any(count < 0 for count in counts.values()) or sum(counts.values()) != self.value):
                raise ValueError(f"{label}은 음수가 될 수 없고 value 합계와 같아야 합니다.")
        weekly_total = sum((self.weekly_registration_counts or {}).values())
        for label, counts in (("weekly_district_counts", self.weekly_district_counts), ("weekly_species_counts", self.weekly_species_counts), ("weekly_status_counts", self.weekly_status_counts)):
            if counts is not None and (any(count < 0 for count in counts.values()) or sum(counts.values()) != weekly_total):
                raise ValueError(f"{label}은 음수가 될 수 없고 지난주 등록 합계와 같아야 합니다.")
        return self


class FailureState(BaseModel):
    type: FailureType
    code: str
    message: str
    http_status: Optional[int] = None
    occurred_at: datetime
    data_origin: DataOrigin = DataOrigin.SYNTHETIC


class MonitoringStatus(BaseModel):
    status: CollectionStatus
    failure: Optional[FailureState] = None
    current_latest_available: bool
    last_successful_observed_at: Optional[datetime] = None
    source: Optional[str] = None
    basis_timezone: str = "Asia/Seoul"
    data_origin: Optional[DataOrigin] = None
    message: str


class LatestView(BaseModel):
    status: CollectionStatus
    current_latest: Optional[DailyRecord]
    last_known_good: Optional[DailyRecord]
    current_latest_available: bool
    failure: Optional[FailureState] = None
    message: str


class FailureReplayRequest(BaseModel):
    failure_type: FailureType


class RecoveryResponse(BaseModel):
    status: CollectionStatus
    saved_record: Optional[DailyRecord]
    current_latest_available: bool
    message: str
