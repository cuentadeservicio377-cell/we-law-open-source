import { getSummary, getWorkspaceOverview, type WorkspaceOverview } from "@/lib/data";
import { probeLiveDashboardSnapshotInput } from "@/lib/live-probes";

export type LiveStatus = "healthy" | "degraded" | "unauthorized" | "offline";

export type LiveWorkspaceFolder = {
  name: string;
  status: string;
  url?: string;
};

export type LiveWorkspaceSheet = {
  name: string;
  status: string;
  url?: string;
};

export type LiveWorkspaceDoc = {
  title: string;
  status: string;
  url?: string;
};

export type LiveWorkspaceStatus = {
  status: LiveStatus;
  rootName: string;
  lastSyncAt: string | null;
  detail?: string | null;
  folders: LiveWorkspaceFolder[];
  sheets: LiveWorkspaceSheet[];
  docs: LiveWorkspaceDoc[];
};

export type LivePaperclipWorker = {
  id: string;
  role: string;
  status: "active" | "idle" | "blocked";
};

export type LivePaperclipIssue = {
  id: string;
  title: string;
  state: string;
};

export type LivePaperclipStatus = {
  status: LiveStatus;
  activeWorkers: LivePaperclipWorker[];
  openIssues: LivePaperclipIssue[];
  lastRunAt: string | null;
  detail?: string | null;
};

export type LiveCommandSpineStatus = {
  status: LiveStatus;
  chain: string[];
  activeController: string;
  detail?: string | null;
};

export type LiveActionIntent = {
  kind:
    | "refresh_snapshot"
    | "prepare_intake"
    | "create_issue"
    | "request_writeback"
    | "open_target"
    | "mark_blocked";
  targetId?: string;
  payload?: Record<string, unknown>;
};

export type LiveDashboardSnapshot = {
  generatedAt: string;
  source: "local_fallback" | "hermes";
  commandSpine: LiveCommandSpineStatus;
  workspace: LiveWorkspaceStatus;
  paperclip: LivePaperclipStatus;
  actions: LiveActionIntent[];
};

export type HermesLiveSnapshotInput = {
  source?: LiveDashboardSnapshot["source"];
  generatedAt?: string;
  workspace?: Partial<LiveWorkspaceStatus>;
  paperclip?: Partial<LivePaperclipStatus>;
  commandSpine?: Partial<LiveCommandSpineStatus>;
  actions?: LiveActionIntent[];
};

function buildCommandSpineStatus(): LiveCommandSpineStatus {
  return {
    status: "healthy",
    chain: ["the lawyer", "Hermes Managing Partner", "Paperclip staff", "Workspace", "Aprobacion"],
    activeController: "Hermes Managing Partner",
    detail: "Hermes dirige el despacho; Paperclip ejecuta; Workspace conserva; the lawyer aprueba.",
  };
}

function buildWorkspaceStatus(overview: WorkspaceOverview): LiveWorkspaceStatus {
  const folderStatus = overview.clientFolders.length ? "synced" : "empty";
  return {
    status: overview.clientFolders.length ? "healthy" : "degraded",
    rootName: "We Law S.C.",
    lastSyncAt: null,
    detail: overview.clientFolders.length
      ? "Modelo local listo para comparar con el estado vivo."
      : "Modelo local vacío; Workspace no tiene base de clientes todavía.",
    folders: overview.clientFolders.map((folder) => ({
      name: folder.clientName,
      status: folder.path.includes("pendiente") ? "pending" : folderStatus,
      url: folder.path.includes("pendiente") ? undefined : folder.path,
    })),
    sheets: overview.sheetRegistry.map((sheet) => ({
      name: sheet.name,
      status: "available",
    })),
    docs: overview.documentQueue.slice(0, 8).map((document) => ({
      title: document.title,
      status: document.status,
    })),
  };
}

function buildPaperclipStatus(summary: ReturnType<typeof getSummary>) {
  const activeWorkers = summary.roleSections.slice(0, 6).map((section) => ({
    id: section.role.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
    role: section.role,
    status: section.open > 0 ? "active" : "idle",
  })) satisfies LivePaperclipWorker[];
  const openIssues = summary.operations.slice(0, 6).map((operation) => ({
    id: operation.id,
    title: operation.nextAction,
    state: operation.blockers.length ? "blocked" : "ready",
  })) satisfies LivePaperclipIssue[];
  return {
    status: openIssues.some((issue) => issue.state === "blocked") ? "degraded" : "healthy",
    activeWorkers,
    openIssues,
    lastRunAt: null,
    detail: openIssues.some((issue) => issue.state === "blocked")
      ? "Hay asuntos bloqueados en el modelo local de despacho."
      : "Modelo local Paperclip listo para recibir el estado vivo.",
  } satisfies LivePaperclipStatus;
}

function defaultActions(): LiveActionIntent[] {
  return [
    { kind: "refresh_snapshot" },
    { kind: "prepare_intake" },
    { kind: "create_issue", payload: { source: "dashboard" } },
    { kind: "request_writeback", payload: { mode: "approval_gate" } },
    { kind: "open_target" },
    { kind: "mark_blocked" },
  ];
}

export function adaptLiveDashboardSnapshot(input: HermesLiveSnapshotInput = {}): LiveDashboardSnapshot {
  const summary = getSummary();
  const workspace = getWorkspaceOverview();
  const localWorkspace = buildWorkspaceStatus(workspace);
  const localPaperclip = buildPaperclipStatus(summary);
  const localCommandSpine = buildCommandSpineStatus();
  const mergedWorkspace: LiveWorkspaceStatus = {
    ...localWorkspace,
    ...input.workspace,
    folders: input.workspace?.folders ?? localWorkspace.folders,
    sheets: input.workspace?.sheets ?? localWorkspace.sheets,
    docs: input.workspace?.docs ?? localWorkspace.docs,
  };
  const mergedPaperclip: LivePaperclipStatus = {
    ...localPaperclip,
    ...input.paperclip,
    activeWorkers: input.paperclip?.activeWorkers ?? localPaperclip.activeWorkers,
    openIssues: input.paperclip?.openIssues ?? localPaperclip.openIssues,
  };

  return {
    generatedAt: input.generatedAt ?? new Date().toISOString(),
    source: input.source ?? (input.workspace || input.paperclip ? "hermes" : "local_fallback"),
    commandSpine: {
      ...localCommandSpine,
      ...input.commandSpine,
      chain: input.commandSpine?.chain ?? localCommandSpine.chain,
    },
    workspace: mergedWorkspace,
    paperclip: mergedPaperclip,
    actions: input.actions ?? defaultActions(),
  } satisfies LiveDashboardSnapshot;
}

export function getLiveDashboardSnapshot(): LiveDashboardSnapshot {
  return adaptLiveDashboardSnapshot();
}

export async function getLiveDashboardSnapshotLive(): Promise<LiveDashboardSnapshot> {
  try {
    const probeInput = await probeLiveDashboardSnapshotInput();
    return adaptLiveDashboardSnapshot(probeInput);
  } catch {
    return adaptLiveDashboardSnapshot();
  }
}
