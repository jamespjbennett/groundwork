import * as vscode from "vscode";

let _decoration: vscode.TextEditorDecorationType | undefined;

export function renderGhostText(result: any, doc: vscode.TextDocument) {
  clearGhostText();

  const editor = vscode.window.visibleTextEditors.find(
    (e) => e.document.uri.toString() === doc.uri.toString()
  );
  if (!editor) return;

  _decoration = vscode.window.createTextEditorDecorationType({
    after: {
      contentText: `  ← ${result.novel_concept}`,
      color: new vscode.ThemeColor("editorGhostText.foreground"),
      fontStyle: "italic",
    },
  });

  // annotate the first line as a simple indicator
  const range = new vscode.Range(0, 0, 0, 0);
  editor.setDecorations(_decoration, [range]);
}

export function clearGhostText() {
  _decoration?.dispose();
  _decoration = undefined;
}
