import type { DailyRecord } from "../types/api";

export function ValueComparison({ record, stale = false }: { record: DailyRecord; stale?: boolean }) {
  const displayValue = `${record.value.toLocaleString("ko-KR")} ${record.unit}`;
  const sourceValue = record.source_value;
  const isConsistent = sourceValue !== null && sourceValue !== undefined && sourceValue === record.value;
  const status = sourceValue === null || sourceValue === undefined
    ? "원천 원자료 비교 대기"
    : isConsistent
      ? "원천·저장값 일치"
      : "원천·저장값 불일치 확인 필요";

  return <div className="value-comparison">
    <p className={`comparison-context ${stale ? "stale" : ""}`}>
      {stale ? "마지막 정상 기록 · 현재 최신값 아님" : "실제 기록의 값 일치 확인"}
    </p>
    <dl>
      <div><dt>기준일</dt><dd>{record.basis_date}</dd></div>
      <div><dt>원천 데이터</dt><dd>{sourceValue ?? "원천 원자료 미수신"}{sourceValue !== null && sourceValue !== undefined ? ` ${record.unit}` : ""}</dd></div>
      <div><dt>저장값</dt><dd>{displayValue}</dd></div>
      <div><dt>화면 표시</dt><dd>{displayValue}</dd></div>
      <div><dt>상태</dt><dd className={isConsistent ? "comparison-good" : "comparison-pending"}>{status}</dd></div>
      <div><dt>출처</dt><dd>{record.source}</dd></div>
      <div><dt>원천 시각</dt><dd>{record.source_timestamp ?? "미제공"}</dd></div>
      <div><dt>조회 시각</dt><dd>{record.fetched_at_kst}</dd></div>
    </dl>
  </div>;
}
