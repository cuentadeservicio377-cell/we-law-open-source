import DeadlineList from "@/components/DeadlineList";
import { getSummary } from "@/lib/data";

export default function PlazosPage() {
  const { tasks } = getSummary();
  const deadlines = tasks.filter((task) => task.due_date);

  return (
    <>
      <div className="page-hero">
        <div>
          <h1 className="page-title">Plazos</h1>
          <p className="page-subtitle">Tareas y vencimientos operativos del despacho.</p>
        </div>
        <div className="badge-row">
          <span className="badge">{deadlines.length} vencimientos</span>
          <span className="badge">Escaneo conservador</span>
          <span className="badge">Prioridad por asunto</span>
        </div>
      </div>
      <DeadlineList tasks={deadlines} />
    </>
  );
}
