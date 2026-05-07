import { EntryCard } from "../components/EntryCard";
import { useFeed } from "../hooks/useFeed";

export function Feed() {
  const { entries, error, loading } = useFeed();

  if (loading && entries === null) {
    return <p className="muted">Loading…</p>;
  }

  return (
    <div>
      {error && <div className="error-banner">{error}</div>}

      {entries !== null && entries.length === 0 && !error && (
        <p className="muted">
          No entries yet — save a Python file in your editor.
        </p>
      )}

      {entries?.map((e) => (
        <EntryCard key={e.id} item={e} />
      ))}
    </div>
  );
}
