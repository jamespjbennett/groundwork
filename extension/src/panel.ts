import * as vscode from "vscode";
import { AnalyseResult } from "./types";

const API_BASE = "http://localhost:8000";

export class GroundworkPanel {
  static currentPanel: GroundworkPanel | undefined;
  private readonly _panel: vscode.WebviewPanel;

  static createOrShow(extensionUri: vscode.Uri, result: AnalyseResult) {
    const column = vscode.ViewColumn.Beside;

    if (GroundworkPanel.currentPanel) {
      GroundworkPanel.currentPanel._panel.reveal(column);
      GroundworkPanel.currentPanel._update(result);
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      "groundwork",
      "Groundwork",
      column,
      { enableScripts: true, localResourceRoots: [extensionUri] }
    );

    GroundworkPanel.currentPanel = new GroundworkPanel(panel, result);
  }

  private constructor(panel: vscode.WebviewPanel, result: AnalyseResult) {
    this._panel = panel;
    this._update(result);

    this._panel.onDidDispose(() => {
      GroundworkPanel.currentPanel = undefined;
    });

    this._panel.webview.onDidReceiveMessage(async (msg) => {
      if (msg.type === "respond") {
        await fetch(`${API_BASE}/respond`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ concept_id: msg.conceptId, understood: msg.understood }),
        });
        this._panel.webview.postMessage({ type: "responded" });
      }
    });
  }

  private _update(result: AnalyseResult) {
    this._panel.webview.html = this._getHtml(result);
  }

  private _getHtml(result: AnalyseResult): string {
    const concept = esc(result.novel_concept);
    const explanation = esc(result.explanation);
    const question = esc(result.challenge_question);

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline';">
  <style>
    body { font-family: var(--vscode-font-family); padding: 16px; color: var(--vscode-foreground); }
    h2 { margin-top: 0; font-size: 1rem; }
    .explanation { line-height: 1.6; margin-bottom: 16px; }
    .question { background: var(--vscode-editor-background); padding: 12px; border-radius: 4px; margin-bottom: 16px; }
    .actions { display: flex; gap: 8px; }
    button { padding: 6px 14px; cursor: pointer; border: none; border-radius: 3px; font-size: 0.9rem; }
    .got-it { background: var(--vscode-button-background); color: var(--vscode-button-foreground); }
    .not-quite { background: var(--vscode-button-secondaryBackground); color: var(--vscode-button-secondaryForeground); }
    .done { opacity: 0.6; font-style: italic; }
  </style>
</head>
<body>
  <h2>New concept: <strong>${concept}</strong></h2>
  <div class="explanation">${explanation}</div>
  <div class="question"><strong>Challenge:</strong> ${question}</div>
  <div class="actions" id="actions">
    <button class="got-it" onclick="respond(true)">Got it</button>
    <button class="not-quite" onclick="respond(false)">Not quite</button>
  </div>
  <script>
    const vscode = acquireVsCodeApi();
    const conceptId = ${JSON.stringify(result.novel_concept)};
    function respond(understood) {
      vscode.postMessage({ type: 'respond', conceptId, understood });
    }
    window.addEventListener('message', e => {
      if (e.data.type === 'responded') {
        document.getElementById('actions').innerHTML = '<span class="done">Response recorded.</span>';
      }
    });
  </script>
</body>
</html>`;
  }
}

function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
