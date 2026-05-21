import TemplateLibrary from "@/components/TemplateLibrary";
import { getSummary } from "@/lib/data";

export default function PlantillasPage() {
  const { templates } = getSummary();

  return (
    <>
      <div className="page-hero">
        <div>
          <h1 className="page-title">Plantillas</h1>
          <p className="page-subtitle">Biblioteca local legal, lista para sincronizar a Drive cuando existan credenciales.</p>
        </div>
        <div className="badge-row">
          <span className="badge">{templates.length} plantillas</span>
          <span className="badge">Variables visibles</span>
          <span className="badge">Estado drive ready</span>
        </div>
      </div>
      <TemplateLibrary templates={templates} />
    </>
  );
}
