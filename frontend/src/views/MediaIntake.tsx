// Implements specs/005-media-query-draft/spec.md — branch feature/005-media-query-draft.
import { FormEvent, useState } from "react";
import { submitMediaQuery } from "../api/mediaQuery";

const EMPTY = { text: "", submitter_name: "", submitter_org: "", submitter_email: "" };

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
      <div>
        <h2>Media enquiry received</h2>
        <p>{confirmation}</p>
        <button onClick={() => setConfirmation(null)}>Submit another enquiry</button>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit}>
      <h2>Media enquiry</h2>
      <p>
        <label htmlFor="submitter_name">Your name</label>
        <br />
        <input {...field("submitter_name")} />
      </p>
      <p>
        <label htmlFor="submitter_org">Publication / organisation</label>
        <br />
        <input {...field("submitter_org")} />
      </p>
      <p>
        <label htmlFor="submitter_email">Email</label>
        <br />
        <input type="email" {...field("submitter_email")} />
      </p>
      <p>
        <label htmlFor="text">Your question</label>
        <br />
        <textarea rows={5} {...field("text")} />
      </p>
      {error && <p role="alert">{error}</p>}
      <button type="submit" disabled={submitting}>
        {submitting ? "Submitting..." : "Submit enquiry"}
      </button>
    </form>
  );
}
