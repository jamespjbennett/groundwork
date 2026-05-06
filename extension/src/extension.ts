import * as vscode from "vscode";
import { analyseDocument } from "./analyser";
import { renderGhostText, clearGhostText } from "./decorator";
import { GroundworkPanel } from "./panel";

export function activate(context: vscode.ExtensionContext) {
  const onSave = vscode.workspace.onDidSaveTextDocument(async (doc) => {
    if (doc.languageId !== "python") return;

    const result = await analyseDocument(doc);
    if (!result || result.skipped) return;

    renderGhostText(result, doc);
    GroundworkPanel.createOrShow(context.extensionUri, result);
  });

  context.subscriptions.push(onSave);
}

export function deactivate() {
  clearGhostText();
}
