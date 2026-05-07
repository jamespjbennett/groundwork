import hljs from "highlight.js/lib/core";
import javascript from "highlight.js/lib/languages/javascript";
import python from "highlight.js/lib/languages/python";
import typescript from "highlight.js/lib/languages/typescript";

import "highlight.js/styles/atom-one-dark.css";

// Register up front; avoids per-render registration overhead.
hljs.registerLanguage("python", python);
hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("typescript", typescript);

const SUPPORTED = new Set(["python", "javascript", "typescript"]);

export function CodeBlock({
  code,
  language = "python",
}: {
  code: string;
  language?: string;
}) {
  const isSupported = SUPPORTED.has(language);
  const html = isSupported
    ? hljs.highlight(code, { language, ignoreIllegals: true }).value
    : escapeHtml(code);

  return (
    <pre className="codeblock">
      <code
        className={`hljs language-${isSupported ? language : "plaintext"}`}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </pre>
  );
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
