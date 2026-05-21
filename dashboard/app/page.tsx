import { CalendarClock, BriefcaseBusiness, FileText } from "lucide-react";
import { getCommandSpineOverview, getSummary } from "@/lib/data";
import { getLiveDashboardSnapshotLive } from "@/lib/live-state";
import TodayBriefing from "@/components/TodayBriefing";
import TodaySummary from "@/components/TodaySummary";
import RecentClientCard from "@/components/RecentClientCard";
import HermesRequestsPanel from "@/components/HermesRequestsPanel";

export default async function DashboardPage() {
  const summary = getSummary();
  const commandSpine = getCommandSpineOverview();
  const liveSnapshot = await getLiveDashboardSnapshotLive();
  const recentClients = summary.clients.slice(0, 3).map((client) => ({
    client,
    matters: summary.matters.filter((matter) => matter.client_id === client.id).slice(0, 2),
    memory: summary.clientMemories.find((memory) => memory.client_id === client.id),
  }));
  const agenda = summary.tasks
    .filter((task) => task.due_date)
    .slice()
    .sort((left, right) => String(left.due_date).localeCompare(String(right.due_date)))
    .slice(0, 5);

  return (
    <>
      <div className="page-hero today-hero">
        <div>
          <h1 className="page-title">Hoy</h1>
          <p className="page-subtitle">Lo que necesita atención ahora mismo en el despacho.</p>
        </div>
        <div className="badge-row">
          <span className={`badge ${liveSnapshot.workspace.status === "healthy" ? "ok" : "warn"}`}>Workspace {liveSnapshot.workspace.status === "healthy" ? "activo" : liveSnapshot.workspace.status}</span>
          <span className={`badge ${liveSnapshot.paperclip.status === "healthy" ? "ok" : "warn"}`}>Paperclip {liveSnapshot.paperclip.status === "healthy" ? "operativo" : liveSnapshot.paperclip.status}</span>
          <span className="badge warn">Sincronización {liveSnapshot.workspace.lastSyncAt ? new Date(liveSnapshot.workspace.lastSyncAt).toLocaleString("es-MX") : "pendiente"}</span>
        </div>
      </div>

      <TodayBriefing
        activeMatters={summary.activeMatters}
        pendingTasks={summary.pendingTasks}
        draftDocuments={summary.draftDocuments}
        pendingApprovals={summary.pendingApprovals}
        openIntakes={summary.openIntakes}
        liveSnapshot={liveSnapshot}
        commandSpine={commandSpine}
      />

      <TodaySummary
        activeMatters={summary.activeMatters}
        pendingTasks={summary.pendingTasks}
        draftDocuments={summary.draftDocuments}
        pendingApprovals={summary.pendingApprovals}
        openIntakes={summary.openIntakes}
        templateCount={summary.templateCount}
      />

      <div className="grid today-grid">
        <section className="card">
          <div className="section-head">
            <h2>Agenda de hoy</h2>
            <CalendarClock size={18} />
          </div>
          <div className="agenda-list">
            {agenda.map((task) => (
              <article className="agenda-item" key={task.id}>
                <div className="agenda-date">{task.due_date}</div>
                <div className="agenda-content">
                  <strong>{task.title}</strong>
                  <span>{task.owner || "Despacho Legal"}</span>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="card">
          <div className="section-head">
            <h2>Clientes recientes</h2>
            <BriefcaseBusiness size={18} />
          </div>
          <div className="client-stack">
            {recentClients.map(({ client, matters, memory }) => (
              <RecentClientCard key={client.id} client={client} matters={matters} memory={memory} />
            ))}
          </div>
        </section>

        <HermesRequestsPanel intakeSessions={summary.intakeSessions} blockers={summary.operations} />
      </div>

      <section className="card dashboard-lower">
        <div className="section-head">
          <h2>Actividad Paperclip</h2>
          <FileText size={18} />
        </div>
        <table className="table operations-table">
          <thead>
            <tr>
              <th>Matter</th>
              <th>Siguiente accion</th>
              <th>Estado</th>
              <th>Artefactos</th>
            </tr>
          </thead>
          <tbody>
            {summary.operations.slice(0, 4).map((matter) => (
              <tr key={matter.id}>
                <td>
                  <strong>{matter.id}</strong>
                  <br />
                  <span className="muted">{matter.cliente}</span>
                </td>
                <td>{matter.nextAction}</td>
                <td>{matter.blockers.length ? <span className="badge warn">con faltantes</span> : <span className="badge ok">flujo estable</span>}</td>
                <td>{matter.artifactPresence.documents} docs / {matter.artifactPresence.tasks} tareas / {matter.artifactPresence.approvals} aprob.</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
