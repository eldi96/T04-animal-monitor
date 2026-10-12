import { useState } from "react";
import type { LatestView, DailyRecord } from "../types/api";
import type { IconName } from "../components/Icon";
import { Icon } from "../components/Icon";
import { ValueComparison } from "../components/ValueComparison";

type Destination = "analysis" | "reliability" | "test" | "recovery";

function MetricCard({ icon, label, value, unit, detail, primary = false, secondary, breakdown, compactMeta = false }: {
  icon: IconName; label: string; value: string; unit?: string; detail: string; primary?: boolean; secondary?: string; breakdown?: { label: string; value: string }[]; compactMeta?: boolean;
}) {
  return <article className={`metric-card ${primary ? "metric-card-primary" : ""} ${compactMeta ? "metric-card-compact-meta" : ""}`}>
    <div className="metric-icon"><Icon name={icon} /></div>
    <div className="metric-copy"><p>{label}</p><strong className={value === "확인 불가" ? "metric-value-unavailable" : ""}>{value}{unit && <small> {unit}</small>}</strong>
      <span>{detail}</span>{secondary && <span className="metric-secondary">{secondary}</span>}{breakdown && <div className="metric-breakdown">{breakdown.map((day) => <div key={day.label}><span>{day.label}</span><strong>{day.value}</strong></div>)}</div>}
    </div>
  </article>;
}

function SevenDayChart({ record, failed }: { record: DailyRecord | null; failed: boolean }) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const counts = record?.recent_7_day_registration_counts;
  if (failed || !record || !counts) return <div className="chart-empty"><div className="chart-grid"><span /><span /><span /><span /></div><div className="chart-empty-message"><span className="empty-chart-icon"><Icon name="chart" /></span><strong>{failed ? "최근 7일 공고 현황 확인 불가" : "오늘 실제 수집 후 표시됩니다"}</strong><small>{failed ? "마지막 정상 그래프를 현재 데이터처럼 표시하지 않습니다." : "현재 API 응답을 정상 수집하면 최근 7일 등록일별 공고 수를 표시합니다."}</small></div></div>;
  const days = Object.entries(counts).sort(([a], [b]) => a.localeCompare(b)).map(([date, count]) => ({ date, count }));
  const values = days.map(({ count }) => count);
  const width = 800, height = 250, left = 48, right = 18, top = 18, bottom = 34;
  const plotHeight = height - top - bottom;
  const step = Math.max(1, Math.ceil(Math.max(...values, 1) / 4));
  const yMax = step * 4;
  const x = (index: number) => left + index * ((width - left - right) / 6);
  const y = (value: number) => top + (1 - value / yMax) * plotHeight;
  let path = "", drawing = false;
  days.forEach(({ count }, index) => { path += `${drawing ? " L" : "M"}${x(index)} ${y(count)}`; drawing = true; });
  return <div className="trend-chart-wrap"><svg className="trend-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="현재 API 응답 기준 최근 7일 게시글 등록일별 신규 공고 수">
    {Array.from({ length: 5 }, (_, index) => { const value = yMax - index * step, lineY = y(value); return <g key={value}><line x1={left} x2={width - right} y1={lineY} y2={lineY} className="trend-grid-line"/><text x={left - 10} y={lineY + 4} textAnchor="end" className="trend-axis-label">{value}</text></g>; })}
    <path d={path} className="trend-line"/>
    {days.map(({ date, count }, index) => <g key={date}><circle cx={x(index)} cy={y(count)} r={activeIndex === index ? "7" : "4.5"} className="trend-point" tabIndex={0} role="img" aria-label={`${date}, ${count}건`} aria-describedby={activeIndex === index ? "trend-chart-tooltip" : undefined} onMouseEnter={() => setActiveIndex(index)} onMouseLeave={() => setActiveIndex(null)} onFocus={() => setActiveIndex(index)} onBlur={() => setActiveIndex(null)} onClick={() => setActiveIndex(index)}><title>{`${date}: ${count}건`}</title></circle><text x={x(index)} y={height - 8} textAnchor="middle" className="trend-axis-label trend-date-label">{date.slice(5).replace("-", "/")}</text></g>)}
  </svg>{activeIndex !== null && days[activeIndex] && <div id="trend-chart-tooltip" role="tooltip" className="trend-tooltip" style={{ left: `${Math.min(91, Math.max(9, x(activeIndex) / width * 100))}%`, top: `${Math.max(13, y(days[activeIndex].count) / height * 100)}%` }}><strong>{days[activeIndex].date}</strong><span>{days[activeIndex].count.toLocaleString("ko-KR")}건</span></div>}<div className="trend-chart-meta"><div className="trend-meta-source"><i aria-hidden="true"/><span>실제 API 응답 · 게시글 등록일 기준</span></div><div className="trend-meta-details"><span><small>기준일</small><strong>{record.basis_date.replaceAll("-", ".")}</strong></span><span><small>조회 시각</small><strong>{compactKstTimestamp(record.fetched_at_kst)}</strong></span></div></div></div>;
}

