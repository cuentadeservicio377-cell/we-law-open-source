import IntakeMissingInfo from "@/components/IntakeMissingInfo";
import IntakeWizard from "@/components/IntakeWizard";
import { getIntakeOverview, getSummary } from "@/lib/data";

export default function IntakePage() {
  const summary = getSummary();
  const intake = getIntakeOverview();

  return (
    <>
      <div className="page-hero">
        <div>
          <h1 className="page-title">Intake</h1>
          <p className="page-subtitle">Recepción jurídica para convertir transcripciones en cliente, asunto y carpeta.</p>
        </div>
        <div className="badge-row">
          <span className="badge">{summary.openIntakes} abiertas</span>
          <span className="badge">{summary.missingInfoTaxonomy.length} faltantes tipificados</span>
          <span className="badge">{summary.clients.length} clientes reutilizables</span>
        </div>
      </div>

      <div className="grid stats">
        <article className="card stat">
          <div>
            <span className="stat-value">{summary.openIntakes}</span>
            <span className="stat-label">Sesiones abiertas</span>
            <div className="muted">pendientes de completar</div>
          </div>
        </article>
        <article className="card stat">
          <div>
            <span className="stat-value">{summary.missingInfoTaxonomy.length}</span>
            <span className="stat-label">Tipos de faltante</span>
            <div className="muted">para avanzar, firma o no bloqueante</div>
          </div>
        </article>
        <article className="card stat">
          <div>
            <span className="stat-value">{summary.clients.length}</span>
            <span className="stat-label">Clientes conocidos</span>
            <div className="muted">listos para reusar</div>
          </div>
        </article>
        <article className="card stat">
          <div>
            <span className="stat-value">{summary.matters.length}</span>
            <span className="stat-label">Matters</span>
            <div className="muted">con memoria y carpeta</div>
          </div>
        </article>
      </div>

      <div className="grid two dashboard-lower">
        <IntakeWizard
          openSessions={intake.openSessions.length}
          missingInfoTaxonomy={summary.missingInfoTaxonomy}
          recentPackets={intake.recentPackets}
        />

        <section className="card">
          <div className="section-head">
            <h2>Sesiones abiertas</h2>
          </div>
          <div className="grid intake-stack">
            {intake.openSessions.map((session) => (
              <IntakeMissingInfo
                key={session.id}
                id={session.id}
                status={session.status}
                clientName={session.collected.client_name || session.client_id || "pendiente"}
                matterDescription={session.collected.matter_description || "pendiente"}
                missing={session.missing}
                nextQuestions={session.next_questions}
              />
            ))}
          </div>
        </section>
      </div>
    </>
  );
}
