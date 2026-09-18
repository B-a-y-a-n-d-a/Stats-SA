// Implements specs/011-frontend-shell-integration/spec.md item 2 (role
// switcher) — holds the logged-in demo user's identity for the whole app.
//
// This is a demo-UX convenience layer only. The real security boundary is
// server-side RBAC (specs/009): GET/POST /api/review/*, /api/curator/* and
// GET /api/audit all independently re-check the JWT's role on every request.
// Nothing client-side here grants or restricts API access — it just decides
// what the UI shows, and apiFetch (api/client.ts) already reads the token
// from localStorage["token"] regardless of what this context does.
import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { loginAs as apiLoginAs } from "../api/auth";

export interface AuthUser {
  user_id: string;
  role: string;
  name: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  loginAs: (role: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const TOKEN_KEY = "token";
const USER_KEY = "authUser";

function readStoredUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (
      parsed &&
      typeof parsed.user_id === "string" &&
      typeof parsed.role === "string" &&
      typeof parsed.name === "string"
    ) {
      return parsed as AuthUser;
    }
    return null;
  } catch {
    // localStorage can throw (private browsing, disabled storage) or hold
    // garbage from a previous app version — either way, just start logged out.
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);

  // Hydrate from localStorage on mount so a page refresh doesn't lose the
  // logged-in demo role.
  useEffect(() => {
    const stored = readStoredUser();
    let token: string | null = null;
    try {
      token = localStorage.getItem(TOKEN_KEY);
    } catch {
      token = null;
    }
    if (stored && token) {
      setUser(stored);
    }
  }, []);

  const loginAs = useCallback(async (role: string) => {
    const result = await apiLoginAs(role);
    const nextUser: AuthUser = {
      user_id: result.user_id,
      role: result.role,
      name: result.name,
    };
    try {
      localStorage.setItem(TOKEN_KEY, result.token);
      localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
    } catch {
      // If storage is unavailable, the login still succeeds for this
      // in-memory session — it just won't survive a refresh.
    }
    setUser(nextUser);
  }, []);

  const logout = useCallback(() => {
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    } catch {
      // Ignore — falling through to clear in-memory state either way.
    }
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loginAs, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
