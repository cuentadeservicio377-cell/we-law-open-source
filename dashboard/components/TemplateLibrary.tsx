import type { TemplateRecord } from "@/lib/data";

type TemplateLibraryProps = {
  templates: TemplateRecord[];
};

export default function TemplateLibrary({ templates }: TemplateLibraryProps) {
  return (
    <div className="grid two">
      {templates.map((template) => (
        <article className="card" key={template.id}>
          <div className="section-head">
            <h2>{template.title}</h2>
            <span className={template.drive_ready ? "badge ok" : "badge warn"}>
              {template.drive_ready ? "drive ready" : "pendiente"}
            </span>
          </div>
          <div className="badge-row">
            <span className="badge">{template.area}</span>
            <span className="badge">{template.document_type}</span>
            <span className="badge">{template.status || "listo para revisión"}</span>
          </div>
          <div className="memory-section">
            <div className="muted">Variables</div>
            <div className="badge-row">
              {(template.variables.length ? template.variables : ["ninguna"]).map((variable) => (
                <span className="badge" key={variable}>{variable}</span>
              ))}
            </div>
          </div>
          <p className="muted">{template.path}</p>
        </article>
      ))}
    </div>
  );
}
