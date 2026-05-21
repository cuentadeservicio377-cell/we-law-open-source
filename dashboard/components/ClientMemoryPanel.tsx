import type { ClientMemory } from "@/lib/data";

type ClientMemoryPanelProps = {
  memory?: ClientMemory;
};

export default function ClientMemoryPanel({ memory }: ClientMemoryPanelProps) {
  if (!memory) {
    return (
      <section className="card">
        <div className="section-head">
          <h2>Cuaderno del cliente</h2>
        </div>
        <p className="muted">Todavía no hay memoria persistente para este cliente.</p>
      </section>
    );
  }

  return (
    <section className="card client-memory-panel">
      <div className="section-head">
        <h2>Cuaderno del cliente</h2>
        <span className="badge">actualizada {memory.updated_at || "hoy"}</span>
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
    </section>
  );
}
