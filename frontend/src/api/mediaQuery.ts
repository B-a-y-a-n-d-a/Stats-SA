// Implements specs/005-media-query-draft/spec.md — branch feature/005-media-query-draft.
import { apiFetch } from "./client";

export interface MediaQuerySubmission {
  text: string;
  submitter_name: string;
  submitter_org: string;
  submitter_email: string;
}

// The endpoint deliberately returns no answer or draft — only a receipt.
export interface MediaQueryReceipt {
  query_id: string;
  status: string;
  message: string;
}

export function submitMediaQuery(submission: MediaQuerySubmission): Promise<MediaQueryReceipt> {
  return apiFetch("/media/query", { method: "POST", body: JSON.stringify(submission) });
}
