import os

from app.config import get_database_path
from app.storage.base import RecordRepository
from app.storage.repository import SQLiteRepository


def create_repository() -> RecordRepository:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        if not database_url.startswith(("postgres://", "postgresql://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection URL")
        from app.storage.postgres import PostgresRepository

        # Never fall back to temporary local storage after a connection failure.
        return PostgresRepository(database_url)
    if os.getenv("T04_REQUIRE_POSTGRES", "false").lower() == "true":
        raise RuntimeError("DATABASE_URL is required for this deployment")
    return SQLiteRepository(get_database_path())
