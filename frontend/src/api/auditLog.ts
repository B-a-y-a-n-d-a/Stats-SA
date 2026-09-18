// Implements specs/010-audit-log/spec.md. File-per-feature API module for the
// audit log viewer, following the pattern set by api/publicQuery.ts: response
// shapes live here as TypeScript interfaces, and one exported function calls
// apiFetch.
//
// GET /api/audit is role-gated to comms_official/curator_admin via the real
// require_role dependency (specs/009-rbac-auth, merged) — apiFetch (client.ts)
// already sends whatever JWT is in localStorage under "token" as a Bearer
// header, so no extra auth wiring is needed here. There is no login/role-
// switcher UI yet (specs/011's job), so until then a tester logs in via
// POST /api/auth/login and puts the returned access_token in localStorage
// under "token" by hand to exercise this view.
import { apiFetch } from "./client";

export interface AuditLogEntry {
  log_id: string;
  event_type: string;
  actor_id: string | null;
  query_id: string | null;
  source_id: string | null;
  payload: Record<string, unknown> | null;
  sla_status: string | null;
  created_at: string;
}

export interface AuditLogFilters {
  query_id?: string;
  start_date?: string;
  end_date?: string;
}

export function fetchAuditLog(
  filters: AuditLogFilters = {}
): Promise<AuditLogEntry[]> {
  const params = new URLSearchParams();
  if (filters.query_id) params.set("query_id", filters.query_id);
  if (filters.start_date) params.set("start_date", filters.start_date);
  if (filters.end_date) params.set("end_date", filters.end_date);
  const queryString = params.toString();

  return apiFetch(`/audit?${queryString}`) as Promise<AuditLogEntry[]>;
}
