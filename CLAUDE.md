# Groundwork — CLAUDE.md

> This file is the authoritative reference for building Groundwork. Read it before writing any code.
> Update it whenever a significant decision changes.

---

## What is Groundwork?

Groundwork is a developer learning tool that silently observes your coding sessions and builds a rich, queryable record of everything you've built and every concept you've encountered. At any point — mid-session or end of day — you open the Groundwork web UI to review what you wrote, understand why it works, and see what you've been learning over time.

**The problem it solves:** AI coding tools help developers ship faster but create a gap between what you can produce and what you actually understand. Paste a Claude-generated snippet, ship the feature, learn nothing. Groundwork closes that gap — by capturing context *as it happens* and presenting it back to you on your terms, without interrupting flow.

**The design philosophy (v2):**

The original design surfaced explanations inline in the editor after every save. This was too intrusive — it interrupted flow and felt like a teacher tapping your shoulder mid-thought. The right model is closer to a **coding journal with understanding baked in**: it records everything silently, and you come to *it* when you're ready. Think less "push notification", more "daily newspaper you actually want to read."

**The core loop:**
1. You write or paste code in your editor (Cursor, VS Code)
2. The extension silently sends each meaningful change to the API — no UI interruption whatsoever
3. The API extracts concepts, generates a full contextual explanation, stores everything against the change
4. You open the Groundwork web UI whenever you want — mid-session or end of day
5. You see a feed of your changes: what you wrote, what concepts they introduced, explanations in context
6. Your knowledge model updates as you mark concepts understood — depth adjusts next session

---

## Current State (v0.2)

**What is working:**
- FastAPI backend running locally
- VS Code / Cursor extension detects file saves and sends diffs to the API
- API identifies a concept and returns a basic explanation
- Extension writes output to a file

**What is wrong and needs fixing:**
- The extension interrupts flow — any in-editor popup must be removed entirely
- The DB stores almost nothing: just concept name, confidence, last seen. Useless for recall
- There is no web UI — output goes to a file nobody reads
- Explanations describe a concept in isolation, not *why it appeared in your specific code*

**The next phase focuses on:** richer data storage, a standalone web UI, removing all intrusive editor UI.

---

## Architecture Overview

```
┌───────────────────────────────────────────────────────────────┐
│                       CLIENT SURFACES                         │
│                                                               │
│   VS Code / Cursor Extension         Web UI (localhost:3000)  │
│   (TypeScript — silent sender only)  (React — the main UI)    │
└─────────────────────┬────────────────────────┬────────────────┘
                      │ POST on save            │ GET / polling
                      ▼                        ▼
┌───────────────────────────────────────────────────────────────┐
│                   PYTHON API  (FastAPI :8000)                 │
│                                                               │
│  POST /analyse              — receives diff, stores entry     │
│  GET  /feed                 — paginated entries for web UI    │
│  GET  /feed/:id             — single entry with full detail   │
│  GET  /concepts             — full knowledge graph            │
│  POST /concepts/:id/respond — mark understood / not yet       │
│  GET  /digest               — today's summary stats           │
└──────────────────────┬────────────────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────────────────┐
│                          SQLite DB                            │
│                                                               │
│   entries         — one row per meaningful code change        │
│   concepts        — knowledge graph (confidence, recency)     │
│   entry_concepts  — join table linking entries to concepts    │
└───────────────────────────────────────────────────────────────┘
```

**Key architectural principle:** The extension is dumb and passive. It sends a diff and does nothing else. All intelligence and all UI lives in the API and the web app. The extension should be completely invisible during normal coding.

---

## The Data Model

This is the most important thing to get right. The original schema stored almost nothing useful. The new schema stores enough to make the web UI genuinely valuable for recall.

### `entries` table
One row per analysed code change. The core record.

