import type { Approval } from "@/lib/data";

type ApprovalQueueProps = {
  approvals: Approval[];
};

export default function ApprovalQueue({ approvals }: ApprovalQueueProps) {
  return (
    <div className="grid two">
      {approvals.map((approval) => (
        <article className="card" key={approval.id}>
          <div className="section-head">
            <h2>{approval.title}</h2>
            <span className="badge warn">{approval.status}</span>
          </div>
          <div className="badge-row">
            <span className="badge">{approval.type}</span>
            <span className="badge">{approval.matter_id}</span>
            <span className="badge">{approval.document_id || "ningún documento"}</span>
          </div>
        </article>
      ))}
    </div>
  );
}
