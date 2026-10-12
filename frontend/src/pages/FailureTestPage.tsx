import type { ReplayErrorCode, ReplayFixtureId, ReplayPackageStatus, ReplayState } from "../types/api";
import { Icon } from "../components/Icon";

const failures: { fixture: ReplayFixtureId; error: Exclude<ReplayErrorCode, "none">; criterion: string; label: string; transport: string }[] = [
  { fixture: "T04-TIMEOUT", error: "timeout", criterion: "T04-C12", label: "응답이 너무 늦어요", transport: "잠시 기다린 뒤 다시 확인" },
  { fixture: "T04-AUTH-401", error: "auth", criterion: "T04-C13", label: "자료 제공처가 접근을 거부해요", transport: "접근 권한을 확인해야 해요" },
  { fixture: "T04-RATE-429", error: "rate_limit", criterion: "T04-C14", label: "요청이 많아 잠시 제한됐어요", transport: "잠시 후 다시 확인" },
  { fixture: "T04-OFFLINE", error: "offline", criterion: "T04-C15", label: "인터넷 연결이 끊겼어요", transport: "네트워크 연결 확인" },
  { fixture: "T04-SCHEMA-BREAK", error: "schema_error", criterion: "T04-C16", label: "자료 형식이 달라졌어요", transport: "자료 제공처 확인 필요" },
];

const errorLabels: Record<ReplayErrorCode, string> = {
  none: "오류 없음",
  timeout: "응답 지연",
  auth: "접근 거부",
  rate_limit: "요청 제한",
  offline: "오프라인",
  schema_error: "자료 형식 변경",
};

function displayTime(value: string | null | undefined) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", dateStyle: "medium", timeStyle: "medium" }).format(new Date(value));
}

