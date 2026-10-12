import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from app.models.schemas import (
    CollectionStatus,
    DailyRecord,
    FailureState,
    MonitoringStatus,
)


class SQLiteRepository:
    def __init__(self, path: Path | str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS daily_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    basis_date TEXT NOT NULL UNIQUE,
                    basis_timezone TEXT NOT NULL,
                    value INTEGER NOT NULL CHECK(value >= 0),
                    source_value INTEGER CHECK(source_value IS NULL OR source_value >= 0),
                    district_counts_json TEXT,
                    species_counts_json TEXT,
                    status_counts_json TEXT,
                    weekly_registration_counts_json TEXT,
                    weekly_district_counts_json TEXT,
                    weekly_species_counts_json TEXT,
                    weekly_status_counts_json TEXT,
                    recent_7_day_registration_counts_json TEXT,
                    unit TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_timestamp TEXT,
                    fetched_at_kst TEXT NOT NULL,
                    data_origin TEXT NOT NULL CHECK(data_origin IN ('real', 'synthetic')),
                    error_code TEXT,
                    created_at TEXT NOT NULL
                )"""
            )
            record_columns = {row["name"] for row in connection.execute("PRAGMA table_info(daily_records)")}
            if "source_value" not in record_columns:
                connection.execute("ALTER TABLE daily_records ADD COLUMN source_value INTEGER")
            if "district_counts_json" not in record_columns:
                connection.execute("ALTER TABLE daily_records ADD COLUMN district_counts_json TEXT")
            if "species_counts_json" not in record_columns:
                connection.execute("ALTER TABLE daily_records ADD COLUMN species_counts_json TEXT")
            if "status_counts_json" not in record_columns:
                connection.execute("ALTER TABLE daily_records ADD COLUMN status_counts_json TEXT")
            if "weekly_registration_counts_json" not in record_columns:
                connection.execute("ALTER TABLE daily_records ADD COLUMN weekly_registration_counts_json TEXT")
            for column in ("weekly_district_counts_json", "weekly_species_counts_json", "weekly_status_counts_json"):
                if column not in record_columns:
                    connection.execute(f"ALTER TABLE daily_records ADD COLUMN {column} TEXT")
            if "recent_7_day_registration_counts_json" not in record_columns:
                connection.execute("ALTER TABLE daily_records ADD COLUMN recent_7_day_registration_counts_json TEXT")
            # Keep stored historical display labels consistent with current API mappings.
            species_rows = connection.execute("SELECT id, species_counts_json FROM daily_records WHERE species_counts_json IS NOT NULL").fetchall()
            for row in species_rows:
                species_counts = json.loads(row["species_counts_json"])
                if "개" in species_counts:
                    species_counts["강아지"] = species_counts.get("강아지", 0) + species_counts.pop("개")
                    connection.execute(
                        "UPDATE daily_records SET species_counts_json=? WHERE id=?",
                        (json.dumps(species_counts, ensure_ascii=False), row["id"]),
                    )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS monitoring_state (
                    singleton_id INTEGER PRIMARY KEY CHECK(singleton_id = 1),
                    status TEXT NOT NULL,
                    failure_json TEXT,
                    current_latest_available INTEGER NOT NULL,
                    last_successful_observed_at TEXT,
                    source TEXT,
                    data_origin TEXT,
                    message TEXT NOT NULL
                )"""
            )
            connection.execute(
                """INSERT OR IGNORE INTO monitoring_state
                   (singleton_id, status, current_latest_available, message)
                   VALUES (1, 'UNINITIALIZED', 0, '아직 실제 데이터 수집이 설정되지 않았습니다.')"""
            )

    def upsert_daily_record(self, record: DailyRecord) -> DailyRecord:
        if record.data_origin != "real":
            raise ValueError("daily_records에는 실제 수집값(data_origin=real)만 저장할 수 있습니다.")
        now = datetime.now(ZoneInfo("Asia/Seoul")).isoformat()
        payload = record.model_dump(mode="json")
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO daily_records
                   (basis_date, basis_timezone, value, source_value, district_counts_json, species_counts_json, status_counts_json, weekly_registration_counts_json, weekly_district_counts_json, weekly_species_counts_json, weekly_status_counts_json, recent_7_day_registration_counts_json, unit, source, source_timestamp,
                    fetched_at_kst, data_origin, error_code, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(basis_date) DO UPDATE SET
                     basis_timezone=excluded.basis_timezone,
                     value=excluded.value,
                     source_value=excluded.source_value,
                     district_counts_json=excluded.district_counts_json,
                     species_counts_json=excluded.species_counts_json,
                     status_counts_json=excluded.status_counts_json,
                     weekly_registration_counts_json=excluded.weekly_registration_counts_json,
                     weekly_district_counts_json=excluded.weekly_district_counts_json,
                     weekly_species_counts_json=excluded.weekly_species_counts_json,
                     weekly_status_counts_json=excluded.weekly_status_counts_json,
                     recent_7_day_registration_counts_json=excluded.recent_7_day_registration_counts_json,
                     unit=excluded.unit,
                     source=excluded.source,
                     source_timestamp=excluded.source_timestamp,
                     fetched_at_kst=excluded.fetched_at_kst,
                     data_origin=excluded.data_origin,
                     error_code=excluded.error_code""",
                (
                    payload["basis_date"],
                    payload["basis_timezone"],
                    payload["value"],
                    payload["source_value"],
                    json.dumps(payload["district_counts"], ensure_ascii=False) if payload["district_counts"] is not None else None,
                    json.dumps(payload["species_counts"], ensure_ascii=False) if payload["species_counts"] is not None else None,
                    json.dumps(payload["status_counts"], ensure_ascii=False) if payload["status_counts"] is not None else None,
                    json.dumps(payload["weekly_registration_counts"], ensure_ascii=False) if payload["weekly_registration_counts"] is not None else None,
                    json.dumps(payload["weekly_district_counts"], ensure_ascii=False) if payload["weekly_district_counts"] is not None else None,
                    json.dumps(payload["weekly_species_counts"], ensure_ascii=False) if payload["weekly_species_counts"] is not None else None,
                    json.dumps(payload["weekly_status_counts"], ensure_ascii=False) if payload["weekly_status_counts"] is not None else None,
                    json.dumps(payload["recent_7_day_registration_counts"], ensure_ascii=False) if payload["recent_7_day_registration_counts"] is not None else None,
                    payload["unit"],
                    payload["source"],
                    payload["source_timestamp"],
                    payload["fetched_at_kst"],
                    payload["data_origin"],
                    payload["error_code"],
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM daily_records WHERE basis_date = ?",
                (payload["basis_date"],),
            ).fetchone()
        return self._record_from_row(row)

    def latest_real_record(self) -> Optional[DailyRecord]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM daily_records WHERE data_origin='real' ORDER BY basis_date DESC LIMIT 1"
            ).fetchone()
        return self._record_from_row(row) if row else None

    def list_records(self) -> list[DailyRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM daily_records WHERE data_origin='real' ORDER BY basis_date"
            ).fetchall()
        return [self._record_from_row(row) for row in rows]

    def get_status(self) -> MonitoringStatus:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM monitoring_state WHERE singleton_id=1"
            ).fetchone()
        failure = FailureState.model_validate(json.loads(row["failure_json"])) if row["failure_json"] else None
        return MonitoringStatus(
            status=row["status"],
            failure=failure,
            current_latest_available=bool(row["current_latest_available"]),
            last_successful_observed_at=row["last_successful_observed_at"],
            source=row["source"],
            data_origin=row["data_origin"],
            message=row["message"],
        )

    def set_status(self, status: MonitoringStatus) -> None:
        failure_json = status.failure.model_dump_json() if status.failure else None
        with self._connect() as connection:
            connection.execute(
                """UPDATE monitoring_state SET status=?, failure_json=?,
                   current_latest_available=?, last_successful_observed_at=?,
                   source=?, data_origin=?, message=? WHERE singleton_id=1""",
                (
                    status.status.value if isinstance(status.status, CollectionStatus) else status.status,
                    failure_json,
                    int(status.current_latest_available),
                    status.last_successful_observed_at.isoformat() if status.last_successful_observed_at else None,
                    status.source,
                    status.data_origin.value if hasattr(status.data_origin, "value") else status.data_origin,
                    status.message,
                ),
            )

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> DailyRecord:
        return DailyRecord(
            id=row["id"],
            basis_date=date.fromisoformat(row["basis_date"]),
            basis_timezone=row["basis_timezone"],
            value=row["value"],
            source_value=row["source_value"],
            district_counts=json.loads(row["district_counts_json"]) if row["district_counts_json"] else None,
            species_counts=json.loads(row["species_counts_json"]) if row["species_counts_json"] else None,
            status_counts=json.loads(row["status_counts_json"]) if row["status_counts_json"] else None,
            weekly_registration_counts=json.loads(row["weekly_registration_counts_json"]) if row["weekly_registration_counts_json"] else None,
            weekly_district_counts=json.loads(row["weekly_district_counts_json"]) if row["weekly_district_counts_json"] else None,
            weekly_species_counts=json.loads(row["weekly_species_counts_json"]) if row["weekly_species_counts_json"] else None,
            weekly_status_counts=json.loads(row["weekly_status_counts_json"]) if row["weekly_status_counts_json"] else None,
            recent_7_day_registration_counts=json.loads(row["recent_7_day_registration_counts_json"]) if row["recent_7_day_registration_counts_json"] else None,
            unit=row["unit"],
            source=row["source"],
            source_timestamp=row["source_timestamp"],
            fetched_at_kst=row["fetched_at_kst"],
            data_origin=row["data_origin"],
            error_code=row["error_code"],
            created_at=row["created_at"],
        )
