import { getSummary } from "@/lib/data";
import LawyerCommandStrip from "./LawyerCommandStrip";
import TopBarStatus from "./TopBarStatus";

const links = [
  ["Hoy", "/"],
  ["Clientes", "/clientes"],
  ["Asuntos", "/matters"],
  ["Intake", "/intake"],
  ["Workspace", "/workspace"],
  ["Memoria", "/memoria"],
  ["Plazos", "/plazos"],
  ["Plantillas", "/plantillas"],
  ["Aprobaciones", "/aprobaciones"],
];

export default function Nav() {
  const summary = getSummary();
  return (
    <header className="topbar">
      <div className="topbar-head">
        <div className="topbar-brand">
          <div className="brand">Hermes We Law OS</div>
          <div className="brand-subtitle">Centro de control del despacho</div>
        </div>
        <TopBarStatus />
      </div>
      <div className="topbar-command-row">
        <LawyerCommandStrip clients={summary.clients.slice(0, 8)} matters={summary.matters.slice(0, 8)} />
        <nav className="navlinks" aria-label="Navegacion principal">
          {links.map(([label, href]) => (
            <a key={href} href={href}>
              {label}
            </a>
          ))}
        </nav>
      </div>
    </header>
  );
}
