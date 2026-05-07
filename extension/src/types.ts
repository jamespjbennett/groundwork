export interface ResultConcept {
  id: string;
  name: string;
  is_novel: boolean;
}

// Mirrors the slim response shape returned by POST /analyse.
// Heavy fields (explanation, code_snippet, diff, challenge_q) live
// in the database and are fetched via GET /feed/:id when the web UI needs them.
export interface AnalyseResult {
  skipped: boolean;
  reason?: string;
  entry_id?: string;
  summary?: string;
  concepts: ResultConcept[];
}
