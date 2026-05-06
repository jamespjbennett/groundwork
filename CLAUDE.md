# Groundwork — CLAUDE.md

> This file is the authoritative reference for building Groundwork. Read it before writing any code.
> Keep it updated as the project evolves.

---

## What is Groundwork?

Groundwork is a developer learning tool that runs alongside your editor. When you write or paste code, it detects concepts you haven't fully encountered before, explains them at your level, and asks you one question to make the understanding stick.

**The problem it solves:** AI coding tools help developers ship faster, but create a gap between what you can produce and what you actually understand. Groundwork closes that gap — passively, without interrupting your flow.

**The core loop:**
1. You write or paste code (or an AI agent writes it for you)
2. Groundwork detects what changed and extracts the concepts present
3. It checks those concepts against a personal model of what you already know
4. It surfaces a short explanation + one challenge question, pitched at your level
5. Your knowledge model updates — next time, it won't repeat itself

**What makes it different from "just ask Claude":**
- It watches passively — you don't have to ask
- It knows what *you specifically* already understand
- It never explains the same concept twice at the same depth
- It works across VS Code, Cursor, and agentic CLI workflows (Claude Code)

---

## Architecture Overview

Groundwork is a **learning engine with multiple thin-client surfaces**. The intelligence lives entirely in the backend. The editor extension and CLI are just surfaces that send code and render responses.

```
┌─────────────────────────────────────────────────────┐
│                   CLIENT SURFACES                    │
│                                                     │
│  VS Code / Cursor Extension    CLI (groundwork diff)│
│  (TypeScript)                  (Python)             │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP (JSON + streaming)
┌──────────────────────▼──────────────────────────────┐
│                  PYTHON API (FastAPI)                │
│                                                     │
│  POST /analyse   — main entry point                 │
│  GET  /concepts  — query knowledge graph            │
│  POST /respond   — user answered challenge Q        │
└──────┬───────────────┬──────────────────────────────┘
       │               │
┌──────▼──────┐  ┌─────▼──────────────────────────────┐
│  SQLite DB  │  │           Claude API               │
│             │  │                                    │
│  Concept    │  │  Explanation generation            │
│  graph per  │  │  Challenge question generation     │
│  user       │  │  Depth calibration via prompt      │
└─────────────┘  └────────────────────────────────────┘
```

---

## Services and Their Responsibilities

There are **four distinct pieces** to build. They are listed in the order you should build them.

---

### Service 1 — Python API (FastAPI)
**The core. Build this first. Everything else depends on it.**

**Responsibility:** Receive code, extract concepts, check the knowledge graph, call Claude, return structured responses.

**Key endpoints:**
```
POST /analyse
  Body: { code: str, language: str, origin: "typed" | "ai_generated" }
  Returns: { concepts: [...], explanation: str, challenge_question: str, confidence_before: float }

POST /respond
  Body: { concept_id: str, understood: bool }
  Returns: { updated_concept: {...} }

GET /concepts
  Returns: { concepts: [...] }  # full knowledge graph for the user

GET /session/digest
  Returns: { concepts_seen: int, new_concepts: [...], gaps: [...] }
```

**Internal modules inside the API:**

`concept_extractor.py` — Takes raw Python code, runs it through Python's built-in `ast` module, and returns a list of concepts present (e.g. decorators, list comprehensions, class inheritance, context managers). This is pure Python, no AI needed.

`knowledge_graph.py` — SQLite-backed store. Tracks every concept the user has seen, a confidence score (0.0–1.0), and a last-seen timestamp. Exposes methods: `is_novel(concept)`, `update(concept, understood)`, `get_fading()`.

`depth_calibrator.py` — Given a concept and the user's graph state, determines explanation depth. A user who has seen 50 Python concepts gets a shorter, more precise explanation than one who has seen 5.

`explainer.py` — Assembles the prompt for Claude. Includes: the concept, the surrounding code snippet, the user's depth level, and instruction to end with exactly one challenge question.

**Stack:** Python 3.11+, FastAPI, SQLite (via `aiosqlite`), Anthropic Python SDK, `uvicorn`

---

### Service 2 — Concept Taxonomy
**A flat file, not a service. Define this early so Service 1 has something to work with.**

**Responsibility:** A structured list of learnable Python concepts that the AST extractor maps to. Without this, the extractor has no vocabulary to output.

