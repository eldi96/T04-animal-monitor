from dataclasses import dataclass
from datetime import date, datetime, timedelta
import math
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from zoneinfo import ZoneInfo

import httpx

from app.config import get_data_go_service_key
from app.models.schemas import DailyRecord, FailureType


ENDPOINT = "https://apis.data.go.kr/6300000/animalDaejeonService/animalDaejeonList"
SOURCE = "대전광역시 유기동물공고 현황 API"
PAGE_SIZE = 1000
KST = ZoneInfo("Asia/Seoul")
# The live response returns Daejeon municipal institution codes, rather than
# the 1–5 display values shown as examples in the portal's older schema page.
DISTRICTS = {
    "3640000": "동구", "3650000": "중구", "3660000": "서구",
    "3670000": "유성구", "3680000": "대덕구",
}
SPECIES = {"417000": "강아지", "422400": "고양이", "429900": "기타동물"}
STATUSES = {
    "1": "공고중", "2": "입양가능", "3": "입양예정", "4": "입양완료", "7": "주인반환",
}


@dataclass
class ProviderError(Exception):
    failure_type: FailureType
    code: str
    message: str
    http_status: int | None = None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(root: ET.Element, name: str) -> str | None:
    for element in root.iter():
        if _local_name(element.tag) == name and element.text:
            return element.text.strip()
    return None


def _items(root: ET.Element) -> list[ET.Element]:
    # Daejeon's live XML uses ServiceResult/MsgBody/items per record. Also
    # accept the common data.go.kr resultList and body/items variants.
    body = next((node for node in root.iter() if _local_name(node.tag) in {"MsgBody", "body"}), None)
    result_list = next((node for node in root.iter() if _local_name(node.tag) == "resultList"), None)
    container = result_list or body
    if container is None:
        return []
    direct_items = [node for node in container if _local_name(node.tag) == "items"]
    if direct_items and any(any(_local_name(child.tag) == "animalSeq" for child in node) for node in direct_items):
        return direct_items
    rows = [node for node in container if _local_name(node.tag) in {"item", "result"}]
    if rows:
        return rows
    nested_items = next((node for node in container if _local_name(node.tag) == "items"), None)
    if nested_items is not None:
        nested_rows = [node for node in nested_items if _local_name(node.tag) in {"item", "result"}]
        if nested_rows:
            return nested_rows
        if any(_local_name(node.tag) == "animalSeq" for node in nested_items):
            return [nested_items]
    if any(_local_name(node.tag) == "animalSeq" for node in container):
        return [container]
    return []


def _raise_for_result(root: ET.Element) -> None:
    code = _text(root, "resultCode") or _text(root, "returnCode") or _text(root, "returnReasonCode")
    message = _text(root, "resultMsg") or _text(root, "returnMessage") or _text(root, "errMsg") or _text(root, "returnAuthMsg") or ""
    success = _text(root, "successYN")
    if code in {"00", "0000"} or success == "Y":
        return
    normalized = (code or "").strip()
    error_text = f"{normalized} {message}".lower()
    if normalized in {"20", "30", "31"} or any(word in error_text for word in ("service_key", "auth", "permission", "인증", "권한", "접근거부")):
        kind = FailureType.AUTH_ERROR
    elif normalized == "05" or "timeout" in error_text:
        kind = FailureType.TIMEOUT
    elif normalized in {"01", "04", "12"}:
        kind = FailureType.SERVER_ERROR
    else:
        kind = FailureType.MALFORMED_RESPONSE
    # Upstream text can include request details; never expose it to the client.
    raise ProviderError(kind, normalized or "MISSING_RESULT_CODE", "대전 유기동물 API가 정상 응답을 반환하지 않았습니다.")


