import type { ReactNode } from "react";

type StatCardProps = {
  label: string;
  value: string | number;
  detail: string;
  icon: ReactNode;
};

export default function StatCard({ label, value, detail, icon }: StatCardProps) {
  return (
    <section className="card stat">
      <div className="stat-icon">{icon}</div>
      <div>
        <span className="stat-value">{value}</span>
        <span className="stat-label">{label}</span>
        <div className="muted">{detail}</div>
      </div>
    </section>
  );
}
