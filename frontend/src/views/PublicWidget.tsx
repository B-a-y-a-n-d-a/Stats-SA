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
import { colors } from "../styles/theme";
import { shared } from "../styles/shared";

// --- Styling: shared design tokens (styles/theme.ts, styles/shared.ts) plus
// a few page-specific overrides below, per specs/011 item 3. Local values
// that differ from `shared` by a pixel/color are kept as explicit overrides
// so the rendered output is unchanged. ---

const styles: Record<string, CSSProperties> = {
  ...shared,
  container: shared.containerNarrow,
  form: {
    display: "flex",
    gap: 8,
  },
  input: {
    flex: 1,
    padding: "10px 12px",
    fontSize: 16,
    border: `1px solid ${colors.borderInput}`,
    borderRadius: 4,
  },
  button: {
    ...shared.button,
    padding: "10px 18px",
    fontSize: 16,
  },
  errorBox: {
    ...shared.errorBox,
    marginTop: 16,
  },
  // No shared equivalent by this name — same box as shared.warningBox, with
  // this view's original marginTop preserved.
  escalatedBox: {
    ...shared.warningBox,
    marginTop: 16,
  },
  // The AI-generated answer is visually distinct from the sourced citations
  // block below it, per docs/02-architecture.md Section 1.1 ("Trusted
  // Responses and Source Transparency"). No shared equivalent.
  answerBox: {
    marginTop: 16,
    padding: 12,
    borderRadius: 4,
    backgroundColor: colors.bgNeutral,
    border: "1px dashed #999",
  },
  confidenceBadge: {
    ...shared.confidenceBadge,
    marginTop: 8,
    fontSize: 13,
  },
  citationsHeading: {
    ...shared.citationsHeading,
    color: "#2f5d2f",
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