async def collect_snapshot(basis_date: date | None = None) -> DailyRecord:
    service_key = get_data_go_service_key()
    if not service_key:
        raise RuntimeError("DATA_GO_KR_SERVICE_KEY가 설정되지 않았습니다.")
    snapshot_date = basis_date or datetime.now(KST).date()
    if snapshot_date != datetime.now(KST).date():
        raise ValueError("이 API는 과거 시점 조회를 지원하지 않아 오늘 날짜로만 스냅샷을 저장할 수 있습니다.")

    # Decode a portal-provided encoded key once; httpx safely encodes query parameters.
    params_key = unquote(service_key)
    current_week_start = snapshot_date - timedelta(days=snapshot_date.weekday())
    week_start = current_week_start - timedelta(days=7)
    weekly_registration_counts = {
        (week_start + timedelta(days=offset)).isoformat(): 0 for offset in range(7)
    }
    weekly_district_counts = {name: 0 for name in DISTRICTS.values()}
    weekly_species_counts = {name: 0 for name in SPECIES.values()}
    weekly_status_counts = {name: 0 for name in STATUSES.values()}
    recent_start = snapshot_date - timedelta(days=6)
    recent_7_day_registration_counts = {
        (recent_start + timedelta(days=offset)).isoformat(): 0 for offset in range(7)
    }
    seen_sequences: set[str] = set()
    district_counts = {name: 0 for name in DISTRICTS.values()}
    species_counts = {name: 0 for name in SPECIES.values()}
    status_counts = {name: 0 for name in STATUSES.values()}
    unknown = {"구": 0, "동물종류": 0, "분양상태": 0}
    seen_category_fields = False
    seen_status_fields = False
    total_count: int | None = None
    total_rows_seen = 0
    published_today_count = 0
    page = 1

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0), follow_redirects=True) as client:
            while True:
                response = await client.get(ENDPOINT, params={
                    "serviceKey": params_key,
                    "pageNo": page,
                    "numOfRows": PAGE_SIZE,
                })
                if response.status_code in (401, 403):
                    kind = FailureType.AUTH_ERROR if response.status_code == 401 else FailureType.FORBIDDEN
                    raise ProviderError(kind, f"HTTP_{response.status_code}", "유기동물 API 인증 또는 접근이 거부되었습니다.", response.status_code)
                if response.status_code >= 500:
                    raise ProviderError(FailureType.SERVER_ERROR, f"HTTP_{response.status_code}", "유기동물 API 서버 오류입니다.", response.status_code)
                if response.status_code >= 400:
                    raise ProviderError(FailureType.SERVER_ERROR, f"HTTP_{response.status_code}", "유기동물 API 요청이 실패했습니다.", response.status_code)
                try:
                    root = ET.fromstring(response.content)
                except ET.ParseError as error:
                    raise ProviderError(FailureType.MALFORMED_RESPONSE, "INVALID_XML", "유기동물 API 응답이 유효한 XML이 아닙니다.") from error

                _raise_for_result(root)
                rows = _items(root)
                total_text = _text(root, "totalCount")
                if total_text is None:
                    raise ProviderError(FailureType.MALFORMED_RESPONSE, "MISSING_TOTAL_COUNT", "API 응답에 totalCount가 없습니다.")
                try:
                    page_total = int(total_text)
                except ValueError as error:
                    raise ProviderError(FailureType.MALFORMED_RESPONSE, "INVALID_TOTAL_COUNT", "API totalCount가 숫자가 아닙니다.") from error
                if total_count is not None and total_count != page_total:
                    raise ProviderError(FailureType.MALFORMED_RESPONSE, "CHANGING_TOTAL_COUNT", "페이지 조회 중 totalCount가 바뀌었습니다.")
                total_count = page_total

                for row in rows:
                    seq = _text(row, "animalSeq")
                    if not seq:
                        raise ProviderError(FailureType.MALFORMED_RESPONSE, "MISSING_ANIMAL_SEQ", "공고 응답에 게시물 번호가 없습니다.")
                    if seq in seen_sequences:
                        raise ProviderError(FailureType.MALFORMED_RESPONSE, "DUPLICATE_PAGE_RECORD", "페이지 간 중복 공고가 확인되어 수집을 중단했습니다.")
                    seen_sequences.add(seq)
                    total_rows_seen += 1

                    registered_date = _text(row, "regDtTm")
                    if not registered_date:
                        raise ProviderError(FailureType.MALFORMED_RESPONSE, "MISSING_REGISTRATION_DATE", "공고 게시글 등록일을 확인할 수 없어 오늘 공고를 집계할 수 없습니다.")
                    try:
                        registered_day = date.fromisoformat(registered_date[:10])
                    except ValueError as error:
                        raise ProviderError(FailureType.MALFORMED_RESPONSE, "INVALID_REGISTRATION_DATE", "공고 게시글 등록일 형식이 변경되어 집계를 중단했습니다.") from error
                    if week_start <= registered_day <= week_start + timedelta(days=6):
                        weekly_registration_counts[registered_day.isoformat()] += 1
                        gu = _text(row, "gu")
                        species = _text(row, "classification")
                        status = _text(row, "adoptionStatusCd")
                        weekly_district_counts[DISTRICTS.get(gu, "미분류")] = weekly_district_counts.get(DISTRICTS.get(gu, "미분류"), 0) + 1
                        weekly_species_counts[SPECIES.get(species, "기타/미확인")] = weekly_species_counts.get(SPECIES.get(species, "기타/미확인"), 0) + 1
                        weekly_status_counts[STATUSES.get(status, "기타/미확인")] = weekly_status_counts.get(STATUSES.get(status, "기타/미확인"), 0) + 1
                    if recent_start <= registered_day <= snapshot_date:
                        recent_7_day_registration_counts[registered_day.isoformat()] += 1
                    if registered_day != snapshot_date:
                        continue

                    published_today_count += 1

                    gu = _text(row, "gu")
                    species = _text(row, "classification")
                    status = _text(row, "adoptionStatusCd")
                    seen_category_fields = seen_category_fields or species is not None
                    seen_status_fields = seen_status_fields or status is not None
                    if gu in DISTRICTS:
                        district_counts[DISTRICTS[gu]] += 1
                    else:
                        unknown["구"] += 1
                    if species in SPECIES:
                        species_counts[SPECIES[species]] += 1
                    else:
                        unknown["동물종류"] += 1
                    if status in STATUSES:
                        status_counts[STATUSES[status]] += 1
                    else:
                        unknown["분양상태"] += 1

                if total_rows_seen >= total_count:
                    break
                if not rows or page >= max(1, math.ceil(total_count / PAGE_SIZE)):
                    raise ProviderError(FailureType.MALFORMED_RESPONSE, "INCOMPLETE_PAGES", "전체 건수에 도달하기 전에 페이지 응답이 끝났습니다.")
                page += 1
    except httpx.TimeoutException as error:
        raise ProviderError(FailureType.TIMEOUT, "TIMEOUT", "유기동물 API 응답 시간이 초과되었습니다.") from error
    except httpx.ConnectError as error:
        raise ProviderError(FailureType.OFFLINE, "OFFLINE", "유기동물 API에 연결할 수 없습니다.") from error
    except httpx.RequestError as error:
        raise ProviderError(FailureType.OFFLINE, "NETWORK_ERROR", "유기동물 API 네트워크 요청이 실패했습니다.") from error

    if total_count != total_rows_seen:
        raise ProviderError(FailureType.MALFORMED_RESPONSE, "COUNT_MISMATCH", "페이지별 공고 합계와 totalCount가 일치하지 않습니다.")
    if published_today_count and (not seen_category_fields or not seen_status_fields):
        raise ProviderError(FailureType.MALFORMED_RESPONSE, "MISSING_AGGREGATE_FIELDS", "응답에서 동물 종류 또는 분양 상태 필드를 확인할 수 없습니다.")

    # Keep output dimensions exhaustive without persisting any record-level fields.
    if unknown["구"]:
        district_counts["미분류"] = unknown["구"]
    if unknown["동물종류"]:
        species_counts["기타/미확인"] = unknown["동물종류"]
    if unknown["분양상태"]:
        status_counts["기타/미확인"] = unknown["분양상태"]

    return DailyRecord(
        basis_date=snapshot_date,
        basis_timezone="Asia/Seoul",
        value=published_today_count,
        source_value=published_today_count,
        district_counts=district_counts,
        species_counts=species_counts,
        status_counts=status_counts,
        weekly_registration_counts=weekly_registration_counts,
        weekly_district_counts=weekly_district_counts,
        weekly_species_counts=weekly_species_counts,
        weekly_status_counts=weekly_status_counts,
        recent_7_day_registration_counts=recent_7_day_registration_counts,
        unit="건",
        source=SOURCE,
        source_timestamp=None,
        fetched_at_kst=datetime.now(KST),
        data_origin="real",
    )
