import * as vscode from "vscode";
import { AnalyseResult } from "./types";

let _decoration: vscode.TextEditorDecorationType | undefined;

export function renderGhostText(result: AnalyseResult, doc: vscode.TextDocument) {
  clearGhostText();

  const editor = vscode.window.visibleTextEditors.find(
    (e) => e.document.uri.toString() === doc.uri.toString()
  );
  if (!editor) return;

  const line = findConceptLine(result.novel_concept, doc);
  const lineLength = doc.lineAt(line).text.length;

  _decoration = vscode.window.createTextEditorDecorationType({
    after: {
      contentText: `  ← ${result.novel_concept}`,
      color: new vscode.ThemeColor("editorGhostText.foreground"),
      fontStyle: "italic",
    },
  });

  editor.setDecorations(_decoration, [new vscode.Range(line, lineLength, line, lineLength)]);
}

export function clearGhostText() {
  _decoration?.dispose();
  _decoration = undefined;
}

// Maps taxonomy concept IDs to the tokens that signal their presence on a line.
const CONCEPT_TOKENS: Record<string, string[]> = {
  decorator:             ["@"],
  dataclass:             ["@dataclass"],
  list_comprehension:    ["["],
  generator_expression:  ["("],
  generator:             ["yield"],
  context_manager:       ["with "],
  lambda:                ["lambda "],
  class_inheritance:     ["class "],
  dunder_methods:        ["__"],
  type_annotation:       ["->"],
  walrus_operator:       [":="],
  f_string:              ['f"', "f'"],
  match_statement:       ["match "],
  async_function:        ["async def"],
  async_for:             ["async for"],
  async_with:            ["async with"],
};

function findConceptLine(concept: string, doc: vscode.TextDocument): number {
  const tokens = CONCEPT_TOKENS[concept];
  if (!tokens) return 0;

  const lines = doc.getText().split("\n");
  for (let i = 0; i < lines.length; i++) {
    if (tokens.some((t) => lines[i].includes(t))) return i;
  }
  return 0;
}
