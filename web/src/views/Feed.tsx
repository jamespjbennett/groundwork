import { EntryCard } from "../components/EntryCard";
import { useFeed } from "../hooks/useFeed";

export function Feed() {
  const { entries, error, loading } = useFeed();

  if (loading && entries === null) {
    return <p style={{ opacity: 0.6 }}>Loading…</p>;
  }

  return (
    <div>
      {error && (
        <p
          style={{
            color: "#ff8a8a",
            fontSize: "0.8rem",
            marginBottom: 16,
            opacity: 0.85,
          }}
        >
          {error}
        </p>
      )}

      {entries !== null && entries.length === 0 && (
        <p style={{ opacity: 0.6 }}>
          No entries yet — save a Python file in your editor.
        </p>
      )}

      {entries?.map((e) => (
        <EntryCard key={e.id} item={e} />
      ))}
    </div>
  );
}
