import { CSSProperties } from "react";
import { Routes, Route, Link, useLocation } from "react-router-dom";
import PublicWidget from "./views/PublicWidget";
import MediaIntake from "./views/MediaIntake";
import ReviewConsole from "./views/ReviewConsole";
import CuratorAdmin from "./views/CuratorAdmin";
import AuditLog from "./views/AuditLog";
import { AuthProvider } from "./auth/AuthContext";
import RequireRole from "./components/RequireRole";
import RoleSwitcher from "./components/RoleSwitcher";
import { colors, font } from "./styles/theme";

// Implements specs/011-frontend-shell-integration/spec.md items 1-2: wires
// the 5 individually-built views into one app with shared nav/styling, a
// role switcher, and role-gated routing that mirrors the real server-side
// RBAC (specs/009) so the demo UI never claims access the API wouldn't
// actually grant. /review requires comms_official, /curator and /audit
// require curator_admin (audit also allows comms_official) — / and /media
// stay open, matching that both query endpoints accept unauthenticated
// submissions.
const navBar: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  flexWrap: "wrap",
  gap: 12,
  padding: "10px 20px",
  backgroundColor: colors.primary,
  fontFamily: font,
};

const navLinks: CSSProperties = {
  display: "flex",
  gap: 4,
  flexWrap: "wrap",
};

const navLink: CSSProperties = {
  color: "#fff",
  textDecoration: "none",
  padding: "6px 12px",
  borderRadius: 4,
  fontSize: 14,
};

const navLinkActive: CSSProperties = {
  backgroundColor: "rgba(255, 255, 255, 0.2)",
  fontWeight: 600,
};

// RoleSwitcher is styled for a light background (it's reused as-is inside
// RequireRole's warning box), so on the dark nav bar it sits in its own
// light pill rather than directly on colors.primary.
const roleSwitcherWrap: CSSProperties = {
  backgroundColor: "#fff",
  borderRadius: 6,
  padding: "6px 10px",
};

const NAV_ITEMS = [
  { to: "/", label: "Public" },
  { to: "/media", label: "Media" },
  { to: "/review", label: "Review" },
  { to: "/curator", label: "Curator Admin" },
  { to: "/audit", label: "Audit Log" },
];

function NavBar() {
  const location = useLocation();
  return (
    <nav style={navBar}>
      <div style={navLinks}>
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            style={{
              ...navLink,
              ...(location.pathname === item.to ? navLinkActive : {}),
            }}
          >
            {item.label}
          </Link>
        ))}
      </div>
      <div style={roleSwitcherWrap}>
        <RoleSwitcher />
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <div>
        <NavBar />
        <Routes>
          <Route path="/" element={<PublicWidget />} />
          <Route path="/media" element={<MediaIntake />} />
          <Route
            path="/review"
            element={
              <RequireRole roles={["comms_official"]}>
                <ReviewConsole />
              </RequireRole>
            }
          />
          <Route
            path="/curator"
            element={
              <RequireRole roles={["curator_admin"]}>
                <CuratorAdmin />
              </RequireRole>
            }
          />
          <Route
            path="/audit"
            element={
              <RequireRole roles={["comms_official", "curator_admin"]}>
                <AuditLog />
              </RequireRole>
            }
          />
        </Routes>
      </div>
    </AuthProvider>
  );
}
