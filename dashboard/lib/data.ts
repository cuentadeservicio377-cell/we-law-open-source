import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.cwd(), "..");
const demoMode = process.env.NEXT_PUBLIC_DEMO_MODE !== "false";

export type Client = {
  id: string;
  nombre: string;
  empresa?: string;
  estado: string;
  drive_path?: string;
  source_folder_url?: string;
  control_master_url?: string;
  senior_status?: string;
  missing_count?: number;
};

export type Matter = {
  id: string;
  client_id: string;
  cliente: string;
  tipo: string;
  estado: string;
  descripcion: string;
  fase?: string;
  honorarios?: number;
  engagement?: string;
  drive_path?: string;
  source_folder_url?: string;
  control_master_url?: string;
  senior_status?: string;
  legacy_aliases?: string[];
};

export type Task = {
  id: string;
  matter_id: string;
  title: string;
  status: string;
  owner?: string;
  priority?: string;
  due_date?: string;
};

export type Document = {
  id: string;
  matter_id: string;
  type: string;
  title: string;
  status: string;
  version?: string;
  drive_path?: string;
};

export type Approval = {
  id: string;
  matter_id: string;
  type: string;
  status: string;
  title: string;
  document_id?: string;
};

export type IntakeSession = {
  id: string;
  status: string;
  source?: string;
  client_id?: string | null;
  matter_id?: string | null;
  collected: Record<string, string>;
  missing: string[];
  next_questions: string[];
};

export type TemplateRecord = {
  id: string;
  title: string;
  area: string;
  document_type: string;
  path: string;
  variables: string[];
  status?: string;
  drive_ready?: boolean;
  review_status?: string;
  owner?: string;
  jurisdiction?: string;
  last_reviewed_at?: string | null;
};

export type FirmRole = {
  key: string;
  displayName: string;
  requiredArtifacts: string[];
  completionGates: string[];
};

export type CommandSpineOverview = {
  firm: string;
  chain: {
    id: string;
    label: string;
    authority: string;
  }[];
  requiredArtifacts: string[];
  dashboardPrinciples: string[];
};

export type MatterOperation = {
  id: string;
  cliente: string;
  fase: string;
  owner: string;
  nextAction: string;
  blockers: string[];
  signatureReadiness: "blocked" | "review" | "ready";
  deadlineStatus: "none" | "scheduled" | "attention";
  paymentStatus: "unknown" | "pending" | "authorized";
  artifactPresence: {
    documents: number;
    tasks: number;
    approvals: number;
  };
};

export type ClientMemory = {
  client_id: string;
  client_name?: string;
  facts: string[];
  preferences: string[];
  risks: string[];
  matter_ids?: string[];
  document_notes?: string[];
  updated_at?: string;
};

export type ClientDetail = {
  client: Client;
  memory?: ClientMemory;
  matters: Matter[];
  tasks: Task[];
  documents: Document[];
  approvals: Approval[];
  intakeSessions: IntakeSession[];
};

export type MatterDetail = {
  matter: Matter;
  client?: Client;
  memory?: ClientMemory;
  tasks: Task[];
  documents: Document[];
  approvals: Approval[];
  intakeSessions: IntakeSession[];
};

export type WorkspaceOverview = {
  clientFolders: {
    clientId: string;
    clientName: string;
    path: string;
    sourceFolderUrl?: string;
    controlMasterUrl?: string;
    seniorStatus?: string;
    missingCount?: number;
    matterCount: number;
    documentCount: number;
  }[];
  upcomingTasks: {
    id: string;
    matterId: string;
    title: string;
    owner?: string;
    dueDate?: string;
    priority?: string;
  }[];
  documentQueue: {
    id: string;
    matterId: string;
    title: string;
    type: string;
    status: string;
  }[];
  sheetRegistry: {
    name: string;
    purpose: string;
    url?: string;
  }[];
};

export type IntakeOverview = {
  openSessions: IntakeSession[];
  recentPackets: IntakeOrchestratorPacket[];
};

