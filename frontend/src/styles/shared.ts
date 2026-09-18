// Implements specs/011-frontend-shell-integration/spec.md item 3. Reusable
// CSSProperties fragments, deduplicated from the near-identical `styles`
// objects that views/PublicWidget.tsx, ReviewConsole.tsx, AuditLog.tsx and
// CuratorAdmin.tsx each defined independently.
//
// Usage pattern (keeps every existing view's JSX untouched — only the
// top-of-file `styles` object definition changes):
//
//   import { shared } from "../styles/shared";
//   const styles: Record<string, CSSProperties> = {
//     ...shared,
//     // page-specific additions/overrides only
//   };
//
// A view's own local key (e.g. `escalatedBox`) can alias a shared one
// (`escalatedBox: shared.warningBox`) when the view's JSX already refers to
// it by that name — no need to rename every `style={styles.x}` call site.
import { CSSProperties } from "react";
import { colors, font } from "./theme";

function pillBadge(bg: string, text: string, border?: string): CSSProperties {
  return {
    display: "inline-block",
    padding: "2px 10px",
    borderRadius: 12,
    fontSize: 12,
    fontWeight: 600,
    backgroundColor: bg,
    color: text,
    ...(border ? { border: `1px solid ${border}` } : {}),
    whiteSpace: "nowrap",
  };
}

export const shared: Record<string, CSSProperties> = {
  // --- layout ---
  container: {
    maxWidth: 960,
    margin: "0 auto",
    padding: 16,
    fontFamily: font,
  },
  containerNarrow: {
    maxWidth: 640,
    margin: "0 auto",
    padding: 16,
    fontFamily: font,
  },
  heading: {
    margin: "0 0 12px 0",
  },
  sectionHeading: {
    margin: "32px 0 4px 0",
  },
  sectionSubtext: {
    margin: "0 0 12px 0",
    fontSize: 13,
    color: colors.textMuted,
  },

  // --- buttons ---
  button: {
    padding: "9px 18px",
    fontSize: 14,
    border: "none",
    borderRadius: 4,
    backgroundColor: colors.primary,
    color: "#fff",
    cursor: "pointer",
  },
  buttonDisabled: {
    backgroundColor: colors.primaryDisabled,
    cursor: "not-allowed",
  },
  secondaryButton: {
    padding: "9px 18px",
    fontSize: 14,
    border: `1px solid ${colors.border}`,
    borderRadius: 4,
    backgroundColor: "#fff",
    color: colors.textDefault,
    cursor: "pointer",
  },
  dangerButton: {
    padding: "9px 18px",
    fontSize: 14,
    border: "none",
    borderRadius: 4,
    backgroundColor: colors.danger,
    color: "#fff",
    cursor: "pointer",
  },
  dangerButtonDisabled: {
    backgroundColor: colors.dangerDisabled,
    cursor: "not-allowed",
  },

  // --- status/notice boxes ---
  errorBox: {
    marginTop: 8,
    padding: 12,
    borderRadius: 4,
    backgroundColor: colors.errorBg,
    border: `1px solid ${colors.errorBorder}`,
    color: colors.errorText,
  },
  successBox: {
    marginTop: 8,
    padding: 12,
    borderRadius: 4,
    backgroundColor: colors.successBg,
    border: `1px solid ${colors.successBorder}`,
    color: colors.successText,
  },
  warningBox: {
    marginTop: 8,
    padding: 12,
    borderRadius: 4,
    backgroundColor: colors.warningBg,
    border: `1px solid ${colors.warningBorder}`,
    color: colors.warningText,
  },
  emptyBox: {
    marginTop: 8,
    padding: 12,
    borderRadius: 4,
    backgroundColor: colors.bgNeutral,
    border: "1px dashed #999",
    color: colors.textMuted,
  },

  // --- badges ---
  confidenceBadge: pillBadge(colors.badgeNeutralBg, colors.badgeNeutralText),

  // --- citations (PublicWidget + ReviewConsole render the same shape) ---
  citationsBox: {
    marginTop: 12,
    padding: 12,
    borderRadius: 4,
    backgroundColor: colors.successBg,
    border: `1px solid ${colors.successBorder}`,
  },
  citationsHeading: {
    margin: "0 0 8px 0",
    fontSize: 13,
    fontWeight: 600,
    color: colors.successText,
  },
  citationItem: {
    marginBottom: 6,
  },
  citationLink: {
    color: colors.linkColor,
  },
  citationQuote: {
    display: "block",
    fontSize: 13,
    color: colors.textMuted,
    marginTop: 2,
  },

  // --- form fields (AuditLog, CuratorAdmin, ReviewConsole's reject/edit panels) ---
  field: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  label: {
    fontSize: 12,
    fontWeight: 600,
    color: colors.textLabel,
  },
  input: {
    padding: "8px 10px",
    fontSize: 14,
    border: `1px solid ${colors.borderInput}`,
    borderRadius: 4,
  },
  textarea: {
    padding: "8px 10px",
    fontSize: 14,
    fontFamily: "inherit",
    border: `1px solid ${colors.borderInput}`,
    borderRadius: 4,
  },

  // --- tables (AuditLog, CuratorAdmin) ---
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
    backgroundColor: colors.bgNeutral,
    whiteSpace: "nowrap",
  },
  td: {
    padding: "8px 10px",
    borderBottom: "1px solid #eee",
    verticalAlign: "top",
  },
};

export { pillBadge };
