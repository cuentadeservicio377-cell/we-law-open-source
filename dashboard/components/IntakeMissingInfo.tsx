type IntakeMissingInfoProps = {
  id: string;
  status: string;
  clientName: string;
  matterDescription: string;
  missing: string[];
  nextQuestions: string[];
};

export default function IntakeMissingInfo({
  id,
  status,
  clientName,
  matterDescription,
  missing,
  nextQuestions,
}: IntakeMissingInfoProps) {
  return (
    <article className="card">
      <div className="section-head">
        <h2>Sesión {id}</h2>
        <span className="badge warn">{status}</span>
      </div>
      <table className="table compact-table">
        <tbody>
          <tr><th>Cliente</th><td>{clientName}</td></tr>
          <tr><th>Asunto</th><td>{matterDescription || "pendiente"}</td></tr>
          <tr><th>Faltan</th><td>{missing.join(" · ") || "ninguno"}</td></tr>
          <tr><th>Siguiente</th><td>{nextQuestions[0] || "Convertir a matter"}</td></tr>
        </tbody>
      </table>
    </article>
  );
}
