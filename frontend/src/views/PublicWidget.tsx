// Implements specs/004-public-query-widget/spec.md — branch feature/004-public-query-widget.
//
// Public self-service query widget. Calls POST /api/public/query (see
// backend contract in the spec / app/retrieval/service.py answer_query) and
// renders one of two shapes depending on the retrieval confidence gate:
//   - status "answered": answer text + confidence badge + clickable citations.
//   - status "escalated": only the escalation message — no answer, no
//     citations, no confidence badge, nothing fabricated.
import { useState, FormEvent, CSSProperties } from "react";
import { submitPublicQuery, PublicQueryResponse } from "../api/publicQuery";

// --- Minimal inline styling (hackathon MVP — no CSS framework/file) ---

const styles: Record<string, CSSProperties> = {
  container: {
    maxWidth: 640,
    margin: "0 auto",
    padding: 16,
    fontFamily: "system-ui, sans-serif",
  },
  form: {
    display: "flex",
    gap: 8,
  },
  input: {
    flex: 1,
    padding: "10px 12px",
    fontSize: 16,
    border: "1px solid #999",
    borderRadius: 4,
  },
  button: {
    padding: "10px 18px",
    fontSize: 16,
    border: "none",
    borderRadius: 4,
    backgroundColor: "#00529B", // Stats SA-ish blue
    color: "#fff",
    cursor: "pointer",
  },
  buttonDisabled: {
    backgroundColor: "#7a9cc0",
    cursor: "not-allowed",
  },
  errorBox: {
    marginTop: 16,
    padding: 12,
    borderRadius: 4,
    backgroundColor: "#fdecea",
    border: "1px solid #f5c6cb",
    color: "#611a15",
  },
  escalatedBox: {
    marginTop: 16,
    padding: 12,
    borderRadius: 4,
    backgroundColor: "#fff8e1",
    border: "1px solid #ffe0a3",
    color: "#4a3c00",
  },
  // The AI-generated answer is visually distinct from the sourced citations
  // block below it, per docs/02-architecture.md Section 1.1 ("Trusted
  // Responses and Source Transparency").
  answerBox: {
    marginTop: 16,
    padding: 12,
    borderRadius: 4,
    backgroundColor: "#f5f5f5",
    border: "1px dashed #999",
  },
  confidenceBadge: {
    display: "inline-block",
    marginTop: 8,
    padding: "2px 10px",
    borderRadius: 12,
    fontSize: 13,
    fontWeight: 600,
    backgroundColor: "#e0e0e0",
    color: "#333",
  },
  citationsBox: {
    marginTop: 12,
    padding: 12,
    borderRadius: 4,
    backgroundColor: "#eaf3ea",
    border: "1px solid #b7d8b7",
  },
  citationsHeading: {
    margin: "0 0 8px 0",
    fontSize: 13,
    fontWeight: 600,
    color: "#2f5d2f",
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
};

function ConfidenceBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  return <span style={styles.confidenceBadge}>Confidence: {pct}%</span>;
}

export default function PublicWidget() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PublicQueryResponse | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const text = query.trim();
    if (!text || loading) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await submitPublicQuery(text);
      setResult(data);
    } catch (err) {
      setError(
        "Sorry, something went wrong while getting an answer. Please try again shortly."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.container} id="statssa-public-query-widget">
      <form style={styles.form} onSubmit={handleSubmit}>
        <input
          style={styles.input}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question about Stats SA statistics"
          aria-label="Ask a question about Stats SA statistics"
          disabled={loading}
        />
        <button
          style={{
            ...styles.button,
            ...(loading || !query.trim() ? styles.buttonDisabled : {}),
          }}
          type="submit"
          disabled={loading || !query.trim()}
        >
          {loading ? "Asking..." : "Ask"}
        </button>
      </form>

      {loading && <p role="status">Looking that up…</p>}

      {error && <div style={styles.errorBox}>{error}</div>}

      {result && result.status === "escalated" && (
        <div style={styles.escalatedBox}>{result.message}</div>
      )}

      {result && result.status === "answered" && (
        <>
          <div style={styles.answerBox}>
            <p style={{ margin: 0 }}>{result.answer}</p>
            <ConfidenceBadge score={result.confidence_score} />
          </div>

          <div style={styles.citationsBox}>
            <p style={styles.citationsHeading}>Sources</p>
            {result.citations.length === 0 ? (
              <p style={{ margin: 0, fontSize: 13, color: "#555" }}>
                No sources were returned for this answer.
              </p>
            ) : (
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {result.citations.map((citation) => (
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
        </>
      )}
    </div>
  );
}
