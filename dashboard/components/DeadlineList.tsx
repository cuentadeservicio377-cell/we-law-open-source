import type { Task } from "@/lib/data";

type DeadlineListProps = {
  tasks: Task[];
};

export default function DeadlineList({ tasks }: DeadlineListProps) {
  return (
    <section className="card">
      <div className="section-head">
        <h2>Vencimientos del despacho</h2>
      </div>
      <div className="deadline-list">
        {tasks.map((task) => (
          <article className="deadline-item" key={task.id}>
            <div className="deadline-date">{task.due_date || "sin fecha"}</div>
            <div className="deadline-body">
              <strong>{task.title}</strong>
              <span>{task.owner || "Despacho Legal"}</span>
            </div>
            <span className="badge">{task.priority || "media"}</span>
          </article>
        ))}
      </div>
    </section>
  );
}
