import { CalendarClock, Database, FileText, FolderOpen, LayoutGrid } from "lucide-react";
import type { WorkspaceOverview } from "@/lib/data";
import WorkspaceToolCard from "@/components/WorkspaceToolCard";

type WorkspaceSurfaceProps = {
  overview: WorkspaceOverview;
};

export default function WorkspaceSurface({ overview }: WorkspaceSurfaceProps) {
  return (
    <>
      <div className="grid stats">
        <WorkspaceToolCard title="Drive" count={overview.clientFolders.length} detail="carpetas de clientes" icon={<FolderOpen size={22} />} />
        <WorkspaceToolCard title="Calendar" count={overview.upcomingTasks.length} detail="tareas con fecha" icon={<CalendarClock size={22} />} />
        <WorkspaceToolCard title="Docs" count={overview.documentQueue.length} detail="documentos y borradores" icon={<FileText size={22} />} />
        <WorkspaceToolCard title="Sheets" count={overview.sheetRegistry.length} detail="tablas de control" icon={<Database size={22} />} />
        <WorkspaceToolCard title="Matters" count={overview.clientFolders.reduce((total, item) => total + item.matterCount, 0)} detail="asuntos ligados" icon={<LayoutGrid size={22} />} />
      </div>

      <div className="grid two dashboard-lower">
        <section className="card">
          <div className="section-head">
            <h2>Drive por cliente</h2>
            <FolderOpen size={18} />
          </div>
          <table className="table compact-table">
            <thead>
              <tr>
                <th>Cliente</th>
                <th>Carpeta</th>
                <th>Matters</th>
                <th>Docs</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {overview.clientFolders.map((client) => (
                <tr key={client.clientId}>
                  <td>{client.clientName}</td>
                  <td>{client.sourceFolderUrl ? "Drive ligado" : client.path}</td>
                  <td>{client.matterCount}</td>
                  <td>{client.documentCount}</td>
                  <td><span className={`badge ${client.seniorStatus === "blocked" ? "danger" : ""}`}>{client.seniorStatus || "pendiente"}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="card">
          <div className="section-head">
            <h2>Calendar y tareas</h2>
            <CalendarClock size={18} />
          </div>
          <table className="table compact-table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Tarea</th>
                <th>Matter</th>
              </tr>
            </thead>
            <tbody>
              {overview.upcomingTasks.slice(0, 5).map((task) => (
                <tr key={task.id}>
                  <td>{task.dueDate}</td>
                  <td>{task.title}</td>
                  <td>{task.matterId}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>

      <div className="grid two dashboard-lower">
        <section className="card">
          <div className="section-head">
            <h2>Docs en trabajo</h2>
            <FileText size={18} />
          </div>
          <table className="table compact-table">
            <thead>
              <tr>
                <th>Documento</th>
                <th>Matter</th>
                <th>Tipo</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {overview.documentQueue.slice(0, 6).map((doc) => (
                <tr key={doc.id}>
                  <td>{doc.title}</td>
                  <td>{doc.matterId}</td>
                  <td>{doc.type}</td>
                  <td><span className="badge">{doc.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="card">
          <div className="section-head">
            <h2>Sheets / control maestro</h2>
            <Database size={18} />
          </div>
          <div className="badge-row">
            {overview.sheetRegistry.map((sheet) => (
              <span className="badge" key={sheet.name}>{sheet.name}{sheet.url ? " ligado" : ""}</span>
            ))}
          </div>
          <table className="table compact-table">
            <tbody>
              {overview.sheetRegistry.map((sheet) => (
                <tr key={sheet.name}>
                  <th>{sheet.name}</th>
                  <td>{sheet.purpose}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </>
  );
}
