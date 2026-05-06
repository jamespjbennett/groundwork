import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

declare function acquireVsCodeApi(): { postMessage: (msg: any) => void };
const vscode = acquireVsCodeApi();

// Data injected by the panel via window.__GROUNDWORK__
const data = (window as any).__GROUNDWORK__ ?? {};

const root = createRoot(document.getElementById("root")!);
root.render(
  <App
    novelConcept={data.novel_concept}
    explanation={data.explanation}
    challengeQuestion={data.challenge_question}
    onRespond={(understood) =>
      vscode.postMessage({ type: "respond", conceptId: data.novel_concept, understood })
    }
  />
);