```sql
CREATE TABLE entries (
  id            TEXT PRIMARY KEY,      -- uuid4
  created_at    DATETIME DEFAULT (datetime('now')),
  session_id    TEXT NOT NULL,         -- groups changes within one working session
  file_path     TEXT NOT NULL,         -- e.g. "api/concept_extractor.py"
  language      TEXT NOT NULL,         -- "python", "typescript" etc
  origin        TEXT NOT NULL,         -- "typed" | "ai_generated"
  diff          TEXT NOT NULL,         -- raw unified diff
  code_snippet  TEXT NOT NULL,         -- the new/changed code block (not whole file)
  summary       TEXT NOT NULL,         -- one sentence: what this change does
  explanation   TEXT NOT NULL,         -- full explanation, written in context of this code
  challenge_q   TEXT                   -- one challenge question, or null
);
```

**Why `summary` and `explanation` are separate:** The feed shows `summary` as the headline — one line per entry, scannable. You expand an entry to read `explanation`. This mirrors how a commit message relates to a diff.

**Why `session_id`:** Groups all changes in one sitting. The digest can then say "in this session you touched 6 files and encountered 4 new concepts." A new session starts after 30 minutes of inactivity.

### `concepts` table

```sql
CREATE TABLE concepts (
  id            TEXT PRIMARY KEY,      -- matches taxonomy id e.g. "decorator"
  name          TEXT NOT NULL,
  first_seen    DATETIME,
  last_seen     DATETIME,
  seen_count    INTEGER DEFAULT 0,
  confidence    REAL DEFAULT 0.0,      -- 0.0 (never seen) to 1.0 (solid)
  depth_level   INTEGER DEFAULT 1      -- 1 beginner / 2 intermediate / 3 advanced
);
```

### `entry_concepts` join table

```sql
CREATE TABLE entry_concepts (
  entry_id      TEXT REFERENCES entries(id),
  concept_id    TEXT REFERENCES concepts(id),
  is_novel      BOOLEAN,              -- was this concept new at time of this entry?
  PRIMARY KEY (entry_id, concept_id)
);
```

**Why this join table matters:** You can now query "every change where I first encountered a decorator" or filter the feed by concept. This is what makes the Concepts view useful — clicking a concept shows every time it appeared in your code.

---

## Services and Responsibilities

### Service 1 — Python API (FastAPI) ✅ Exists — needs schema and prompt upgrade

**What needs to change:**

Upgrade the DB schema to the three-table model above. The `/analyse` endpoint must now write a full `entry` row. Claude must be prompted to return structured JSON with `summary`, `explanation`, and `challenge_q` as separate fields. Add `GET /feed`, `GET /feed/:id`, and `GET /digest` endpoints.

**Updated `/analyse` endpoint:**
```
POST /analyse
  Body: {
    code:        str,   -- the new/changed code
    diff:        str,   -- unified diff
    file_path:   str,
    language:    str,
    origin:      "typed" | "ai_generated",
    session_id:  str
  }
  Returns: {
    entry_id:    str,
    concepts:    [{ id, name, is_novel }],
    summary:     str,
    skipped:     bool   -- true if no novel concepts detected
  }
```

Note: the extension does not receive the full explanation. That lives in the DB and is fetched by the web UI. The extension only needs confirmation the call succeeded.

**Claude prompt structure:**

The prompt must instruct Claude to return a JSON object with exactly these fields:

```
{
  "summary": "One sentence describing what this specific code change does — not what the concept is, but what this code accomplishes",
  "explanation": "2-4 paragraphs explaining the novel concept(s) in the context of the actual code snippet. Reference the specific variable names, patterns, and choices in the submitted code. Explain not just what the concept is but why it was used here and what it achieves.",
  "challenge_q": "One specific, testable question about the code just written. Should have a concrete answer the developer can verify."
}
```

Always include the actual `code_snippet`, `file_path`, and the user's current `depth_level` in the prompt so explanations are contextual, not generic.

**New endpoints:**
```
GET /feed?session_id=&limit=50
  Returns: [{ id, created_at, file_path, summary, concepts: [{id, name, is_novel}] }]

GET /feed/:id
  Returns: full entry including explanation, code_snippet, challenge_q, diff

GET /digest?date=2026-05-07
  Returns: {
    session_count: int,
    files_touched: [str],
    new_concepts: [concept],
    reinforced_concepts: [concept],
    fading_concepts: [concept],    -- confidence < 0.6, last_seen > 7 days
    unanswered_challenges: int
  }

POST /concepts/:id/respond
  Body: { understood: bool }
  Returns: { confidence: float, depth_level: int }
```

