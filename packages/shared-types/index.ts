/**
 * Shared TypeScript API contracts between the frontend and the FastAPI
 * backend. This package is the source of truth for these shapes; the
 * frontend currently keeps a local mirror in apps/frontend/lib/types.ts
 * because the Docker build context per app (see docker-compose.yml) does not
 * include this package. If a proper npm workspace is introduced later,
 * apps/frontend can depend on this package directly instead of mirroring it.
 */

export type NotebookVisibility = "private" | "shared";

export interface Notebook {
  id: string;
  owner_id: string;
  title: string;
  description: string | null;
  visibility: NotebookVisibility;
  source_count: number;
  created_at: string;
  updated_at: string;
}

export type SourceStatus = "uploaded" | "processing" | "indexed" | "failed" | "deleted";

export interface Source {
  id: string;
  notebook_id: string;
  filename: string;
  original_filename: string;
  mime_type: string;
  status: SourceStatus;
  page_count: number | null;
  token_count: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  source_id: string;
  chunk_id: string;
  document_name: string;
  page_start: number | null;
  page_end: number | null;
  quote: string;
  supports_claim?: string | null;
}

export type Confidence = "low" | "medium" | "high";

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  confidence: Confidence;
  missing_information: string[];
  follow_up_questions: string[];
}

export type MessageRole = "user" | "assistant" | "system";

export interface Message {
  id: string;
  notebook_id: string;
  role: MessageRole;
  content: string;
  model: string | null;
  citations_json: Citation[] | null;
  created_at: string;
}

export interface Note {
  id: string;
  notebook_id: string;
  title: string;
  content: string;
  source_refs_json: unknown;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
}
