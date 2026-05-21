import Link from "next/link";
import { notFound } from "next/navigation";
import ClientMemoryPanel from "@/components/ClientMemoryPanel";
import { getClientDetail } from "@/lib/data";

type ClientPageProps = {
  params: Promise<{ id: string }>;
};

export default async function ClientDetailPage({ params }: ClientPageProps) {
  const { id } = await params;
  const detail = getClientDetail(id);
  if (!detail) {
    notFound();
  }

  return (
    <>
      <div className="page-hero detail-hero">
        <div>
          <h1 className="page-title">{detail.client.nombre}</h1>
          <p className="page-subtitle">{detail.client.id} · {detail.client.estado} · {detail.client.drive_path || "sin carpeta"}</p>
        </div>
        <div className="badge-row">
          <span className="badge">{detail.matters.length} asuntos</span>
          <span className="badge">{detail.tasks.length} tareas</span>
          <span className="badge">{detail.documents.length} documentos</span>
          <Link className="badge" href="/clientes">
            Volver a clientes
          </Link>
        </div>
      </div>

      <div className="grid stats">
        <article className="card">
          <span className="muted">Matters</span>
          <div className="stat-value">{detail.matters.length}</div>
        </article>
        <article className="card">
          <span className="muted">Tareas</span>
          <div className="stat-value">{detail.tasks.length}</div>
        </article>
        <article className="card">
          <span className="muted">Documentos</span>
          <div className="stat-value">{detail.documents.length}</div>
        </article>
        <article className="card">
          <span className="muted">Aprobaciones</span>
          <div className="stat-value">{detail.approvals.length}</div>
        </article>
      </div>

      <div className="grid two dashboard-lower">
        <ClientMemoryPanel memory={detail.memory} />

        <section className="card">
          <div className="section-head">
            <h2>Intake y seguimiento</h2>
          </div>
          <table className="table compact-table">
            <tbody>
              <tr><th>Sesiones</th><td>{detail.intakeSessions.length}</td></tr>
              <tr><th>Documentos</th><td>{detail.documents.map((doc) => doc.title).join(" · ") || "ninguno"}</td></tr>
              <tr><th>Tareas</th><td>{detail.tasks.map((task) => task.title).join(" · ") || "ninguna"}</td></tr>
              <tr><th>Aprobaciones</th><td>{detail.approvals.map((approval) => approval.title).join(" · ") || "ninguna"}</td></tr>
            </tbody>
          </table>
        </section>
      </div>

      <div className="grid two dashboard-lower">
        <section className="card">
          <div className="section-head">
            <h2>Matters</h2>
          </div>
          <table className="table compact-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Descripcion</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {detail.matters.map((matter) => (
                <tr key={matter.id}>
                  <td>{matter.id}</td>
                  <td>{matter.descripcion}</td>
                  <td><span className="badge">{matter.estado}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="card">
          <div className="section-head">
            <h2>Documentos y carpeta</h2>
          </div>
          <table className="table compact-table">
            <tbody>
              {detail.documents.map((doc) => (
                <tr key={doc.id}>
                  <th>{doc.title}</th>
                  <td>{doc.drive_path || "sin ruta"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </>
  );
}