function SummaryList({ title, counts, failed, emptyText }: { title: string; counts: Record<string, number> | null | undefined; failed: boolean; emptyText: string }) {
  if (failed) return <div className="category-empty unavailable"><strong>현재 최신 현황 확인 불가</strong><span>마지막 정상 분포를 현재값으로 표시하지 않습니다.</span></div>;
  const rows = Object.entries(counts ?? {}).filter(([, count]) => count > 0).sort((a, b) => b[1] - a[1]);
  if (rows.length === 0) return <div className="category-empty"><strong>{emptyText}</strong><span>정상 스냅샷 저장 후 표시합니다.</span></div>;
  const maximum = Math.max(...rows.map(([, count]) => count));
  return <div className="district-list" aria-label={title}>{rows.map(([name, count]) => <div key={name}><span>{name}</span><i className="distribution-track"><b style={{ width: `${Math.max(3, count / maximum * 100)}%` }}/></i><strong>{count.toLocaleString("ko-KR")}건</strong></div>)}</div>;
}

function kstTimestamp(value?: string | null) {
  return value ? new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—";
}

function compactKstTimestamp(value: string) {
  return new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", month: "numeric", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(value));
}

function todayInKst() {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? "";
  return `${part("year")}-${part("month")}-${part("day")}`;
}

