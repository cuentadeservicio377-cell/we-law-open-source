"use client";

import type { LiveActionIntent } from "@/lib/live-state";
import { ClipboardList, FolderOpen, RotateCcw, ShieldAlert, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";

type LiveActionRailProps = {
  actions: LiveActionIntent[];
};

const actionConfig: Record<LiveActionIntent["kind"], { label: string; icon: typeof Sparkles; href?: string }> = {
  refresh_snapshot: { label: "Refrescar estado", icon: RotateCcw },
  prepare_intake: { label: "Preparar intake", icon: ClipboardList, href: "/intake" },
  create_issue: { label: "Crear issue", icon: Sparkles, href: "/aprobaciones" },
  request_writeback: { label: "Abrir aprobaciones", icon: ShieldAlert, href: "/aprobaciones" },
  open_target: { label: "Abrir Workspace", icon: FolderOpen, href: "/workspace" },
  mark_blocked: { label: "Marcar bloqueado", icon: ShieldAlert, href: "/aprobaciones" },
};

export default function LiveActionRail({ actions }: LiveActionRailProps) {
  const router = useRouter();

  return (
    <section className="live-action-rail" aria-label="Intents seguros de Hermes">
      <div className="live-action-rail-head">
        <span className="today-eyebrow">Acciones seguras</span>
        <p>Hermes decide, la UI solo expresa el intento y navega a la superficie correcta.</p>
      </div>
      <div className="live-action-rail-actions">
        {actions.map((action, index) => {
          const config = actionConfig[action.kind];
          const Icon = config.icon;
          const key = `${action.kind}-${index}`;
          if (action.kind === "refresh_snapshot") {
            return (
              <button
                className="today-action"
                key={key}
                type="button"
                onClick={() => {
                  router.refresh();
                }}
              >
                <Icon size={14} />
                <span>{config.label}</span>
              </button>
            );
          }
          return (
            <button
              className="today-action"
              key={key}
              type="button"
              onClick={() => {
                if (config.href) router.push(config.href);
              }}
            >
              <Icon size={14} />
              <span>{config.label}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
