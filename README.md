# Groundwork

Groundwork is a **local learning loop** for Python: when you change code, it detects concepts in your snippet, checks what you have already “seen” in a small SQLite knowledge store, and—when something is still worth teaching—calls Claude for a short explanation and one challenge question. It is meant to run beside the editor (VS Code / Cursor extension) or after agent work (CLI against `git diff`).

Project design, roadmap, and vocabulary live in [CLAUDE.md](CLAUDE.md).

## Repository layout

| Path | Role |
|------|------|
| `api/` | FastAPI app: `POST /analyse`, `POST /respond`, `GET /concepts`, `GET /session/digest` |
| `extension/` | VS Code–compatible extension (`onLanguage:python`), talks to the API on save |
| `cli/` | Typer CLI (`diff`, `analyse`, `concepts`, `digest`) — HTTP client to the same API |

## Prerequisites

- **Python 3.11+**
- **Anthropic API key** (`ANTHROPIC_API_KEY`)
- **Node.js** (only if you build/run the extension)

## Run the API

From `api/`:

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # add your real ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8000
```

- Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- The SQLite file is created at `api/db/groundwork.db` (gitignored).

**Failure modes:** If the model call or parsing fails, `POST /analyse` responds with **503** and a `detail` message. Missing `ANTHROPIC_API_KEY` is rejected the same way.

## Run the extension

The extension expects the API at **`http://localhost:8000`** (see `extension/src/analyser.ts`).

From `extension/`:

```bash
npm install
npm run compile
npm run build-webview
```

Open the folder in VS Code, run **Run → Start Debugging** (F5) for the extension host. Saving a `.py` file triggers `/analyse` and can open the side panel with the explanation.

## Run the CLI

The CLI is a thin HTTP client: start the API first.

From `cli/`:

```bash
pip install httpx typer   # matches cli/pyproject.toml
python main.py diff       # git diff against HEAD → /analyse
python main.py analyse path/to/file.py
python main.py concepts
python main.py digest
```

Adjust `API_BASE` in `cli/main.py` if the API is not on port 8000.

## Configuration notes

- **`origin`** on `POST /analyse` can be `typed` or `ai_generated`. The editor sends `ai_generated` when it guesses a paste; the API uses a **stricter** “already known” threshold for that path so pasted / agent-shaped code gets explanations more often.
- Concept detection is **AST + taxonomy** (`api/concept_extractor.py`, `api/taxonomy.json`), not raw LLM guessing on the full file.

## License

Not specified in this repo; add a `LICENSE` file if you publish the project.
