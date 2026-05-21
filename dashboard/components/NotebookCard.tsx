import type { ClientMemory } from "@/lib/data";

type NotebookCardProps = {
  memory: ClientMemory;
};

export default function NotebookCard({ memory }: NotebookCardProps) {
  return (
    <article className="card notebook-card">
      <div className="section-head">
        <h2>{memory.client_name || memory.client_id}</h2>
        <span className="badge">cuaderno</span>
      </div>
      <div className="memory-sections">
        <section className="memory-section">
          <div className="muted">Hechos</div>
          <div className="badge-row">
            {(memory.facts.length ? memory.facts : ["ninguno"]).map((fact) => (
              <span className="badge" key={fact}>{fact}</span>
            ))}
          </div>
        </section>
        <section className="memory-section">
          <div className="muted">Preferencias</div>
          <div className="badge-row">
            {(memory.preferences.length ? memory.preferences : ["ninguna"]).map((item) => (
              <span className="badge" key={item}>{item}</span>
            ))}
          </div>
        </section>
        <section className="memory-section">
          <div className="muted">Riesgos</div>
          <div className="badge-row">
            {(memory.risks.length ? memory.risks : ["ninguno"]).map((item) => (
              <span className="badge danger" key={item}>{item}</span>
            ))}
          </div>
        </section>
        <section className="memory-section">
          <div className="muted">Matters</div>
          <div className="badge-row">
            {(memory.matter_ids?.length ? memory.matter_ids : ["ninguno"]).map((item) => (
              <span className="badge" key={item}>{item}</span>
            ))}
          </div>
        </section>
      </div>
    </article>
  );
}
