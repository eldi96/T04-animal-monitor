import type { LatestView } from "../types/api";
import { Icon } from "../components/Icon";
import { ValueComparison } from "../components/ValueComparison";

export function ReliabilityPage({ view, apiAvailable }: { view: LatestView | null; apiAvailable: boolean }) {
  const failed = view?.status === "FAILED";
  const normal = view?.status === "NORMAL" || view?.status === "RECOVERED";
  const comparisonRecord = failed ? view?.last_known_good : view?.current_latest;
  const checks = [
    { label: "수집 상태 API", detail: apiAvailable ? (normal ? "내부 API 및 대전 원천 데이터 정상" : failed ? "내부 API 연결 · 원천 조회 실패" : "내부 API 연결 · 원천 수집 전") : "내부 상태 API 연결 대기", ok: apiAvailable && normal },
    { label: "데이터 검증", detail: normal ? "최근 실데이터 확인됨" : "실데이터 검증 전", ok: normal },
    { label: "데이터 저장", detail: view?.last_known_good ? "마지막 정상값 보존 중" : "저장된 실데이터 없음", ok: Boolean(view?.last_known_good) },
    { label: "화면 표시", detail: failed ? "최신값 미확인 상태 표시 중" : "데이터 출처와 시각 분리 표시", ok: true },
  ];
  return <div className="page-stack">
    <header className="page-header"><p className="eyebrow">T04 · RELIABILITY</p><h1>데이터 신뢰성</h1><p>대전 유기동물 공고의 수집·저장·표시 결과를 비교합니다.</p></header>
    <section className={`reliability-banner ${failed ? "error" : normal ? "healthy" : "pending"}`}><div className="banner-icon"><Icon name={failed ? "alert" : normal ? "check" : "clock"} /></div><div><h2>{failed ? "현재 최신 데이터 확인 불가" : normal ? "데이터 정상 수집 중" : "실제 데이터 수집 전"}</h2><p>{failed ? "마지막 정상값은 유지하고 있습니다. 최신 데이터로 간주하지 않습니다." : normal ? "현재 확인된 대전 유기동물 공고 스냅샷과 조회 시각을 확인할 수 있습니다." : "대전광역시 유기동물 API의 실제 응답을 아직 저장하지 않았습니다."}</p></div></section>
    <div className="reliability-grid"><section className="surface-card"><div className="section-heading"><div><h2>데이터 수집 상태</h2><p>처리 단계별 확인 결과</p></div></div><div className="check-list">{checks.map((check) => <div className="check-row" key={check.label}><span className={`check-icon ${check.ok ? "ok" : "idle"}`}><Icon name={check.ok ? "check" : "clock"} /></span><div><strong>{check.label}</strong><small>{check.detail}</small></div><span className={`check-result ${check.ok ? "ok" : "idle"}`}>{check.ok ? "확인" : "대기"}</span></div>)}</div></section>
      <section className="surface-card last-observed"><div className="section-heading"><div><h2>{failed ? "마지막 정상 수집" : "현재 데이터 값 검증"}</h2><p>{failed ? "현재 최신값과 분리된 마지막 정상 기록" : "원천·저장·화면 값을 나란히 비교"}</p></div><Icon name="clock" className="heading-icon" /></div>{comparisonRecord?.data_origin === "real" ? <ValueComparison record={comparisonRecord} stale={failed} /> : <div className="empty-inline"><span>비교할 실제 저장 데이터가 없습니다.</span></div>}</section></div>
    {failed && view?.failure && <section className="surface-card active-failure"><span className="failure-label">{view.failure.data_origin === "synthetic" ? "현재 synthetic 실패 재생" : "실제 API 오류 관측"}</span><h2>{view.failure.type}{view.failure.http_status ? ` · HTTP ${view.failure.http_status}` : ""}</h2><p>{view.failure.message}</p><small>발생 시각 · {view.failure.occurred_at}</small></section>}
    <p className="privacy-note">실패 시나리오의 synthetic 상태는 실제 원천 데이터와 분리되어 표시됩니다.</p>
  </div>;
}
