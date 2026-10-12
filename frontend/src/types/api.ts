export type CollectionStatus = "UNINITIALIZED" | "NORMAL" | "FAILED" | "RECOVERED";
export type FailureType =
  | "TIMEOUT"
  | "AUTH_ERROR"
  | "FORBIDDEN"
  | "SERVER_ERROR"
  | "OFFLINE"
  | "MALFORMED_RESPONSE"
  | "STALE_RESPONSE";

export interface DailyRecord {
  id: number | null;
  basis_date: string;
  basis_timezone: string;
  value: number;
  source_value?: number | null;
  district_counts?: Record<string, number> | null;
  species_counts?: Record<string, number> | null;
  status_counts?: Record<string, number> | null;
  weekly_registration_counts?: Record<string, number> | null;
  weekly_district_counts?: Record<string, number> | null;
  weekly_species_counts?: Record<string, number> | null;
  weekly_status_counts?: Record<string, number> | null;
  recent_7_day_registration_counts?: Record<string, number> | null;
  unit: string;
  source: string;
  source_timestamp: string | null;
  fetched_at_kst: string;
  data_origin: "real" | "synthetic";
  error_code: string | null;
  created_at: string | null;
}

export interface FailureState {
  type: FailureType;
  code: string;
  message: string;
  http_status: number | null;
  occurred_at: string;
  data_origin: "real" | "synthetic";
}

export interface MonitoringStatus {
  status: CollectionStatus;
  failure: FailureState | null;
  current_latest_available: boolean;
  last_successful_observed_at: string | null;
  source: string | null;
  basis_timezone: string;
  data_origin: "real" | "synthetic" | null;
  message: string;
}

export interface LatestView {
  status: CollectionStatus;
  current_latest: DailyRecord | null;
  last_known_good: DailyRecord | null;
  current_latest_available: boolean;
  failure: FailureState | null;
  message: string;
}

export type ReplayErrorCode = "none" | "timeout" | "auth" | "rate_limit" | "offline" | "schema_error";
export type ReplayFixtureId =
  | "T04-NORMAL-D1-A"
  | "T04-NORMAL-D1-B"
  | "T04-NORMAL-D2"
  | "T04-TIMEOUT"
  | "T04-AUTH-401"
  | "T04-RATE-429"
  | "T04-OFFLINE"
  | "T04-SCHEMA-BREAK"
  | "T04-RECOVER-D2";

export interface ReplayReading {
  signal_id: string;
  normalized_value: number;
  unit: string;
  source_name: string;
  source_url: string;
  source_time: string | null;
  fetched_at: string;
  record_timezone: "Asia/Seoul";
  record_date: string;
}

export interface ReplayState {
  schema_version: string;
  data_origin: "synthetic";
  daily_readings: {
    record_id: string;
    signal_id: string;
    record_date: string;
    normalized_value: number;
    unit: string;
    first_fetched_at: string;
    last_fetched_at: string;
    reading: ReplayReading;
  }[];
  current_reading: ReplayReading | null;
  status: { freshness: "fresh" | "stale"; error_code: ReplayErrorCode } | null;
  last_delta: number | null;
  last_comparison: { state: string; direction: string | null; magnitude: number | null; unit: string | null };
  last_run: { fixture_id: ReplayFixtureId | null; virtual_now: string | null; outcome: "success" | "error"; error_code: ReplayErrorCode; retry_after_seconds: number | null } | null;
  sequence: number;
  message_ko: string;
  next_action_ko: string | null;
}

export interface ReplayPackageStatus {
  package_id: string;
  hash_algorithm: "sha256";
  checked_file_count: number;
  integrity_ok: boolean;
  files: { path: string; exists: boolean; bytes_match: boolean; sha256_match: boolean; expected_sha256: string }[];
}
