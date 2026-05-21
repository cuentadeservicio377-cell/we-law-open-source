import { getWorkspaceOverview } from "@/lib/data";
import WorkspaceSurface from "@/components/WorkspaceSurface";

export default function WorkspacePage() {
  const overview = getWorkspaceOverview();

  return (
    <>
      <div className="page-hero">
        <div>
          <h1 className="page-title">Workspace</h1>
          <p className="page-subtitle">La oficina operativa del despacho: Drive, Calendar, Tasks, Docs y Sheets organizados por cliente y asunto.</p>
        </div>
        <div className="badge-row">
          <span className="badge">{overview.clientFolders.length} carpetas</span>
          <span className="badge">{overview.upcomingTasks.length} tareas con fecha</span>
          <span className="badge">{overview.documentQueue.length} docs en trabajo</span>
        </div>
      </div>
      <WorkspaceSurface overview={overview} />
    </>
  );
}
