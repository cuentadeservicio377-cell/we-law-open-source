type IntakeWizardProps = {
  openSessions: number;
  missingInfoTaxonomy: string[];
  recentPackets?: {
    mode: string;
    created_at: string;
    drive_folder?: { id: string; url: string } | null;
    artifacts: {
      dashboard_snapshot?: {
        status?: string;
        client_name?: string;
        matter_description?: string;
        required_documents?: string[];
        missing_count?: number;
        paperclip_roles?: string[];
      };
      partner_briefing?: {
        summary?: string;
        next_ask?: string;
      };
    };
  }[];
};

const steps = [
  {
    title: "1. Recibir transcripción",
    body: "Pega o adjunta la conversacion del cliente. Hermes la lee primero y extrae hechos antes de preguntar.",
  },
  {
    title: "2. Identificar cliente y asunto",
    body: "Hermes reutiliza cliente si existe o crea uno nuevo, luego decide si es litigio, contrato, privacidad, cobranza u otro track.",
  },
  {
    title: "3. Completar faltantes y arrancar trabajo",
    body: "El sistema marca lo que falta para avanzar o para firma y crea carpeta, memoria, tareas y follow-up de Paperclip.",
  },
];

const hermesInstructions = [
  {
    mode: "Migrar carpeta de Drive",
    command: "Hermes, migra este cliente. Carpeta: [link de Drive]. Contexto: [quien es, que contrato, honorarios, documentos ya trabajados, revisiones y faltantes].",
    result: "Hermes clasifica fuentes, abre cliente/asunto, memoria, control maestro, faltantes y tareas Paperclip.",
  },
  {
    mode: "Nuevo cliente conversacional",
    command: "Hermes, nuevo cliente. Te mando la transcripcion inicial o te doy los datos por partes. Abre intake y dime que falta.",
    result: "Hermes crea intake parcial, pregunta lo minimo y convierte a matter cuando tenga datos suficientes.",
  },
];

export default function IntakeWizard({ openSessions, missingInfoTaxonomy, recentPackets = [] }: IntakeWizardProps) {
  return (
    <section className="card intake-control-room">
      <div className="section-head">
        <h2>Mesa de recepción Hermes</h2>
        <span className="badge warn">{openSessions} abiertos</span>
      </div>
      <div className="intake-mode-grid">
        {hermesInstructions.map((item) => (
          <article className="intake-mode-card" key={item.mode}>
            <strong>{item.mode}</strong>
            <code>{item.command}</code>
            <p className="muted">{item.result}</p>
          </article>
        ))}
      </div>
      <div className="wizard-steps">
        {steps.map((step) => (
          <article className="wizard-step" key={step.title}>
            <strong>{step.title}</strong>
            <p className="muted">{step.body}</p>
          </article>
        ))}
      </div>
      <div className="badge-row">
        {missingInfoTaxonomy.map((item) => (
          <span className="badge" key={item}>{item}</span>
        ))}
      </div>
      <div className="intake-packet-list">
        <div className="section-head compact">
          <h3>Últimos paquetes Hermes</h3>
          <span className="badge">{recentPackets.length} paquetes</span>
        </div>
        {recentPackets.length ? (
          recentPackets.map((packet) => {
            const snapshot = packet.artifacts.dashboard_snapshot || {};
            const briefing = packet.artifacts.partner_briefing || {};
            return (
              <article className="intake-packet" key={`${packet.created_at}-${packet.mode}`}>
                <div>
                  <strong>{snapshot.client_name || "Cliente por confirmar"}</strong>
                  <span>{snapshot.matter_description || packet.mode}</span>
                </div>
                <p>{briefing.summary || "Paquete de intake listo para revision."}</p>
                <div className="badge-row">
                  <span className="badge">{packet.mode}</span>
                  <span className="badge">{snapshot.required_documents?.length || 0} docs</span>
                  <span className="badge warn">{snapshot.missing_count || 0} faltantes</span>
                </div>
              </article>
            );
          })
        ) : (
          <p className="muted">Todavía no hay paquetes de intake generados por Hermes.</p>
        )}
      </div>
    </section>
  );
}
