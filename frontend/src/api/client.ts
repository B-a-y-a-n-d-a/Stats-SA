// Shared fetch wrapper. Feature branches import this instead of calling fetch()
// directly, so auth-header injection (specs/009) only needs to change in one place.
const BASE_URL = "/api";

export async function apiFetch(path: string, options: RequestInit = {}) {
  const token = localStorage.getItem("token");
  // FormData bodies (specs/008 file uploads) need the browser to set its own
  // multipart boundary in Content-Type, which only happens if Content-Type is
  // left unset here — so only default to JSON when the body isn't FormData.
  const isFormData = options.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json();
}
