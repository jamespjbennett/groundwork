# Groundwork Extension

The extension is a silent background process. Its only job is to notice meaningful Python code changes — manual saves and AI-written blocks — and POST them to the local API. All explanations, knowledge tracking, and UI live elsewhere (the API and, in Phase 3, the web app at `localhost:3000`).

The response from the API is intentionally ignored. Detail lives in the database; the developer reads it later via the web UI.

---

## What triggers a send

Two listeners in `extension.ts`, both funnelling into the same `analyseDocument` call:

**Manual save** (`onDidSaveTextDocument`) — fires when you hit Cmd+S. Always sends if the file content has changed since the last send.

**AI agent write** (`onDidChangeTextDocument`) — fires whenever the document changes. Most events are single keystrokes and are ignored. When more than 5 lines appear in a single change — the signature of an AI-generated block — the extension starts a 1.5 second debounce timer. If no further large edits arrive in that window, it sends. This is what catches Cursor's agent writing code when you accept its output, without requiring a manual save.

## What gets sent

`POST /analyse` with:

```
{
  code:        full file contents
  diff:        unified diff vs the last seen version
  file_path:   workspace-relative path (e.g. "api/main.py")
  session_id:  UUID per editor session, rotated after 30 minutes idle
  language:    "python"
  origin:      "typed" or "ai_generated"
}
```

`analyser.ts` builds the payload. `session.ts` owns the session UUID lifecycle. Errors and non-200 responses are swallowed silently — the extension must never disrupt coding.

---

## File map

```
src/
  extension.ts   entry point, registers save + change listeners
  analyser.ts    diffs the file, detects paste vs typed, posts to /analyse
  session.ts     UUID generator with 30-min idle rotation
  types.ts       AnalyseResult type matching the API response shape
```

---

## What it deliberately does not do

- It does not parse Python or extract concepts. The API does that.
- It does not store anything locally. SQLite lives in the API.
- It does not render anything in the editor — no ghost text, no panel, no notifications.
- It does not activate for non-Python files (`activationEvents: ["onLanguage:python"]`).
- It does not retry failed requests. A dropped save just means the next save will pick up the same diff.
