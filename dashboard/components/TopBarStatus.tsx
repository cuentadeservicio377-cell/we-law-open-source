import { getLiveDashboardSnapshotLive } from "@/lib/live-state";

function formatSyncLabel(lastSyncAt: string | null) {
  return lastSyncAt ? `Sincronización ${new Date(lastSyncAt).toLocaleString("es-MX")}` : "Sincronización pendiente";
}

export default async function TopBarStatus() {
  const snapshot = await getLiveDashboardSnapshotLive();
  return (
    <div className="topbar-status" aria-label="Estado de plataformas">
      <span className="status-pill ok">Hermes listo</span>
      <span className={`status-pill ${snapshot.workspace.status === "healthy" ? "ok" : "warn"}`}>
        Workspace {snapshot.workspace.status === "healthy" ? "activo" : snapshot.workspace.status}
      </span>
      <span className={`status-pill ${snapshot.paperclip.status === "healthy" ? "ok" : "warn"}`}>
        Paperclip {snapshot.paperclip.status === "healthy" ? "operativo" : snapshot.paperclip.status}
      </span>
      <span className="status-pill warn">{formatSyncLabel(snapshot.workspace.lastSyncAt)}</span>
      <div className="topbar-status-detail">
        <span>{snapshot.workspace.detail ?? "Workspace sin detalle de probe."}</span>
        <span>{snapshot.paperclip.detail ?? "Paperclip sin detalle de probe."}</span>
      </div>
    </div>
  );
}
