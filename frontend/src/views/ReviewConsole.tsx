// Implements specs/006-review-console/spec.md — branch feature/006-review-console.
//
// Communications Official review console: every media enquiry draft and every
// low-confidence public draft lands here (GET /api/review/queue) before a
// human decides what happens to it (POST /api/review/{draft_id}/decide). See
// api/review.ts for the exact contract this view calls — built concurrently
// on the backend side of this same branch.
import { useEffect, useState, CSSProperties } from "react";
import {
  fetchReviewQueue,
  decideReview,
  ReviewQueueItem,
  ReviewDecisionRequest,
} from "../api/review";

// --- Minimal inline styling (hackathon MVP — no CSS framework/file), matching
// the conventions used in views/AuditLog.tsx and views/PublicWidget.tsx ---
const styles: Record<string, CSSProperties> = {
  container: {
    maxWidth: 960,
    margin: "0 auto",
    padding: 16,
    fontFamily: "system-ui, sans-serif",
  },
  heading: {
    margin: "0 0 12px 0",
  },
  errorBox: {
    marginTop: 8,
    padding: 12,
    borderRadius: 4,
    backgroundColor: "#fdecea",
    border: "1px solid #f5c6cb",
    color: "#611a15",
  },
  emptyBox: {
    marginTop: 8,
    padding: 12,
    borderRadius: 4,
    backgroundColor: "#f5f5f5",
    border: "1px dashed #999",
    color: "#555",
  },
  list: {
    listStyle: "none",
    margin: 0,
    padding: 0,
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  item: {
    border: "1px solid #ccc",
    borderRadius: 4,
    overflow: "hidden",
  },
  row: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "10px 12px",
    cursor: "pointer",
    backgroundColor: "#fff",
  },
  rowExpanded: {
    backgroundColor: "#f5f9fc",
    borderBottom: "1px solid #ccc",
  },
  channelBadge: {
    display: "inline-block",
    padding: "2px 10px",
    borderRadius: 12,
    fontSize: 12,
    fontWeight: 600,
    backgroundColor: "#e0e0e0",
    color: "#333",
    whiteSpace: "nowrap",
  },
  statusEscalated: {
    display: "inline-block",
    padding: "2px 10px",
    borderRadius: 12,
    fontSize: 12,
    fontWeight: 600,
    backgroundColor: "#fff8e1",
    color: "#7a5c00",
    border: "1px solid #ffe0a3",
    whiteSpace: "nowrap",
  },
  statusRejected: {
    display: "inline-block",
    padding: "2px 10px",
    borderRadius: 12,
    fontSize: 12,
    fontWeight: 600,
    backgroundColor: "#fdecea",
    color: "#611a15",
    border: "1px solid #f5c6cb",
    whiteSpace: "nowrap",
  },
  excerpt: {
    flex: 1,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  confidenceBadge: {
    display: "inline-block",
    padding: "2px 10px",
    borderRadius: 12,
    fontSize: 12,
    fontWeight: 600,
    backgroundColor: "#e0e0e0",
    color: "#333",
    whiteSpace: "nowrap",
  },
  detail: {
    padding: 16,
    backgroundColor: "#fbfbfb",
  },
  section: {
    marginBottom: 14,
  },
  sectionHeading: {
    margin: "0 0 6px 0",
    fontSize: 13,
    fontWeight: 700,
    color: "#333",
    textTransform: "uppercase",
    letterSpacing: 0.4,
  },
  headline: {
    margin: "0 0 8px 0",
    fontSize: 17,
    fontWeight: 700,
  },
  body: {
    margin: 0,
    whiteSpace: "pre-wrap",
  },
  gapBox: {
    marginBottom: 14,
    padding: 12,
    borderRadius: 4,
    backgroundColor: "#fff8e1",
    border: "1px solid #ffe0a3",
    color: "#4a3c00",
    fontWeight: 600,
  },
  keyFigureList: {
    margin: 0,
    paddingLeft: 18,
  },
  citationsBox: {
    padding: 12,
    borderRadius: 4,
    backgroundColor: "#eaf3ea",
    border: "1px solid #b7d8b7",
  },
  citationItem: {
    marginBottom: 6,
  },
  citationLink: {
    color: "#0b5394",
  },
  citationQuote: {
    display: "block",
    fontSize: 13,
    color: "#555",
    marginTop: 2,
  },
  submitterBox: {
    padding: 12,
    borderRadius: 4,
    backgroundColor: "#f0f0f0",
    border: "1px solid #ccc",
    fontSize: 14,
  },
  historyList: {
    margin: 0,
    paddingLeft: 18,
  },
  historyItem: {
    marginBottom: 8,
  },
  historyMeta: {
    fontSize: 12,
    color: "#666",
  },
  actions: {
    display: "flex",
    flexWrap: "wrap",
    gap: 8,
    marginTop: 8,
  },
  button: {
    padding: "9px 18px",
    fontSize: 14,
    border: "none",
    borderRadius: 4,
    backgroundColor: "#00529B", // Stats SA-ish blue, matches AuditLog.tsx / PublicWidget.tsx
    color: "#fff",
    cursor: "pointer",
  },
  rejectButton: {
    padding: "9px 18px",
    fontSize: 14,
    border: "none",
    borderRadius: 4,
    backgroundColor: "#a12622",
    color: "#fff",
    cursor: "pointer",
  },
  secondaryButton: {
    padding: "9px 18px",
    fontSize: 14,
    border: "1px solid #999",
    borderRadius: 4,
    backgroundColor: "#fff",
    color: "#333",
    cursor: "pointer",
  },
  buttonDisabled: {
    backgroundColor: "#7a9cc0",
    cursor: "not-allowed",
  },
  textarea: {
    width: "100%",
    minHeight: 120,
    padding: "8px 10px",
    fontSize: 14,
    fontFamily: "inherit",
    border: "1px solid #999",
    borderRadius: 4,
    boxSizing: "border-box",
    marginBottom: 8,
  },
  reasonInput: {
    width: "100%",
    padding: "8px 10px",
    fontSize: 14,
    border: "1px solid #999",
    borderRadius: 4,
    boxSizing: "border-box",
    marginBottom: 8,
  },
  actionErrorBox: {
    marginTop: 8,
    padding: 8,
    borderRadius: 4,
    backgroundColor: "#fdecea",
    border: "1px solid #f5c6cb",
    color: "#611a15",
    fontSize: 13,
  },
};

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

function truncateId(id: string): string {
  return id ? id.slice(0, 8) : "unknown";
}

function excerpt(text: string, max = 100): string {
  const trimmed = text.trim();
  return trimmed.length > max ? trimmed.slice(0, max - 1).trimEnd() + "…" : trimmed;
}

function ConfidenceBadge({ score }: { score: number }) {
  return <span style={styles.confidenceBadge}>Confidence: {Math.round(score * 100)}%</span>;
}

function ChannelBadge({ channel }: { channel: "public" | "media" }) {
  return <span style={styles.channelBadge}>{channel === "media" ? "Media" : "Public"}</span>;
}

function StatusBadge({ status }: { status: "escalated" | "rejected" }) {
  if (status === "rejected") {
    return <span style={styles.statusRejected}>Previously rejected</span>;
  }
  return <span style={styles.statusEscalated}>Never reviewed</span>;
}

// Per-row UI-only state: which action panel (if any) is open, the in-progress
// edit text / reject reason, and submit-in-flight / error status. Keyed by
// draft_id so it survives a queue refresh without losing what a reviewer was
// mid-typing on a different row.
interface RowUiState {
  panel: "none" | "edit" | "reject";
  editText: string;
  reason: string;
  submitting: boolean;
  actionError: string | null;
}

const DEFAULT_ROW_STATE: RowUiState = {
  panel: "none",
  editText: "",
  reason: "",
  submitting: false,
  actionError: null,
};

export default function ReviewConsole() {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [rowState, setRowState] = useState<Record<string, RowUiState>>({});

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchReviewQueue();
      setItems(data);
    } catch (err) {
      setError(
        "Sorry, something went wrong while loading the review queue. Please try again shortly."
      );
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function getRow(draftId: string): RowUiState {
    return rowState[draftId] ?? DEFAULT_ROW_STATE;
  }

  function patchRow(draftId: string, patch: Partial<RowUiState>) {
    setRowState((prev) => ({ ...prev, [draftId]: { ...getRow(draftId), ...patch } }));
  }

  function toggleExpanded(item: ReviewQueueItem) {
    setExpandedId((prev) => (prev === item.draft_id ? null : item.draft_id));
    if (!rowState[item.draft_id]) {
      patchRow(item.draft_id, { editText: item.draft.body });
    }
  }

  function openPanel(item: ReviewQueueItem, panel: "edit" | "reject") {
    const row = getRow(item.draft_id);
    patchRow(item.draft_id, {
      panel: row.panel === panel ? "none" : panel,
      editText: row.editText || item.draft.body,
      actionError: null,
    });
  }

  // A rejected item is refreshed from the server rather than reconstructed
  // client-side, so its new review_history entry carries the real
  // reviewer_id / decided_at the backend recorded instead of a guess. An
  // approved item simply drops out of the next queue fetch, since
  // GET /api/review/queue only ever returns escalated/rejected items.
  async function submitDecision(item: ReviewQueueItem, decision: ReviewDecisionRequest["decision"]) {
    const row = getRow(item.draft_id);

    if (decision === "reject" && !row.reason.trim()) {
      patchRow(item.draft_id, { actionError: "A reason is required to reject a draft." });
      return;
    }

    patchRow(item.draft_id, { submitting: true, actionError: null });

    const body: ReviewDecisionRequest = { decision };
    if (decision === "edit_approve") body.final_text = row.editText;
    if (decision === "reject") body.reason = row.reason.trim();

    try {
      const result = await decideReview(item.draft_id, body);

      if (result.query_status === "approved") {
        setItems((prev) => prev.filter((i) => i.draft_id !== item.draft_id));
        setExpandedId((prev) => (prev === item.draft_id ? null : prev));
        setRowState((prev) => {
          const next = { ...prev };
          delete next[item.draft_id];
          return next;
        });
      } else {
        try {
          const refreshed = await fetchReviewQueue();
          setItems(refreshed);
        } catch {
          // The decision itself succeeded; only the re-fetch failed. Leave
          // the (now stale) item in place rather than losing it, and let the
          // reviewer know a manual reload may be needed.
          patchRow(item.draft_id, {
            actionError:
              "Rejection was recorded, but refreshing the queue failed. Reload the page to see the latest state.",
          });
        }
        patchRow(item.draft_id, {
          panel: "none",
          reason: "",
          submitting: false,
          actionError: null,
        });
      }
    } catch (err) {
      patchRow(item.draft_id, {
        submitting: false,
        actionError:
          err instanceof Error ? err.message : "Something went wrong recording this decision.",
      });
    }
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.heading}>Review Console</h2>

      {loading && <p role="status">Loading review queue…</p>}

      {error && <div style={styles.errorBox}>{error}</div>}

      {!loading && !error && items.length === 0 && (
        <div style={styles.emptyBox}>No items awaiting review.</div>
      )}

      {!loading && !error && items.length > 0 && (
        <ul style={styles.list}>
          {items.map((item) => {
            const isExpanded = expandedId === item.draft_id;
            const row = getRow(item.draft_id);
            return (
              <li key={item.draft_id} style={styles.item}>
                <div
                  style={{ ...styles.row, ...(isExpanded ? styles.rowExpanded : {}) }}
                  onClick={() => toggleExpanded(item)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      toggleExpanded(item);
                    }
                  }}
                >
                  <ChannelBadge channel={item.channel} />
                  <StatusBadge status={item.status} />
                  <span style={styles.excerpt}>{excerpt(item.query_text)}</span>
                  <ConfidenceBadge score={item.draft.confidence_score} />
                </div>

                {isExpanded && (
                  <div style={styles.detail}>
                    <div style={styles.section}>
                      <p style={styles.sectionHeading}>Draft headline</p>
                      <p style={styles.headline}>{item.draft.headline}</p>
                    </div>

                    {item.draft.information_gap && (
                      <div style={styles.gapBox}>
                        No grounded answer available — this draft states an information gap,
                        it is not a real answer. Do not release as-is.
                      </div>
                    )}

                    <div style={styles.section}>
                      <p style={styles.sectionHeading}>Draft body</p>
                      <p style={styles.body}>{item.draft.body}</p>
                    </div>

                    <div style={styles.section}>
                      <ConfidenceBadge score={item.draft.confidence_score} />
                      <span style={{ marginLeft: 12, fontSize: 13, color: "#555" }}>
                        Suggested tone: {item.draft.suggested_tone}
                      </span>
                    </div>

                    {item.draft.key_figures.length > 0 && (
                      <div style={styles.section}>
                        <p style={styles.sectionHeading}>Key figures (verbatim from sources)</p>
                        <ul style={styles.keyFigureList}>
                          {item.draft.key_figures.map((fig, i) => (
                            <li key={`${fig.chunk_id}-${i}`}>
                              {fig.figure}
                              {fig.source && (
                                <span style={{ color: "#555" }}> — {fig.source}</span>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div style={styles.section}>
                      <p style={styles.sectionHeading}>Sources / evidence used</p>
                      <div style={styles.citationsBox}>
                        {item.draft.citations.length === 0 ? (
                          <p style={{ margin: 0, fontSize: 13, color: "#555" }}>
                            No sources were returned for this draft.
                          </p>
                        ) : (
                          <ul style={{ margin: 0, paddingLeft: 18 }}>
                            {item.draft.citations.map((citation) => (
                              <li key={citation.chunk_id} style={styles.citationItem}>
                                <a
                                  href={citation.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  style={styles.citationLink}
                                >
                                  {citation.title}
                                </a>
                                {citation.quote && (
                                  <span style={styles.citationQuote}>
                                    &ldquo;{citation.quote}&rdquo;
                                  </span>
                                )}
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>

                    {item.draft.submitter && (
                      <div style={styles.section}>
                        <p style={styles.sectionHeading}>Submitter (media)</p>
                        <div style={styles.submitterBox}>
                          <div>{item.draft.submitter.name}</div>
                          <div>{item.draft.submitter.org}</div>
                          <div>{item.draft.submitter.email}</div>
                        </div>
                      </div>
                    )}

                    {item.review_history.length > 0 && (
                      <div style={styles.section}>
                        <p style={styles.sectionHeading}>Review history</p>
                        <ul style={styles.historyList}>
                          {item.review_history.map((h, i) => (
                            <li key={i} style={styles.historyItem}>
                              <div>
                                <strong>{h.decision}</strong>
                                {h.reason && <>: {h.reason}</>}
                              </div>
                              <div style={styles.historyMeta}>
                                {formatTimestamp(h.decided_at)} · reviewer {truncateId(h.reviewer_id)}
                              </div>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div style={styles.section}>
                      <p style={styles.sectionHeading}>Decision</p>

                      <div style={styles.actions}>
                        <button
                          style={{
                            ...styles.button,
                            ...(row.submitting ? styles.buttonDisabled : {}),
                          }}
                          disabled={row.submitting}
                          onClick={() => submitDecision(item, "approve")}
                        >
                          {row.submitting ? "Working…" : "Approve"}
                        </button>
                        <button
                          style={styles.secondaryButton}
                          disabled={row.submitting}
                          onClick={() => openPanel(item, "edit")}
                        >
                          Edit then Approve
                        </button>
                        <button
                          style={{
                            ...styles.rejectButton,
                            ...(row.submitting ? styles.buttonDisabled : {}),
                          }}
                          disabled={row.submitting}
                          onClick={() => openPanel(item, "reject")}
                        >
                          Reject
                        </button>
                      </div>

                      {row.panel === "edit" && (
                        <div style={{ marginTop: 10 }}>
                          <textarea
                            style={styles.textarea}
                            value={row.editText}
                            onChange={(e) => patchRow(item.draft_id, { editText: e.target.value })}
                            disabled={row.submitting}
                          />
                          <div style={styles.actions}>
                            <button
                              style={{
                                ...styles.button,
                                ...(row.submitting ? styles.buttonDisabled : {}),
                              }}
                              disabled={row.submitting}
                              onClick={() => submitDecision(item, "edit_approve")}
                            >
                              {row.submitting ? "Working…" : "Submit edit & approve"}
                            </button>
                            <button
                              style={styles.secondaryButton}
                              disabled={row.submitting}
                              onClick={() => patchRow(item.draft_id, { panel: "none" })}
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      )}

                      {row.panel === "reject" && (
                        <div style={{ marginTop: 10 }}>
                          <label
                            htmlFor={`reject-reason-${item.draft_id}`}
                            style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 4 }}
                          >
                            Reason for rejection (required)
                          </label>
                          <input
                            id={`reject-reason-${item.draft_id}`}
                            style={styles.reasonInput}
                            type="text"
                            value={row.reason}
                            onChange={(e) => patchRow(item.draft_id, { reason: e.target.value })}
                            disabled={row.submitting}
                          />
                          <div style={styles.actions}>
                            <button
                              style={{
                                ...styles.rejectButton,
                                ...(row.submitting || !row.reason.trim() ? styles.buttonDisabled : {}),
                              }}
                              disabled={row.submitting || !row.reason.trim()}
                              onClick={() => submitDecision(item, "reject")}
                            >
                              {row.submitting ? "Working…" : "Confirm reject"}
                            </button>
                            <button
                              style={styles.secondaryButton}
                              disabled={row.submitting}
                              onClick={() => patchRow(item.draft_id, { panel: "none", reason: "" })}
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      )}

                      {row.actionError && <div style={styles.actionErrorBox}>{row.actionError}</div>}
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
