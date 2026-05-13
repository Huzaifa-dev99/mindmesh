export type User = {
  id: string;
  email: string;
  username: string;
  full_name?: string | null;
};

export type Journal = {
  id: string;
  title?: string | null;
  content: string;
  mood?: string | null;
  tags: string[];
  created_at: string;
};

export type Note = {
  id: string;
  title: string;
  content: string;
  source?: string | null;
  tags: string[];
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at?: string | null;
};

export type SearchResult = {
  source_type: string;
  source_id: string;
  score: number;
  title?: string | null;
  snippet: string;
  metadata?: Record<string, unknown>;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  created_at?: string;
  citations?: SearchResult[];
};

export type ConversationSummary = {
  id: string;
  title?: string | null;
  created_at: string;
  updated_at?: string | null;
  message_count: number;
  last_message_at?: string | null;
};

export type ConversationDetail = ConversationSummary & {
  messages: Array<ChatMessage & { id: string }>;
};

export type DocumentResource = {
  document_id: string;
  file_name: string;
  file_type?: string | null;
  uploaded_date?: string | null;
  minio_object_path: string;
  chunk_count: number;
};

export type PreviewTarget =
  | { type: "note"; id: string }
  | { type: "document"; id: string };
