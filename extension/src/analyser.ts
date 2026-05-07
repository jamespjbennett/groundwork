import * as vscode from "vscode";
import { createPatch } from "diff";

import { AnalyseResult } from "./types";
import { getSessionId } from "./session";

const API_BASE = "http://localhost:8000";
const _lastContent = new Map<string, string>();

export async function analyseDocument(doc: vscode.TextDocument): Promise<AnalyseResult | null> {
  const current = doc.getText();
  const previous = _lastContent.get(doc.uri.toString()) ?? "";
  _lastContent.set(doc.uri.toString(), current);

  if (current === previous) return null;

  const filePath = relativePath(doc);
  const diff = createPatch(filePath, previous, current);
  const origin = isLikelyPasted(previous, current) ? "ai_generated" : "typed";

  try {
    const res = await fetch(`${API_BASE}/analyse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        code: current,
        diff,
        file_path: filePath,
        session_id: getSessionId(),
        language: "python",
        origin,
      }),
    });
    return res.ok ? (res.json() as Promise<AnalyseResult>) : null;
  } catch {
    return null;
  }
}

function relativePath(doc: vscode.TextDocument): string {
  // Workspace-relative when possible, absolute otherwise. Matches what
  // a developer expects to see in the feed (e.g. "api/main.py").
  const ws = vscode.workspace.getWorkspaceFolder(doc.uri);
  return ws ? vscode.workspace.asRelativePath(doc.uri, false) : doc.uri.fsPath;
}

// More than 5 lines added in one save = likely paste / AI-generated block.
function isLikelyPasted(before: string, after: string): boolean {
  const added = after.split("\n").length - before.split("\n").length;
  return added > 5;
}
