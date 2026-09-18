// Implements specs/008-curator-admin/spec.md. File-per-feature API module for
// the curator admin views, following the pattern set by api/auditLog.ts and
// api/review.ts: response shapes live here as TypeScript interfaces, and one
// exported function per endpoint calls apiFetch.
//
// All 5 /api/curator/* endpoints are role-gated to curator_admin via the real
// require_role dependency (specs/009-rbac-auth, merged) — apiFetch (client.ts)
// already sends whatever JWT is in localStorage under "token" as a Bearer
// header, so no extra auth wiring is needed here. There is no login/role-
// switcher UI yet (specs/011's job), so until then a tester logs in via
// POST /api/auth/login and puts the returned access_token in localStorage
// under "token" by hand to exercise this view.
import { apiFetch } from "./client";

export type SourceCategory =
  | "Statistical Release"
  | "Publication"
  | "Press Statement"
  | "FAQ"
  | "Historical Communication";

export type TerminologyCategory =
  | "Terminology"
  | "Style Rule"
  | "Branding Standard"
  | "Preferred Phrasing"
  | "Prohibited Term";

export interface Source {
  source_id: string;
  title: string;
  url: string;
  category: string;
  published_date: string;
  ingested_date: string;
  version: number;
  superseded_by: string | null;
  retired_at: string | null;
  confidentiality_tag: string;
}

export interface UploadSourceResult {
  source_id: string;
  version: number;
  title: string;
}

export interface RetireSourceResult {
  source_id: string;
  retired_at: string;
}

export interface UploadSourceForm {
  title: string;
  url: string;
  category: string;
  published_date: string;
  file?: File | null;
}

export interface TerminologyEntry {
  guide_entry_id: string;
  category: string;
  term_or_topic: string;
  approved_guidance: string;
  discouraged_alternative: string | null;
  rationale: string;
  version: number;
  superseded_by: string | null;
  approved_by: string | null;
  effective_date: string;
  last_reviewed_date: string | null;
}

export interface CreateTerminologyEntryRequest {
  category: string;
  term_or_topic: string;
  approved_guidance: string;
  discouraged_alternative?: string;
  rationale: string;
  effective_date?: string;
}

export function fetchSources(): Promise<Source[]> {
  return apiFetch("/curator/sources") as Promise<Source[]>;
}

// multipart/form-data upload — the file is appended only when present, since
// the backend fetches the PDF itself from `url` when no file is attached.
// No explicit headers are set here; client.ts's FormData check leaves
// Content-Type unset so the browser can fill in its own multipart boundary.
export function uploadSource(form: UploadSourceForm): Promise<UploadSourceResult> {
  const formData = new FormData();
  formData.append("title", form.title);
  formData.append("url", form.url);
  formData.append("category", form.category);
  formData.append("published_date", form.published_date);
  if (form.file) formData.append("file", form.file);

  return apiFetch("/curator/sources", {
    method: "POST",
    body: formData,
  }) as Promise<UploadSourceResult>;
}

export function retireSource(sourceId: string): Promise<RetireSourceResult> {
  return apiFetch(`/curator/sources/${sourceId}`, {
    method: "DELETE",
  }) as Promise<RetireSourceResult>;
}

export function fetchTerminology(): Promise<TerminologyEntry[]> {
  return apiFetch("/curator/terminology") as Promise<TerminologyEntry[]>;
}

export function createTerminologyEntry(
  entry: CreateTerminologyEntryRequest
): Promise<TerminologyEntry> {
  return apiFetch("/curator/terminology", {
    method: "POST",
    body: JSON.stringify(entry),
  }) as Promise<TerminologyEntry>;
}
