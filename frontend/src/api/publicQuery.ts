// Implements specs/004-public-query-widget/spec.md. Extracted from PublicWidget.tsx
// so the API contract and response shapes live in one place, matching the
// pattern other query-path specs (005) also follow.
import { apiFetch } from "./client";

export interface Citation {
  chunk_id: string;
  source_id: string;
  title: string;
  url: string;
  quote: string;
}

export interface AnsweredResponse {
  status: "answered";
  answer: string;
  confidence_score: number;
  citations: Citation[];
}

export interface EscalatedResponse {
  status: "escalated";
  message: string;
  query_id: string;
}

export type PublicQueryResponse = AnsweredResponse | EscalatedResponse;

export function submitPublicQuery(text: string): Promise<PublicQueryResponse> {
  return apiFetch("/public/query", {
    method: "POST",
    body: JSON.stringify({ text }),
  }) as Promise<PublicQueryResponse>;
}
