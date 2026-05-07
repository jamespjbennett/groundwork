# Groundwork Extension

The extension is the editor-side surface of Groundwork. It has one job: notice when you save a Python file, send the code to the API, and show you what came back.

All the intelligence — concept extraction, knowledge tracking, Claude prompting — lives in the Python API. The extension is a thin client.

---

## What triggers an analysis

There are two triggers, both in `extension.ts`:

**Manual save** (`onDidSaveTextDocument`) — fires when you hit Cmd+S. Always runs an analysis if the file content has changed.

**AI agent write** (`onDidChangeTextDocument`) — fires whenever the document changes. Most of those events are single keystrokes and are ignored. When more than 5 lines appear in a single change — the signature of an AI-generated block — the extension starts a 1.5 second debounce timer. If no further large edits arrive in that window, it runs an analysis. This is what catches Cursor's agent writing code when you accept its output, without requiring a manual save.

Both paths funnel into the same `trigger()` function.

## What happens next

1. **`analyser.ts`** is called. It compares the current file content against what it saw last time. If nothing changed, it stops early. If something changed, it works out whether the change looks like a paste (more than 5 lines appeared at once) or was typed incrementally, then POSTs the full file contents to `POST /analyse` on the local API. The `origin` field (`"typed"` or `"ai_generated"`) goes with the request so the API can weight pasted code higher — code you didn't write yourself is more likely to contain things you don't understand.

3. The API response either says `skipped: true` (the concept is already known) or carries a `novel_concept`, `explanation`, and `challenge_question`. If skipped, the extension stops. If not, control passes to the two render surfaces.

4. **`decorator.ts`** adds a small piece of ghost text at the end of the line where the concept appears. It looks up the concept ID in a token map (`CONCEPT_TOKENS`) to find which syntactic marker to search for — `@` for decorators, `yield` for generators, `with ` for context managers, and so on — then scans the file line by line to find the right one. The ghost text just names the concept inline so you can see it without opening the panel.

5. **`panel.ts`** opens (or updates) a webview panel beside your editor with the full explanation and challenge question. It renders plain HTML using VS Code's theme variables so it looks native. When you click "Got it" or "Not quite", the panel sends a message back to the extension host, which POSTs to `POST /respond` so the API can update your knowledge graph.

---

## File map

```
src/
  extension.ts   entry point, registers the save listener
  analyser.ts    diffs the file, detects paste vs typed, calls the API
  decorator.ts   places ghost text on the concept's line in the editor
  panel.ts       renders the explanation + challenge question in a side panel
  types.ts       shared AnalyseResult interface matching the API response shape
```

---

## What it does not do

- It does not parse Python itself. The API handles that.
- It does not store anything. The knowledge graph lives in the API's SQLite database.
- It does not talk to Claude directly. That's the API's responsibility too.
- It does not activate for non-Python files (`activationEvents: ["onLanguage:python"]`).
