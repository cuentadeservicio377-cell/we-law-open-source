type LiveFilePanelProps = {
  matterId: string;
  clientName: string;
  liveFile: string;
};

export default function LiveFilePanel({ matterId, clientName, liveFile }: LiveFilePanelProps) {
  return (
    <section className="card">
      <div className="section-head">
        <h2>Expediente vivo</h2>
        <span className="badge">texto operativo</span>
      </div>
      <p className="muted">{matterId} · {clientName}</p>
      <pre className="live-file">{liveFile}</pre>
    </section>
  );
}
