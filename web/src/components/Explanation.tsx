// Renders Claude's explanation text as paragraphs with inline-code spans.
// We deliberately avoid a full markdown parser — the explainer is prompted
// to return prose + backtick-wrapped code references, nothing more.
//
// HTML is escaped before any tags are added, so this is safe to feed into
// dangerouslySetInnerHTML even though the source is model-generated.
export function Explanation({ text }: { text: string }) {
  return (
    <div
      className="explanation"
      dangerouslySetInnerHTML={{ __html: render(text) }}
    />
  );
}

function render(text: string): string {
  return text
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean)
    .map((p) => `<p>${formatInline(escape(p)).replace(/\n/g, "<br>")}</p>`)
    .join("");
}

function formatInline(escaped: string): string {
  // Backticks survived `escape()` (it doesn't touch them), so we can
  // match them here and wrap in a styled <code>.
  return escaped.replace(
    /`([^`]+)`/g,
    '<code class="inline-code">$1</code>'
  );
}

function escape(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
