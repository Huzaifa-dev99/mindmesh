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
  created_at: string;
};

export type SearchResult = {
  source_type: string;
  source_id: string;
  score: number;
  title?: string | null;
  snippet: string;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};
