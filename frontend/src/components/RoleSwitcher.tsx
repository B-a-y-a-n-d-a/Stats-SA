// Implements specs/011-frontend-shell-integration/spec.md item 2 ("a role
// switcher for demo purposes — log in as any of the 4 seeded accounts").
// Every click calls the real POST /api/auth/login (via useAuth().loginAs,
// which goes through api/auth.ts) and stores the returned JWT — this is not
// a hardcoded bypass.
import { CSSProperties, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { DEMO_ACCOUNTS } from "../api/auth";
import { shared } from "../styles/shared";
import { colors } from "../styles/theme";

const wrap: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 8,
  flexWrap: "wrap",
  fontSize: 13,
};

const status: CSSProperties = {
  color: colors.textMuted,
  marginRight: 4,
  whiteSpace: "nowrap",
};

const smallButton: CSSProperties = {
  padding: "5px 10px",
  fontSize: 12,
};

const smallErrorBox: CSSProperties = {
  ...shared.errorBox,
  marginTop: 0,
  padding: "4px 8px",
  fontSize: 12,
};

export default function RoleSwitcher() {
  const { user, loginAs } = useAuth();
  const [pendingRole, setPendingRole] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSwitch(role: string) {
    setPendingRole(role);
    setError(null);
    try {
      await loginAs(role);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setPendingRole(null);
    }
  }

  return (
    <div style={wrap}>
      <span style={status}>
        {user ? `Logged in as: ${user.name} (${user.role})` : "Not logged in"}
      </span>
      {DEMO_ACCOUNTS.map((account) => {
        const isActive = user?.role === account.role;
        const isPending = pendingRole === account.role;
        const buttonStyle: CSSProperties = {
          ...smallButton,
          ...(isActive ? shared.button : shared.secondaryButton),
          ...(isPending ? shared.buttonDisabled : {}),
        };
        return (
          <button
            key={account.role}
            type="button"
            style={buttonStyle}
            disabled={pendingRole !== null}
            onClick={() => handleSwitch(account.role)}
          >
            {isPending ? "Logging in..." : account.label}
          </button>
        );
      })}
      {error && <span style={smallErrorBox}>{error}</span>}
    </div>
  );
}
