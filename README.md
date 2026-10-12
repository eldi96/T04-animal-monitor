# T04 대전 유기동물 공고 모니터링

대전광역시 유기동물공고 현황 API를 조회해 `regDtTm`(게시글 등록일)이 해당 KST 날짜인 공고만 날짜별로 집계하고, 날짜 간 변화를 보여주는 프로젝트입니다. API `totalCount`는 조회 목록 전체 건수이며 오늘 등록된 공고 건수와 구분합니다. 구조일(`rescueDate`)이나 공고일(`noticeDate`) 기준으로 해석하지 않습니다.

## 구조

- `backend/app`: FastAPI, 대전 API 수집, 실패·복구 상태 처리, SQLite 저장소
- `assets/studio-task-assets/t04-real-information-board`: T04 공개 계약·manifest·정상/실패/복구 fixture
- `backend/app/services/replay.py`: 공개 합성 fixture 재생기. 실제 조회 상태와 일별 SQLite를 변경하지 않음
- `frontend/src/pages`: 홈, 데이터 분석, 데이터 신뢰성, 실패 테스트, 복구
- `data`: 유기동물 스냅샷 DB (`t04-animals.sqlite`)
- `docs`: 데이터 정의 및 운영 안내

## 실행

백엔드는 `cd backend`, 가상환경에서 `pip install -r requirements.txt`, 이어서 `uvicorn app.main:app --reload`로 실행합니다. 프런트엔드는 `cd frontend`, `pnpm install`, `pnpm dev`로 실행합니다. 백엔드는 `http://127.0.0.1:8000`, 프런트엔드는 `http://127.0.0.1:5173`에서 엽니다.

## 설정

저장소 루트의 무시 대상 `.env`에 해당 API 활용 신청에 연결된 공공데이터포털 인증키를 `DATA_GO_KR_SERVICE_KEY`로 설정합니다. 키는 백엔드에서만 사용하며 프런트엔드 변수로 복사하거나 Git에 추가하지 않습니다. 기본 DB 경로는 `data/t04-animals.sqlite`이고, 필요하면 `T04_DB_PATH`로 바꿀 수 있습니다.

## 지표와 데이터 보호

`value`와 `source_value`는 API 전체 페이지를 검증한 후 `regDtTm`이 기준일과 일치하는 공고 수로 저장합니다. 페이지 전체 행 수는 별도로 `totalCount`와 대조하며 `totalCount`를 오늘 공고 수로 사용하지 않습니다. 구·동물 종류·분양 상태별 집계도 오늘 등록된 공고에 한정됩니다. `weekly_registration_counts`는 오늘 조회한 API 목록에서 지난주 월요일부터 일요일까지, `recent_7_day_registration_counts`는 오늘 포함 최근 7일 등록일별로 집계한 값입니다. 두 값 모두 과거 날짜의 스냅샷으로 간주하지 않습니다. 게시물 번호, 동물등록번호, 메모, 발견장소, 사진 경로는 저장하거나 화면에 표시하지 않습니다. 이전 수집 대비 값은 날짜별 등록 공고 수의 차이입니다.

## 공개 실패 fixture 재생

`실패 테스트` 화면은 `assets/studio-task-assets/t04-real-information-board/asset-manifest.json`에 등록된 파일 17개의 크기와 SHA-256을 확인한 뒤에만 재생 버튼을 활성화합니다. package ID는 `aleph-t04-real-information-board-public-contract-v2`입니다. 공개 계약은 `public-contract.json`이며 fixture 계약 버전은 1.1.0입니다.

실패 유형을 선택하면 합성 상태만 초기화하고 `T04-NORMAL-D1-A → T04-NORMAL-D1-B → 선택한 실패 fixture` 순서로 재생합니다. 같은 합성 날짜의 두 정상 값은 한 행으로 갱신되고 마지막 값 105 pt를 유지합니다. 실패 상태는 `stale`과 `timeout`, `auth`, `rate_limit`, `offline`, `schema_error`로 구분하며 각 유형별 다음 행동을 안내합니다. 실패 후 다시 시도는 실제 API를 호출하지 않고 공개 `T04-RECOVER-D2`를 재생해 다음 날짜 행 하나와 120 pt를 추가하고 `fresh / none`으로 복구합니다.

정상 D1-A → D1-B와 다음 날짜 D2 흐름도 화면에서 따로 재생할 수 있습니다. 이 합성 날짜와 값은 실제 공개 원천의 두 날짜 기록을 대신하지 않으며, 합성 reset은 실제 SQLite의 일별 기록과 운영 상태를 지우지 않습니다.

API 경로는 `GET /api/replay/package`, `GET /api/replay/state`, `POST /api/replay/reset`, `POST /api/replay/fixtures/{fixture_id}`, `POST /api/replay/recover`입니다. 실제 수집 실패와 복구는 별도 운영 경로에서 실제 응답을 기준으로 처리합니다.