**Internal modules:**

`concept_extractor.py` — AST parsing. No changes needed if working correctly.

`knowledge_graph.py` — Rewrite to handle three-table schema. Methods: `is_novel(concept_id)`, `record_entry(entry)`, `update_confidence(concept_id, understood)`, `get_feed(session_id, limit)`, `get_entry(id)`, `get_digest(date)`.

`explainer.py` — Update prompt to request structured JSON. Always include the actual code snippet and file path. Parse the JSON response and validate it has all required fields before storing.

`session_manager.py` — New. Tracks session IDs and last-seen timestamps. If last activity > 30 minutes ago, issue a new session ID. The extension generates a session ID on activation and passes it with every request — the API records it as-is.

---

### Service 2 — Web UI (React) 🆕 Build this next

**The main user-facing product. This is where Groundwork becomes useful.**

**Stack:** React + TypeScript, Vite, served from `localhost:3000`. No framework (Next.js etc.) needed — it's a single-page app talking to a local API.

**This is not a VS Code webview panel.** It's a standalone app running in a browser tab. You open it alongside your editor and leave it open. It polls for updates automatically.

**Three views:**

**1. Feed (default)**

Reverse-chronological list of entries from the current session. Each entry card shows:
- File name and time
- Summary (one sentence)
- Concept badges — new concepts highlighted in a distinct colour
- Expand to reveal: full explanation, syntax-highlighted code snippet, challenge question, "Got it / Not yet" buttons

Auto-refreshes every 10 seconds. New entries slide in at the top.

**2. Concepts**

Grid of all concepts in the knowledge graph. Each card shows:
- Concept name and confidence bar
- First seen / last seen
- Click → filters the feed to entries where this concept appeared

This is the "what have I learned over time?" view.

**3. Digest**

Today's session summary (date picker for history):
- Files touched, session duration
- New concepts introduced
- Concepts reinforced
- Concepts fading (resurface these)
- Unanswered challenge questions

**File structure:**
```
web/
  src/
    App.tsx
    views/
      Feed.tsx
      ConceptsView.tsx
      DigestView.tsx
    components/
      EntryCard.tsx       -- collapsed and expanded states
      ConceptBadge.tsx
      CodeBlock.tsx       -- syntax highlighted, use highlight.js
      ConfidenceBar.tsx
      ChallengeQuestion.tsx
    hooks/
      useFeed.ts          -- polling hook, 10s interval
      useConcepts.ts
      useDigest.ts
    api.ts                -- typed fetch wrappers for all endpoints
  index.html
  vite.config.ts
  package.json
```

**Design direction:** Dark mode first. Developer tool aesthetic — think Linear or Raycast. High information density, good mono/sans type pairing, subtle animations. No consumer-app softness. Monospace for code and file paths, sans-serif for explanations.

---

### Service 3 — VS Code / Cursor Extension ✅ Exists — strip it back

**Passive background process only. Remove all intrusive UI.**

**What changes:**
- Remove any inline popups, ghost text, decorations, or side panels
- Add session ID: generate a UUID on activation, pass it with every request
- Add one status bar item: `⬡ Groundwork — 4 concepts today`
- Clicking the status bar item opens `http://localhost:3000` in the browser
- That is the only UI the extension needs

**Complete extension behaviour:**
```
On activation:
  → generate session_id (UUID)
  → show status bar: "⬡ Groundwork"

On .py file save:
  → compute diff vs last known state
  → POST /analyse { code, diff, file_path, language, origin, session_id }
  → on 200: refresh concept count, update status bar
  → on error: log to output channel silently — never alert the user

On status bar click:
  → vscode.env.openExternal("http://localhost:3000")
```

**The extension must never interrupt coding.** If the API is down, it fails silently. If a file has no novel concepts, nothing happens. The developer should be able to forget Groundwork is running.

---

### Service 4 — CLI Surface ⏸ Deferred

Not needed yet. Revisit after the web UI is solid. The `groundwork diff` concept (for post-Claude-Code-task analysis) remains valid but is not a priority.

---

## Build Order from Current State

**Phase 1 — Upgrade the data model**

