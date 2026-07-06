import type { ChatResponse, Message, Note, Notebook, Source, StudioArtifact, StudioArtifactType, User } from "./types";

// Leer = same-origin, relative Pfade (z. B. "/api/notebooks"), die Caddy
// bereits auf denselben Origin wie das Frontend routet (siehe
// docs/deployment.md, Abschnitt "Frontend-Build-Variable"). Nur bei einer
// komplett separaten API-Domain/Subdomain hier eine absolute URL setzen.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";
const CSRF_COOKIE_NAME = "csrf_token";
const CSRF_HEADER_NAME = "X-CSRF-Token";
const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function getCsrfCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${CSRF_COOKIE_NAME}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", headers.get("Content-Type") ?? "application/json");
  if (MUTATING_METHODS.has(method)) {
    const csrfToken = getCsrfCookie();
    if (csrfToken) headers.set(CSRF_HEADER_NAME, csrfToken);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers, credentials: "include" });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API error ${response.status}: ${body}`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const register = (email: string, password: string, name: string) =>
  apiFetch<User>("/api/auth/register", { method: "POST", body: JSON.stringify({ email, password, name }) });

export const login = (email: string, password: string) =>
  apiFetch<User>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });

export const logout = () => apiFetch<{ ok: boolean }>("/api/auth/logout", { method: "POST" });

export const getMe = () => apiFetch<User>("/api/auth/me");

export const listNotebooks = () => apiFetch<Notebook[]>("/api/notebooks");

export const createNotebook = (title: string, description?: string) =>
  apiFetch<Notebook>("/api/notebooks", { method: "POST", body: JSON.stringify({ title, description }) });

export const getNotebook = (id: string) => apiFetch<Notebook>(`/api/notebooks/${id}`);

export const deleteNotebook = (id: string) => apiFetch<void>(`/api/notebooks/${id}`, { method: "DELETE" });

export const listSources = (notebookId: string) => apiFetch<Source[]>(`/api/notebooks/${notebookId}/sources`);

export async function uploadSource(notebookId: string, file: File): Promise<Source> {
  const formData = new FormData();
  formData.append("file", file);

  const headers = new Headers();
  const csrfToken = getCsrfCookie();
  if (csrfToken) headers.set(CSRF_HEADER_NAME, csrfToken);

  const response = await fetch(`${API_BASE_URL}/api/notebooks/${notebookId}/sources/upload`, {
    method: "POST",
    headers,
    credentials: "include",
    body: formData,
  });
  if (!response.ok) {
    throw new Error(`Upload failed: ${response.status} ${await response.text()}`);
  }
  const data = await response.json();
  return data.source as Source;
}

export const deleteSource = (sourceId: string) => apiFetch<void>(`/api/sources/${sourceId}`, { method: "DELETE" });

export const listMessages = (notebookId: string) => apiFetch<Message[]>(`/api/notebooks/${notebookId}/messages`);

export const sendChatMessage = (notebookId: string, message: string, sourceIds?: string[]) =>
  apiFetch<ChatResponse>(`/api/notebooks/${notebookId}/chat`, {
    method: "POST",
    body: JSON.stringify({ message, source_ids: sourceIds, mode: "grounded" }),
  });

export const listNotes = (notebookId: string) => apiFetch<Note[]>(`/api/notebooks/${notebookId}/notes`);

export const createNote = (notebookId: string, title: string, content: string) =>
  apiFetch<Note>(`/api/notebooks/${notebookId}/notes`, {
    method: "POST",
    body: JSON.stringify({ title, content }),
  });

export async function getStudioArtifact<T>(
  notebookId: string,
  type: StudioArtifactType
): Promise<StudioArtifact<T> | null> {
  const response = await fetch(`${API_BASE_URL}/api/notebooks/${notebookId}/studio/${type}`, {
    credentials: "include",
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`API error ${response.status}: ${await response.text()}`);
  return (await response.json()) as StudioArtifact<T>;
}

export const generateStudioArtifact = <T,>(notebookId: string, type: StudioArtifactType) =>
  apiFetch<StudioArtifact<T>>(`/api/notebooks/${notebookId}/studio/${type}`, { method: "POST" });

const EXPORT_EXTENSIONS: Record<"docx" | "pdf" | "png", string> = { docx: "docx", pdf: "pdf", png: "png" };

export async function exportStudioArtifact(
  notebookId: string,
  type: StudioArtifactType,
  format: "docx" | "pdf" | "png"
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/notebooks/${notebookId}/studio/${type}/export?format=${format}`,
    { credentials: "include" }
  );
  if (!response.ok) throw new Error(`Export fehlgeschlagen (${response.status}): ${await response.text()}`);

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition");
  const filenameMatch = disposition?.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
  const filename = filenameMatch ? decodeURIComponent(filenameMatch[1]) : `${type}.${EXPORT_EXTENSIONS[format]}`;

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