export type IntakeOrchestratorPacket = {
  mode: string;
  created_at: string;
  controller: string;
  staff_system: string;
  drive_folder?: {
    id: string;
    url: string;
  } | null;
  client?: {
    id?: string;
    nombre?: string;
    estado?: string;
    legacy_aliases?: string[];
  };
  matter?: {
    id?: string;
    client_id?: string;
    descripcion?: string;
    estado?: string;
    fase?: string;
    legacy_aliases?: string[];
  };
  workspace?: {
    source_folder?: {
      id?: string;
      url?: string;
    } | null;
    control_master?: {
      url?: string;
      spreadsheet_id?: string;
    };
    packet_file?: {
      webViewLink?: string;
      id?: string;
    };
    read?: {
      source_count?: number;
      folder_id?: string;
    };
  };
  missing_info?: Record<string, unknown>[];
  required_documents?: string[];
  senior_status?: {
    status?: string;
    decision?: string;
    reason?: string;
  };
  artifacts: {
    dashboard_snapshot?: {
      status?: string;
      client_id?: string;
      client_name?: string;
      matter_description?: string;
      matter_id?: string;
      legacy_matter_aliases?: string[];
      mode?: string;
      required_documents?: string[];
      missing_count?: number;
      paperclip_roles?: string[];
    };
    partner_briefing?: {
      summary?: string;
      next_ask?: string;
    };
  };
};

type FirmModel = {
  missingInfoTaxonomy: string[];
  roles: Record<string, {
    displayName: string;
    requiredArtifacts: { name: string; required: boolean }[];
    completionGates: string[];
  }>;
};

type FirmCommandSpine = {
  firm: string;
  actors: Record<string, { displayName: string; authority: string }>;
  chainOfCommand: string[];
  requiredArtifacts: string[];
  dashboardPrinciples: string[];
};

function readJson<T>(relative: string): T {
  const file = path.join(root, relative);
  return JSON.parse(fs.readFileSync(file, "utf8")) as T;
}

function readJsonOptional<T>(relative: string, fallback: T): T {
  const file = path.join(root, relative);
  if (!fs.existsSync(file)) return fallback;
  return JSON.parse(fs.readFileSync(file, "utf8")) as T;
}

function readClientMemories(): ClientMemory[] {
  const dir = path.join(root, "data/client_memory");
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter((file) => file.endsWith(".json"))
    .map((file) => JSON.parse(fs.readFileSync(path.join(dir, file), "utf8")) as ClientMemory);
}

function readIntakeOrchestratorPackets(): IntakeOrchestratorPacket[] {
  const dirs = [
    path.join(root, "workspace/generated/intake-orchestrator"),
    path.join(root, "fixtures/demo/intake-orchestrator"),
  ];
  const packets: IntakeOrchestratorPacket[] = [];
  for (const dir of dirs) {
    if (!fs.existsSync(dir)) continue;
    for (const file of fs.readdirSync(dir).filter((item) => item.endsWith(".json")).sort().reverse()) {
      packets.push(JSON.parse(fs.readFileSync(path.join(dir, file), "utf8")) as IntakeOrchestratorPacket);
    }
  }
  return packets.slice(0, 8);
}

export function getData() {
  const intakeOrchestratorPackets = readIntakeOrchestratorPackets();
  const derived = buildOperationalRecordsFromPackets(intakeOrchestratorPackets);
  const clients = mergeById(readJson<Client[]>("data/clients.json"), derived.clients);
  const matters = mergeById(readJson<Matter[]>("data/matters.json"), derived.matters);
  const tasks = mergeById(readJson<Task[]>("data/tasks.json"), derived.tasks);
  const documents = mergeById(readJson<Document[]>("data/documents.json"), derived.documents);
  const approvals = mergeById(readJson<Approval[]>("data/approvals.json"), derived.approvals);
  const intakeData = readJsonOptional<{ sessions: IntakeSession[] }>("data/intake_sessions.json", { sessions: [] });
  const templateData = readJsonOptional<{ templates: TemplateRecord[] }>("workspace/templates/legal/manifest.json", { templates: [] });
  const firmModel = readJson<FirmModel>("config/firm-operating-model.json");
  const commandSpine = readJson<FirmCommandSpine>("config/firm-command-spine.json");
  const clientMemories = mergeById(readClientMemories(), derived.clientMemories, "client_id");

  return { clients, matters, tasks, documents, approvals, intakeSessions: intakeData.sessions, templates: templateData.templates, firmModel, commandSpine, clientMemories, intakeOrchestratorPackets };
}

