import type { AIModel, AIProviderConfig, ConversationDetail, ConversationSummary, DocumentResource, Journal, Note, SearchResult, User } from "../types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

type LoginResponse = {
  access_token: string;
  user: User;
};

async function request<T>(path: string, options: RequestInit = {}, token?: string | null): Promise<T> {
  const headers: Record<string, string> = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((options.headers as Record<string, string> | undefined) || {})
  };
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${API_BASE_URL}/v1${path}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail || response.statusText);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  register(payload: { email: string; username: string; full_name?: string; password: string }) {
    return request<User>("/users", { method: "POST", body: JSON.stringify(payload) });
  },
  login(email: string, password: string) {
    return request<LoginResponse>("/users/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
  },
  me(token: string) {
    return request<User>("/users/me", {}, token);
  },
  journals(token: string) {
    return request<Journal[]>("/journals", {}, token);
  },
  createJournal(token: string, payload: { title?: string; mood?: string; content: string; tags: string[] }) {
    return request<Journal>("/journals", { method: "POST", body: JSON.stringify(payload) }, token);
  },
  summarizeJournal(token: string, id: string) {
    return request<{ summary: string }>(`/journals/${id}/summary`, { method: "POST" }, token);
  },
  notes(token: string) {
    return request<Note[]>("/knowledge/notes", {}, token);
  },
  aiConfig(token: string) {
    return request<AIProviderConfig | null>("/ai/config", {}, token);
  },
  saveAiConfig(token: string, payload: { provider: string; api_key: string; default_model_id?: string | null }) {
    return request<AIProviderConfig>("/ai/config", { method: "POST", body: JSON.stringify(payload) }, token);
  },
  aiModels(token: string, provider?: string) {
    const query = provider ? `?provider=${encodeURIComponent(provider)}` : "";
    return request<AIModel[]>(`/ai/models${query}`, {}, token);
  },
  setChatModel(token: string, conversationId: string, payload: { provider: string; model_id: string }) {
    return request<{ provider: string; model_id: string }>(`/ai/chats/${conversationId}/model`, { method: "PATCH", body: JSON.stringify(payload) }, token);
  },
  getChatModel(token: string, conversationId: string) {
    return request<{ provider?: string | null; model_id?: string | null }>(`/ai/chats/${conversationId}/model`, {}, token);
  },
  documents(token: string, params?: { scope?: "chat" | "global"; chatId?: string | null }) {
    const query = new URLSearchParams();
    if (params?.scope) query.set("scope", params.scope);
    if (params?.chatId) query.set("chat_id", params.chatId);
    const suffix = query.toString() ? `?${query}` : "";
    return request<DocumentResource[]>(`/knowledge/documents${suffix}`, {}, token);
  },
  async uploadDocument(
    token: string,
    file: File,
    options: { scope: "chat" | "global"; chatId?: string | null; selectedModelId?: string | null; selectedModelSupportsVision?: boolean }
  ) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("scope", options.scope);
    if (options.scope === "chat" && options.chatId) formData.append("chat_id", options.chatId);
    if (options.selectedModelId) formData.append("selected_model_id", options.selectedModelId);
    formData.append("selected_model_supports_vision", String(Boolean(options.selectedModelSupportsVision)));
    return request<DocumentResource>(
      "/knowledge/documents",
      {
        method: "POST",
        body: formData
      },
      token
    );
  },
  createNote(token: string, payload: { title: string; source?: string; content: string; tags: string[]; metadata?: Record<string, unknown> }) {
    return request<Note>("/knowledge/notes", { method: "POST", body: JSON.stringify(payload) }, token);
  },
  updateNote(token: string, id: string, payload: { title?: string; source?: string | null; content?: string; tags?: string[]; metadata?: Record<string, unknown> }) {
    return request<Note>(`/knowledge/notes/${id}`, { method: "PATCH", body: JSON.stringify(payload) }, token);
  },
  updateNoteScope(token: string, id: string, payload: { scope: "chat" | "global"; chat_id?: string | null }) {
    return request<Note>(`/knowledge/notes/${id}/scope`, { method: "PATCH", body: JSON.stringify(payload) }, token);
  },
  deleteNote(token: string, id: string) {
    return request<void>(`/knowledge/notes/${id}`, { method: "DELETE" }, token);
  },
  updateDocumentScope(token: string, id: string, payload: { scope: "chat" | "global"; chat_id?: string | null }) {
    return request<DocumentResource>(`/knowledge/documents/${id}/scope`, { method: "PATCH", body: JSON.stringify(payload) }, token);
  },
  deleteDocument(token: string, id: string) {
    return request<void>(`/knowledge/documents/${id}`, { method: "DELETE" }, token);
  },
  tags(token: string) {
    return request<Array<{ id: string; name: string }>>("/knowledge/tags", {}, token);
  },
  search(token: string, query: string, sourceTypes: string[]) {
    return request<{ results: SearchResult[] }>(
      "/search",
      {
        method: "POST",
        body: JSON.stringify({ query, limit: 5, source_types: sourceTypes.length ? sourceTypes : undefined })
      },
      token
    );
  },
  chat(token: string, message: string, conversationId?: string | null, tavilyApiKey?: string | null, model?: { provider?: string | null; modelId?: string | null }) {
    return request<{ conversation_id: string; answer: string; citations: SearchResult[] }>(
      "/chat",
      {
        method: "POST",
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
          use_rag: true,
          limit: 5,
          tavily_api_key: tavilyApiKey || undefined,
          provider: model?.provider || undefined,
          model_id: model?.modelId || undefined
        })
      },
      token
    );
  },
  conversations(token: string) {
    return request<ConversationSummary[]>("/conversations", {}, token);
  },
  conversation(token: string, id: string) {
    return request<ConversationDetail>(`/conversations/${id}`, {}, token);
  },
  updateConversation(token: string, id: string, title: string) {
    return request<ConversationSummary>(`/conversations/${id}`, { method: "PATCH", body: JSON.stringify({ title }) }, token);
  },
  deleteConversation(token: string, id: string) {
    return request<void>(`/conversations/${id}`, { method: "DELETE" }, token);
  },
  archiveConversation(token: string, id: string) {
    return request<void>(`/conversations/${id}/archive`, { method: "PATCH" }, token);
  },
  health() {
    return fetch(`${API_BASE_URL}/v1/health/full`).then((res) => res.json());
  }
};
