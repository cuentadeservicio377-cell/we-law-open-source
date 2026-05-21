import { execFile } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { promisify } from "node:util";

import { getSummary, getWorkspaceOverview } from "@/lib/data";
import type {
  HermesLiveSnapshotInput,
  LivePaperclipStatus,
  LivePaperclipWorker,
  LiveStatus,
  LiveWorkspaceStatus,
} from "@/lib/live-state";

const execFileAsync = promisify(execFile);
const ROOT = path.resolve(process.cwd(), "..");
const PAPERCLIP_MANIFEST = path.join(ROOT, "runtime", "config", "paperclip-welaw-instance.json");

function hermesWorkspaceEnv(): NodeJS.ProcessEnv {
  const env = { ...process.env };
  if (env.GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE || env.GOOGLE_WORKSPACE_CLI_TOKEN) {
    return env;
  }
  const home = os.homedir();
  const activeProfilePath = path.join(home, ".hermes", "active_profile");
  const activeProfile = existsSync(activeProfilePath) ? readFileSync(activeProfilePath, "utf8").trim() : "";
  const tokenCandidates = [
    activeProfile ? path.join(home, ".hermes", "profiles", activeProfile, "google_token.json") : "",
    path.join(home, ".hermes", "profiles", "welaw", "google_token.json"),
  ].filter(Boolean);
  const tokenPath = tokenCandidates.find((candidate) => existsSync(candidate));
  if (tokenPath) {
    env.GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE = tokenPath;
  }
  return env;
}

function sanitizeDetail(value: string, limit = 180): string {
  const compact = value.replace(/\s+/g, " ").trim();
  return compact.length > limit ? `${compact.slice(0, limit - 1)}…` : compact;
}

function statusFromAuthError(message: string): LiveStatus {
  const lowered = message.toLowerCase();
  if (lowered.includes("invalid_client") || lowered.includes("autherror") || lowered.includes("401")) {
    return "unauthorized";
  }
  if (lowered.includes("forbidden") || lowered.includes("permission")) {
    return "unauthorized";
  }
  return "degraded";
}

function buildWorkspaceBaseline(): LiveWorkspaceStatus {
  const overview = getWorkspaceOverview();
  const folderStatus = overview.clientFolders.length ? "synced" : "empty";
  return {
    status: overview.clientFolders.length ? "healthy" : "degraded",
    rootName: "We Law S.C.",
    lastSyncAt: null,
    detail: overview.clientFolders.length
      ? "Modelo local listo para compararse contra Workspace vivo."
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

function buildPaperclipBaseline(): LivePaperclipStatus {
  const summary = getSummary();
  const activeWorkers: LivePaperclipWorker[] = summary.roleSections.slice(0, 6).map((section) => ({
    id: section.role.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
    role: section.role,
    status: section.open > 0 ? "active" : "idle",
  }));
  const openIssues = summary.operations.slice(0, 6).map((operation) => ({
    id: operation.id,
    title: operation.nextAction,
    state: operation.blockers.length ? "blocked" : "ready",
  }));
  return {
    status: openIssues.some((issue) => issue.state === "blocked") ? "degraded" : "healthy",
    activeWorkers,
    openIssues,
    lastRunAt: null,
    detail: openIssues.some((issue) => issue.state === "blocked")
      ? "Hay asuntos bloqueados en el modelo local de despacho."
      : "Modelo local Paperclip listo para recibir el estado vivo.",
  };
}

export async function probeWorkspaceLiveStatus(): Promise<LiveWorkspaceStatus> {
  const baseline = buildWorkspaceBaseline();
  try {
    const result = await execFileAsync(
      "gws",
      ["drive", "files", "list", "--params", JSON.stringify({ pageSize: 1 }), "--format", "json"],
      {
        timeout: 7000,
        maxBuffer: 1024 * 1024,
        env: hermesWorkspaceEnv(),
      },
    );
    const payload = result.stdout ? JSON.parse(result.stdout) : {};
    if (payload?.error) {
      const message = typeof payload.error.message === "string" ? payload.error.message : JSON.stringify(payload.error);
      const code = Number(payload.error.code ?? 0);
      return {
        ...baseline,
        status: code === 401 ? "unauthorized" : statusFromAuthError(message),
        detail: sanitizeDetail(message),
        lastSyncAt: null,
      };
    }
    const files = Array.isArray(payload?.files) ? payload.files.length : 0;
    return {
      ...baseline,
      status: "healthy",
      detail: sanitizeDetail(files > 0 ? `gws drive files list respondió con ${files} archivo(s).` : "gws drive files list respondió correctamente."),
      lastSyncAt: new Date().toISOString(),
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      ...baseline,
      status: message.toLowerCase().includes("invalid_client") ? "unauthorized" : "offline",
      detail: sanitizeDetail(message),
      lastSyncAt: null,
    };
  }
}

export async function probePaperclipLiveStatus(): Promise<LivePaperclipStatus> {
  const baseline = buildPaperclipBaseline();
  try {
    const manifest = JSON.parse(await readFile(PAPERCLIP_MANIFEST, "utf8")) as { apiUrl: string };
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 7000);
    try {
      const response = await fetch(`${manifest.apiUrl}/health`, {
        method: "GET",
        headers: { Accept: "application/json" },
        signal: controller.signal,
        cache: "no-store",
      });
      const payload = (await response.json()) as {
        status?: string;
        body?: {
          version?: string;
          deploymentMode?: string;
          authReady?: boolean;
          bootstrapStatus?: string;
          devServer?: { lastRestartAt?: string | null };
        };
      };

      if (!response.ok || payload.status !== "ok") {
        return {
          ...baseline,
          status: response.ok ? "degraded" : "offline",
          detail: sanitizeDetail(
            payload.body?.bootstrapStatus
              ? `Paperclip health respondió ${payload.body.bootstrapStatus}.`
              : `Paperclip health HTTP ${response.status}.`,
          ),
          lastRunAt: payload.body?.devServer?.lastRestartAt ?? null,
        };
      }

      return {
        ...baseline,
        status: "healthy",
        detail: sanitizeDetail(
          `Paperclip ${payload.body?.version ?? "unknown"} · ${payload.body?.deploymentMode ?? "unknown"} · authReady=${String(payload.body?.authReady ?? false)}`,
        ),
        lastRunAt: payload.body?.devServer?.lastRestartAt ?? new Date().toISOString(),
      };
    } finally {
      clearTimeout(timeout);
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      ...baseline,
      status: message.toLowerCase().includes("connect") ? "offline" : "degraded",
      detail: sanitizeDetail(message),
      lastRunAt: null,
    };
  }
}

export async function probeLiveDashboardSnapshotInput(): Promise<HermesLiveSnapshotInput> {
  const [workspace, paperclip] = await Promise.all([probeWorkspaceLiveStatus(), probePaperclipLiveStatus()]);
  return {
    source: "hermes",
    generatedAt: new Date().toISOString(),
    workspace,
    paperclip,
  };
}
