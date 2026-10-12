import { useState } from "react";
import type { DailyRecord } from "../types/api";

type AnalysisTab = "dates" | "districts" | "species" | "statuses";
const tabs: { id: AnalysisTab; label: string }[] = [
  { id: "dates", label: "날짜별 추이" },
  { id: "districts", label: "구별 현황" },
  { id: "species", label: "동물 종류별" },
  { id: "statuses", label: "분양 상태별" },
];
const dimensions = {
  districts: { label: "구", key: "weekly_district_counts", description: "지난주 월요일부터 일요일까지 등록된 공고를 구별로 집계합니다." },
  species: { label: "동물 종류", key: "weekly_species_counts", description: "지난주 월요일부터 일요일까지 등록된 공고를 동물 종류별로 집계합니다." },
  statuses: { label: "분양 상태", key: "weekly_status_counts", description: "지난주 월요일부터 일요일까지 등록된 공고를 현재 분양 상태별로 집계합니다." },
} as const;

export function AnalysisPage({ records }: { records: DailyRecord[] }) {
  const [tab, setTab] = useState<AnalysisTab>("dates");
  const sorted = [...records].filter((record) => record.data_origin === "real").sort((a, b) => a.basis_date.localeCompare(b.basis_date));
  const latest = sorted.at(-1) ?? null;
  const weekDates = latest?.weekly_registration_counts ? Object.keys(latest.weekly_registration_counts).sort() : [];
  const weekRange = weekDates.length ? `${weekDates[0]} ~ ${weekDates[weekDates.length - 1]} · 월–일` : "지난주 수집 대기";
  const description = tab === "dates" ? "지난주 월요일부터 일요일까지, 게시글 등록일별 공고 수입니다." : dimensions[tab].description;
  return <div className="page-stack">
    <header className="page-header"><p className="eyebrow">T04 · ANALYSIS</p><h1>데이터 분석</h1><p>대전에서 날짜별로 새로 등록된 유기동물 공고 수와 구성을 분석합니다.</p></header>
    <div className="analysis-toolbar"><div className="tab-switch" role="tablist" aria-label="분석 기준">{tabs.map((item) => <button role="tab" aria-selected={tab === item.id} className={tab === item.id ? "selected" : ""} key={item.id} onClick={() => setTab(item.id)}>{item.label}</button>)}</div><span className="select-like">{weekRange}</span></div>
    <section className="surface-card analysis-chart"><div className="section-heading"><div><h2>{tab === "dates" ? "지난주 일별 신규 등록 공고 수" : `지난주 ${dimensions[tab].label} 공고 현황`}</h2><p>{description}</p></div><span className="select-like">단위: 건</span></div>{tab === "dates" ? <SnapshotTable record={latest}/> : <DimensionTable record={latest} dimension={tab} weekRange={weekRange}/>}</section>
    <p className="privacy-note">기준일은 게시글 등록일입니다. 각 날짜의 수치는 그 날짜에 등록된 공고 건수이며, 구조일이나 공고일 기준과 다릅니다. 상세 메모, 등록번호, 사진 주소는 저장하거나 표시하지 않습니다.</p>
  </div>;
}

function SnapshotTable({ record }: { record: DailyRecord | null }) {
  const days = record?.weekly_registration_counts ? Object.entries(record.weekly_registration_counts).sort(([a], [b]) => a.localeCompare(b)) : [];
  if (!record || days.length === 0) return <EmptyAnalysis/>;
  return <><p className="category-analysis-meta">조회 기준일 {record.basis_date} · 조회 시각 {record.fetched_at_kst} · 지난주 실제 API 등록일 집계</p><div className="table-wrap"><table><thead><tr><th>등록일 (KST)</th><th>신규 등록 공고 수</th><th>전날 대비</th></tr></thead><tbody>{days.map(([day, count], index) => {
    const previous = index > 0 ? days[index - 1][1] : null;
    const delta = previous === null ? null : count - previous;
    return <tr key={day}><td>{day}</td><td>{count.toLocaleString("ko-KR")}건</td><td>{delta === null ? "비교 시작" : `${delta > 0 ? "+" : ""}${delta.toLocaleString("ko-KR")}건`}</td></tr>;
  })}</tbody></table></div></>;
}

function EmptyAnalysis() {
  return <div className="analysis-empty"><strong>지난주 실제 공고 집계가 아직 없습니다</strong><p>오늘 실제 데이터를 다시 수집하면 지난주 월요일부터 일요일까지의 등록 현황이 표시됩니다.</p></div>;
}

function DimensionTable({ record, dimension, weekRange }: { record: DailyRecord | null; dimension: Exclude<AnalysisTab, "dates">; weekRange: string }) {
  if (!record) return <EmptyAnalysis/>;
  const definition = dimensions[dimension];
  const counts = record[definition.key] ?? {};
  const rows = Object.entries(counts).filter(([, count]) => count > 0).sort((a, b) => b[1] - a[1]);
  const weekTotal = Object.values(record.weekly_registration_counts ?? {}).reduce((sum, count) => sum + count, 0);
  if (rows.length === 0) return <p className="empty-state compact">{weekTotal > 0 ? "지난주 등록 공고는 있지만 주간 분류값이 아직 저장되지 않았습니다. 백엔드를 다시 시작한 뒤 오늘 실제 수집을 실행해 주세요." : "지난주 등록 공고가 없어 표시할 분류 자료가 없습니다."}</p>;
  return <><p className="category-analysis-meta">{weekRange} · 지난주 등록 {weekTotal.toLocaleString("ko-KR")}건 · 실제 데이터</p><div className="table-wrap"><table><thead><tr><th>{definition.label}</th><th>지난주 등록 공고 수</th><th>지난주 등록분 대비</th></tr></thead><tbody>{rows.map(([name, count]) => <tr key={name}><td>{name}</td><td>{count.toLocaleString("ko-KR")}건</td><td>{weekTotal ? `${(count / weekTotal * 100).toFixed(1)}%` : "—"}</td></tr>)}</tbody></table></div><p className="card-footnote">출처: {record.source} · 조회 시각: {record.fetched_at_kst} · 분류 기준: {definition.label}</p></>;
}
