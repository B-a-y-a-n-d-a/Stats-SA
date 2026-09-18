// Implements specs/011-frontend-shell-integration/spec.md item 1 (routing
// "gated by the logged-in demo role").
//
// This is a client-side UX convenience only, NOT the real access control —
// it just hides a route's UI when the demo operator is logged in as the
// wrong role, and offers the switcher right there to fix it. The actual
// security boundary is server-side (specs/009): the endpoints each of these
// views call re-check the JWT's role independently on every request, so even
// if this gate were bypassed entirely, an unauthorized call would still be
// rejected by the API.
import { ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";
import RoleSwitcher from "./RoleSwitcher";
import { shared } from "../styles/shared";
import { DEMO_ACCOUNTS } from "../api/auth";

interface RequireRoleProps {
  roles: string[];
  children: ReactNode;
}

export default function RequireRole({ roles, children }: RequireRoleProps) {
  const { user } = useAuth();

  if (user && roles.includes(user.role)) {
    return <>{children}</>;
  }

  const roleLabels = roles
    .map((role) => DEMO_ACCOUNTS.find((a) => a.role === role)?.label ?? role)
    .join(", ");

  return (
    <div style={shared.container}>
      <div style={shared.warningBox}>
        Log in as one of: {roleLabels} to view this.
      </div>
      <div style={{ marginTop: 12 }}>
        <RoleSwitcher />
      </div>
    </div>
  );
}
