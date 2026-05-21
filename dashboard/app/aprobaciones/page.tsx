import ApprovalQueue from "@/components/ApprovalQueue";
import { getSummary } from "@/lib/data";

export default function AprobacionesPage() {
  const { approvals } = getSummary();

  return (
    <>
      <div className="page-hero">
        <div>
          <h1 className="page-title">Aprobaciones</h1>
          <p className="page-subtitle">Decisiones que Hermes no debe tomar sin the lawyer.</p>
        </div>
        <div className="badge-row">
          <span className="badge warn">{approvals.length} decisiones</span>
          <span className="badge">Requieren visto bueno</span>
          <span className="badge">Bloquean entregables</span>
        </div>
      </div>
      <ApprovalQueue approvals={approvals} />
    </>
  );
}
