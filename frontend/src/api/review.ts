// Implements specs/006-review-console/spec.md. File-per-feature API module for
// the review console, following the pattern set by api/auditLog.ts: response
// shapes live here as TypeScript interfaces, and one exported function per
// endpoint calls apiFetch.
//
// Both endpoints are role-gated to comms_official via the real require_role
// dependency (specs/009-rbac-auth, merged) — apiFetch (client.ts) already
// sends whatever JWT is in localStorage under "token" as a Bearer header, so
// no extra auth wiring is needed here. There is no login/role-switcher UI yet
// (specs/011's job), so until then a tester logs in via POST /api/auth/login
// and puts the returned access_token in localStorage under "token" by hand to
// exercise this view.
import { apiFetch } from "./client";
import { Citation } from "./publicQuery";

// A key figure is lifted verbatim from a citation quote by build_draft
// (backend/app/retrieval/draft_builder.py) — never invented — so a reviewer
// can sanity-check it against the body text and its source.
export interface KeyFigure {
  figure: string;
  chunk_id: string;
  source: string | null;
}

// Only present on media-channel drafts (specs/005) — the media enquirer's
// contact details travel with the draft since `queries` has no submitter
// columns.
export interface Submitter {
  name: string;
  org: string;
  email: string;
}

// The exact shape build_draft() produces, shared by the media path and 004's
// low-confidence public path — see backend/app/retrieval/draft_builder.py.
export interface ReviewDraft {
  headline: string;
  body: string;
  key_figures: KeyFigure[];
  citations: Citation[];
  suggested_tone: string;
  information_gap: boolean;
  confidence_score: number;
  submitter?: Submitter;
}

export interface ReviewHistoryEntry {
  decision: string;
  reason: string | null;
  reviewer_id: string;
  decided_at: string;
}

export interface ReviewQueueItem {
  query_id: string;
  draft_id: string;
  channel: "public" | "media";
  query_text: string;
  status: "escalated" | "rejected";
  confidence_score: number;
  submitted_at: string;
  draft: ReviewDraft;
  // Always null for now — populated by specs/007 (Communication Memory) once
  // it exists; the field is already on the contract so 007 can fill it in
  // without another shape change here.
  reuse_match: null;
  review_history: ReviewHistoryEntry[];
}

export type ReviewDecision = "approve" | "edit_approve" | "reject";

export interface ReviewDecisionRequest {
  decision: ReviewDecision;
  final_text?: string;
  reason?: string;
}

export interface ReviewDecisionResult {
  review_id: string;
  decision: string;
  query_status: string;
}

export function fetchReviewQueue(): Promise<ReviewQueueItem[]> {
  return apiFetch("/review/queue") as Promise<ReviewQueueItem[]>;
}

export function decideReview(
  draftId: string,
  decision: ReviewDecisionRequest
): Promise<ReviewDecisionResult> {
  return apiFetch(`/review/${draftId}/decide`, {
    method: "POST",
    body: JSON.stringify(decision),
  }) as Promise<ReviewDecisionResult>;
}
