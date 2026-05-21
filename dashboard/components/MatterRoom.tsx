import type { MatterDetail } from "@/lib/data";

type MatterRoomProps = {
  detail: MatterDetail;
};

export default function MatterRoom({ detail }: MatterRoomProps) {
  const blockers = detail.documents.some((doc) => doc.status === "borrador") ? "documentos en borrador" : "sin bloqueo";

  return (
    <section className="card matter-room-panel">
      <div className="section-head">
        <h2>Room del asunto</h2>
        <span className="badge">{detail.matter.estado}</span>
      </div>
      <p className="muted">{detail.matter.descripcion}</p>
      <div className="matter-room-summary">
        <article>
          <span>Cliente</span>
          <strong>{detail.client?.nombre || detail.matter.cliente}</strong>
        </article>
        <article>
          <span>Fase</span>
          <strong>{detail.matter.fase || detail.matter.estado}</strong>
        </article>
        <article>
          <span>Siguiente acción</span>
          <strong>{detail.tasks[0]?.title || "Revisar expediente"}</strong>
        </article>
        <article>
          <span>Bloqueo</span>
          <strong>{blockers}</strong>
        </article>
      </div>
      <div className="badge-row">
        <span className="badge">Documentos {detail.documents.length}</span>
        <span className="badge">Aprobaciones {detail.approvals.length}</span>
        <span className="badge">Tareas {detail.tasks.length}</span>
      </div>
    </section>
  );
}
