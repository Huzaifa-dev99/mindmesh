import { KeyRound, LockKeyhole, MessageSquareText, Moon, Save, Sun, X } from "lucide-react";
import { useState } from "react";

type SettingsTab = "keys" | "tools" | "prompts" | "security";

type Props = {
  open: boolean;
  onClose: () => void;
  theme: "dark" | "light";
  onThemeChange: (theme: "dark" | "light") => void;
};

const tabs: Array<{ key: SettingsTab; label: string; icon: typeof KeyRound }> = [
  { key: "keys", label: "API Keys", icon: KeyRound },
  { key: "tools", label: "Tools", icon: KeyRound },
  { key: "prompts", label: "Prompts", icon: MessageSquareText },
  { key: "security", label: "Security", icon: LockKeyhole }
];

export function SettingsDialog({ open, onClose, theme, onThemeChange }: Props) {
  const [activeTab, setActiveTab] = useState<SettingsTab>("keys");
  const [provider, setProvider] = useState(localStorage.getItem("mindmesh.provider") || "Groq");
  const [apiKey, setApiKey] = useState(localStorage.getItem("mindmesh.apiKey") || "");
  const [tavilyApiKey, setTavilyApiKey] = useState(localStorage.getItem("mindmesh.tavilyApiKey") || "");
  const [name, setName] = useState(localStorage.getItem("mindmesh.userName") || "");
  const [bio, setBio] = useState(localStorage.getItem("mindmesh.userBio") || "");
  const [preferences, setPreferences] = useState(localStorage.getItem("mindmesh.responsePrefs") || "");

  if (!open) return null;

  function save() {
    localStorage.setItem("mindmesh.provider", provider);
    localStorage.setItem("mindmesh.apiKey", apiKey);
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
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`sidebar-item ${activeTab === tab.key ? "sidebar-item-active" : ""}`}
                >
                  <Icon size={16} />
                  {tab.label}
                </button>
              );
            })}
          </nav>

          <div className="p-5">
            {activeTab === "keys" && (
              <div className="space-y-4">
                <div>
                  <label className="field-label">LLM Provider</label>
                  <select className="control mt-2" value={provider} onChange={(event) => setProvider(event.target.value)}>
                    {["OpenAI", "Gemini", "Claude", "Groq"].map((item) => <option key={item}>{item}</option>)}
                  </select>
                </div>
                <div>
                  <label className="field-label">API Key</label>
                  <input className="control mt-2" value={apiKey} onChange={(event) => setApiKey(event.target.value)} type="password" placeholder={`${provider} API key`} />
                  <p className="mt-2 text-xs text-muted">Stored locally in this browser for the single-user workspace UI.</p>
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
                  <button
                    className="button-ghost mt-3"
                    onClick={() => {
                      localStorage.removeItem("mindmesh.workspace.pin");
                      onClose();
                    }}
                  >
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
