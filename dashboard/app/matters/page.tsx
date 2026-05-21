import Link from "next/link";
import { getSummary } from "@/lib/data";

export default function MattersPage() {
  const { matters, operations } = getSummary();
  const blocked = operations.filter((item) => item.blockers.length).length;

  return (
    <>
      <div className="page-hero">
        <div>
          <h1 className="page-title">Asuntos</h1>
          <p className="page-subtitle">Expedientes vivos por cliente, con acceso a la ficha completa del asunto.</p>
        </div>
        <div className="badge-row">
          <span className="badge">{matters.length} asuntos</span>
          <span className="badge warn">{blocked} con faltantes</span>
          <span className="badge">{operations.length} rooms operativos</span>
        </div>
      </div>
      <div className="grid two">
        {matters.map((matter) => (
          <article className="card matter-card" key={matter.id}>
            <div className="section-head">
              <h2>{matter.id}</h2>
              <Link className="badge" href={`/matters/${matter.id}`}>
                Abrir room
              </Link>
            </div>
            <p className="muted">{matter.cliente}</p>
            <div className="matter-card-body">
              <div>
                <div className="muted">Descripcion</div>
                <div>{matter.descripcion}</div>
              </div>
              <div className="badge-row">
                <span className="badge">{matter.fase || matter.estado}</span>
                <span className="badge">{matter.tipo}</span>
              </div>
            </div>
          </article>
        ))}
      </div>
    </>
  );
}
