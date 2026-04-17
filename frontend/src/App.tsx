const features = [
  "FastAPI backend scaffold",
  "React + Vite frontend scaffold",
  "PostgreSQL, MinIO, Kafka, Grafana baseline",
];

export default function App() {
  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">filesh</p>
        <h1>File sharing system scaffold is ready to evolve.</h1>
        <p className="lede">
          This starter focuses on infra first, so we can layer auth, uploads,
          sharing, observability, and cleanup workflows on a stable foundation.
        </p>
      </section>

      <section className="panel">
        <h2>Current baseline</h2>
        <ul>
          {features.map((feature) => (
            <li key={feature}>{feature}</li>
          ))}
        </ul>
      </section>
    </main>
  );
}
