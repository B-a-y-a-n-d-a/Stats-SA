// Implements specs/005-media-query-draft/spec.md — branch feature/005-media-query-draft.
// Visual/markup styling per specs/011-frontend-shell-integration/spec.md item
// 3 — reuses the shared design tokens (styles/theme.ts, styles/shared.ts) so
// this view looks like the same product as PublicWidget.tsx and AuditLog.tsx
// instead of an unstyled form stapled on. Pure visual/markup change: the
// controlled fields, submission logic and confirmation-screen behavior below
// are unchanged from the original.
import { FormEvent, useState, CSSProperties } from "react";
import { submitMediaQuery } from "../api/mediaQuery";
import { shared } from "../styles/shared";

const EMPTY = { text: "", submitter_name: "", submitter_org: "", submitter_email: "" };

const styles: Record<string, CSSProperties> = {
  ...shared,
  container: shared.containerNarrow,
  // No shared equivalent — this view's fields stack vertically, unlike
  // PublicWidget's single-row query form.
  form: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
};

export default function MediaIntake() {
  const [form, setForm] = useState(EMPTY);
  const [submitting, setSubmitting] = useState(false);
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const field = (name: keyof typeof EMPTY) => ({
    id: name,
    value: form[name],
    onChange: (e: { target: { value: string } }) => setForm({ ...form, [name]: e.target.value }),
    required: true,
  });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      // Only the confirmation is ever shown — the draft goes to the Review
      // Console (specs/006), never back to the enquirer.
      const receipt = await submitMediaQuery(form);
      setConfirmation(receipt.message);
      setForm(EMPTY);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (confirmation) {
    return (
      <div style={styles.container}>
        <h2 style={styles.heading}>Media enquiry received</h2>
        <p>{confirmation}</p>
        <button style={styles.button} onClick={() => setConfirmation(null)}>
          Submit another enquiry
        </button>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.heading}>Media enquiry</h2>
      <form style={styles.form} onSubmit={onSubmit}>
        <div style={styles.field}>
          <label style={styles.label} htmlFor="submitter_name">
            Your name
          </label>
          <input style={styles.input} {...field("submitter_name")} />
        </div>
        <div style={styles.field}>
          <label style={styles.label} htmlFor="submitter_org">
            Publication / organisation
          </label>
          <input style={styles.input} {...field("submitter_org")} />
        </div>
        <div style={styles.field}>
          <label style={styles.label} htmlFor="submitter_email">
            Email
          </label>
          <input style={styles.input} type="email" {...field("submitter_email")} />
        </div>
        <div style={styles.field}>
          <label style={styles.label} htmlFor="text">
            Your question
          </label>
          <textarea style={styles.textarea} rows={5} {...field("text")} />
        </div>
        {error && (
          <div style={styles.errorBox} role="alert">
            {error}
          </div>
        )}
        <button
          style={{ ...styles.button, ...(submitting ? styles.buttonDisabled : {}) }}
          type="submit"
          disabled={submitting}
        >
          {submitting ? "Submitting..." : "Submit enquiry"}
        </button>
      </form>
    </div>
  );
}