This must come first. Migrate to the three-table schema. Update `knowledge_graph.py`. Update `/analyse` to write full `entry` rows. Update the Claude prompt to return structured JSON. Verify with `curl` or the FastAPI `/docs` UI that `GET /feed` returns entries with real summaries.

_Done when:_ `GET /feed` returns `[{ id, file_path, summary, concepts }]` with meaningful summaries.

**Phase 2 — Build the web UI feed**

Scaffold the React app with Vite. Build `Feed.tsx` with polling. Build `EntryCard.tsx` with collapsed/expanded states. Add `CodeBlock.tsx` with `highlight.js`. At this point the product becomes usable — you can code and watch entries appear.

_Done when:_ Save a Python file, wait 10 seconds, see a card appear in the browser with the summary and explanation.

**Phase 3 — Simplify the extension**

Remove all in-editor UI. Add status bar item. Wire click to open the web UI. Done in an afternoon.

_Done when:_ The extension produces no visible output during coding except a status bar count.

**Phase 4 — Concepts and Digest views**

Build `ConceptsView.tsx` from `GET /concepts`. Build `DigestView.tsx` from `GET /digest`. Add navigation between views.

_Done when:_ After a session, the digest accurately summarises what was learned.

**Phase 5 — Challenge questions and confidence**

Wire "Got it / Not yet" buttons to `POST /concepts/:id/respond`. Watch confidence update in the Concepts view. Add fading concept logic to the digest.

---

## What a Good Entry Looks Like

This is the target quality for Claude's output. The difference between a useful tool and a useless one.

**Bad (what v0.1 produces):**
> **Concept:** Class
> **Explanation:** A class is a blueprint for creating objects in Python.

**Good (what to aim for):**
> **Summary:** Added a `DatabaseConnection` class to centralise connection handling across the app
>
> **Explanation:** In this change, you wrapped your database setup in a class — specifically using `__init__` to run setup code automatically whenever a `DatabaseConnection` is created. The `self` parameter that appears in every method is Python's way of giving each instance access to its own data: `self.conn` belongs to *this* connection, not all connections. You also used `__enter__` and `__exit__`, which is what makes `with DatabaseConnection() as db` work — Python calls those methods automatically when entering and leaving the `with` block, ensuring the connection always closes even if an error occurs. This pattern (a context manager) is idiomatic Python for anything that needs setup and teardown.
>
> **Challenge:** If you removed the `__exit__` method, what would happen when an exception is raised inside the `with` block?

The explanation references `DatabaseConnection`, `self.conn`, and the actual `with` block from the submitted code. It explains *why* these choices were made, not just what the concepts are.

---

## Key Decisions Log

| Decision | Choice | Rationale |
|---|---|---|
| UX model | Pull (web UI) not push (editor popup) | Interruption kills flow. Users come to the UI when ready |
| Web UI | Standalone `localhost:3000`, not VS Code webview | Webviews are constrained. A real browser tab is richer and persistent |
| Extension role | Silent sender only | Keeps the extension invisible and non-intrusive |
| Data model | Rich `entries` table with full text stored | Concept names alone are useless for recall — need full context |
| Claude output | Structured JSON (summary + explanation + challenge_q) | Allows scannable feed without loading full text per entry |
| Feed refresh | Polling every 10s | WebSockets are overkill; polling is simpler and reliable |
| Session tracking | UUID per activation, new session after 30min gap | Groups related changes for digest view |
| Claude model | `claude-sonnet-4-20250514` | Speed + quality balance for real-time use |

---

## What Success Looks Like

**After Phase 1:** `GET /feed` returns entries with summaries like "Added error handling to the database connection function" — contextual, not generic concept names.

**After Phase 2:** Code in your editor. Open `localhost:3000` in a browser tab. Save a file. An entry card appears within 10 seconds with the summary and an expandable explanation that references your actual variable names and code decisions.

**After Phase 3:** The extension is completely invisible during coding. Status bar shows a count. Nothing else.

**Demo-ready product:** Screen-record a 10-minute coding session with the browser tab visible alongside the editor. Watch entries build up in the feed in real time. Switch to Digest at the end — it accurately summarises what was learned that session. That's the portfolio demo.
