import { Feed } from "./views/Feed";

export default function App() {
  return (
    <main style={{ padding: 32, maxWidth: 880, margin: "0 auto" }}>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: "1.25rem", margin: 0 }}>Groundwork</h1>
        <p
          style={{
            margin: "4px 0 0",
            opacity: 0.55,
            fontSize: "0.8rem",
          }}
        >
          A coding journal with understanding baked in.
        </p>
      </header>
      <Feed />
    </main>
  );
}
