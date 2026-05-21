import type { ReactNode } from "react";

type WorkspaceToolCardProps = {
  title: string;
  count: string | number;
  detail: string;
  icon: ReactNode;
};

export default function WorkspaceToolCard({ title, count, detail, icon }: WorkspaceToolCardProps) {
  return (
    <article className="card stat">
      <div className="stat-icon">{icon}</div>
      <div>
        <span className="stat-value">{count}</span>
        <span className="stat-label">{title}</span>
        <div className="muted">{detail}</div>
      </div>
    </article>
  );
}