export function FailureTestPage({
  replay,
  replayPackage,
  onReplay,
  onNormalSequence,
  onD2Sequence,
  onRecover,
  onReset,
  busy,
  notice,
}: {
  replay: ReplayState | null;
  replayPackage: ReplayPackageStatus | null;
  onReplay: (fixture: ReplayFixtureId) => void;
  onNormalSequence: () => void;
  onD2Sequence: () => void;
  onRecover: () => void;
  onReset: () => void;
  busy: boolean;
  notice: string;
}) {
  const rows = replay?.daily_readings ?? [];
  const status = replay?.status;
  const failed = status?.freshness === "stale";
  const lastGood = rows.length ? rows[rows.length - 1] : null;
  const retryAfter = replay?.last_run?.retry_after_seconds;
  const packageReady = replayPackage?.integrity_ok === true;
  const nextAction = status?.error_code === "timeout"
    ? "잠시 기다린 뒤 다시 확인해 주세요."
    : status?.error_code === "auth"
      ? "자료 제공처의 연결 상태를 확인한 뒤 다시 시도해 주세요."
      : status?.error_code === "rate_limit"
        ? "요청 제한이 풀릴 때까지 기다린 뒤 다시 시도해 주세요."
        : status?.error_code === "offline"
          ? "인터넷 연결을 확인한 뒤 다시 시도해 주세요."
          : status?.error_code === "schema_error"
            ? "자료 제공처가 보내는 내용이 달라졌어요. 확인한 뒤 다시 시도해 주세요."
            : replay?.next_action_ko;

  return <div className="page-stack">
    <header className="page-header"><p className="eyebrow">데이터 문제 상황 연습</p><h1>문제 상황 확인</h1><p>자료를 가져오지 못했을 때 화면이 어떻게 안내하는지 확인해 보세요. 실제 데이터에는 영향을 주지 않습니다.</p></header>

    <section className="surface-card replay-package-card">
      <div className="section-heading"><div><h2>시험 준비 상태</h2><p>시험에 필요한 예시 자료가 준비됐는지 확인합니다.</p></div><span className={`status-pill ${packageReady ? "success" : "danger"}`}><i />{packageReady ? "시험 준비 완료" : "시험 자료 확인 필요"}</span></div>
      {replayPackage && !packageReady && <p className="replay-warning">시험 자료를 확인하지 못해 아래 버튼을 사용할 수 없습니다. 자료 파일과 서버 연결을 확인해 주세요.</p>}
      {replayPackage && <details className="replay-technical-details"><summary>검증 정보 보기</summary><dl className="replay-package-meta"><div><dt>패키지 번호</dt><dd>{replayPackage.package_id}</dd></div><div><dt>파일 확인</dt><dd>{replayPackage.checked_file_count}개 · SHA-256</dd></div></dl></details>}
    </section>

    <section className="surface-card replay-controls-card">
      <div className="section-heading"><div><h2>어떻게 확인하나요?</h2><p>아래에서 한 가지 문제를 고르면 예시 상황이 바로 나타납니다.</p></div><span className="synthetic-tag">실제 데이터 변경 없음</span></div>
      <ol className="replay-howto">
        <li><strong>문제를 하나 골라요</strong><span>예: 응답이 늦거나 인터넷 연결이 끊긴 상황을 눌러요.</span></li>
        <li><strong>화면 안내를 살펴봐요</strong><span>새 자료를 못 가져온 상태와 마지막으로 확인한 값을 보여 줘요.</span></li>
        <li><strong>다시 시도해 봐요</strong><span>아래 버튼을 눌러 자료가 정상적으로 들어오는 모습을 확인해요.</span></li>
      </ol>
      <div className="replay-sequence-actions">
        <button className="secondary-action" disabled={busy || !packageReady} onClick={onNormalSequence}>문제없이 자료를 가져온 경우</button>
        <button className="secondary-action" disabled={busy || !packageReady} onClick={onD2Sequence}>하루 뒤 자료와 비교한 경우</button>
        <button className="secondary-action subtle-action" disabled={busy} onClick={onReset}>처음 상태로 돌아가기</button>
      </div>
      <h3 className="replay-subheading">어떤 문제가 생겼는지 골라 보세요</h3>
      <div className="failure-options">{failures.map((item) => <button key={item.fixture} className={`failure-option ${replay?.last_run?.fixture_id === item.fixture ? "chosen" : ""}`} disabled={busy || !packageReady} onClick={() => onReplay(item.fixture)}><small>{item.criterion}</small><strong>{item.label}</strong><small>{item.transport}</small></button>)}</div>
      <div className="notice-line" role="status">{busy && <span className="mini-spinner" />}{notice}</div>
    </section>

    <section className="surface-card replay-state-card">
      <div className="section-heading"><div><h2>시험 결과</h2><p>예시 자료로 확인한 결과예요. 실제 자료나 저장 기록은 바뀌지 않습니다.</p></div><span className="synthetic-tag">연습 결과</span></div>
      {!status ? <div className="test-idle"><Icon name="flask" /><div><strong>위에서 문제 상황을 하나 골라 보세요.</strong><p>예시 자료를 준비한 뒤 화면에 결과를 보여 드립니다.</p></div></div> : <>
        <div className={`test-error-banner ${failed ? "failed" : "replay-fresh"}`}><div className="banner-icon"><Icon name={failed ? "alert" : "check"} /></div><div><strong>{failed ? "지금은 새 자료를 확인할 수 없어요." : "자료를 정상적으로 확인했어요."}</strong><p>{failed ? "새 자료를 확인할 수 없으므로 아래 값은 마지막으로 확인한 참고값입니다." : "예시 자료가 정상적으로 들어왔어요. 아래 날짜별 기록을 확인해 보세요."}</p></div><span className="synthetic-tag">{errorLabels[status.error_code]}</span></div>
        {failed && <div className="replay-next-action"><strong>어떻게 하면 되나요?</strong><p>{nextAction}</p>{retryAfter !== null && retryAfter !== undefined && <small>{retryAfter}초 정도 기다린 뒤 다시 시도해 주세요.</small>}</div>}
      </>}
      <div className="replay-stats-grid">
        <div><small>시험용 점수 · 실제 공고 수 아님</small><strong>{lastGood ? `${lastGood.normalized_value.toLocaleString("ko-KR")} ${lastGood.unit}` : "아직 없음"}</strong><span>{lastGood ? `${lastGood.record_date} · ${failed ? "이전 시험값, 최신값 아님" : "예시 시험값"}` : "문제없이 자료를 가져오면 표시돼요"}</span></div>
        <div><small>날짜별 기록</small><strong>{rows.length}건</strong><span>예시 자료로 저장한 날짜 수</span></div>
        <div><small>시험용 점수 변화</small><strong>{replay?.last_delta === null || replay?.last_delta === undefined ? "비교할 자료 없음" : `${replay.last_comparison.direction === "increase" ? "+" : replay.last_comparison.direction === "decrease" ? "−" : ""}${replay.last_delta} ${replay.last_comparison.unit}`}</strong><span>실제 공고 건수의 변화가 아닌 예시값</span></div>
        <div><small>확인한 상황</small><strong>{replay?.last_run?.fixture_id ? failures.find((item) => item.fixture === replay.last_run?.fixture_id)?.label ?? "자료 복구" : "아직 없음"}</strong><span>{displayTime(replay?.last_run?.virtual_now)}</span></div>
      </div>
      {failed && <button className="primary-action replay-retry" disabled={busy || !packageReady} onClick={onRecover}><Icon name="rotate" />{busy ? "다시 확인하는 중" : "다시 시도해 정상으로 돌아오는지 확인"}</button>}
      {rows.length > 0 && <div className="replay-record-list"><h3 className="replay-subheading">날짜별 시험용 점수</h3>{rows.map((row) => <div className="replay-record-row" key={row.record_id}><span>{row.record_date}</span><strong>{row.normalized_value} {row.unit}</strong><small>실제 공고 수 아님</small></div>)}</div>}
      <p className="privacy-note">이 숫자와 날짜는 사용법을 보여 주기 위한 예시입니다. 실제 유기동물 공고 수가 아닙니다.</p>
    </section>
  </div>;
}
