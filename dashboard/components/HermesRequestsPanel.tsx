type IntakeSession = {
  id: string;
  client_id?: string | null;
  matter_id?: string | null;
  missing: string[];
  next_questions: string[];
};

type MatterBlocker = {
  id: string;
  cliente: string;
  nextAction: string;
  blockers: string[];
};

type HermesRequestsPanelProps = {
  intakeSessions: IntakeSession[];
  blockers: MatterBlocker[];
};

export default function HermesRequestsPanel({ intakeSessions, blockers }: HermesRequestsPanelProps) {
  const firstRequests = intakeSessions.slice(0, 3);
  const topBlockers = blockers.filter((matter) => matter.blockers.length).slice(0, 3);

  return (
    <section className="card">
      <div className="section-head">
        <h2>Hermes me pide</h2>
        <span className="badge warn">{firstRequests.length + topBlockers.length} pendientes</span>
      </div>

      <div className="request-stack">
        {firstRequests.map((session) => (
          <article className="request-item" key={session.id}>
            <strong>{session.client_id || "Cliente pendiente"}</strong>
            <div className="muted">{session.next_questions[0] || "Definir siguiente paso"}</div>
            <div className="badge-row">
              {session.missing.slice(0, 3).map((item) => (
                <span className="badge" key={item}>{item}</span>
              ))}
            </div>
          </article>
        ))}

        {topBlockers.map((matter) => (
          <article className="request-item" key={matter.id}>
            <strong>{matter.id} · {matter.cliente}</strong>
            <div className="muted">{matter.nextAction}</div>
            <div className="badge-row">
              {matter.blockers.slice(0, 3).map((item) => (
                <span className="badge danger" key={item}>{item}</span>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
