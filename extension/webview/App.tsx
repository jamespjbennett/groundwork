import React, { useState } from "react";

interface Props {
  novelConcept: string;
  explanation: string;
  challengeQuestion: string;
  onRespond: (understood: boolean) => void;
}

export default function App({ novelConcept, explanation, challengeQuestion, onRespond }: Props) {
  const [responded, setResponded] = useState(false);

  function handle(understood: boolean) {
    setResponded(true);
    onRespond(understood);
  }

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ marginTop: 0 }}>
        New concept: <strong>{novelConcept}</strong>
      </h2>
      <p>{explanation}</p>
      <blockquote>
        <strong>Challenge:</strong> {challengeQuestion}
      </blockquote>
      {responded ? (
        <em>Response recorded.</em>
      ) : (
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={() => handle(true)}>Got it</button>
          <button onClick={() => handle(false)}>Not quite</button>
        </div>
      )}
    </div>
  );
}
