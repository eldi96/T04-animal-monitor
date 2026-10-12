import { useCallback, useEffect, useState } from "react";
import { collectToday, getDailyRecords, getLatest, getReplayPackage, getReplayState, recoverReplay, requestRecovery, resetReplay, runReplayFixture } from "./api/client";
import type { DailyRecord, LatestView, ReplayFixtureId, ReplayPackageStatus, ReplayState } from "./types/api";
import { Icon, type IconName } from "./components/Icon";
import { HomePage } from "./pages/HomePage";
import { AnalysisPage } from "./pages/AnalysisPage";
import { ReliabilityPage } from "./pages/ReliabilityPage";
import { FailureTestPage } from "./pages/FailureTestPage";
import { RecoveryPage } from "./pages/RecoveryPage";

type Page = "home" | "analysis" | "reliability" | "test" | "recovery";
const navigation: { id: Page; label: string; icon: IconName }[] = [
  { id: "home", label: "홈", icon: "home" },
  { id: "analysis", label: "데이터 분석", icon: "chart" },
  { id: "reliability", label: "데이터 신뢰성", icon: "shield" },
  { id: "test", label: "실패 테스트", icon: "flask" },
  { id: "recovery", label: "복구", icon: "rotate" },
];

export default function App() {
  const [page, setPage] = useState<Page>("home");
  const [view, setView] = useState<LatestView | null>(null);
  const [records, setRecords] = useState<DailyRecord[]>([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("화면 미리보기입니다. 서버가 없어 실제 데이터 조회와 실패 재생은 사용할 수 없습니다.");
  const [apiAvailable, setApiAvailable] = useState(false);
  const [replay, setReplay] = useState<ReplayState | null>(null);
  const [replayPackage, setReplayPackage] = useState<ReplayPackageStatus | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [latest, daily] = await Promise.all([getLatest(), getDailyRecords()]);
      setView(latest);
      setRecords(daily);
      setApiAvailable(true);
    } catch {
      setApiAvailable(false);
      setView(null);
      setRecords([]);
    }
    try {
      const [replayState, packageStatus] = await Promise.all([getReplayState(), getReplayPackage()]);
      setReplay(replayState);
      setReplayPackage(packageStatus);
    } catch {
      setReplay(null);
      setReplayPackage(null);
    }
  }, []);

  useEffect(() => { if (import.meta.env.VITE_STATIC_PREVIEW === "true") return;
    void refresh();
    const refreshTimer = window.setInterval(() => { void refresh(); }, 60_000);
    return () => window.clearInterval(refreshTimer);
  }, [refresh]);

  const onReplay = async (fixtureId: ReplayFixtureId) => {
    setBusy(true);
    try {
      if (!replayPackage?.integrity_ok) throw new Error("공개 fixture 파일의 SHA-256 검증이 완료되지 않았습니다.");
      await resetReplay();
      await runReplayFixture("T04-NORMAL-D1-A");
      await runReplayFixture("T04-NORMAL-D1-B");
      setReplay(await runReplayFixture(fixtureId));
      setNotice("선택한 문제 상황을 예시 자료로 보여 드립니다. 실제 자료와 저장 기록은 바뀌지 않았어요.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "실패 재생 요청에 실패했습니다.");
    } finally { setBusy(false); }
  };

  const onReplayNormalSequence = async () => {
    setBusy(true);
    try {
      if (!replayPackage?.integrity_ok) throw new Error("공개 fixture 파일의 SHA-256 검증이 완료되지 않았습니다.");
      await resetReplay();
      await runReplayFixture("T04-NORMAL-D1-A");
      setReplay(await runReplayFixture("T04-NORMAL-D1-B"));
      setNotice("정상 D1-A → D1-B를 재생했습니다. 같은 날짜 기록은 1건이며 값은 105 pt입니다.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "예시 자료를 불러오지 못했습니다. 다시 시도해 주세요.");
    } finally { setBusy(false); }
  };

  const onReplayD2 = async () => {
    setBusy(true);
    try {
      if (!replayPackage?.integrity_ok) throw new Error("공개 fixture 파일의 SHA-256 검증이 완료되지 않았습니다.");
      await resetReplay();
      await runReplayFixture("T04-NORMAL-D1-A");
      await runReplayFixture("T04-NORMAL-D1-B");
      setReplay(await runReplayFixture("T04-NORMAL-D2"));
      setNotice("정상 D1-A → D1-B → D2를 재생했습니다. 두 번째 날짜 행과 +15 pt 변화가 표시됩니다.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "예시 자료를 불러오지 못했습니다. 다시 시도해 주세요.");
    } finally { setBusy(false); }
  };

  const onReplayRecovery = async () => {
    setBusy(true);
    try {
      if (!replayPackage?.integrity_ok) throw new Error("공개 fixture 파일의 SHA-256 검증이 완료되지 않았습니다.");
      setReplay(await recoverReplay());
      setNotice("다음 날짜의 예시 자료를 확인했습니다. 문제가 해결된 상태를 보여 드립니다.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "예시 자료를 다시 확인하지 못했습니다. 다시 눌러 주세요.");
    } finally { setBusy(false); }
  };

  const onReplayReset = async () => {
    setBusy(true);
    try {
      setReplay(await resetReplay());
      setNotice("예시 시험 결과를 지웠습니다. 실제 자료와 저장 기록은 그대로예요.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "예시 시험 결과를 지우지 못했습니다.");
    } finally { setBusy(false); }
  };

  const onRecover = async () => {
    setBusy(true);
    try {
      if (view?.status === "FAILED") {
        await requestRecovery();
        setNotice("새 실제 데이터가 저장되어 복구되었습니다.");
      } else {
        await collectToday();
        setNotice("오늘 기준의 실제 데이터가 저장되었습니다.");
      }
      await refresh();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "새 실제 데이터가 없어 복구할 수 없습니다.");
      await refresh();
    } finally { setBusy(false); }
  };

  const pageProps = { view, records };
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-symbol"><Icon name="paw" /></div>
          <div className="brand-name">대전광역시<span>유기동물 공고 모니터링</span></div>
        </div>
        <div className="sidebar-welcome"><span>함께 만드는 더 따뜻한 대전</span><p>모든 생명이 소중한 대전</p></div>
        <nav aria-label="주 메뉴" className="main-nav">
          {navigation.map(({ id, label, icon }) => (
            <button key={id} className={`nav-item ${page === id ? "active" : ""}`} onClick={() => setPage(id)} aria-current={page === id ? "page" : undefined}>
              <Icon name={icon} /><span>{label}</span>
            </button>
          ))}
        </nav>
        <img className="sidebar-scene" src={`${import.meta.env.BASE_URL}daejeon-sidebar-scenery.svg`} alt="" aria-hidden="true" />
        <div className="sidebar-caption"><span>DAEJEON ANIMAL NOTICE</span><br />유기동물 공고 모니터링 서비스</div>
      </aside>

      <main className="main-content">
        {!apiAvailable && <div className="connection-banner"><span className="connection-dot" /> 정적 화면 미리보기 · 서버 미연결 · 실제 데이터 없음</div>}
        {page === "home" && <HomePage {...pageProps} onNavigate={setPage} />}
        {page === "analysis" && <AnalysisPage records={records} />}
        {page === "reliability" && <ReliabilityPage view={view} apiAvailable={apiAvailable} />}
        {page === "test" && <FailureTestPage replay={replay} replayPackage={replayPackage} onReplay={onReplay} onNormalSequence={onReplayNormalSequence} onD2Sequence={onReplayD2} onRecover={onReplayRecovery} onReset={onReplayReset} busy={busy} notice={notice} />}
        {page === "recovery" && <RecoveryPage view={view} onRecover={onRecover} busy={busy} notice={notice} apiAvailable={apiAvailable} />}
      </main>
    </div>
  );
}