export function getSummary() {
  const data = getData();
  const operations = buildMatterOperations(data);
  const roleSections = buildRoleSections(data.tasks);
  return {
    ...data,
    operations,
    roleSections,
    firmRoles: buildFirmRoles(data.firmModel),
    commandSpine: buildCommandSpineOverview(data.commandSpine),
    missingInfoTaxonomy: data.firmModel.missingInfoTaxonomy,
    controlMasterTables: [
      "Clientes",
      "Matters",
      "Fuentes",
      "Transcripciones",
      "Hechos",
      "Documentos",
      "Faltantes",
      "Correcciones",
      "Tareas",
      "Aprobaciones",
      "Plazos",
      "Cobranza",
      "Entregables",
    ],
    documentPackageState: buildDocumentPackageState(data.documents),
    activeMatters: data.matters.filter((matter) => matter.estado === "activo").length,
    pendingTasks: data.tasks.filter((task) => !["done", "cancelled"].includes(task.status)).length,
    pendingApprovals: data.approvals.filter((approval) => approval.status === "pendiente").length,
    draftDocuments: data.documents.filter((doc) => doc.status === "borrador").length,
    openIntakes: data.intakeSessions.filter((session) => !["converted", "cancelled"].includes(session.status)).length,
    templateCount: data.templates.length,
  };
}

export function getCommandSpineOverview(): CommandSpineOverview {
  return buildCommandSpineOverview(readJson<FirmCommandSpine>("config/firm-command-spine.json"));
}

export function getClientDetail(clientId: string): ClientDetail | null {
  const data = getData();
  const client = data.clients.find((item) => item.id === clientId);
  if (!client) return null;

  const matters = data.matters.filter((matter) => matter.client_id === clientId);
  const matterIds = new Set(matters.map((matter) => matter.id));
  return {
    client,
    memory: data.clientMemories.find((memory) => memory.client_id === clientId),
    matters,
    tasks: data.tasks.filter((task) => matterIds.has(task.matter_id)),
    documents: data.documents.filter((document) => matterIds.has(document.matter_id)),
    approvals: data.approvals.filter((approval) => matterIds.has(approval.matter_id)),
    intakeSessions: data.intakeSessions.filter(
      (session) => session.client_id === clientId || (session.matter_id ? matterIds.has(session.matter_id) : false),
    ),
  };
}

export function getMatterDetail(matterId: string): MatterDetail | null {
  const data = getData();
  const matter = data.matters.find((item) => item.id === matterId);
  if (!matter) return null;

  return {
    matter,
    client: data.clients.find((client) => client.id === matter.client_id),
    memory: data.clientMemories.find((memory) => memory.client_id === matter.client_id),
    tasks: data.tasks.filter((task) => task.matter_id === matterId),
    documents: data.documents.filter((document) => document.matter_id === matterId),
    approvals: data.approvals.filter((approval) => approval.matter_id === matterId),
    intakeSessions: data.intakeSessions.filter(
      (session) => session.matter_id === matterId || session.client_id === matter.client_id,
    ),
  };
}

export function getWorkspaceOverview(): WorkspaceOverview {
  const data = getData();
  return {
    clientFolders: data.clients.map((client) => {
      const matters = data.matters.filter((matter) => matter.client_id === client.id);
      const documentCount = data.documents.filter((document) => matters.some((matter) => matter.id === document.matter_id)).length;
      return {
        clientId: client.id,
        clientName: client.nombre,
        path: client.drive_path || "carpeta pendiente",
        sourceFolderUrl: client.source_folder_url,
        controlMasterUrl: client.control_master_url,
        seniorStatus: client.senior_status,
        missingCount: client.missing_count,
        matterCount: matters.length,
        documentCount,
      };
    }),
    upcomingTasks: data.tasks
      .filter((task) => task.due_date)
      .slice()
      .sort((left, right) => String(left.due_date).localeCompare(String(right.due_date)))
      .map((task) => ({
        id: task.id,
        matterId: task.matter_id,
        title: task.title,
        owner: task.owner,
        dueDate: task.due_date,
        priority: task.priority,
      })),
    documentQueue: data.documents
      .slice()
      .sort((left, right) => left.status.localeCompare(right.status) || left.title.localeCompare(right.title))
      .map((document) => ({
        id: document.id,
        matterId: document.matter_id,
        title: document.title,
        type: document.type,
        status: document.status,
      })),
    sheetRegistry: [
      { name: "Clientes", purpose: "control maestro de clientes", url: firstControlMasterUrl(data.clients) },
      { name: "Asuntos", purpose: "control maestro de matters", url: firstControlMasterUrl(data.clients) },
      { name: "Finanzas", purpose: "cobranza y autorizaciones", url: firstControlMasterUrl(data.clients) },
      { name: "Plantillas", purpose: "biblioteca reutilizable" },
    ],
  };
}