export function HomePage({ view, records, onNavigate }: { view: LatestView | null; records: DailyRecord[]; onNavigate: (page: Destination) => void }) {
  const failed = view?.status === "FAILED";
  const byDate = new Map(records.filter((record) => record.data_origin === "real").map((record) => [record.basis_date, record]));
  if (view?.last_known_good?.data_origin === "real") byDate.set(view.last_known_good.basis_date, view.last_known_good);
  const history = [...byDate.values()].sort((a, b) => a.basis_date.localeCompare(b.basis_date));
  const latestHistory = history.at(-1) ?? null;
  const latestAvailable = !failed && view?.current_latest_available && view.current_latest?.data_origin === "real" ? view.current_latest : null;
  const todayRecord = history.find((record) => record.basis_date === todayInKst()) ?? null;
  // An older successful snapshot is history, not today's current value.
  const current = latestAvailable?.basis_date === todayInKst() ? latestAvailable : todayRecord;
  const yesterdayDate = (() => { const d = new Date(`${todayInKst()}T00:00:00Z`); d.setUTCDate(d.getUTCDate() - 1); return d.toISOString().slice(0, 10); })();
  const yesterdayRecord = history.find((record) => record.basis_date === yesterdayDate) ?? null;
  const recheckedYesterdayCount = current?.recent_7_day_registration_counts?.[yesterdayDate];
  const yesterdayDelta = current && yesterdayRecord ? current.value - yesterdayRecord.value : null;
  const weekStart = (() => { const d = new Date(`${todayInKst()}T00:00:00Z`); d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7) - 7); return d; })();
  const weeklySnapshot = current ?? (!failed ? latestHistory : null);
  const targetWeekDates = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(weekStart); date.setUTCDate(date.getUTCDate() + index);
    return date.toISOString().slice(0, 10);
  });
  const storedWeek = weeklySnapshot?.weekly_registration_counts;
  const storedRecent = weeklySnapshot?.recent_7_day_registration_counts;
  const coversTargetWeek = (counts?: Record<string, number> | null) => Boolean(counts && targetWeekDates.every((date) => date in counts));
  const weeklyCounts = coversTargetWeek(storedWeek) ? storedWeek : coversTargetWeek(storedRecent) ? storedRecent : undefined;
  const chartRecord = failed ? null : current ?? latestHistory;
  const weekDays = targetWeekDates.map((isoDate, index) => {
    const labels = ["월", "화", "수", "목", "금", "토", "일"];
    const count = weeklyCounts?.[isoDate];
    return { label: labels[index], value: count === undefined ? "—" : count.toLocaleString("ko-KR"), count: count ?? 0 };
  });
  const previousWeekTotal = weeklyCounts ? weekDays.reduce((sum, day) => sum + day.count, 0) : null;
  const weekEnd = new Date(weekStart); weekEnd.setUTCDate(weekEnd.getUTCDate() + 6);
  const weekStartLabel = weekStart.toISOString().slice(0, 10).replaceAll("-", ".");
  const weekEndIso = weekEnd.toISOString().slice(0, 10);
  const weekEndLabel = weekEndIso.slice(0, 4) === weekStartLabel.slice(0, 4) ? weekEndIso.slice(5).replace("-", ".") : weekEndIso.replaceAll("-", ".");
  const statusLabel = failed ? "현재 최신 데이터 확인 불가" : current ? "오늘 실제 데이터 수집 완료" : "오늘 실제 데이터 수집 전";
  const latestTimestamp = current?.fetched_at_kst ?? view?.last_known_good?.fetched_at_kst;

  return <div className="page-stack">
    <header className="page-header home-header"><div><p className="eyebrow">DAEJEON · ANIMAL NOTICE MONITOR</p><h1>대전 유기동물 공고 현황</h1><p>대전의 유기동물 공고를 살피고, 필요한 정보를 신뢰할 수 있게 전합니다.</p></div><div className="home-pets" aria-hidden="true"><span>🐕</span><span>🐈</span></div><div className="header-aside"><span>{failed || !current ? "마지막 정상 수집 시각 (KST)" : "오늘 수집 시각 (KST)"}</span><strong>{kstTimestamp(latestTimestamp)}</strong><span className={`status-pill ${failed ? "danger" : current ? "success" : "pending"}`}><i/>{statusLabel}</span></div></header>

    <section className="metric-grid" aria-label="핵심 지표">
      <MetricCard icon="chart" label="이전 수집 대비" value={yesterdayRecord ? yesterdayRecord.value.toLocaleString("ko-KR") : "비교 대기"} unit={yesterdayRecord ? "건" : undefined} detail={yesterdayRecord ? `어제 ${yesterdayDate} 등록 공고 · 실제 저장값` : `어제(${yesterdayDate}) 실제 수집 기록이 필요합니다.`} secondary={failed ? "오늘 최신값 확인 불가 · 어제 기록은 과거값" : yesterdayDelta === null ? "오늘 실제 수집 후 증감 표시" : `오늘 ${yesterdayDelta > 0 ? "+" : ""}${yesterdayDelta.toLocaleString("ko-KR")}건 대비`}/>
      <MetricCard icon="calendar" label="오늘 등록된 공고 수" value={failed ? "확인 불가" : current ? current.value.toLocaleString("ko-KR") : "오늘 수집 전"} unit={!failed && current ? "건" : undefined} detail={current ? `${current.basis_date} KST · 게시글 등록일 기준` : failed ? "새 API 응답을 확인할 수 없습니다." : "오늘 수집 전입니다. 이전 수집 값은 비교 카드에 반영됩니다."} primary secondary={failed && view?.last_known_good ? `마지막 정상값 ${view.last_known_good.value.toLocaleString("ko-KR")}건 · 현재값 아님` : "API 전체 페이지에서 오늘 등록된 공고만 집계"}/>
      <MetricCard icon="chart" label="지난주 등록 공고 수" value={failed ? "확인 불가" : previousWeekTotal === null ? "기록 대기" : previousWeekTotal.toLocaleString("ko-KR")} unit={!failed && previousWeekTotal !== null ? "건" : undefined} detail={`지난주 ${weekStartLabel} — ${weekEndLabel}`} secondary={failed ? "마지막 주간 집계는 현재값처럼 표시하지 않습니다." : weeklyCounts ? `월–일 · API 등록일 기준 · 조회 ${weeklySnapshot?.basis_date}` : "해당 날짜 범위를 포함한 실제 수집 기록이 필요합니다."} breakdown={!failed && weeklyCounts ? weekDays.map(({ label, value }) => ({ label, value })) : undefined} compactMeta/>
    </section>

    <section className="surface-card yesterday-verification" aria-label="어제 등록 공고 확인">
      <div className="section-heading"><div><h2>어제 등록분 확인</h2><p>저장 당시 기록과 오늘 다시 조회한 값을 구분합니다.</p></div><span className="select-like">{yesterdayDate}</span></div>
      <div className="yesterday-verification-grid">
        <article className="yesterday-value saved"><span>어제 실제 수집 기록</span><strong>{yesterdayRecord ? `${yesterdayRecord.value.toLocaleString("ko-KR")}건` : "기록 없음"}</strong><small>{yesterdayRecord ? `조회 ${kstTimestamp(yesterdayRecord.fetched_at_kst)} · 당시 저장값` : "어제 날짜의 실제 수집 기록이 없습니다."}</small></article>
        <article className={`yesterday-value ${failed ? "unavailable" : "rechecked"}`}><span>오늘 조회에서 확인한 어제 등록분</span><strong>{failed ? "확인 불가" : recheckedYesterdayCount !== undefined ? `${recheckedYesterdayCount.toLocaleString("ko-KR")}건` : current ? "응답에 날짜 집계 없음" : "오늘 실제 수집 전"}</strong><small>{failed ? "현재 API 응답을 확인할 수 없습니다." : current ? `regDtTm 기준 · 조회 ${kstTimestamp(current.fetched_at_kst)}` : "오늘 정상 수집 후 확인할 수 있습니다."}</small></article>
      </div>
      <p className="yesterday-verification-note">조회 시점이 다른 두 값은 다를 수 있습니다. 오늘 다시 확인한 값은 어제의 저장 기록을 덮어쓰지 않습니다.</p>
    </section>

    <section className="home-grid">
      <article className="surface-card trend-card"><div className="section-heading"><div><h2>최근 7일 신규 등록 공고 추이</h2><p>게시글 등록일 기준 · 건</p></div><span className="select-like">저장된 실제 집계</span></div><SevenDayChart record={chartRecord} failed={Boolean(failed)}/></article>
      <article className="surface-card region-card"><div className="section-heading"><div><h2>구별 공고 현황</h2><p>대전광역시 API 구 코드 기준</p></div><Icon name="pin" className="heading-icon"/></div><SummaryList title="구별 공고 현황" counts={current?.district_counts} failed={Boolean(failed)} emptyText="구별 집계 대기"/></article>
      <article className="surface-card recent-card"><div className="section-heading"><div><h2>최근 수집 기록</h2><p>동물별 상세정보와 사진은 저장·표시하지 않습니다.</p></div><button className="text-link" onClick={() => onNavigate("analysis")}>분석 보기 <Icon name="arrow"/></button></div>{view?.last_known_good ? <ValueComparison record={view.last_known_good} stale={Boolean(failed)}/> : <div className="empty-inline"><Icon name="database"/><span>아직 저장된 실제 스냅샷이 없습니다.</span></div>}</article>
      <article className="surface-card collection-card"><div className="section-heading"><div><h2>동물 종류별 현황</h2><p>오늘 게시글 등록된 공고의 종류별 분포</p></div></div><SummaryList title="동물 종류별 현황" counts={current?.species_counts} failed={Boolean(failed)} emptyText="종류별 집계 대기"/><dl className="info-list"><div><dt>데이터 출처</dt><dd>대전광역시 유기동물공고 현황 API</dd></div><div><dt>집계 기준</dt><dd>게시글 등록일</dd></div><div><dt>기준일</dt><dd>{current?.basis_date ?? (failed ? "최신 확인 불가" : "—")}</dd></div><div><dt>원천 시각</dt><dd>API에서 별도 제공하지 않음</dd></div></dl><button className="text-link collection-link" onClick={() => onNavigate("reliability")}>데이터 신뢰성 확인 <Icon name="arrow"/></button></article>
    </section>
    <p className="privacy-note">공고 수는 게시글 등록일이 해당 KST 날짜인 공고만 집계합니다. 구조일이나 공고일 기준과는 다릅니다. 출처: 대전광역시 유기동물공고 현황 API · 단위: 건 · 시간대: KST</p>
  </div>;
}
