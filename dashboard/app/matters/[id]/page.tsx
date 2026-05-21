import Link from "next/link";
import { notFound } from "next/navigation";
import LiveFilePanel from "@/components/LiveFilePanel";
import MatterRoom from "@/components/MatterRoom";
import { getMatterDetail } from "@/lib/data";

type MatterPageProps = {
  params: Promise<{ id: string }>;
};

function buildLiveFile(detail: NonNullable<ReturnType<typeof getMatterDetail>>) {
  return [
    "EXPEDIENTE VIVO",
    `Matter: ${detail.matter.id}`,
    `Cliente: ${detail.client?.nombre || detail.matter.cliente}`,
    `Fase operativa: ${detail.matter.fase || detail.matter.estado}`,
    `Siguiente accion: ${detail.tasks[0]?.title || "Revisar expediente"}`,
    `Documentos: ${detail.documents.map((doc) => doc.title).join(" · ") || "ninguno"}`,
    `Aprobaciones: ${detail.approvals.map((approval) => approval.title).join(" · ") || "ninguna"}`,
    `Intake: ${detail.intakeSessions.length}`,
  ].join("\n");
}

export default async function MatterDetailPage({ params }: MatterPageProps) {
  const { id } = await params;
  const detail = getMatterDetail(id);
  if (!detail) {
    notFound();
  }

  return (
    <>
      <div className="page-hero detail-hero">
        <div>
          <h1 className="page-title">{detail.matter.id}</h1>
          <p className="page-subtitle">{detail.client?.nombre || detail.matter.cliente} · {detail.matter.descripcion}</p>
        </div>
        <div className="badge-row">
          <span className="badge">{detail.tasks.length} tareas</span>
          <span className="badge">{detail.documents.length} documentos</span>
          <span className="badge">{detail.approvals.length} aprobaciones</span>
          <Link className="badge" href="/matters">
            Volver a asuntos
          </Link>
        </div>
      </div>

      <div className="grid two dashboard-lower">
        <MatterRoom detail={detail} />
        <LiveFilePanel matterId={detail.matter.id} clientName={detail.client?.nombre || detail.matter.cliente} liveFile={buildLiveFile(detail)} />
      </div>

      <div className="grid two dashboard-lower">
        <section className="card">
          <div className="section-head">
            <h2>Tareas</h2>
          </div>
          <table className="table compact-table">
            <thead>
              <tr>
                <th>Tarea</th>
                <th>Owner</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {detail.tasks.map((task) => (
                <tr key={task.id}>
                  <td>{task.title}</td>
                  <td>{task.owner || "Despacho Legal"}</td>
                  <td><span className="badge">{task.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="card">
          <div className="section-head">
            <h2>Documentos y aprobaciones</h2>
          </div>
          <table className="table compact-table">
            <tbody>
              <tr><th>Documentos</th><td>{detail.documents.map((doc) => doc.title).join(" · ") || "ninguno"}</td></tr>
              <tr><th>Aprobaciones</th><td>{detail.approvals.map((approval) => approval.title).join(" · ") || "ninguna"}</td></tr>
              <tr><th>Intake</th><td>{detail.intakeSessions.map((session) => session.id).join(" · ") || "ninguno"}</td></tr>
            </tbody>
          </table>
        </section>
      </div>
    </>
  );
}
