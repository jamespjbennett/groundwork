# Groundwork

Groundwork is a **local learning loop** for developers. As you write or paste code (pertinantly - code written by LLM's that you accept) it silently detects concepts in each change, checks what you already know, and — when something is still worth explaining — asks Claude for a short contextual explanation and a challenge question. 

Currently limited to python as a starting point (as I am not familiar with python and want to learn as I go) - but intended future use case is to expand to all domains of development. Everything is stored locally; you query it whenever you want.

Full design, roadmap, and vocabulary live in [CLAUDE.md](CLAUDE.md).

---

## Purpose

As an engineer, I'm increasingly falling into the trap of generating reems of code I haven't fully taken the time to learn and understand (I'm sure I'm not the only one). For those with a thirst to continue learning in this AI assisted software development age, the hope is that by having this running alongside your development flow, you can take a breath and look back at the code your AI written and have it explained to you so you can continue to take learnings from it :).

## Repository layout

| Path | Role |
|------|------|
| `api/` | FastAPI app — all API logic, SQLite store, concept extraction, explainer |
| `extension/` | VS Code / Cursor extension — sends diffs to the API on every save (and on large AI-generated edits) |
| `cli/` | Typer CLI — HTTP client for the same API, useful post-session or in CI |

---

## Prerequisites

- **Python 3.11+**
- **Anthropic API key** (`ANTHROPIC_API_KEY`)
- **Node.js** (only for the extension)

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

- Currently this only works with VScode/Cursor. Want to extend htis to CLI level for use with claude code and possibly codex if possible (unfamiliar with codex)
- Expand to all programming languages and architectural principles (limited to python now)
- Integrate different LLM apis


## License

Not specified. Add a `LICENSE` file if you publish the project.
