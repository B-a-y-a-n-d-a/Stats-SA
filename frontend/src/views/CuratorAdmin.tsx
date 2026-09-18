// Implements specs/008-curator-admin/spec.md — branch feature/008-curator-admin.
//
// Curator-Admin console: the only role that can change what the assistant is
// allowed to know. Two independent sections — Sources (upload/list/retire,
// GET|POST|DELETE /api/curator/sources) and Terminology (add/list,
// GET|POST /api/curator/terminology). See api/curator.ts for the exact
// contract this view calls — built concurrently on the backend side of this
// same branch.
import { useEffect, useState, FormEvent, CSSProperties } from "react";
import {
  fetchSources,
  uploadSource,
  retireSource,
  fetchTerminology,
  createTerminologyEntry,
  Source,
  TerminologyEntry,
  SourceCategory,
  TerminologyCategory,
} from "../api/curator";
import { shared, pillBadge } from "../styles/shared";
import { colors } from "../styles/theme";

const SOURCE_CATEGORIES: SourceCategory[] = [
  "Statistical Release",
  "Publication",
  "Press Statement",
  "FAQ",
  "Historical Communication",
];

const TERMINOLOGY_CATEGORIES: TerminologyCategory[] = [
  "Terminology",
  "Style Rule",
  "Branding Standard",
  "Preferred Phrasing",
  "Prohibited Term",
];

// --- Shared cross-view styling lives in ../styles/shared.ts and
// ../styles/theme.ts (specs/011-frontend-shell-integration item 3). Only
// this view's page-specific styles (and any local override that differs
// from the shared value — kept after the `...shared` spread so it wins)
// are defined below. ---
const styles: Record<string, CSSProperties> = {
  ...shared,
  // Visually identical to shared.warningBox plus fontWeight: 600, but this
  // view's original box used marginBottom (not shared's marginTop) and a
  // fontSize — override both explicitly so the layout doesn't shift.
  noticeBox: {
    ...shared.warningBox,
    marginTop: 0,
    marginBottom: 16,
    fontSize: 14,
    fontWeight: 600,
  },
  form: {
    display: "flex",
    flexWrap: "wrap",
    gap: 12,
    alignItems: "flex-end",
    marginBottom: 12,
    padding: 12,
    border: "1px solid #ddd",
    borderRadius: 4,
    backgroundColor: "#fafafa",
  },
  hint: {
    fontSize: 11,
    color: "#666",
    maxWidth: 220,
  },
  // shared.textarea matches except this view's textareas also set a min
  // size — keep that on top of the shared base.
  textarea: {
    ...shared.textarea,
    minWidth: 240,
    minHeight: 60,
  },
  // shared.dangerButton matches this view's colors/border/radius but this
  // button is smaller (6px/12px, 13px font) — override those two.
  retireButton: {
    ...shared.dangerButton,
    padding: "6px 12px",
    fontSize: 13,
  },
  // Exact match to shared.dangerButtonDisabled.
  retireButtonDisabled: shared.dangerButtonDisabled,
  // shared.errorBox/successBox match except this view also sets
  // marginBottom — keep it on top of the shared base.
  errorBox: {
    ...shared.errorBox,
    marginBottom: 8,
  },
  successBox: {
    ...shared.successBox,
    marginBottom: 8,
  },
  badgeCurrent: pillBadge(colors.successBg, colors.successText, colors.successBorder),
  badgeSuperseded: pillBadge(colors.badgeNeutralBg, colors.badgeNeutralText),
  badgeRetired: pillBadge(colors.errorBg, colors.errorText, colors.errorBorder),
};

type SourceStatus = "Current" | "Superseded" | "Retired";
type TermStatus = "Current" | "Superseded";

function sourceStatus(source: Source): SourceStatus {
  if (source.retired_at) return "Retired";
  if (source.superseded_by) return "Superseded";
  return "Current";
}

function termStatus(entry: TerminologyEntry): TermStatus {
  return entry.superseded_by ? "Superseded" : "Current";
}

function StatusBadge({ status }: { status: SourceStatus | TermStatus }) {
  if (status === "Retired") return <span style={styles.badgeRetired}>Retired</span>;
  if (status === "Superseded") return <span style={styles.badgeSuperseded}>Superseded</span>;
  return <span style={styles.badgeCurrent}>Current</span>;
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (isNaN(d.getTime())) return value;
  return d.toLocaleDateString();
}