**Format:** A JSON file (`taxonomy.json`) that lives in the API repo. Each entry has an id, a human-readable name, a description, and prerequisite concept ids.

**Example entries:**
```json
[
  { "id": "decorator", "name": "Decorator", "description": "A function that wraps another function", "prereqs": ["function", "higher_order_function"] },
  { "id": "list_comprehension", "name": "List comprehension", "description": "Compact syntax for building lists", "prereqs": ["list", "for_loop"] },
  { "id": "context_manager", "name": "Context manager", "description": "with statement resource handling", "prereqs": ["class", "dunder_methods"] },
  { "id": "dataclass", "name": "Dataclass", "description": "@dataclass decorator for data containers", "prereqs": ["class", "decorator"] }
]
```

Start with ~30 concepts covering the most common Python patterns. Expand over time.

---

### Service 3 — VS Code / Cursor Extension
**Build this once Service 1 is returning real responses.**

**Responsibility:** Watch for file saves in Python files, send the diff to the API, and render the response.

**Stack:** TypeScript, VS Code Extension API. Scaffold with `yo code` (Yeoman generator).

**Key behaviours:**

On save of a `.py` file → compute diff from last known state → `POST /analyse` → render response.

Origin tagging: detect if the new code block was pasted (large chunk appearing at once) vs typed incrementally. Pass `origin: "ai_generated"` for pastes — these get higher learning priority.

**Two render surfaces:**

*Inline ghost text* — a one-line annotation appearing after a line containing a new concept. Use `vscode.window.createTextEditorDecorationType`. Subtle, non-intrusive.

*Webview side panel* — a `vscode.WebviewPanel` running a React app (bundled with esbuild). Shows the full explanation, the challenge question, and a simple "Got it / Not quite" response button.

**File structure:**
```
extension/
  src/
    extension.ts      # entry point, registers event listeners
    analyser.ts       # diff logic, API calls
    decorator.ts      # ghost text rendering
    panel.ts          # webview side panel
  webview/
    App.tsx           # React app rendered in the panel
    index.tsx
  package.json        # declares activationEvents, contributes
  tsconfig.json
```

**Activation event:** `onLanguage:python` — only activates for Python files, keeping it scoped to the MVP.

---

### Service 4 — CLI Surface
**Build this last. Lowest effort, highest flexibility.**

**Responsibility:** A command-line tool for analysing code outside the editor — particularly useful for post-task analysis after an AI agent (e.g. Claude Code) has written files.

**Usage:**
```bash
# Analyse the diff since last commit
groundwork diff

# Analyse a specific file
groundwork analyse path/to/file.py

# Show your knowledge graph
groundwork concepts

# Show today's session digest
groundwork digest
```

**Implementation:** A simple Python CLI using `typer` or `click`. `groundwork diff` runs `git diff HEAD` and pipes the result to `POST /analyse`. That's essentially the whole thing — the API does the real work.

**Why this matters:** Claude Code and other agentic tools write files autonomously. The VS Code save-event loop doesn't map cleanly onto that workflow. The CLI gives you a natural post-task hook: run `groundwork diff` after Claude Code finishes a task to analyse everything it just wrote.

---

## The MVP — What to Build First

The MVP is the smallest thing that proves the core loop works end-to-end. It does not need a polished UI. It does not need the CLI. It does not need a perfect knowledge graph.

**MVP definition:** Paste Python code into a test script → API detects a new concept → Claude returns an explanation and challenge question → it prints to the terminal.

That's it. No extension, no UI, no SQLite yet.

### MVP build order

**Step 1 — Stub the API (Day 1)**

Create a FastAPI app with a single `POST /analyse` endpoint. For now, skip the AST parsing — just take the code as a string and pass it straight to Claude with a simple prompt: *"What is the most interesting Python concept in this code that a beginner might not understand? Explain it in 2 sentences and ask one challenge question."* Return the response as JSON.

Prove: the API starts, accepts code, returns a response.

**Step 2 — Wire up the AST extractor (Day 1–2)**

Replace the raw Claude call with actual AST parsing first. Write `concept_extractor.py` using Python's `ast.parse()`. Get it to reliably detect 5–10 concepts (decorators, comprehensions, context managers, dataclasses, generators). Then pass the extracted concepts to Claude rather than the raw code.

Prove: pasting code with a decorator returns "decorator" as a detected concept.

**Step 3 — Add the knowledge graph (Day 2–3)**