export function getIntakeOverview(): IntakeOverview {
  const data = getData();
  return {
    openSessions: data.intakeSessions
      .filter((session) => !["converted", "cancelled"].includes(session.status))
      .slice()
      .sort((left, right) => left.id.localeCompare(right.id)),
    recentPackets: data.intakeOrchestratorPackets,
  };
}

function buildMatterOperations(data: ReturnType<typeof getData>): MatterOperation[] {
  return data.matters
    .map((matter) => {
      const tasks = data.tasks.filter((task) => task.matter_id === matter.id);
      const docs = data.documents.filter((doc) => doc.matter_id === matter.id);
      const approvals = data.approvals.filter((approval) => approval.matter_id === matter.id);
      const openTasks = tasks.filter((task) => !["done", "cancelled"].includes(task.status));
      const pendingApprovals = approvals.filter((approval) => approval.status === "pendiente");
      const blockers = [
        ...(matter.senior_status === "blocked" ? ["Senior Review bloqueó entrega/firma"] : []),
        ...(matter.engagement !== "aprobado" ? ["engagement pendiente"] : []),
        ...(pendingApprovals.length ? [`${pendingApprovals.length} aprobacion(es) pendiente(s)`] : []),
        ...(docs.some((doc) => doc.status === "borrador") ? ["documentos en borrador"] : []),
      ];
      const nextTask = openTasks[0];
      return {
        id: matter.id,
        cliente: matter.cliente,
        fase: matter.fase || matter.estado,
        owner: nextTask?.owner || "Despacho Legal",
        nextAction: nextTask?.title || "Revisar estado del matter",
        blockers,
        signatureReadiness: blockers.length ? "blocked" : docs.length ? "review" : "review",
        deadlineStatus: deadlineStatus(openTasks),
        paymentStatus: matter.honorarios ? "pending" : "unknown",
        artifactPresence: {
          documents: docs.length,
          tasks: tasks.length,
          approvals: approvals.length,
        },
      } satisfies MatterOperation;
    })
    .sort((a, b) => b.blockers.length - a.blockers.length || a.id.localeCompare(b.id));
}

