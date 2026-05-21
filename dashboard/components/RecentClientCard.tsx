import Link from "next/link";
import type { Client, ClientMemory, Matter } from "@/lib/data";

type RecentClientCardProps = {
  client: Client;
  matters: Matter[];
  memory?: ClientMemory;
};

export default function RecentClientCard({ client, matters, memory }: RecentClientCardProps) {
  const memoryFacts = memory?.facts.slice(0, 2).join(" · ") || "sin memoria cargada";
  const lastMatter = matters[0];

  return (
    <article className="client-card">
      <div className="client-card-head">
        <div>
          <strong>{client.nombre}</strong>
          <div className="muted">{client.id} · {client.estado}</div>
        </div>
        <span className="badge">{matters.length} matters</span>
      </div>
      <div className="client-card-body">
        <div>
          <div className="muted">Memoria</div>
          <div>{memoryFacts}</div>
        </div>
        <div>
          <div className="muted">Ultimo asunto</div>
          <div>{lastMatter?.descripcion || "sin asunto activo"}</div>
        </div>
        <div>
          <div className="muted">Carpeta</div>
          <div>{client.drive_path || "carpeta pendiente"}</div>
        </div>
        <Link className="client-card-link" href={`/clientes/${client.id}`}>
          Abrir ficha
        </Link>
      </div>
    </article>
  );
}
