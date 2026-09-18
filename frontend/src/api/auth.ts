// Implements specs/011-frontend-shell-integration/spec.md item 2 ("role
// switcher for demo purposes — log in as any of the 4 seeded accounts").
//
// The 4 demo accounts and their fixed password mirror backend/app/db/seed.py
// exactly (specs/000/009) — this is a hackathon-only fixture, documented
// there as demo-only and never a real deployment pattern. Logging in for
// real always goes through POST /api/auth/login (specs/009,
// backend/app/api/auth.py); nothing here bypasses server-side auth.
import { apiFetch } from "./client";

export interface DemoAccount {
  role: string;
  label: string;
  email: string;
}

export const DEMO_ACCOUNTS: DemoAccount[] = [
  { role: "public", label: "Public", email: "public@demo.statssa.local" },
  { role: "media", label: "Media", email: "media@demo.statssa.local" },
  {
    role: "comms_official",
    label: "Communications Official",
    email: "official@demo.statssa.local",
  },
  {
    role: "curator_admin",
    label: "Curator Admin",
    email: "curator@demo.statssa.local",
  },
];

// Fixed password for all 4 seeded demo accounts — see backend/app/db/seed.py.
const DEMO_PASSWORD = "StatsSA-Demo-2026";

interface LoginResponse {
  access_token: string;
  token_type: string;
  role: string;
  user_id: string;
  name: string;
}

export interface LoggedInUser {
  user_id: string;
  role: string;
  name: string;
  token: string;
}

// Logs in as one of the 4 seeded demo accounts by calling the real
// POST /api/auth/login endpoint. Throws (via apiFetch) if `role` doesn't
// match a known demo account or the server rejects the login — callers
// should not swallow this.
export async function loginAs(role: string): Promise<LoggedInUser> {
  const account = DEMO_ACCOUNTS.find((a) => a.role === role);
  if (!account) {
    throw new Error(`Unknown demo role: ${role}`);
  }

  const response = (await apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email: account.email, password: DEMO_PASSWORD }),
  })) as LoginResponse;

  return {
    user_id: response.user_id,
    role: response.role,
    name: response.name,
    token: response.access_token,
  };
}
