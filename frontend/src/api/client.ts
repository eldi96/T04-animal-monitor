import type { DailyRecord, LatestView, MonitoringStatus, ReplayFixtureId, ReplayPackageStatus, ReplayState } from "../types/api";

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `API 요청 실패 (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const getStatus = () => request<MonitoringStatus>("/api/status");
export const getLatest = () => request<LatestView>("/api/latest");
export const getDailyRecords = () => request<DailyRecord[]>("/api/daily-records");
export const requestRecovery = () => request("/api/test/recover", { method: "POST" });
export const collectToday = () => request<DailyRecord>("/api/collect/today", { method: "POST" });
export const getReplayPackage = () => request<ReplayPackageStatus>("/api/replay/package");
export const getReplayState = () => request<ReplayState>("/api/replay/state");
export const resetReplay = () => request<ReplayState>("/api/replay/reset", { method: "POST" });
export const runReplayFixture = (fixtureId: ReplayFixtureId) =>
  request<ReplayState>(`/api/replay/fixtures/${fixtureId}`, { method: "POST" });
export const recoverReplay = () => request<ReplayState>("/api/replay/recover", { method: "POST" });
