import Link from "next/link";
import type { Client, ClientMemory, Matter } from "@/lib/data";

type ClientCardProps = {
  client: Client;
  matters: Matter[];
  memory?: ClientMemory;
};

export default function ClientCard({ client, matters, memory }: ClientCardProps) {
  const memoryFacts = memory?.facts.slice(0, 2).join(" · ") || "sin memoria cargada";
  const blocked = client.senior_status === "blocked";

  return (
    <article className="client-card">
      <div className="client-card-head">
        <div>
          <strong>{client.nombre}</strong>
          <div className="muted">{client.id} · {client.estado}</div>
        </div>
        <div className="badge-row">
          {blocked ? <span className="badge danger">Senior bloqueó entrega/firma</span> : null}
          <Link className="badge" href={`/clientes/${client.id}`}>
            Abrir expediente
          </Link>
        </div>
      </div>
      <div className="client-card-body">
        <div>
          <div className="muted">Matters</div>
          <div>{matters.length} asuntos en curso</div>
        </div>
        <div>
          <div className="muted">Memoria</div>
          <div>{memoryFacts}</div>
        </div>
        <div>
          <div className="muted">Carpeta</div>
          <div>{client.drive_path || "carpeta pendiente"}</div>
        </div>
        <div>
          <div className="muted">Faltantes</div>
          <div>{client.missing_count ?? 0} dato(s) por cerrar</div>
        </div>
        <div>
          <div className="muted">Control maestro</div>
          <div>{client.control_master_url ? "Sheet ligado" : "pendiente"}</div>
        </div>
      </div>
    </article>
  );
}
