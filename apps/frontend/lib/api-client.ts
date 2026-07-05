import type { ChatResponse, Message, Note, Notebook, Source, User } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_STORAGE_KEY = "notebooklmc_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", headers.get("Content-Type") ?? "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API error ${response.status}: ${body}`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function login(email?: string): Promise<string> {
  const data = await apiFetch<{ access_token: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
  setToken(data.access_token);
  return data.access_token;
}

export const getMe = () => apiFetch<User>("/api/auth/me");

export const listNotebooks = () => apiFetch<Notebook[]>("/api/notebooks");

export const createNotebook = (title: string, description?: string) =>
  apiFetch<Notebook>("/api/notebooks", { method: "POST", body: JSON.stringify({ title, description }) });

export const getNotebook = (id: string) => apiFetch<Notebook>(`/api/notebooks/${id}`);

export const deleteNotebook = (id: string) => apiFetch<void>(`/api/notebooks/${id}`, { method: "DELETE" });

export const listSources = (notebookId: string) => apiFetch<Source[]>(`/api/notebooks/${notebookId}/sources`);

export async function uploadSource(notebookId: string, file: File): Promise<Source> {
  const token = getToken();
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/notebooks/${notebookId}/sources/upload`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
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
