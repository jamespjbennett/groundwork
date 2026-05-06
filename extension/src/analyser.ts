import * as vscode from "vscode";

const API_BASE = "http://localhost:8000";
const _lastContent = new Map<string, string>();

export async function analyseDocument(doc: vscode.TextDocument) {
  const current = doc.getText();
  const previous = _lastContent.get(doc.uri.toString()) ?? "";
  _lastContent.set(doc.uri.toString(), current);

  if (current === previous) return null;

  const origin = isLikelyPasted(previous, current) ? "ai_generated" : "typed";

  try {
    const res = await fetch(`${API_BASE}/analyse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: current, language: "python", origin }),
    });
    return res.ok ? res.json() : null;
  } catch {
    return null;
  }
}

// heuristic: if > 5 lines appeared at once, treat as paste
function isLikelyPasted(before: string, after: string): boolean {
  const added = after.split("\n").length - before.split("\n").length;
  return added > 5;
}
