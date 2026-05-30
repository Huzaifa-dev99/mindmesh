const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

type RequestOptions = RequestInit & { body?: BodyInit | null };

async function request<T = any>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: options.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...options
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      detail = await response.text();
    }
    throw new Error(detail || "Request failed");
  }

  if (response.status === 204) return {} as T;
  return response.json();
}

export const api = {
  health: () => request("/health"),
  user: () => request("/user"),
  updateUserProfile: (payload: unknown) =>
    request("/user/profile", {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  setUserPin: (pin: string) =>
    request("/user/pin", {
      method: "PUT",
      body: JSON.stringify({ pin })
    }),
  resetUserPin: (pin: string) =>
    request("/user/pin/reset", {
      method: "POST",
      body: JSON.stringify({ pin })
    }),
  verifyUserPin: (pin: string) =>
    request("/user/pin/verify", {
      method: "POST",
      body: JSON.stringify({ pin })
    }),
  dashboard: () => request("/dashboard"),
  sessions: () => request("/chat/sessions"),
  updateSession: (sessionId: string, payload: unknown) =>
    request(`/chat/sessions/${sessionId}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    }),
  deleteSession: (sessionId: string) =>
    request(`/chat/sessions/${sessionId}`, {
      method: "DELETE"
    }),
  interactions: (sessionId: string) => request(`/chat/sessions/${sessionId}/interactions`),
  documents: () => request("/documents"),
  syncDocuments: () => request("/documents/sync", { method: "POST" }),
  uploadDocuments: (formData: FormData) => request("/documents/upload", { method: "POST", body: formData }),
  indexDocuments: (documentIds: string[]) =>
    request("/documents/index", {
      method: "POST",
      body: JSON.stringify({ document_ids: documentIds })
    }),
  removeVectors: (documentIds: string[]) =>
    request("/documents/remove-vectors", {
      method: "POST",
      body: JSON.stringify({ document_ids: documentIds })
    }),
  removeDocuments: (documentIds: string[]) =>
    request("/documents/remove", {
      method: "POST",
      body: JSON.stringify({ document_ids: documentIds })
    }),
  generate: (payload: unknown) =>
    request("/generate", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  aiAdmin: () => request("/admin/ai"),
  aiModels: (provider: string, keyId?: string) => {
    const query = new URLSearchParams({ provider });
    if (keyId) query.set("key_id", keyId);
    return request(`/admin/ai/models?${query.toString()}`);
  },
  addAiKey: (payload: unknown) =>
    request("/admin/ai/keys", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  deleteAiKey: (keyId: string) =>
    request(`/admin/ai/keys/${keyId}`, {
      method: "DELETE"
    }),
  saveAiSettings: (payload: unknown) =>
    request("/admin/ai/settings", {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  prompts: () => request("/admin/prompts"),
  savePrompt: (name: string, payload: unknown) =>
    request(`/admin/prompts/${name}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    })
};
