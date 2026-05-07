import * as vscode from "vscode";
import { analyseDocument } from "./analyser";

const DEBOUNCE_MS = 1500;
const _timers = new Map<string, NodeJS.Timeout>();

export function activate(context: vscode.ExtensionContext) {
  // Manual save — always analyse if content changed.
  const onSave = vscode.workspace.onDidSaveTextDocument(async (doc) => {
    if (doc.languageId !== "python") return;
    await analyseDocument(doc);
  });

  // AI agent write — debounced, large-edit only.
  // Cursor applies agent edits via onDidChangeTextDocument, not a save.
  // We ignore single keystrokes and only react when many lines appear at
  // once, which is the signature of an AI-generated block.
  const onChange = vscode.workspace.onDidChangeTextDocument((event) => {
    const { document: doc, contentChanges } = event;
    if (doc.languageId !== "python") return;
    if (!isLargeEdit(contentChanges)) return;

    const key = doc.uri.toString();
    clearTimeout(_timers.get(key));
    _timers.set(
      key,
      setTimeout(async () => {
        _timers.delete(key);
        await analyseDocument(doc);
      }, DEBOUNCE_MS)
    );
  });

  context.subscriptions.push(onSave, onChange);
}

export function deactivate() {
  for (const t of _timers.values()) clearTimeout(t);
  _timers.clear();
}

function isLargeEdit(changes: readonly vscode.TextDocumentContentChangeEvent[]): boolean {
  return changes.some((c) => c.text.split("\n").length > 5);
}