function buildOperationalRecordsFromPackets(packets: IntakeOrchestratorPacket[]) {
  const clients: Client[] = [];
  const matters: Matter[] = [];
  const tasks: Task[] = [];
  const documents: Document[] = [];
  const approvals: Approval[] = [];
  const clientMemories: ClientMemory[] = [];
  const seenClients = new Set<string>();

  for (const packet of packets) {
    const snapshot = packet.artifacts.dashboard_snapshot || {};
    const clientName = packet.client?.nombre || snapshot.client_name || "Cliente por confirmar";
    const clientId = packet.client?.id || snapshot.client_id || inferDashboardClientId(clientName);
    if (seenClients.has(clientId)) continue;
    seenClients.add(clientId);

    const matterDescription = packet.matter?.descripcion || snapshot.matter_description || "Asunto por clasificar";
    const matterId = packet.matter?.id || snapshot.matter_id || inferDashboardMatterId(clientName, matterDescription);
    const legacyMatterAliases = packet.matter?.legacy_aliases || snapshot.legacy_matter_aliases || [];
    const sourceFolderUrl = packet.workspace?.source_folder?.url || packet.drive_folder?.url;
    const controlMasterUrl = packet.workspace?.control_master?.url || readControlMasterUrl();
    const seniorStatus = deriveSeniorStatus(packet, matterId);
    const missingCount = packet.missing_info?.length ?? snapshot.missing_count ?? 0;
    const requiredDocuments = packet.required_documents || snapshot.required_documents || [];
    const blocked = seniorStatus === "blocked";

    clients.push({
      id: clientId,
      nombre: clientName,
      estado: blocked ? "bloqueado" : packet.client?.estado || "intake",
      drive_path: sourceFolderUrl || `workspace/matters/${matterId}`,
      source_folder_url: sourceFolderUrl,
      control_master_url: controlMasterUrl,
      senior_status: seniorStatus,
      missing_count: missingCount,
    });
    matters.push({
      id: matterId,
      client_id: clientId,
      cliente: clientName,
      tipo: "contractual",
      estado: blocked ? "blocked" : packet.matter?.estado || "intake",
      descripcion: matterDescription,
      fase: packet.matter?.fase || "migracion_drive",
      engagement: "pendiente",
      drive_path: `workspace/matters/${matterId}`,
      source_folder_url: sourceFolderUrl,
      control_master_url: controlMasterUrl,
      senior_status: seniorStatus,
      legacy_aliases: legacyMatterAliases,
    });
    requiredDocuments.forEach((documentType, index) => {
      documents.push({
        id: `${matterId}-DOC-${String(index + 1).padStart(3, "0")}`,
        matter_id: matterId,
        type: documentType,
        title: documentTitle(documentType, clientName),
        status: blocked ? "bloqueado_revision_senior" : "solicitado",
        version: "v1",
        drive_path: `workspace/matters/${matterId}/documentos-legales`,
      });
      tasks.push({
        id: `${matterId}-TASK-DOC-${String(index + 1).padStart(3, "0")}`,
        matter_id: matterId,
        title: `Preparar ${documentTitle(documentType, clientName)}`,
        status: blocked ? "blocked" : "todo",
        owner: "Documentos Legales",
        priority: "high",
      });
    });
    tasks.push({
      id: `${matterId}-TASK-SENIOR`,
      matter_id: matterId,
      title: blocked ? "Cerrar blockers antes de entrega o firma" : "Revisión senior del paquete",
      status: blocked ? "blocked" : "todo",
      owner: "Revisor Senior",
      priority: "high",
    });
    approvals.push({
      id: `${matterId}-APPROVAL-SENIOR`,
      matter_id: matterId,
      type: "senior_review",
      status: blocked ? "bloqueado" : "pendiente",
      title: blocked ? "Senior Review: no entregar / no firma" : "Revisión senior requerida",
    });
    clientMemories.push({
      client_id: clientId,
      client_name: clientName,
      facts: [
        `Matter: ${matterDescription}`,
        `Fuentes Drive: ${packet.workspace?.read?.source_count ?? "pendiente"}`,
        `Documentos requeridos: ${requiredDocuments.length}`,
      ],
      preferences: ["Usar Workspace como oficina viva", "No entregar sin revisión senior"],
      risks: [
        ...(blocked ? ["Senior Review bloqueó entrega/firma"] : []),
        ...(missingCount ? [`${missingCount} faltante(s) de información`] : []),
      ],
      matter_ids: [matterId, ...legacyMatterAliases],
      document_notes: requiredDocuments,
      updated_at: packet.created_at,
    });
  }

  return { clients, matters, tasks, documents, approvals, clientMemories };
}

function mergeById<T extends Record<string, unknown>>(base: T[], derived: T[], key = "id"): T[] {
  const map = new Map<string, T>();
  for (const item of base) map.set(String(item[key]), item);
  for (const item of derived) map.set(String(item[key]), { ...(map.get(String(item[key])) || {}), ...item });
  return [...map.values()];
}

function inferDashboardClientId(clientName: string): string {
  const normalized = normalizeForId(clientName);
  return `CLI-${normalized.slice(0, 40) || "CLIENT-PENDING"}`;
}

function inferDashboardMatterId(clientName: string, matterDescription: string): string {
  return `MAT-${normalizeForId(matterDescription || clientName).slice(0, 48) || "MATTER-PENDING"}`;
}

