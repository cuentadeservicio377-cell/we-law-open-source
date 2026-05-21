"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { BriefcaseBusiness, FileText, Search, Users } from "lucide-react";
import type { Client, Matter } from "@/lib/data";
import { useRouter } from "next/navigation";

type LawyerCommandStripProps = {
  clients: Pick<Client, "id" | "nombre" | "estado" | "drive_path">[];
  matters: Pick<Matter, "id" | "client_id" | "cliente" | "tipo" | "descripcion" | "estado">[];
};

const quickActions = [
  { label: "Nuevo cliente", href: "/intake?mode=client", icon: Users },
  { label: "Nuevo asunto", href: "/intake?mode=matter", icon: BriefcaseBusiness },
  { label: "Nueva transcripción", href: "/intake?mode=transcript", icon: FileText },
];

function normalize(value: string) {
  return value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

export default function LawyerCommandStrip({ clients, matters }: LawyerCommandStripProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const normalized = normalize(query.trim());

  const clientMatches = useMemo(() => {
    if (!normalized) return clients.slice(0, 4);
    return clients
      .filter((client) =>
        normalize([client.nombre, client.estado, client.drive_path || ""].join(" ")).includes(normalized),
      )
      .slice(0, 4);
  }, [clients, normalized]);

  const matterMatches = useMemo(() => {
    if (!normalized) return matters.slice(0, 4);
    return matters
      .filter((matter) =>
        normalize([matter.id, matter.cliente, matter.tipo, matter.descripcion, matter.estado].join(" ")).includes(normalized),
      )
      .slice(0, 4);
  }, [matters, normalized]);

  const jumpToFirstMatch = () => {
    const client = clientMatches[0];
    if (client) {
      router.push(`/clientes/${client.id}`);
      return;
    }
    const matter = matterMatches[0];
    if (matter) {
      router.push(`/matters/${matter.id}`);
    }
  };

  return (
    <section className="command-strip" aria-label="Comandos rápidos del despacho">
      <div className="command-strip-inputs">
        <label className="command-strip-search">
          <span>Buscar cliente, asunto o expediente</span>
          <div className="command-strip-field">
            <Search size={16} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  jumpToFirstMatch();
                }
              }}
              placeholder="Escribe un nombre, matter o carpeta"
              aria-label="Buscar cliente, asunto o expediente"
              autoComplete="off"
            />
          </div>
        </label>

        <label className="command-strip-switcher">
          <span>Ir a cliente</span>
          <select
            aria-label="Ir a cliente"
            defaultValue=""
            onChange={(event) => {
              if (event.target.value) {
                router.push(`/clientes/${event.target.value}`);
              }
            }}
          >
            <option value="">Seleccionar</option>
            {clients.map((client) => (
              <option key={client.id} value={client.id}>
                {client.nombre}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="command-strip-actions">
        {quickActions.map((action) => {
          const Icon = action.icon;
          return (
            <Link key={action.href} className="command-action" href={action.href}>
              <Icon size={14} />
              <span>{action.label}</span>
            </Link>
          );
        })}
      </div>

      <div className="command-strip-results" aria-label="Resultados rápidos">
        <div className="command-strip-column">
          <div className="command-strip-heading">
            <Users size={14} />
            <span>Clientes visibles</span>
          </div>
          {clientMatches.map((client) => (
            <Link key={client.id} className="command-result" href={`/clientes/${client.id}`}>
              <strong>{client.nombre}</strong>
              <span>{client.estado}</span>
            </Link>
          ))}
          {!clientMatches.length ? <p className="command-empty">Sin coincidencias de cliente.</p> : null}
        </div>

        <div className="command-strip-column">
          <div className="command-strip-heading">
            <BriefcaseBusiness size={14} />
            <span>Asuntos visibles</span>
          </div>
          {matterMatches.map((matter) => (
            <Link key={matter.id} className="command-result" href={`/matters/${matter.id}`}>
              <strong>{matter.id}</strong>
              <span>{matter.cliente}</span>
            </Link>
          ))}
          {!matterMatches.length ? <p className="command-empty">Sin coincidencias de asunto.</p> : null}
        </div>
      </div>
    </section>
  );
}
