export default function Home() {
  return (
    <main className="shell">
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">Historical scouting workspace</p>
        <h1 id="page-title">Find the shape behind the player.</h1>
        <p className="intro">
          AVScout turns historical performance evidence into transparent player
          comparisons. The recommendation workspace is coming next.
        </p>
        <div className="status" role="status">
          <span className="status-dot" aria-hidden="true" />
          Workspace initialized
        </div>
      </section>
      <aside className="context" aria-label="Project context">
        <span className="context-label">Dataset window</span>
        <strong>2017/18</strong>
        <span className="context-detail">Five major European leagues</span>
      </aside>
    </main>
  );
}
