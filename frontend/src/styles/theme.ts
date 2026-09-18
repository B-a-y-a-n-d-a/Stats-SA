// Implements specs/011-frontend-shell-integration/spec.md item 3 ("shared
// styling so the four views look like one product, not four prototypes
// stapled together"). Design tokens only — no CSSProperties objects here,
// see shared.ts for those. Values are lifted verbatim from the colors
// already duplicated across views/PublicWidget.tsx, ReviewConsole.tsx,
// AuditLog.tsx and CuratorAdmin.tsx, not new choices, so this is a
// deduplication, not a redesign.
export const colors = {
  primary: "#00529B", // Stats SA-ish blue, used by every view's main action button
  primaryDisabled: "#7a9cc0",
  danger: "#a12622",
  dangerDisabled: "#c98d8b",

  border: "#999",
  borderLight: "#ccc",
  borderInput: "#999",

  textDefault: "#333",
  textMuted: "#555",
  textFaint: "#666",
  textLabel: "#333",

  bgNeutral: "#f5f5f5",
  bgSubtle: "#fafafa",

  errorBg: "#fdecea",
  errorBorder: "#f5c6cb",
  errorText: "#611a15",

  successBg: "#eaf3ea",
  successBorder: "#b7d8b7",
  successText: "#1e4620",

  warningBg: "#fff8e1",
  warningBorder: "#ffe0a3",
  warningText: "#4a3c00",

  badgeNeutralBg: "#e0e0e0",
  badgeNeutralText: "#333",

  linkColor: "#0b5394",
} as const;

export const font = "system-ui, sans-serif";