function normalizeForId(value: string): string {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase().replace(/[^A-Z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function deriveSeniorStatus(packet: IntakeOrchestratorPacket, matterId: string): string {
  const status = packet.senior_status?.status;
  if (status) return status;
  const legacyAliases = packet.matter?.legacy_aliases || packet.artifacts.dashboard_snapshot?.legacy_matter_aliases || [];
  const candidates = [matterId, ...legacyAliases];
  for (const candidate of candidates) {
    const reviewPath = path.join(root, "workspace/matters", candidate, "senior-review/CLIENT_DELIVERY_DECISION.md");
    if (!fs.existsSync(reviewPath)) continue;
    const text = fs.readFileSync(reviewPath, "utf8").toLowerCase();
    if (text.includes("blocked") || text.includes("no entregar") || text.includes("no firma")) return "blocked";
    if (text.includes("signature-ready") || text.includes("listo_firma")) return "signature-ready";
    if (text.includes("client-deliverable") || text.includes("entregable")) return "client-deliverable";
  }
  return "pending_review";
}

function readControlMasterUrl(): string | undefined {
  if (demoMode) return "demo://workspace/sheets/control-master";
  const config = readJsonOptional<{ spreadsheet_url?: string }>("runtime/config/welaw-control-master.json", {});
  return config.spreadsheet_url;
}

function firstControlMasterUrl(clients: Client[]): string | undefined {
  return clients.find((client) => client.control_master_url)?.control_master_url;
}

function documentTitle(documentType: string, clientName: string): string {
  const titles: Record<string, string> = {
    terminos_condiciones: "Términos y Condiciones",
    aviso_privacidad_integral: "Aviso de Privacidad Integral",
    aviso_privacidad_medicos_pacientes: "Aviso de Privacidad Médicos/Pacientes",
    formato_arco: "Formato ARCO",
    nda: "NDA",
    contrato_desarrollo_software: "Contrato de Desarrollo de Software",
    convenio_cotitularidad: "Convenio de Cotitularidad",
  };
  return `${titles[documentType] || documentType} - ${clientName}`;
}

function buildRoleSections(tasks: Task[]) {
  const roles = [
    "Despacho Legal",
    "Recepcionista Juridico",
    "Expediente",
    "Data Clerk / Google Sheets",
    "Analista Juridico",
    "Documentos Legales",
    "Privacidad y Compliance",
    "IP / Software",
    "Litigio",
    "Plazos",
    "Cobranza",
    "Produccion Editorial",
    "Revisor Senior",
    "Admin Biblioteca",
  ];
  return roles.map((role) => {
    const owned = tasks.filter((task) => (task.owner || "Despacho Legal") === role && !["done", "cancelled"].includes(task.status));
    return {
      role,
      open: owned.length,
      high: owned.filter((task) => task.priority === "high").length,
      next: owned[0]?.title || "Sin tarea abierta",
    };
  });
}

function buildFirmRoles(firmModel: FirmModel): FirmRole[] {
  return Object.entries(firmModel.roles).map(([key, role]) => ({
    key,
    displayName: role.displayName,
    requiredArtifacts: role.requiredArtifacts.filter((artifact) => artifact.required).map((artifact) => artifact.name),
    completionGates: role.completionGates,
  }));
}

function buildCommandSpineOverview(commandSpine: FirmCommandSpine): CommandSpineOverview {
  return {
    firm: commandSpine.firm,
    chain: commandSpine.chainOfCommand.map((id) => ({
      id,
      label: commandSpine.actors[id]?.displayName || id,
      authority: commandSpine.actors[id]?.authority || "unknown",
    })),
    requiredArtifacts: commandSpine.requiredArtifacts,
    dashboardPrinciples: commandSpine.dashboardPrinciples,
  };
}

function buildDocumentPackageState(documents: Document[]) {
  const mat005Required = [
    "terminos_condiciones",
    "aviso_privacidad_integral",
    "aviso_privacidad_medicos_pacientes",
    "formato_arco",
    "nda",
    "contrato_desarrollo_software",
    "convenio_cotitularidad",
  ];
  const availableTypes = new Set(documents.map((doc) => doc.type));
  return {
    packageName: "Demo software / health package",
    required: mat005Required.length,
    present: mat005Required.filter((type) => availableTypes.has(type)).length,
    missing: mat005Required.filter((type) => !availableTypes.has(type)),
  };
}

function deadlineStatus(tasks: Task[]): MatterOperation["deadlineStatus"] {
  if (!tasks.some((task) => task.due_date)) return "none";
  return tasks.some((task) => task.priority === "high" && task.due_date) ? "attention" : "scheduled";
}
