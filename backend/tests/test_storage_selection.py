import asyncio
from unittest.mock import MagicMock

import pytest

from app.storage.factory import create_repository
from app.storage.postgres import PostgresRepository
from app.storage.repository import SQLiteRepository
from conftest import unit_record


def test_unconnected_mode_uses_persistent_local_sqlite(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("T04_REQUIRE_POSTGRES", raising=False)
    monkeypatch.setenv("T04_DB_PATH", str(tmp_path / "local.sqlite"))
    first = create_repository()
    assert isinstance(first, SQLiteRepository)
    first.upsert_daily_record(unit_record("2026-10-15"))
    assert create_repository().list_records()[0].value == 17


def test_deployment_rejects_missing_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("T04_REQUIRE_POSTGRES", "true")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        create_repository()


def test_configured_database_failure_never_falls_back(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example.invalid/t04")
    def fail(_):
        raise ConnectionError("test database unavailable")
    monkeypatch.setattr(PostgresRepository, "_initialize", fail)
    with pytest.raises(ConnectionError):
        create_repository()


def test_postgres_upsert_parameterizes_data_and_preserves_creation_time(monkeypatch):
    monkeypatch.setattr(PostgresRepository, "_initialize", lambda _: None)
    repository = PostgresRepository("postgresql://unused")
    record = unit_record("2026-10-15")
    connection = MagicMock()
    connection.execute.return_value.fetchone.return_value = {
        "id": 3, "record_json": record.model_dump_json(), "created_at": "2026-10-15T12:00:00+09:00",
    }
    context = MagicMock()
    context.__enter__.return_value = connection
    monkeypatch.setattr(repository, "_connect", lambda: context)
    saved = repository.upsert_daily_record(record)
    sql, parameters = connection.execute.call_args.args
    assert "ON CONFLICT(basis_date)" in sql
    assert "RETURNING *" in sql
    assert record.basis_date.isoformat() == parameters[0]
    assert "created_at=excluded" not in sql
    assert saved.id == 3 and saved.value == record.value
    with pytest.raises(ValueError):
        repository.upsert_daily_record(record.model_copy(update={"data_origin": "synthetic"}))


def test_manual_collection_mode_does_not_start_scheduler(monkeypatch):
    import app.main as main
    monkeypatch.delenv("T04_ENABLE_SCHEDULER", raising=False)
    def unexpected():
        raise AssertionError("automatic collection must stay disabled")
    monkeypatch.setattr(main, "run_daily_collection", unexpected)
    async def run():
        async with main.lifespan(main.app):
            pass
    asyncio.run(run())
