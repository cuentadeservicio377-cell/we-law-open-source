import { getSummary } from "@/lib/data";
import ClientCard from "@/components/ClientCard";

export default function ClientesPage() {
  const { clients, matters, clientMemories } = getSummary();

  return (
    <>
      <div className="page-hero">
        <div>
          <h1 className="page-title">Clientes</h1>
          <p className="page-subtitle">Directorio vivo del despacho, con memoria, matters y carpeta de trabajo.</p>
        </div>
        <div className="badge-row">
          <span className="badge">{clients.length} clientes</span>
          <span className="badge">{matters.length} asuntos</span>
          <span className="badge">{clientMemories.length} memorias</span>
        </div>
      </div>
      <div className="grid two">
        {clients.map((client) => (
          <ClientCard
            key={client.id}
            client={client}
            matters={matters.filter((matter) => matter.client_id === client.id)}
            memory={clientMemories.find((memory) => memory.client_id === client.id)}
          />
        ))}
      </div>
    </>
  );
}
