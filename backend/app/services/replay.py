"""Deterministic T04 public-fixture replay, isolated from live data storage."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")
ERROR_CODES = {"timeout", "auth", "rate_limit", "offline", "schema_error"}
FIXTURE_IDS = {
    "T04-NORMAL-D1-A": "normal-d1-a.json",
    "T04-NORMAL-D1-B": "normal-d1-b.json",
    "T04-NORMAL-D2": "normal-d2.json",
    "T04-TIMEOUT": "timeout.json",
    "T04-AUTH-401": "auth-401.json",
    "T04-RATE-429": "rate-429.json",
    "T04-OFFLINE": "offline.json",
    "T04-SCHEMA-BREAK": "schema-break.json",
    "T04-RECOVER-D2": "recover-d2.json",
}
NORMALIZED_KEYS = {
    "signal_id", "normalized_value", "unit", "source_name", "source_url",
    "source_time", "fetched_at", "record_timezone", "record_date",
}
NEXT_ACTIONS = {
    "timeout": "외부 응답이 늦었습니다. 잠시 기다린 뒤 다시 시도하세요.",
    "auth": "외부 원천이 인증을 거절했습니다. API 인증 설정과 이용 권한을 확인한 뒤 다시 시도하세요.",
    "rate_limit": "외부 원천이 호출을 제한했습니다. 안내된 재시도 대기 시간 후 다시 시도하세요.",
    "offline": "네트워크 연결을 확인한 뒤 다시 시도하세요.",
    "schema_error": "외부 응답 형식이 변경됐을 수 있습니다. 필드 구조를 확인한 뒤 다시 시도하세요.",
}


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed


class ReplayService:
    """Replays only the public synthetic fixtures; never touches SQLite live records."""

    def __init__(self, asset_root: Path | None = None):
        self.asset_root = asset_root or Path(__file__).resolve().parents[3] / "assets" / "studio-task-assets" / "t04-real-information-board"
        self.state: dict[str, Any] = self.reset()

    def verify_package(self) -> dict[str, Any]:
        manifest_path = self.asset_root / "asset-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        results = []
        for entry in manifest["files"]:
            path = self.asset_root / entry["path"]
            content = path.read_bytes() if path.is_file() else b""
            results.append({
                "path": entry["path"],
                "exists": path.is_file(),
                "bytes_match": len(content) == entry["bytes"],
                "sha256_match": hashlib.sha256(content).hexdigest() == entry["sha256"],
                "expected_sha256": entry["sha256"],
            })
        return {
            "package_id": manifest["package_id"],
            "hash_algorithm": manifest["hash_algorithm"],
            "checked_file_count": len(results),
            "integrity_ok": all(row["exists"] and row["bytes_match"] and row["sha256_match"] for row in results),
            "files": results,
        }

    def reset(self) -> dict[str, Any]:
        """Reset only the synthetic replay state, not real daily records or status."""
        self.state = {
            "schema_version": "aleph-t04-evaluation-state-v1",
            "data_origin": "synthetic",
            "daily_readings": [],
            "current_reading": None,
            "status": None,
            "last_delta": None,
            "last_comparison": {"state": "insufficient", "direction": None, "magnitude": None, "unit": None},
            "last_run": None,
            "sequence": 0,
            "message_ko": "합성 fixture 재생을 시작하기 전입니다.",
            "next_action_ko": None,
        }
        return self.snapshot()

    def run_fixture(self, fixture_id: str) -> dict[str, Any]:
        if fixture_id not in FIXTURE_IDS:
            raise ValueError(f"알 수 없는 공개 fixture입니다: {fixture_id}")
        if not self.verify_package()["integrity_ok"]:
            raise RuntimeError("공개 fixture 패키지의 크기 또는 SHA-256 검증에 실패했습니다.")

        path = self.asset_root / "fixtures" / FIXTURE_IDS[fixture_id]
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if fixture.get("fixture_id") != fixture_id or fixture.get("contract_version") != "1.1.0":
            raise ValueError("fixture ID 또는 계약 버전이 공개 정본과 일치하지 않습니다.")

        transport = fixture["transport"]
        status = transport["status"]
        code: str | None = None
        if transport["mode"] == "timeout":
            code = "timeout"
        elif transport["mode"] == "offline":
            code = "offline"
        elif status in (401, 403):
            code = "auth"
        elif status == 429:
            code = "rate_limit"
        elif status is None or status < 200 or status >= 300:
            code = "schema_error"
        else:
            try:
                self._apply_reading(fixture["payload"])
            except (TypeError, ValueError, KeyError):
                code = "schema_error"

        if code:
            retry_after = transport["headers"].get("retry-after")
            self.state["status"] = {"freshness": "stale", "error_code": code}
            self.state["sequence"] += 1
            self.state["last_run"] = {
                "fixture_id": fixture_id,
                "virtual_now": fixture["virtual_now"],
                "outcome": "error",
                "error_code": code,
                "retry_after_seconds": int(retry_after) if retry_after is not None else None,
            }
            self.state["message_ko"] = fixture["description_ko"]
            self.state["next_action_ko"] = NEXT_ACTIONS[code]
        else:
            self.state["sequence"] += 1
            self.state["last_run"] = {
                "fixture_id": fixture_id,
                "virtual_now": fixture["virtual_now"],
                "outcome": "success",
                "error_code": "none",
                "retry_after_seconds": None,
            }
            self.state["message_ko"] = fixture["description_ko"]
            self.state["next_action_ko"] = None
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self.state)

    def _apply_reading(self, reading: dict[str, Any]) -> None:
        if not isinstance(reading, dict) or set(reading) != NORMALIZED_KEYS:
            raise TypeError("normalized reading keys differ from the public schema")
        value = reading["normalized_value"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise TypeError("normalized_value must be a finite number")
        if reading["record_timezone"] != "Asia/Seoul":
            raise ValueError("record_timezone must be Asia/Seoul")
        if not str(reading["source_url"]).startswith("https://"):
            raise ValueError("source_url must use HTTPS")
        fetched_at = _parse_time(reading["fetched_at"])
        if fetched_at.astimezone(KST).date().isoformat() != reading["record_date"]:
            raise ValueError("record_date must match fetched_at in Asia/Seoul")
        for field in ("signal_id", "unit", "source_name"):
            if not isinstance(reading[field], str) or not reading[field].strip():
                raise TypeError(f"{field} must be a non-empty string")

        rows = self.state["daily_readings"]
        index = next((i for i, row in enumerate(rows) if row["signal_id"] == reading["signal_id"] and row["record_date"] == reading["record_date"]), -1)
        previous_row = rows[index] if index >= 0 else None
        record_id = previous_row["record_id"] if previous_row else f"demo-{reading['signal_id']}-{reading['record_date']}"
        row = {
            "record_id": record_id,
            "signal_id": reading["signal_id"],
            "record_date": reading["record_date"],
            "normalized_value": value,
            "unit": reading["unit"],
            "first_fetched_at": previous_row["first_fetched_at"] if previous_row else reading["fetched_at"],
            "last_fetched_at": reading["fetched_at"],
            "reading": copy.deepcopy(reading),
        }
        if index >= 0:
            rows[index] = row
        else:
            rows.append(row)
        rows.sort(key=lambda item: (item["signal_id"], item["record_date"]))

        previous = next((item for item in reversed(rows) if item["signal_id"] == reading["signal_id"] and item["record_date"] < reading["record_date"]), None)
        if previous is None:
            comparison = {"state": "insufficient", "direction": None, "magnitude": None, "unit": None}
        elif previous["unit"] != reading["unit"]:
            comparison = {"state": "unit_mismatch", "direction": None, "magnitude": None, "unit": None}
        else:
            signed = value - previous["normalized_value"]
            comparison = {
                "state": "comparable",
                "direction": "increase" if signed > 0 else "decrease" if signed < 0 else "unchanged",
                "magnitude": abs(signed),
                "unit": reading["unit"],
            }
        self.state["current_reading"] = copy.deepcopy(reading)
        self.state["status"] = {"freshness": "fresh", "error_code": "none"}
        self.state["last_comparison"] = comparison
        self.state["last_delta"] = comparison["magnitude"]
