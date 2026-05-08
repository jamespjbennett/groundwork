# Groundwork

<img width="640" height="360" alt="groundword-mvp-demo" src="https://github.com/user-attachments/assets/f0800c68-cd1b-4a3f-81db-b0a5c17e2a93" />

---

Groundwork is a **local learning loop** for developers. As you write or paste code (pertinantly - code written by LLM's that you accept) it silently detects concepts in each change, checks what you already know, and — when something is still worth explaining — asks Claude for a short contextual explanation and a challenge question. 

Bit of a fun side project, but also intend to increase the usefulness of it and make it a more well rounded learning utility.

Full design, roadmap, and vocabulary live in [CLAUDE.md](CLAUDE.md).

---

## Purpose

As an engineer, I'm increasingly falling into the trap of generating reems of code I haven't fully taken the time to learn and understand (I'm sure I'm not the only one). For those with a thirst to continue learning in this AI assisted software development age, the hope is that by having this running alongside your development flow, you can take a breath and look back at the code your AI written and have it explained to you so you can continue to take learnings from it :).

## Repository layout

| Path | Role |
|------|------|
| `api/` | FastAPI app — all API logic, SQLite store, concept extraction, explainer |
| `web/` | React + Vite UI — dev server proxies `/api/*` → `:8000` |
| `extension/` | VS Code / Cursor extension — sends diffs to the API on every save (and on large AI-generated edits) |
| `cli/` | Typer CLI — HTTP client for the same API, useful post-session or in CI |

---

## Prerequisites

- **Python 3.10+** (3.11+ if you install the CLI as a packaged project from `cli/pyproject.toml`)
- **Anthropic API key** (`ANTHROPIC_API_KEY`)
- **Node.js** (extension + web UI dev server)

---

## Quick setup (macOS / Linux)

From the **repository root**:

```bash
make setup       # venv + pip, api/.env prompt, extension (npm install + compile), web (npm install)
make start       # API only — background uvicorn on :8000
make start-web   # Vite on :3000 (expects API on :8000 for /api/* proxy)
make start-all   # API + web
make stop        # stops API + web (any PID files from our scripts)
make status      # PIDs + quick HTTP checks on :8000 and :3000
make logs        # API log   |  make logs-web — web log
```

Underlying scripts: `scripts/setup.sh`, `start.sh`, `start-web.sh`, `stop.sh`.

**Windows:** use Git Bash or WSL with the same commands, or follow the manual sections below.

#### What this does *not* start

