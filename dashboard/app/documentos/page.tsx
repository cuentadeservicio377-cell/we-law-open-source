import { getSummary } from "@/lib/data";

export default function DocumentosPage() {
  const { documents } = getSummary();

  return (
    <>
      <h1 className="page-title">Documentos</h1>
      <p className="page-subtitle">Borradores, versiones y rutas de trabajo.</p>
      <section className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Documento</th>
              <th>Matter</th>
              <th>Tipo</th>
              <th>Version</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr key={doc.id}>
                <td>{doc.title}</td>
                <td>{doc.matter_id}</td>
                <td>{doc.type}</td>
                <td>{doc.version}</td>
                <td><span className="badge warn">{doc.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
