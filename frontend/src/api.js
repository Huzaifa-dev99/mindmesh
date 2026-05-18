const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

async function request(path, options = {}) {
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
  if (response.status === 204) return {};
  return response.json();
}

export const api = {
  dashboard: () => request("/dashboard"),
  sessions: () => request("/chat/sessions"),
  interactions: (sessionId) => request(`/chat/sessions/${sessionId}/interactions`),
  documents: () => request("/documents"),
  syncDocuments: () => request("/documents/sync", { method: "POST" }),
  uploadDocuments: (formData) => request("/documents/upload", { method: "POST", body: formData }),
  indexDocuments: (documentIds) =>
    request("/documents/index", {
      method: "POST",
      body: JSON.stringify({ document_ids: documentIds })
    }),
  generate: (payload) =>
    request("/generate", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  aiAdmin: () => request("/admin/ai"),
  aiModels: (provider, keyId) => {
    const query = new URLSearchParams({ provider });
    if (keyId) query.set("key_id", keyId);
    return request(`/admin/ai/models?${query.toString()}`);
  },
  addAiKey: (payload) =>
    request("/admin/ai/keys", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  saveAiSettings: (payload) =>
    request("/admin/ai/settings", {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  prompts: () => request("/admin/prompts"),
  savePrompt: (name, payload) =>
    request(`/admin/prompts/${name}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    })
};
