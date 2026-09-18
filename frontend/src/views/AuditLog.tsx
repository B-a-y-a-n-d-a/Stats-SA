// Implements specs/010-audit-log/spec.md — branch feature/010-audit-log.
//
// Audit log viewer for Communications Officials and Curator-Admins: lists
// audit_log rows from GET /api/audit (backend/app/api/audit.py, built
// concurrently on this same branch — see api/auditLog.ts for the exact
// contract this view calls). Filterable by query_id and a created_at date
// range; renders newest-first as returned by the API.
import { useEffect, useState, FormEvent, ReactNode, CSSProperties } from "react";
import { fetchAuditLog, AuditLogEntry } from "../api/auditLog";

// --- Minimal inline styling (hackathon MVP — no CSS framework/file), matching
// the conventions used in views/PublicWidget.tsx ---
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
  filterForm: {
    display: "flex",
    flexWrap: "wrap",
    gap: 8,
    alignItems: "flex-end",
    marginBottom: 16,
  },
  field: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  label: {
    fontSize: 12,
    fontWeight: 600,
    color: "#333",
  },
  input: {
    padding: "8px 10px",
    fontSize: 14,
    border: "1px solid #999",
    borderRadius: 4,
  },
  button: {
    padding: "9px 18px",
    fontSize: 14,
    border: "none",
    borderRadius: 4,
    backgroundColor: "#00529B", // Stats SA-ish blue, matches PublicWidget.tsx
    color: "#fff",
    cursor: "pointer",
  },
  buttonDisabled: {
    backgroundColor: "#7a9cc0",
    cursor: "not-allowed",
  },
  clearButton: {
    padding: "9px 18px",
    fontSize: 14,
    border: "1px solid #999",
    borderRadius: 4,
    backgroundColor: "#fff",
    color: "#333",
    cursor: "pointer",
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
  tableWrap: {
    overflowX: "auto",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: 14,
  },
  th: {
    textAlign: "left",
    padding: "8px 10px",
    borderBottom: "2px solid #ccc",
    backgroundColor: "#f5f5f5",
    whiteSpace: "nowrap",
  },
  td: {
    padding: "8px 10px",
    borderBottom: "1px solid #eee",
    verticalAlign: "top",
  },
  relatedRef: {
    color: "#555",
  },
};

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

// There is no per-query or per-source detail page yet, so related items are
// rendered as plain (non-clickable) truncated-id text with the full id in a
// title attribute, per the task instructions.
function truncateId(id: string): string {
  return id.slice(0, 8);
}

function RelatedCell({ entry }: { entry: AuditLogEntry }) {
  const refs: ReactNode[] = [];
  if (entry.query_id) {
    refs.push(
      <span key="query" style={styles.relatedRef} title={entry.query_id}>
        Query {truncateId(entry.query_id)}
      </span>
    );
  }
  if (entry.source_id) {
    refs.push(
      <span key="source" style={styles.relatedRef} title={entry.source_id}>
        Source {truncateId(entry.source_id)}
      </span>
    );
  }
  if (refs.length === 0) return <span>—</span>;
  return (
    <>
      {refs.map((ref, i) => (
        <span key={i}>
          {i > 0 && ", "}
          {ref}
        </span>
      ))}
    </>
  );
}

interface AppliedFilters {
  query_id?: string;
  start_date?: string;
  end_date?: string;
}

export default function AuditLog() {
  const [queryId, setQueryId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runFilter(filters: AppliedFilters) {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAuditLog(filters);
      setEntries(data);
    } catch (err) {
      setError(
        "Sorry, something went wrong while loading the audit log. Please try again shortly."
      );
      setEntries([]);
    } finally {
      setLoading(false);
    }
  }

  // Initial load, unfiltered.
  useEffect(() => {
    runFilter({});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (loading) return;
    runFilter({
      query_id: queryId.trim() || undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    });
  }

  function handleClear() {
    setQueryId("");
    setStartDate("");
    setEndDate("");
    runFilter({});
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.heading}>Audit Log</h2>

      <form style={styles.filterForm} onSubmit={handleSubmit}>
        <div style={styles.field}>
          <label style={styles.label} htmlFor="audit-query-id">
            Query ID
          </label>
          <input
            id="audit-query-id"
            style={styles.input}
            type="text"
            value={queryId}
            onChange={(e) => setQueryId(e.target.value)}
            placeholder="UUID"
            disabled={loading}
          />
        </div>
        <div style={styles.field}>
          <label style={styles.label} htmlFor="audit-start-date">
            Start date
          </label>
          <input
            id="audit-start-date"
            style={styles.input}
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            disabled={loading}
          />
        </div>
        <div style={styles.field}>
          <label style={styles.label} htmlFor="audit-end-date">
            End date
          </label>
          <input
            id="audit-end-date"
            style={styles.input}
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            disabled={loading}
          />
        </div>
        <button
          style={{ ...styles.button, ...(loading ? styles.buttonDisabled : {}) }}
          type="submit"
          disabled={loading}
        >
          {loading ? "Loading..." : "Filter"}
        </button>
        <button
          style={styles.clearButton}
          type="button"
          onClick={handleClear}
          disabled={loading}
        >
          Clear
        </button>
      </form>

      {loading && <p role="status">Loading audit events…</p>}

      {error && <div style={styles.errorBox}>{error}</div>}

      {!loading && !error && entries.length === 0 && (
        <div style={styles.emptyBox}>No audit events yet.</div>
      )}

      {!loading && !error && entries.length > 0 && (
        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Timestamp</th>
                <th style={styles.th}>Event Type</th>
                <th style={styles.th}>Actor</th>
                <th style={styles.th}>Related item</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.log_id}>
                  <td style={styles.td}>{formatTimestamp(entry.created_at)}</td>
                  <td style={styles.td}>{entry.event_type}</td>
                  <td style={styles.td}>{entry.actor_id ?? "system"}</td>
                  <td style={styles.td}>
                    <RelatedCell entry={entry} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
