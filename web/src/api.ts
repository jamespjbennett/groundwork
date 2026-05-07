import type {
  Concept,
  Digest,
  Entry,
  FeedItem,
  RespondResult,
} from "./types";

// All requests go to /api/* and Vite's dev proxy forwards them to the
// FastAPI server at :8000. Keeps the browser on the same origin.
const BASE = "/api";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new ApiError(res.status, `GET ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, `POST ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

function qs(params: object): string {
  const pairs = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null
  );
  if (pairs.length === 0) return "";
  const search = new URLSearchParams(pairs.map(([k, v]) => [k, String(v)]));
  return `?${search.toString()}`;
}

export interface FeedQuery {
  session_id?: string;
  concept_id?: string;
  limit?: number;
}

export const api = {
  feed: (q: FeedQuery = {}) =>
    get<{ entries: FeedItem[] }>(`/feed${qs(q)}`),

  entry: (id: string) => get<Entry>(`/feed/${encodeURIComponent(id)}`),

  concepts: () => get<{ concepts: Concept[] }>("/concepts"),

  digest: (date?: string) =>
    get<Digest>(`/digest${qs({ date })}`),

  respond: (conceptId: string, understood: boolean) =>
    post<RespondResult>(
      `/concepts/${encodeURIComponent(conceptId)}/respond`,
      { understood }
    ),
};
