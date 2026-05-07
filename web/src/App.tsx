import { Feed } from "./views/Feed";

export default function App() {
  return (
    <main className="app">
      <header className="app__header">
        <h1 className="app__title">Groundwork</h1>
        <p className="app__subtitle">
          A coding journal with understanding baked in.
        </p>
      </header>
      <Feed />
    </main>
  );
}
