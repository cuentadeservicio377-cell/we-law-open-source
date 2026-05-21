import NotebookCard from "@/components/NotebookCard";
import { getSummary } from "@/lib/data";

export default function MemoriaPage() {
  const { clientMemories } = getSummary();

  return (
    <>
      <div className="page-hero">
        <div>
          <h1 className="page-title">Memoria</h1>
          <p className="page-subtitle">Contexto persistente por cliente para Hermes y workers de Paperclip.</p>
        </div>
        <div className="badge-row">
          <span className="badge">{clientMemories.length} cuadernos</span>
          <span className="badge">Hechos reutilizables</span>
          <span className="badge">Riesgos y preferencias</span>
        </div>
      </div>
      <div className="grid two">
        {clientMemories.map((memory) => (
          <NotebookCard key={memory.client_id} memory={memory} />
        ))}
      </div>
    </>
  );
}