Add SQLite. Create a `concepts` table: `(id, name, confidence, seen_count, last_seen)`. Before calling Claude, check if the concept is novel. If confidence > 0.8, skip it. After the response, insert or update the row.

Prove: explaining a decorator twice — the second time it gets skipped.

**Step 4 — Build the extension (Day 3–5)**

Scaffold the VS Code extension. Wire the `onDidSaveTextDocument` event to call your now-working API. Start by just printing the API response to the VS Code Output panel (no UI yet). Once that works, add the webview panel with a basic React component to render the explanation.

Prove: save a Python file in VS Code, see an explanation appear in the side panel.

**Step 5 — Polish the panel, add ghost text (Day 5–7)**

Style the webview panel. Add the "Got it / Not quite" buttons that call `POST /respond`. Add inline ghost text for single-line concept callouts.

**That is a shippable, demonstrable MVP.** Everything after this is expansion.

---

## Post-MVP Expansion (Roughly Prioritised)

**High value, build next:**
- Spaced repetition — resurface concepts where confidence is fading (last seen > 7 days, confidence < 0.6)
- Session digest — end-of-session summary of concepts seen, new vs reviewed, gaps
- Depth calibration — prompt engineering to vary explanation depth based on graph state
- Origin tagging — detect AI-pasted code and weight it higher

**Medium value:**
- CLI surface (`groundwork diff`)
- Support for JavaScript/TypeScript (extend the AST extractor)
- Prerequisite chaining — if you don't know `function`, don't explain `decorator` yet
- Concept search (`groundwork concepts --search decorator`)

**Longer term:**
- Web dashboard showing knowledge graph visually over time
- Team mode — shared concept graph for onboarding new developers
- Language server protocol (LSP) implementation for editor-agnostic support

---

## Repo Structure (Suggested)

```
groundwork/
├── CLAUDE.md                  ← this file
├── api/                       ← Python FastAPI backend
│   ├── main.py
│   ├── concept_extractor.py
│   ├── knowledge_graph.py
│   ├── depth_calibrator.py
│   ├── explainer.py
│   ├── taxonomy.json
│   ├── db/
│   │   └── groundwork.db      ← SQLite (gitignored)
│   ├── requirements.txt
│   └── .env                   ← ANTHROPIC_API_KEY (gitignored)
├── extension/                 ← VS Code extension (TypeScript)
│   ├── src/
│   │   ├── extension.ts
│   │   ├── analyser.ts
│   │   ├── decorator.ts
│   │   └── panel.ts
│   ├── webview/
│   │   ├── App.tsx
│   │   └── index.tsx
│   ├── package.json
│   └── tsconfig.json
└── cli/                       ← CLI surface (Python)
    ├── main.py
    └── pyproject.toml
```

---

## Environment Setup

```bash
# API
cd api
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn aiosqlite anthropic python-dotenv
echo "ANTHROPIC_API_KEY=your_key_here" > .env
uvicorn main:app --reload --port 8000

# Extension (scaffold first time only)
npm install -g yo generator-code
cd extension
yo code   # choose TypeScript, no webpack
npm install

# Press F5 in VS Code to launch extension dev host
```

---

## Key Decisions and Rationale

| Decision | Choice | Why |
|---|---|---|
| Backend language | Python | Native `ast` module, Anthropic SDK, fast to iterate |
| API framework | FastAPI | Async, streaming-ready, auto docs at `/docs` |
| Knowledge store | SQLite | Local, zero infra, sufficient for single-user MVP |
| Extension language | TypeScript | Only real option — VS Code API is typed TS |
| Webview UI | React | Familiar, works well in VS Code webview context |
| Claude model | claude-sonnet-4-6 | Best balance of speed and explanation quality |
| MVP scope | API + extension only | Proves the loop without over-engineering |

---

## What Success Looks Like at Each Stage

**After Step 1 (stub API):** `curl -X POST localhost:8000/analyse -d '{"code": "...", "language": "python"}'` returns a JSON explanation.

**After Step 3 (knowledge graph):** The same concept explained twice — second call returns `{ "skipped": true, "reason": "already_known" }`.

**After Step 4 (extension):** Save a Python file containing a decorator in VS Code. A panel appears explaining what a decorator is.

**Demo-ready MVP:** Record a 60-second screen capture: open a Python file, paste an AI-generated snippet using a concept you haven't seen, watch the panel appear with an explanation and a challenge question. That's the portfolio piece.