const EMPTY_SOURCE_FORM = {
  title: "",
  url: "",
  category: SOURCE_CATEGORIES[0] as string,
  published_date: "",
};

const EMPTY_TERM_FORM = {
  category: TERMINOLOGY_CATEGORIES[0] as string,
  term_or_topic: "",
  approved_guidance: "",
  discouraged_alternative: "",
  rationale: "",
  effective_date: "",
};

export default function CuratorAdmin() {
  // --- Sources section state ---
  const [sources, setSources] = useState<Source[]>([]);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [sourcesError, setSourcesError] = useState<string | null>(null);

  const [sourceForm, setSourceForm] = useState(EMPTY_SOURCE_FORM);
  const [sourceFile, setSourceFile] = useState<File | null>(null);
  const [sourceFileInputKey, setSourceFileInputKey] = useState(0);
  const [uploadSubmitting, setUploadSubmitting] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [retiringId, setRetiringId] = useState<string | null>(null);

  // --- Terminology section state ---
  const [terms, setTerms] = useState<TerminologyEntry[]>([]);
  const [termsLoading, setTermsLoading] = useState(true);
  const [termsError, setTermsError] = useState<string | null>(null);

  const [termForm, setTermForm] = useState(EMPTY_TERM_FORM);
  const [termSubmitting, setTermSubmitting] = useState(false);
  const [termError, setTermError] = useState<string | null>(null);
  const [termSuccess, setTermSuccess] = useState<string | null>(null);

  async function loadSources() {
    setSourcesLoading(true);
    setSourcesError(null);
    try {
      const data = await fetchSources();
      setSources(data);
    } catch (err) {
      setSourcesError(
        "Sorry, something went wrong while loading sources. Please try again shortly."
      );
      setSources([]);
    } finally {
      setSourcesLoading(false);
    }
  }

  async function loadTerms() {
    setTermsLoading(true);
    setTermsError(null);
    try {
      const data = await fetchTerminology();
      setTerms(data);
    } catch (err) {
      setTermsError(
        "Sorry, something went wrong while loading the terminology guide. Please try again shortly."
      );
      setTerms([]);
    } finally {
      setTermsLoading(false);
    }
  }

  useEffect(() => {
    loadSources();
    loadTerms();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleUploadSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (uploadSubmitting) return;
    setUploadSubmitting(true);
    setUploadError(null);
    setUploadSuccess(null);
    try {
      const result = await uploadSource({
        title: sourceForm.title.trim(),
        url: sourceForm.url.trim(),
        category: sourceForm.category,
        published_date: sourceForm.published_date,
        file: sourceFile,
      });
      setUploadSuccess(`Uploaded "${result.title}" as version ${result.version}.`);
      setSourceForm(EMPTY_SOURCE_FORM);
      setSourceFile(null);
      setSourceFileInputKey((k) => k + 1);
      await loadSources();
    } catch (err) {
      setUploadError(
        err instanceof Error ? err.message : "Something went wrong uploading this source."
      );
    } finally {
      setUploadSubmitting(false);
    }
  }

  async function handleRetire(source: Source) {
    if (
      !window.confirm(
        `Retire "${source.title}"? It will no longer be retrievable by the assistant.`
      )
    ) {
      return;
    }
    setRetiringId(source.source_id);
    setSourcesError(null);
    try {
      await retireSource(source.source_id);
      await loadSources();
    } catch (err) {
      setSourcesError(
        err instanceof Error ? err.message : "Something went wrong retiring this source."
      );
    } finally {
      setRetiringId(null);
    }
  }

  async function handleTermSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (termSubmitting) return;
    setTermSubmitting(true);
    setTermError(null);
    setTermSuccess(null);
    try {
      const created = await createTerminologyEntry({
        category: termForm.category,
        term_or_topic: termForm.term_or_topic.trim(),
        approved_guidance: termForm.approved_guidance.trim(),
        discouraged_alternative: termForm.discouraged_alternative.trim() || undefined,
        rationale: termForm.rationale.trim(),
        effective_date: termForm.effective_date || undefined,
      });
      setTermSuccess(`Saved guidance for "${created.term_or_topic}".`);
      setTermForm(EMPTY_TERM_FORM);
      await loadTerms();
    } catch (err) {
      setTermError(
        err instanceof Error ? err.message : "Something went wrong saving this entry."
      );
    } finally {
      setTermSubmitting(false);
    }
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.heading}>Curator Admin</h2>

      {/* --- Sources section --- */}
      <h3 style={styles.sectionHeading}>Sources</h3>
      <p style={styles.sectionSubtext}>
        Upload a PDF, or leave the file blank and the URL below will be fetched
        server-side as the PDF. Re-uploading the same source creates a new
        version rather than overwriting the old one.
      </p>

      <form style={styles.form} onSubmit={handleUploadSubmit}>
        <div style={styles.field}>
          <label style={styles.label} htmlFor="source-title">
            Title
          </label>
          <input
            id="source-title"
            style={styles.input}
            type="text"
            value={sourceForm.title}
            onChange={(e) => setSourceForm({ ...sourceForm, title: e.target.value })}
            required
            disabled={uploadSubmitting}
          />
        </div>
        <div style={styles.field}>
          <label style={styles.label} htmlFor="source-url">
            URL
          </label>
          <input
            id="source-url"
            style={styles.input}
            type="url"
            value={sourceForm.url}
            onChange={(e) => setSourceForm({ ...sourceForm, url: e.target.value })}
            placeholder="https://..."
            required
            disabled={uploadSubmitting}
          />
        </div>
        <div style={styles.field}>
          <label style={styles.label} htmlFor="source-category">
            Category
          </label>
          <select
            id="source-category"
            style={styles.input}
            value={sourceForm.category}
            onChange={(e) => setSourceForm({ ...sourceForm, category: e.target.value })}
            disabled={uploadSubmitting}
          >
            {SOURCE_CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>
        <div style={styles.field}>
          <label style={styles.label} htmlFor="source-published-date">
            Published date
          </label>
          <input
            id="source-published-date"
            style={styles.input}
            type="date"
            value={sourceForm.published_date}
            onChange={(e) => setSourceForm({ ...sourceForm, published_date: e.target.value })}
            required
            disabled={uploadSubmitting}
          />
        </div>
        <div style={styles.field}>
          <label style={styles.label} htmlFor="source-file">
            PDF file (optional)
          </label>
          <input
            key={sourceFileInputKey}
            id="source-file"
            type="file"
            accept="application/pdf"
            onChange={(e) => setSourceFile(e.target.files?.[0] ?? null)}
            disabled={uploadSubmitting}
          />
          <span style={styles.hint}>
            If no file is chosen, the URL above is fetched as the PDF.
          </span>
        </div>
        <button
          style={{ ...styles.button, ...(uploadSubmitting ? styles.buttonDisabled : {}) }}
          type="submit"
          disabled={uploadSubmitting}
        >
          {uploadSubmitting ? "Uploading…" : "Upload source"}
        </button>
      </form>

      {uploadError && <div style={styles.errorBox}>{uploadError}</div>}
      {uploadSuccess && <div style={styles.successBox}>{uploadSuccess}</div>}

      {sourcesLoading && <p role="status">Loading sources…</p>}
      {sourcesError && <div style={styles.errorBox}>{sourcesError}</div>}
      {!sourcesLoading && !sourcesError && sources.length === 0 && (
        <div style={styles.emptyBox}>No sources yet.</div>
      )}
      {!sourcesLoading && !sourcesError && sources.length > 0 && (
        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Title</th>
                <th style={styles.th}>Category</th>
                <th style={styles.th}>Version</th>
                <th style={styles.th}>Status</th>
                <th style={styles.th}>Published</th>
                <th style={styles.th}>Ingested</th>
                <th style={styles.th}>Action</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source) => {
                const status = sourceStatus(source);
                const retireDisabled = status !== "Current" || retiringId === source.source_id;
                return (
                  <tr key={source.source_id}>
                    <td style={styles.td}>{source.title}</td>
                    <td style={styles.td}>{source.category}</td>
                    <td style={styles.td}>{source.version}</td>
                    <td style={styles.td}>
                      <StatusBadge status={status} />
                    </td>
                    <td style={styles.td}>{formatDate(source.published_date)}</td>
                    <td style={styles.td}>{formatDate(source.ingested_date)}</td>
                    <td style={styles.td}>
                      {status === "Current" && (
                        <button
                          style={{
                            ...styles.retireButton,
                            ...(retireDisabled ? styles.retireButtonDisabled : {}),
                          }}
                          disabled={retireDisabled}
                          onClick={() => handleRetire(source)}
                        >
                          {retiringId === source.source_id ? "Retiring…" : "Retire"}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* --- Terminology section --- */}
      <h3 style={styles.sectionHeading}>Terminology Guide</h3>

      <div style={styles.noticeBox}>
        Entries here are authored by a single Curator-Admin. Dual-control
        approval by a Communications Official is planned but not yet enforced
        in this MVP — do not treat an entry as fully governed guidance yet.
      </div>

      <form style={styles.form} onSubmit={handleTermSubmit}>
        <div style={styles.field}>
          <label style={styles.label} htmlFor="term-category">
            Category
          </label>
          <select
            id="term-category"
            style={styles.input}
            value={termForm.category}
            onChange={(e) => setTermForm({ ...termForm, category: e.target.value })}
            disabled={termSubmitting}
          >
            {TERMINOLOGY_CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>
        <div style={styles.field}>
          <label style={styles.label} htmlFor="term-term">
            Term / topic
          </label>
          <input
            id="term-term"
            style={styles.input}
            type="text"
            value={termForm.term_or_topic}
            onChange={(e) => setTermForm({ ...termForm, term_or_topic: e.target.value })}
            required
            disabled={termSubmitting}
          />
        </div>
        <div style={styles.field}>
          <label style={styles.label} htmlFor="term-guidance">
            Approved guidance
          </label>
          <textarea
            id="term-guidance"
            style={styles.textarea}
            value={termForm.approved_guidance}
            onChange={(e) => setTermForm({ ...termForm, approved_guidance: e.target.value })}
            required
            disabled={termSubmitting}
          />
        </div>
        <div style={styles.field}>
          <label style={styles.label} htmlFor="term-discouraged">
            Discouraged alternative (optional)
          </label>
          <input
            id="term-discouraged"
            style={styles.input}
            type="text"
            value={termForm.discouraged_alternative}
            onChange={(e) =>
              setTermForm({ ...termForm, discouraged_alternative: e.target.value })
            }
            disabled={termSubmitting}
          />
        </div>
        <div style={styles.field}>
          <label style={styles.label} htmlFor="term-rationale">
            Rationale
          </label>
          <textarea
            id="term-rationale"
            style={styles.textarea}
            value={termForm.rationale}
            onChange={(e) => setTermForm({ ...termForm, rationale: e.target.value })}
            required
            disabled={termSubmitting}
          />
        </div>
        <div style={styles.field}>
          <label style={styles.label} htmlFor="term-effective-date">
            Effective date (optional)
          </label>
          <input
            id="term-effective-date"
            style={styles.input}
            type="date"
            value={termForm.effective_date}
            onChange={(e) => setTermForm({ ...termForm, effective_date: e.target.value })}
            disabled={termSubmitting}
          />
          <span style={styles.hint}>Leave blank to default to today.</span>
        </div>
        <button
          style={{ ...styles.button, ...(termSubmitting ? styles.buttonDisabled : {}) }}
          type="submit"
          disabled={termSubmitting}
        >
          {termSubmitting ? "Saving…" : "Add entry"}
        </button>
      </form>

      {termError && <div style={styles.errorBox}>{termError}</div>}
      {termSuccess && <div style={styles.successBox}>{termSuccess}</div>}

      {termsLoading && <p role="status">Loading terminology guide…</p>}
      {termsError && <div style={styles.errorBox}>{termsError}</div>}
      {!termsLoading && !termsError && terms.length === 0 && (
        <div style={styles.emptyBox}>No terminology entries yet.</div>
      )}
      {!termsLoading && !termsError && terms.length > 0 && (
        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Term / topic</th>
                <th style={styles.th}>Category</th>
                <th style={styles.th}>Approved guidance</th>
                <th style={styles.th}>Version</th>
                <th style={styles.th}>Status</th>
              </tr>
            </thead>
            <tbody>
              {terms.map((entry) => (
                <tr key={entry.guide_entry_id}>
                  <td style={styles.td}>{entry.term_or_topic}</td>
                  <td style={styles.td}>{entry.category}</td>
                  <td style={styles.td}>{entry.approved_guidance}</td>
                  <td style={styles.td}>{entry.version}</td>
                  <td style={styles.td}>
                    <StatusBadge status={termStatus(entry)} />
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
