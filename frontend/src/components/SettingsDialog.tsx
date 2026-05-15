import { Bot, KeyRound, LockKeyhole, MessageSquareText, Moon, Save, Sun, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { AIModel, AIProviderConfig } from "../types";

type SettingsTab = "ai" | "tools" | "prompts" | "security";

type Props = {
  open: boolean;
  token: string;
  onClose: () => void;
  theme: "dark" | "light";
  onThemeChange: (theme: "dark" | "light") => void;
};

const tabs: Array<{ key: SettingsTab; label: string; icon: typeof KeyRound }> = [
  { key: "ai", label: "AI Settings", icon: Bot },
  { key: "tools", label: "Tools", icon: KeyRound },
  { key: "prompts", label: "Prompts", icon: MessageSquareText },
  { key: "security", label: "Security", icon: LockKeyhole }
];

export function SettingsDialog({ open, token, onClose, theme, onThemeChange }: Props) {
  const [activeTab, setActiveTab] = useState<SettingsTab>("ai");
  const [provider, setProvider] = useState(localStorage.getItem("mindmesh.provider") || "Groq");
  const [apiKey, setApiKey] = useState("");
  const [aiConfig, setAiConfig] = useState<AIProviderConfig | null>(null);
  const [models, setModels] = useState<AIModel[]>([]);
  const [defaultModelId, setDefaultModelId] = useState(localStorage.getItem("mindmesh.defaultModel") || "");
  const [aiStatus, setAiStatus] = useState("");
  const [tavilyApiKey, setTavilyApiKey] = useState(localStorage.getItem("mindmesh.tavilyApiKey") || "");
  const [name, setName] = useState(localStorage.getItem("mindmesh.userName") || "");
  const [bio, setBio] = useState(localStorage.getItem("mindmesh.userBio") || "");
  const [preferences, setPreferences] = useState(localStorage.getItem("mindmesh.responsePrefs") || "");

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    api.aiConfig(token)
      .then((config) => {
        if (cancelled) return;
        setAiConfig(config);
        if (config) {
          setProvider(config.provider);
          setModels(config.models);
          setDefaultModelId(config.default_model_id || config.models[0]?.id || "");
          return;
        }
        return api.aiModels(token, provider).then((items) => {
          if (!cancelled) setModels(items);
        });
      })
      .catch(() => {
        if (!cancelled) setAiStatus("Could not load AI settings.");
      });
    return () => {
      cancelled = true;
    };
  }, [open, token]);

  if (!open) return null;

  async function saveAiSettings() {
    if (!apiKey.trim()) {
      setAiStatus(aiConfig?.has_api_key ? "Enter a replacement API key to verify again." : "Enter an API key to verify this provider.");
      return;
    }
    setAiStatus("Verifying provider and loading models...");
    try {
      const config = await api.saveAiConfig(token, {
        provider,
        api_key: apiKey,
        default_model_id: defaultModelId || undefined
      });
      setAiConfig(config);
      setModels(config.models);
      setDefaultModelId(config.default_model_id || config.models[0]?.id || "");
      localStorage.setItem("mindmesh.provider", config.provider);
      if (config.default_model_id) localStorage.setItem("mindmesh.defaultModel", config.default_model_id);
      localStorage.removeItem("mindmesh.apiKey");
      setApiKey("");
      setAiStatus("API key verified. Models are ready.");
    } catch (error) {
      setAiStatus(error instanceof Error ? error.message : "Could not verify this API key.");
    }
  }

  function save() {
    localStorage.setItem("mindmesh.provider", provider);
    if (defaultModelId) localStorage.setItem("mindmesh.defaultModel", defaultModelId);
    localStorage.setItem("mindmesh.tavilyApiKey", tavilyApiKey);
    localStorage.setItem("mindmesh.userName", name);
    localStorage.setItem("mindmesh.userBio", bio);
    localStorage.setItem("mindmesh.responsePrefs", preferences);
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/45 p-4 backdrop-blur-sm" role="dialog" aria-modal="true">
      <section className="modal-panel w-full max-w-3xl">
        <header className="flex items-center justify-between border-b border-border px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold">Profile Settings</h2>
            <p className="text-sm text-muted">Manage providers, prompts, and local privacy.</p>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Close settings">
            <X size={18} />
          </button>
        </header>

        <div className="grid min-h-[28rem] md:grid-cols-[12rem_1fr]">
          <nav className="border-b border-border p-3 md:border-b-0 md:border-r">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button key={tab.key} onClick={() => setActiveTab(tab.key)} className={`sidebar-item ${activeTab === tab.key ? "sidebar-item-active" : ""}`}>
                  <Icon size={16} />
                  {tab.label}
                </button>
              );
            })}
          </nav>

          <div className="max-h-[65vh] overflow-y-auto p-5">
            {activeTab === "ai" && (
              <div className="space-y-4">
                <div>
                  <label className="field-label">AI Provider</label>
                  <select className="control mt-2" value={provider} onChange={(event) => setProvider(event.target.value)}>
                    {["OpenAI", "Gemini", "Claude", "Groq"].map((item) => <option key={item}>{item}</option>)}
                  </select>
                </div>
                <div>
                  <label className="field-label">API Key</label>
                  <input className="control mt-2" value={apiKey} onChange={(event) => setApiKey(event.target.value)} type="password" placeholder={aiConfig?.has_api_key ? "API key saved. Enter a new key to replace it." : `${provider} API key`} />
                  <p className="mt-2 text-xs text-muted">{aiConfig?.has_api_key ? `API key saved${aiConfig.verified_at ? ` and verified ${new Date(aiConfig.verified_at).toLocaleString()}` : ""}. It is not shown after saving.` : "Keys are sent to the backend for verification and are not exposed after saving."}</p>
                  <button type="button" className="button-ghost mt-3" onClick={saveAiSettings}>
                    <Save size={16} />
                    Verify & Load Models
                  </button>
                  {aiStatus && <p className="mt-2 text-xs text-muted">{aiStatus}</p>}
                </div>
                <div>
                  <label className="field-label">Default Model</label>
                  <select className="control mt-2" value={defaultModelId} onChange={(event) => setDefaultModelId(event.target.value)}>
                    {models.map((model) => <option key={model.id} value={model.id}>{model.display_name}</option>)}
                  </select>
                </div>
                <div className="space-y-2">
                  <p className="field-label">Available Models</p>
                  {models.map((model) => (
                    <div key={model.id} className="rounded-xl border border-border bg-panel p-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="truncate text-sm font-medium">{model.display_name}</p>
                        {!model.supports_vision && <span className="text-xs text-muted">Text only</span>}
                      </div>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {model.capabilities.map((capability) => <span key={capability} className="badge">{capability}</span>)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === "tools" && (
              <div className="space-y-4">
                <div>
                  <label className="field-label">Tavily API Key</label>
                  <input className="control mt-2" value={tavilyApiKey} onChange={(event) => setTavilyApiKey(event.target.value)} type="password" placeholder="tvly-..." />
                  <p className="mt-2 text-xs text-muted">Enables the Supervisor Agent to use Web Search Agent for current external information.</p>
                </div>
              </div>
            )}

            {activeTab === "prompts" && (
              <div className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="field-label">User name</label>
                    <input className="control mt-2" value={name} onChange={(event) => setName(event.target.value)} placeholder="What should MindMesh call you?" />
                  </div>
                  <div>
                    <label className="field-label">Response preferences</label>
                    <input className="control mt-2" value={preferences} onChange={(event) => setPreferences(event.target.value)} placeholder="Concise, detailed, reflective..." />
                  </div>
                </div>
                <div>
                  <label className="field-label">Bio / context</label>
                  <textarea className="control mt-2 min-h-36" value={bio} onChange={(event) => setBio(event.target.value)} placeholder="Background, goals, projects, tone preferences..." />
                </div>
              </div>
            )}

            {activeTab === "security" && (
              <div className="space-y-4">
                <div className="rounded-2xl border border-border bg-panel p-4">
                  <p className="font-medium">Theme</p>
                  <p className="mt-1 text-sm text-muted">Theme is applied globally and remembered between sessions.</p>
                  <div className="mt-3 flex gap-2">
                    <button onClick={() => onThemeChange("dark")} className={`button-ghost ${theme === "dark" ? "ring-2 ring-foreground/20" : ""}`}>
                      <Moon size={16} />
                      Dark
                    </button>
                    <button onClick={() => onThemeChange("light")} className={`button-ghost ${theme === "light" ? "ring-2 ring-foreground/20" : ""}`}>
                      <Sun size={16} />
                      Light
                    </button>
                  </div>
                </div>
                <div className="rounded-2xl border border-border bg-panel p-4">
                  <p className="font-medium">Local lock</p>
                  <p className="mt-1 text-sm text-muted">Inactivity lock is enabled and uses your local workspace PIN.</p>
                  <button className="button-ghost mt-3" onClick={() => {
                    localStorage.removeItem("mindmesh.workspace.pin");
                    onClose();
                  }}>
                    Reset local PIN
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        <footer className="flex justify-end gap-2 border-t border-border px-5 py-4">
          <button className="button-ghost" onClick={onClose}>Cancel</button>
          <button className="button-primary" onClick={save}>
            <Save size={16} />
            Save
          </button>
        </footer>
      </section>
    </div>
  );
}
