// Types mirror the Python API responses. Keep these in sync with
// api/main.py and the store return shapes — any drift surfaces as a
// type error the next time we read a field that's moved.

export interface ResultConcept {
  id: string;
  name: string;
  is_novel: boolean;
}

// GET /feed list shape — slim, no heavy fields.
export interface FeedItem {
  id: string;
  created_at: string;
  file_path: string;
  summary: string;
  concepts: ResultConcept[];
}

// GET /feed/:id detail shape — full record with explanation, diff, snippet.
export interface Entry {
  id: string;
  created_at: string;
  session_id: string;
  file_path: string;
  language: string;
  origin: "typed" | "ai_generated";
  diff: string;
  code_snippet: string;
  summary: string;
  explanation: string;
  challenge_q: string | null;
  concepts: ResultConcept[];
}

// GET /concepts row shape (legacy concept-only list).
export interface Concept {
  id: string;
  name: string;
  confidence: number;
  seen_count: number;
  last_seen: string | null;
}

export interface ConceptSummary {
  id: string;
  name: string;
  confidence: number;
}

// GET /digest shape.
export interface Digest {
  date: string;
  session_count: number;
  files_touched: string[];
  new_concepts: ConceptSummary[];
  reinforced_concepts: ConceptSummary[];
  fading_concepts: ConceptSummary[];
  unanswered_challenges: number;
}

// POST /concepts/:id/respond shape — only what the spec returns.
export interface RespondResult {
  confidence: number;
  depth_level: number;
}
