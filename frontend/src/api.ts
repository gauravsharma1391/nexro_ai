export class ApiError extends Error {
  code: string;
  constructor(message: string, code = "error") {
    super(message);
    this.code = code;
  }
}
const OFFLINE = "Cannot reach the backend. Is it running on http://localhost:8000?";

async function check(res: Response) {
  if (res.ok) return res;
  let msg = `Request failed (${res.status})`, code = "error";
  try {
    const j = await res.json();
    if (j?.error) { msg = j.error.message; code = j.error.code; }
  } catch { /* not JSON */ }
  throw new ApiError(msg, code);
}

export async function api<T = any>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, ...rest } = init;
  let res: Response;
  try {
    res = await fetch(path, {
      ...rest,
      headers: json !== undefined ? { "Content-Type": "application/json", ...(rest.headers || {}) } : rest.headers,
      body: json !== undefined ? JSON.stringify(json) : rest.body,
    });
  } catch { throw new ApiError(OFFLINE, "offline"); }
  await check(res);
  return res.json();
}

export async function upload<T = any>(path: string, file: File, query = ""): Promise<T> {
  const fd = new FormData();
  fd.append("file", file);
  return api<T>(path + query, { method: "POST", body: fd });
}

export async function streamChat(
  body: object, signal: AbortSignal, onChunk: (t: string) => void, onStart: (cid: string) => void,
) {
  let res: Response;
  try {
    res = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal });
  } catch (e: any) {
    if (e?.name === "AbortError") throw e;
    throw new ApiError(OFFLINE, "offline");
  }
  await check(res);
  onStart(res.headers.get("X-Conversation-Id") || "");
  const reader = res.body!.getReader();
  const dec = new TextDecoder();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    onChunk(dec.decode(value, { stream: true }));
  }
}

export const fmtTime = (iso?: string) => (iso ? new Date(iso).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "");
