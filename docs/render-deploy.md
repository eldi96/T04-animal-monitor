# Render + PostgreSQL 연결 준비

현재는 코드와 설정만 준비합니다. DB 생성·연결·배포는 시연 직전에 진행합니다.

## 지금 사용

- DATABASE_URL을 비워두면 기존 SQLite를 사용합니다. API 키는 서버 .env에 둡니다.
- 수집 버튼을 누를 때만 실제 API를 조회하고 저장합니다. 자동 수집은 기본 OFF입니다.
- 원래 작업 폴더의 기존 DB는 수정하지 않습니다. 이 별도 복제 폴더에서 기존 DB를 읽으려면 T04_DB_PATH에 원본 DB의 절대 경로를 지정합니다.

## 시연 직전

1. 코드를 GitHub에 반영합니다.
2. 그 시점의 무료 정책을 확인하고 PostgreSQL을 생성합니다. 현재 Render 무료 DB는 생성 30일 후 만료되므로 지금 만들지 않습니다.
3. 같은 계정·리전에 Web Service를 생성합니다. render.yaml은 무료 웹 서비스만 정의하며 DB나 유료 디스크를 자동 생성하지 않습니다.
4. DATABASE_URL에 PostgreSQL의 Internal URL, DATA_GO_KR_SERVICE_KEY에 인증키를 설정합니다. 둘 다 서버 환경변수로만 사용합니다.
5. 배포 후 요청 시 t04.daily_records와 t04.monitoring_state가 초기화됩니다. DB 계정에 스키마 생성 권한이 필요합니다.
6. 버튼으로 수집하고 다른 PC에서도 같은 날짜 기록이 조회되는지 확인합니다.
7. 웹 서버를 재시작해도 DB 기록이 유지되는지 확인합니다. 실제 연결 검증은 아직 수행하지 않았습니다.

현재 render.yaml은 T04_REQUIRE_POSTGRES=false로 기존 SQLite 방식을 허용합니다. PostgreSQL 없이도 무료 서버에서 실행할 수 있지만 서버 절전·재시작·재배포 시 새로 쌓은 기록은 사라집니다. 나중에 DB를 연결할 때 DATABASE_URL을 추가하고 T04_REQUIRE_POSTGRES=true로 바꾸세요. 그러면 URL 누락 시 임시 SQLite에 저장하지 않고 오류를 반환합니다. DB 연결 실패 시에는 설정에 관계없이 SQLite로 우회하지 않습니다.

## 이전 기록

로컬 SQLite 기록은 PostgreSQL로 자동 이전되지 않습니다. 기존 기록까지 시연하려면 연결 전에 원본을 백업하고 별도로 이전해야 합니다. 현재 변경에 이전 도구는 포함하지 않습니다.

## 점검

- /healthz는 앱 실행 여부만 확인합니다. DB·원천 API는 실제 조회와 수집으로 검사합니다.
- 수집·합성 테스트 API에는 현재 로그인 제한이 없습니다.
- T04_ENABLE_SCHEDULER=true로 기존 23:55 KST 예약 수집을 켤 수 있지만 무료 서버 절전 중 실행은 보장되지 않습니다.
- 테스트는 로컬 SQLite와 DB 연결을 대체한 단위 테스트입니다. 실제 PostgreSQL 연결 및 컨테이너 빌드 검증은 시연 준비 때 추가합니다.

공식 문서: https://render.com/docs/free 및 https://render.com/docs/postgresql-creating-connecting
