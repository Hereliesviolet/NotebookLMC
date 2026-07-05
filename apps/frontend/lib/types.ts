/**
 * Local mirror of packages/shared-types/index.ts - see that package's
 * README for why this isn't imported directly yet.
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

export type SourceStatus = "uploaded" | "processing" | "indexed" | "failed" | "no_content" | "deleted";

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

export type StudioArtifactType =
  | "summary"
  | "faq"
  | "timeline"
  | "briefing"
  | "audio-script"
  | "quiz"
  | "mindmap"
  | "infographic";

export interface StudioSummaryContent {
  summary_markdown: string;
}

export interface StudioFaqItem {
  question: string;
  answer: string;
  source_ids: string[];
}

export interface StudioFaqContent {
  items: StudioFaqItem[];
}

export interface StudioTimelineEvent {
  date: string | null;
  date_label: string;
  description: string;
  source_id: string;
  quote: string;
}

export interface StudioTimelineContent {
  events: StudioTimelineEvent[];
}

export interface StudioBriefingContent {
  summary: string;
  key_points: string[];
  risks: string[];
  recommended_actions: string[];
  open_questions: string[];
}

export interface StudioQuizQuestion {
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
  source_id: string;
}

export interface StudioQuizContent {
  questions: StudioQuizQuestion[];
}

export interface StudioMindmapLeaf {
  label: string;
}

export interface StudioMindmapChild {
  label: string;
  children: StudioMindmapLeaf[];
}

export interface StudioMindmapContent {
  root: {
    label: string;
    children: StudioMindmapChild[];
  };
}

export interface StudioInfographicSection {
  title: string;
  body: string;
}

export interface StudioInfographicStat {
  label: string;
  value: string;
}

export interface StudioInfographicContent {
  headline: string;
  subheadline: string;
  sections: StudioInfographicSection[];
  stats: StudioInfographicStat[];
}

export interface StudioArtifact<T> {
  id: string;
  notebook_id: string;
  type: StudioArtifactType;
  content: T;
  source_ids: string[];
  model: string | null;
  created_at: string;
  updated_at: string;
}
