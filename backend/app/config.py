from pathlib import Path
import os


PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Store this project's snapshots in its own database.
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "t04-animals.sqlite"


def _load_local_env() -> None:
    """Load simple KEY=VALUE entries from the ignored repository .env file."""
    env_file = PROJECT_ROOT / ".env"
    if not env_file.is_file():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if name:
            os.environ.setdefault(name, value)


_load_local_env()


def get_database_path() -> Path:
    configured = os.getenv("T04_DB_PATH")
    if not configured:
        return DEFAULT_DB_PATH
    path = Path(configured)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def get_data_go_service_key() -> str | None:
    return os.getenv("DATA_GO_KR_SERVICE_KEY") or None
