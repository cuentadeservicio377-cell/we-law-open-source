import Link from "next/link";
import { BriefcaseBusiness, ClipboardList, FileClock, FolderOpen } from "lucide-react";
import type { CommandSpineOverview } from "@/lib/data";
import type { LiveDashboardSnapshot } from "@/lib/live-state";
import LiveActionRail from "./LiveActionRail";

type TodayBriefingProps = {
  activeMatters: number;
  pendingTasks: number;
  draftDocuments: number;
  pendingApprovals: number;
  openIntakes: number;
  liveSnapshot: LiveDashboardSnapshot;
  commandSpine: CommandSpineOverview;
};

const quickActions = [
  { href: "/clientes", label: "Abrir clientes", icon: FolderOpen },
  { href: "/matters", label: "Abrir asuntos", icon: BriefcaseBusiness },
  { href: "/intake", label: "Continuar intake", icon: ClipboardList },
  { href: "/aprobaciones", label: "Ver aprobaciones", icon: FileClock },
];

export default function TodayBriefing({
  activeMatters,
  pendingTasks,
  draftDocuments,
  pendingApprovals,
  openIntakes,
  liveSnapshot,
  commandSpine,
}: TodayBriefingProps) {
  return (
    <section className="card today-briefing">
      <div className="today-briefing-copy">
        <div className="today-eyebrow">Mesa de hoy</div>
        <h2>Qué necesita tu atención primero</h2>
        <p>
          Hermes ya tiene el despacho ordenado. Hoy puedes concentrarte en {pendingApprovals} aprobaciones,
          {pendingTasks} tareas pendientes y {openIntakes} intakes que todavía necesitan cierre.
        </p>
        <div className="today-live-state">
          <span className={`status-pill ${liveSnapshot.workspace.status === "healthy" ? "ok" : "warn"}`}>
            Workspace {liveSnapshot.workspace.status === "healthy" ? "activo" : liveSnapshot.workspace.status}
          </span>
          <span className={`status-pill ${liveSnapshot.paperclip.status === "healthy" ? "ok" : "warn"}`}>
            Paperclip {liveSnapshot.paperclip.status === "healthy" ? "operativo" : liveSnapshot.paperclip.status}
          </span>
          <span className="status-pill warn">
            Sincronización {liveSnapshot.workspace.lastSyncAt ? new Date(liveSnapshot.workspace.lastSyncAt).toLocaleString("es-MX") : "pendiente"}
          </span>
        </div>
        <div className="today-live-detail">
          <span>{liveSnapshot.workspace.detail ?? "Workspace sin detalle de probe."}</span>
          <span>{liveSnapshot.paperclip.detail ?? "Paperclip sin detalle de probe."}</span>
          <span>{liveSnapshot.commandSpine.detail ?? "Hermes Managing Partner coordina la firma."}</span>
        </div>
        <div className="firm-spine-panel" aria-label="Cadena de mando del despacho">
          <div className="firm-spine-heading">
            <span>Cadena de mando</span>
            <strong>Hermes Managing Partner</strong>
          </div>
          <div className="firm-spine-chain">
            {commandSpine.chain.map((item) => (
              <article key={item.id}>
                <strong>{item.label.replace(" / ", " ")}</strong>
                <span>{item.authority}</span>
              </article>
            ))}
          </div>
          <p>Paperclip staff ejecuta con paquetes de contexto; Workspace conserva el expediente; Aprobacion queda en the lawyer.</p>
        </div>
        <LiveActionRail actions={liveSnapshot.actions} />
      </div>

      <div className="today-briefing-stats">
        <article>
          <strong>{activeMatters}</strong>
          <span>asuntos en marcha</span>
        </article>
        <article>
          <strong>{draftDocuments}</strong>
          <span>documentos en borrador</span>
        </article>
        <article>
          <strong>{openIntakes}</strong>
          <span>intakes abiertos</span>
        </article>
      </div>

      <div className="today-briefing-actions">
        {quickActions.map((action) => {
          const Icon = action.icon;
          return (
            <Link className="today-action" href={action.href} key={action.href}>
              <Icon size={14} />
              <span>{action.label}</span>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