| Piece | Why | What to do |
|-------|-----|------------|
| **Extension** | Editors don’t allow shell scripts to “inject” an extension. | Open the `extension/` folder in Cursor/VS Code and press **F5** (Extension Development Host), or build a `.vsix` with `npx @vscode/vsce package` and install it via **Extensions → Install from VSIX**. |
| **`make start`** | Only the **Python API**. | Use **`make start-web`** or **`make start-all`** for the browser UI at [http://127.0.0.1:3000](http://127.0.0.1:3000). |

The extension talks to **`http://localhost:8000`** directly; the web app uses **relative `/api/...`** so it works through Vite’s proxy without CORS issues.

---

## Run the API

From `api/`:

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # paste your ANTHROPIC_API_KEY
uvicorn main:app --port 8000
```

> Use `--reload` during development, but be aware it restarts the server on every file save under `api/`, which can mask real request logs. Leave it off when you're testing the extension end-to-end.

- Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- SQLite DB: `api/db/groundwork.db` (gitignored, created on first startup)

### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/analyse` | Receive a code change; extract concepts; explain if novel; persist entry |
| `GET` | `/feed` | Paginated entry feed (`?session_id=`, `?concept_id=`, `?limit=`) |
| `GET` | `/feed/{entry_id}` | Full entry: explanation, code snippet, challenge question |
| `GET` | `/digest` | Session summary (`?date=YYYY-MM-DD`) |
| `GET` | `/concepts` | Full knowledge graph |
| `POST` | `/concepts/{id}/respond` | Mark a concept understood / not yet |

### POST /analyse request shape

```json
{
  "code": "...",
  "diff": "...",
  "file_path": "api/main.py",
  "session_id": "uuid4-from-extension",
  "language": "python",
  "origin": "typed"
}
```

`origin` is `"typed"` or `"ai_generated"`. AI/paste-shaped input uses a stricter novelty threshold (confidence must be ≥ 0.95 to skip, vs 0.80 for typed), so pasted blocks get explained more often.

**On success:** returns `{ skipped, entry_id, summary, concepts }`.  
**On failure:** returns `503` with a `detail` message (missing API key, model error, bad JSON from Claude).

### Quick smoke test

```bash
curl -s -X POST http://localhost:8000/analyse \
  -H "Content-Type: application/json" \
  -d '{"code":"@dataclass\nclass User:\n    name: str","diff":"","file_path":"models/user.py","session_id":"test-1"}' \
  | python3 -m json.tool
```

---

## Run the tests

From `api/` (with the venv active, or via `./venv/bin/python -m pytest`):

```bash
pip install -r requirements-test.txt   # pytest + pytest-asyncio (first time only)
pytest                                  # 114 tests, ~4 seconds
pytest -v                               # verbose
pytest tests/test_analyse_workflow.py  # single file
```

Tests use `InMemoryKnowledgeStore` — no real DB or API key needed.

---

## Run the extension (VS Code / Cursor)

The extension sends each `.py` save (and large AI-generated edits) to `http://localhost:8000`. It fires on two triggers:

- **Manual save (`Cmd+S`)** — always sends if content changed.
- **Large unsaved edit** — debounced 1.5 s; fires when > 5 lines appear at once (AI agent write pattern).

**Build and launch:**

1. Open the **`extension/`** folder in VS Code or Cursor (not the repo root).
2. Install deps and compile:

```bash
cd extension
npm install
npm run compile
```

3. Press **F5** → a new **Extension Development Host** window opens with your build loaded.
4. In that host window: **File → Open Folder** → choose any folder with `.py` files.
5. Open a `.py` file, make a change that introduces a detectable concept, **Save**.
6. Watch the uvicorn terminal for `POST /analyse` — if the response is not skipped, a side panel opens with the explanation and challenge question.

**If nothing appears:**
- Check the uvicorn terminal — did `POST /analyse` arrive? If not, the issue is in the extension (try **DevTools → Console** in the host window for JS errors).
- If the request arrived but returned `skipped: true`, the concept is already known. Reset `api/db/groundwork.db` for a clean store, or try a concept from `api/taxonomy.json` you haven't triggered yet.
- If the request returned `503`, the explainer failed — check the uvicorn terminal for the error detail (usually missing API key or Claude parse error).

---


## Architecture notes

- **Concept detection:** pure AST (`concept_extractor.py`) + a taxonomy file (`taxonomy.json`). No LLM call to identify concepts — only to explain them.
- **Knowledge store seam:** `KnowledgeStore` is a `Protocol`; `SqliteKnowledgeStore` is the production adapter; `InMemoryKnowledgeStore` is used by all tests.
- **Learning loop:** `analyse_workflow.py` owns the full pipeline (extract → novelty filter → explain → persist). `main.py` is a thin HTTP adapter.
- **Session tracking:** the extension generates a UUID on activation and passes it with every request. `session_manager.py` defines a 30-minute idle timeout; rotation happens client-side.
- **Depth calibration:** `depth_calibrator.py` inspects the current `GraphState` (concept count + avg confidence) to pick a `beginner / intermediate / advanced` instruction level for the prompt.

---


## Todo

- Automate the setup - the server setup and running is done with a makefile, but the extension is still fiddly to run. Ideally you could pull this down and have it all run in one magic command.
- Currently this only works with VScode/Cursor. Want to extend this to CLI level for use with claude code and possibly codex (unfamiliar with codex)
- Expand to all programming languages and architectural principles (limited to python now)
- Integrate different LLM apis


