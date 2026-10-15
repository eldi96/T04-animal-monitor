"""Shared server storage. Imported only when DATABASE_URL is configured."""
from datetime import datetime
from zoneinfo import ZoneInfo

from app.models.schemas import DailyRecord, MonitoringStatus


class PostgresRepository:
    def __init__(self, database_url: str):
        self._database_url = database_url
        self._initialize()

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        # The context manager commits on success, rolls back on failure, and closes.
        return psycopg.connect(self._database_url, row_factory=dict_row, connect_timeout=10)

    def _initialize(self):
        with self._connect() as connection:
            connection.execute("CREATE SCHEMA IF NOT EXISTS t04")
            connection.execute("""CREATE TABLE IF NOT EXISTS t04.daily_records (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                basis_date TEXT NOT NULL UNIQUE,
                record_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS t04.monitoring_state (
                singleton_id INTEGER PRIMARY KEY CHECK(singleton_id = 1),
                state_json TEXT NOT NULL
            )""")
            initial = MonitoringStatus(
                status="UNINITIALIZED", current_latest_available=False,
                message="아직 실제 데이터 수집이 설정되지 않았습니다.",
            )
            connection.execute(
                "INSERT INTO t04.monitoring_state VALUES (1, %s) ON CONFLICT DO NOTHING",
                (initial.model_dump_json(),),
            )

    @staticmethod
    def _record(row) -> DailyRecord:
        record = DailyRecord.model_validate_json(row["record_json"])
        return record.model_copy(update={"id": row["id"], "created_at": datetime.fromisoformat(row["created_at"])})

    def upsert_daily_record(self, record: DailyRecord) -> DailyRecord:
        if record.data_origin != "real":
            raise ValueError("daily_records에는 실제 수집값(data_origin=real)만 저장할 수 있습니다.")
        with self._connect() as connection:
            row = connection.execute(
                """INSERT INTO t04.daily_records (basis_date, record_json, created_at)
                VALUES (%s, %s, %s) ON CONFLICT(basis_date) DO UPDATE SET
                record_json=excluded.record_json RETURNING *""",
                (record.basis_date.isoformat(), record.model_dump_json(), datetime.now(ZoneInfo("Asia/Seoul")).isoformat()),
            ).fetchone()
        return self._record(row)

    def list_records(self) -> list[DailyRecord]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM t04.daily_records ORDER BY basis_date").fetchall()
        return [self._record(row) for row in rows]

    def latest_real_record(self) -> DailyRecord | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM t04.daily_records ORDER BY basis_date DESC LIMIT 1").fetchone()
        return self._record(row) if row else None

    def get_status(self) -> MonitoringStatus:
        with self._connect() as connection:
            row = connection.execute("SELECT state_json FROM t04.monitoring_state WHERE singleton_id=1").fetchone()
        return MonitoringStatus.model_validate_json(row["state_json"])

    def set_status(self, status: MonitoringStatus) -> None:
        with self._connect() as connection:
            connection.execute("UPDATE t04.monitoring_state SET state_json=%s WHERE singleton_id=1", (status.model_dump_json(),))
