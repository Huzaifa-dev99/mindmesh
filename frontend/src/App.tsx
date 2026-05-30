import {
  Activity,
  AlertCircle,
  Archive,
  ArrowUpRight,
  BarChart3,
  Bot,
  Brain,
  CheckCircle2,
  Check,
  Clock3,
  Command,
  Database,
  FileText,
  Gauge,
  Globe2,
  History,
  Home,
  KeyRound,
  Layers3,
  Library,
  Loader2,
  Menu,
  MessageSquare,
  MoreHorizontal,
  Palette,
  Plus,
  RefreshCw,
  Search,
  Send,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Moon,
  Sun,
  Tags,
  TerminalSquare,
  Trash2,
  UploadCloud,
  UserRound,
  X
} from "lucide-react";
import type * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { api } from "./api";

type Status = "indexed" | "not_indexed" | "failed";

type DocumentItem = {
  id: string;
  filename: string;
  status: Status;
  size: string;
  sizeBytes: number;
  chunks: number;
  tags: string[];
  version: string;
  updatedAt: string;
  error?: string;
};

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: { title: string; score: number; page: string }[];
};

type PromptItem = {
  name: string;
  description: string;
  status: "active" | "draft" | "archived";
  version: string;
  updatedAt: string;
  body: string;
};

type UserProfile = {
  name: string;
  avatar_url: string;
  bio: string;
  nicknames: string[];
  highlight_color: "mist" | "sage" | "lavender";
};

type WorkspaceContextValue = {
  attachedDocumentIds: string[];
  profile: UserProfile;
  setProfile: (profile: UserProfile) => void;
  toggleDocument: (documentId: string) => void;
};

const pageLabels: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/documents": "Document library",
  "/chat": "New chat",
  "/profile": "Profile",
  "/admin/prompts": "Prompt library",
  "/admin": "Model settings",
  "/api-connection": "API connections",
  "/personalization": "Personalization"
};

const settingsLinks = [
  { path: "/profile", label: "Profile", description: "Name, avatar, and response context", icon: UserRound },
  { path: "/admin/prompts", label: "Prompt library", description: "Review and version system prompts", icon: TerminalSquare },
  { path: "/admin", label: "Model settings", description: "Providers, models, and API keys", icon: Settings },
  { path: "/api-connection", label: "API connections", description: "Run service health checks", icon: KeyRound },
  { path: "/personalization", label: "Personalization", description: "Choose a gentle interface highlight", icon: Palette }
];

const palette = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];

type Theme = "light" | "dark";

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

function normalizeStatus(value?: string): Status {
  const cleaned = String(value || "").toLowerCase();
  if (cleaned.includes("fail")) return "failed";
  if (cleaned.includes("indexed") && !cleaned.includes("not")) return "indexed";
  return "not_indexed";
}

function toDocumentItem(raw: any, index: number): DocumentItem {
  const bytes = raw.size_bytes || raw.sizeBytes || raw.bytes || (typeof raw.size === "number" ? raw.size : 0);
  return {
    id: String(raw.id || raw.document_id || raw.filename || `doc-${index}`),
    filename: raw.filename || raw.name || `document-${index + 1}.pdf`,
    status: normalizeStatus(raw.status || (raw.indexed ? "indexed" : "not_indexed")),
    size: bytes ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : raw.size || "Unknown",
    sizeBytes: bytes,
    chunks: raw.chunk_count || raw.chunks || raw.vector_count || 0,
    tags: Array.isArray(raw.tags) ? raw.tags : [],
    version: raw.version || "v1",
    updatedAt: raw.updated_at || raw.updatedAt || "Recently",
    error: raw.error || raw.failure_reason
  };
}

function toMessage(raw: any): Message {
  return {
    id: String(raw.id || raw.interaction_id || crypto.randomUUID()),
    role: raw.role === "user" || raw.type === "query" ? "user" : "assistant",
    content: raw.content || raw.answer || raw.query || "",
    sources: (raw.sources || []).map((source: any) => ({
      title: source.filename || source.title || source.source || "Retrieved source",
      score: Number(source.score || source.relevance || 0),
      page: source.page || source.location || source.metadata?.page || "source"
    }))
  };
}

function toPromptItem(prompt: any): PromptItem {
  return {
    name: prompt.name,
    description: prompt.description || "Prompt template",
    status: prompt.status || "active",
    version: prompt.version || `v${prompt.version_number || 1}`,
    updatedAt: prompt.updated_at || "Recently",
    body: prompt.body || prompt.template || prompt.content || ""
  };
}

function matchesSearch(values: Array<string | number | undefined>, query: string) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;
  return values.some((value) => String(value || "").toLowerCase().includes(normalized));
}

function normalizeProfile(raw: any): UserProfile {
  return {
    name: raw?.name || "Local user",
    avatar_url: raw?.avatar_url || raw?.avatar || "",
    bio: raw?.bio || "",
    nicknames: Array.isArray(raw?.nicknames) ? raw.nicknames : [],
    highlight_color: ["mist", "sage", "lavender"].includes(raw?.highlight_color) ? raw.highlight_color : "mist"
  };
}

function readStoredDocumentIds() {
  try {
    const value = JSON.parse(window.localStorage.getItem("mindmesh-attached-documents") || "[]");
    return Array.isArray(value) ? value.map(String) : [];
  } catch {
    return [];
  }
}

function useWorkspace() {
  const workspace = useContext(WorkspaceContext);
  if (!workspace) throw new Error("Workspace context is unavailable.");
  return workspace;
}

function sessionGroup(value?: string) {
  if (!value) return "Earlier";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Earlier";
  const today = new Date();
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const startOfSession = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const diffDays = Math.round((startOfToday.getTime() - startOfSession.getTime()) / 86400000);
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return "Previous 7 days";
  return "Earlier";
}

function formatTimestamp(value?: string) {
  if (!value || value === "Recently") return "Recently";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: date.getFullYear() === new Date().getFullYear() ? undefined : "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(date);
}

function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function dashboardTotal(rawDashboard: any, keys: string[], fallback = 0) {
  for (const key of keys) {
    if (rawDashboard?.[key] !== undefined) return rawDashboard[key];
    if (rawDashboard?.totals?.[key] !== undefined) return rawDashboard.totals[key];
  }
  return fallback;
}

function getInitialTheme(): Theme {
  const savedTheme = window.localStorage.getItem("mindmesh-theme");
  if (savedTheme === "light" || savedTheme === "dark") return savedTheme;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    const initialTheme = getInitialTheme();
    document.documentElement.dataset.theme = initialTheme;
    return initialTheme;
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("mindmesh-theme", theme);
  }, [theme]);

  return {
    theme,
    toggleTheme: () => setTheme((current) => current === "dark" ? "light" : "dark")
  };
}

function useAsyncData<T>(loader: () => Promise<T>, fallback: T) {
  const [data, setData] = useState<T>(fallback);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setData(await loader());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return { data, loading, error, reload: load, setData };
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<GuardedShell />}>
          <Route index element={<Navigate to="/chat" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/admin/prompts" element={<PromptLibraryPage />} />
          <Route path="/api-connection" element={<ApiConnectionPage />} />
          <Route path="/personalization" element={<PersonalizationPage />} />
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

function GuardedShell() {
  const [checking, setChecking] = useState(true);
  const [locked, setLocked] = useState(false);
  const [profile, setProfile] = useState<UserProfile>(normalizeProfile({}));

  useEffect(() => {
    api
      .user()
      .then((user: any) => {
        const nextProfile = user.profile || user;
        setProfile(normalizeProfile(nextProfile));
        setLocked(Boolean(user.has_pin));
      })
      .catch(() => setLocked(false))
      .finally(() => setChecking(false));
  }, []);

  if (checking) {
    return (
      <div className="theme-scope app-canvas grid min-h-screen place-items-center text-slate-200">
        <Loader2 className="h-6 w-6 animate-spin text-cyan-300" />
      </div>
    );
  }

  if (locked) return <LockScreen onUnlock={() => setLocked(false)} />;
  return <AppShell profile={profile} />;
}

function LockScreen({ onUnlock }: { onUnlock: () => void }) {
  const [pin, setPin] = useState("");
  const [newPin, setNewPin] = useState("");
  const [resetMode, setResetMode] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      if (resetMode) {
        await api.resetUserPin(newPin);
        onUnlock();
      } else {
        const result: any = await api.verifyUserPin(pin);
        if (result.valid || result.unlocked) onUnlock();
        else setError("That PIN did not match.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to continue");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="theme-scope app-canvas relative grid min-h-screen place-items-center overflow-hidden px-5">
      <div className="ambient-backdrop absolute inset-0" />
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        className="premium-card relative w-full max-w-md rounded-3xl p-7"
      >
        <div className="mb-8 flex items-center gap-3">
          <BrandMark />
          <div>
            <h1 className="text-xl font-semibold text-white">MindMesh</h1>
            <p className="text-sm text-slate-400">Secure workspace access</p>
          </div>
        </div>
        <div className="space-y-4">
          <Input
            label={resetMode ? "New PIN" : "PIN"}
            type="password"
            value={resetMode ? newPin : pin}
            onChange={(event) => (resetMode ? setNewPin(event.target.value) : setPin(event.target.value))}
            placeholder="Enter PIN"
            onKeyDown={(event) => event.key === "Enter" && submit()}
          />
          {error ? <p className="text-sm text-rose-300">{error}</p> : null}
          <Button className="w-full" onClick={submit} disabled={busy || (!pin && !resetMode) || (!newPin && resetMode)}>
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
            {resetMode ? "Reset PIN" : "Unlock Workspace"}
          </Button>
          <button
            className="focus-ring w-full rounded-xl px-3 py-2 text-sm text-slate-400 transition hover:text-white"
            onClick={() => {
              setResetMode((value) => !value);
              setError("");
            }}
          >
            {resetMode ? "Back to unlock" : "Forgot PIN? Reset it"}
          </button>
        </div>
      </motion.div>
    </div>
  );
}

function AppShell({ profile: initialProfile }: { profile: UserProfile }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<"online" | "offline" | "warn">("warn");
  const [profile, setProfile] = useState(initialProfile);
  const [attachedDocumentIds, setAttachedDocumentIds] = useState<string[]>(readStoredDocumentIds);
  const [settingsDialogPath, setSettingsDialogPath] = useState("");
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    api
      .health()
      .then(() => setConnectionStatus("online"))
      .catch(() => setConnectionStatus("offline"));
  }, []);

  useEffect(() => {
    document.documentElement.dataset.accent = profile.highlight_color;
  }, [profile.highlight_color]);

  useEffect(() => {
    window.localStorage.setItem("mindmesh-attached-documents", JSON.stringify(attachedDocumentIds));
  }, [attachedDocumentIds]);

  const workspace = useMemo<WorkspaceContextValue>(
    () => ({
      attachedDocumentIds,
      profile,
      setProfile,
      toggleDocument: (documentId) =>
        setAttachedDocumentIds((current) =>
          current.includes(documentId) ? current.filter((id) => id !== documentId) : [...current, documentId]
        )
    }),
    [attachedDocumentIds, profile]
  );

  return (
    <WorkspaceContext.Provider value={workspace}>
      <div className="theme-scope app-shell min-h-screen text-slate-100">
        <div className="ambient-backdrop pointer-events-none fixed inset-0" />
        <Sidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          connectionStatus={connectionStatus}
          onOpenSettings={(path) => setSettingsDialogPath(path)}
        />
        <div className="relative min-w-0 lg:pl-[296px]">
          <TopBar
            onMenu={() => setSidebarOpen(true)}
            onOpenSettings={() => setSettingsDialogPath("/admin")}
            onToggleTheme={toggleTheme}
            theme={theme}
          />
          <main
            className={cn(
              "relative min-w-0 px-4 pb-6 pt-4 sm:px-6 lg:px-8 lg:pt-6",
              location.pathname === "/chat" ? "mx-auto max-w-[1680px]" : "mx-auto max-w-[1540px]"
            )}
          >
            <AnimatePresence initial={false} mode="wait">
              <motion.div
                key={location.pathname}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.16 }}
              >
                <Routes>
                  <Route index element={<Navigate to="/chat" replace />} />
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/documents" element={<DocumentsPage />} />
                  <Route path="/chat" element={<ChatPage />} />
                  <Route path="/profile" element={<ProfilePage />} />
                  <Route path="/admin" element={<AdminPage />} />
                  <Route path="/admin/prompts" element={<PromptLibraryPage />} />
                  <Route path="/api-connection" element={<ApiConnectionPage />} />
                  <Route path="/personalization" element={<PersonalizationPage />} />
                </Routes>
              </motion.div>
            </AnimatePresence>
          </main>
        </div>
        <WorkspaceSettingsDialog
          activePath={settingsDialogPath}
          open={Boolean(settingsDialogPath)}
          onChange={setSettingsDialogPath}
          onClose={() => setSettingsDialogPath("")}
        />
      </div>
    </WorkspaceContext.Provider>
  );
}

function Sidebar({
  open,
  onClose,
  connectionStatus,
  onOpenSettings
}: {
  open: boolean;
  onClose: () => void;
  connectionStatus: "online" | "offline" | "warn";
  onOpenSettings: (path: string) => void;
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const workspace = useWorkspace();
  const [activeTab, setActiveTab] = useState<"documents" | "chats">("documents");
  const [showArchived, setShowArchived] = useState(false);
  const [openActions, setOpenActions] = useState("");
  const documentsState = useAsyncData<DocumentItem[]>(
    async () => {
      const response: any = await api.documents();
      const documents = Array.isArray(response) ? response : response.documents || [];
      return documents.map(toDocumentItem);
    },
    []
  );
  const sessionsState = useAsyncData<any[]>(
    async () => {
      const response: any = await api.sessions();
      return Array.isArray(response) ? response : response.sessions || [];
    },
    []
  );

  const indexedDocuments = documentsState.data.filter((document) => document.status === "indexed");
  const visibleSessions = sessionsState.data.filter((session) => Boolean(session.archived) === showArchived);
  const groupedSessions = useMemo(
    () =>
      visibleSessions.reduce<Record<string, any[]>>((groups, session) => {
        const group = sessionGroup(session.updated_at || session.updatedAt);
        groups[group] = [...(groups[group] || []), session];
        return groups;
      }, {}),
    [visibleSessions]
  );

  const startNewChat = () => {
    navigate(`/chat?new=${Date.now()}`);
    onClose();
  };

  const updateSession = async (sessionId: string, payload: unknown) => {
    await api.updateSession(sessionId, payload);
    setOpenActions("");
    sessionsState.reload();
  };

  return (
    <>
      <AnimatePresence>
        {open ? (
          <motion.button
            aria-label="Close workspace rail"
            className="fixed inset-0 z-40 bg-black/50 lg:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
        ) : null}
      </AnimatePresence>
      <aside
        className={cn(
          "sidebar-shell fixed inset-y-0 left-0 z-50 flex w-[296px] flex-col border-r border-white/8 p-3 backdrop-blur-xl transition-transform duration-300",
          open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        <div className="flex items-center justify-between px-1 py-1">
          <button className="focus-ring flex items-center gap-3 rounded-xl text-left" onClick={() => navigate("/chat")}>
            <BrandMark />
            <div>
              <p className="text-base font-semibold tracking-tight text-white">MindMesh</p>
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">Knowledge workspace</p>
            </div>
          </button>
          <button className="focus-ring rounded-xl p-2 text-slate-400 hover:bg-white/5 hover:text-white lg:hidden" onClick={onClose}>
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-5 grid gap-2">
          <button
            className={cn(
              "focus-ring flex items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition",
              location.pathname === "/dashboard" ? "active-nav" : "text-slate-400 hover:bg-white/[0.055] hover:text-white"
            )}
            onClick={() => {
              navigate("/dashboard");
              onClose();
            }}
          >
            <Home className="h-4 w-4" />
            Dashboard
          </button>
          <Button className="w-full" onClick={startNewChat}>
            <Plus className="h-4 w-4" />
            New chat
          </Button>
        </div>

        <div className="mt-4 flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-white/8 bg-white/[0.025]">
          <div className="grid grid-cols-2 border-b border-white/8 p-1">
            {(["documents", "chats"] as const).map((tab) => (
              <button
                key={tab}
                className={cn(
                  "focus-ring rounded-lg px-2 py-2 text-xs font-semibold capitalize transition",
                  activeTab === tab ? "tab-active" : "text-slate-500 hover:bg-white/5 hover:text-white"
                )}
                onClick={() => setActiveTab(tab)}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto p-2">
            {activeTab === "documents" ? (
              <WorkspaceDocuments
                documents={indexedDocuments}
                loading={documentsState.loading}
                attachedDocumentIds={workspace.attachedDocumentIds}
                onToggle={workspace.toggleDocument}
                onOpenLibrary={() => {
                  navigate("/documents");
                  onClose();
                }}
              />
            ) : (
              <WorkspaceSessions
                groups={groupedSessions}
                loading={sessionsState.loading}
                openActions={openActions}
                showArchived={showArchived}
                onOpenActions={setOpenActions}
                onOpenSession={(sessionId) => {
                  navigate(`/chat?session=${sessionId}`);
                  onClose();
                }}
                onRename={async (session) => {
                  const title = window.prompt("Rename chat", session.title || "");
                  if (title?.trim()) await updateSession(String(session.id), { title: title.trim() });
                }}
                onArchive={(session) => updateSession(String(session.id), { archived: !Boolean(session.archived) })}
                onDelete={async (session) => {
                  if (!window.confirm(`Delete "${session.title || "this chat"}"? This cannot be undone.`)) return;
                  await api.deleteSession(String(session.id));
                  setOpenActions("");
                  sessionsState.reload();
                }}
                onToggleArchived={() => setShowArchived((current) => !current)}
              />
            )}
          </div>
        </div>

        <div className="mt-3">
          <button
            aria-haspopup="dialog"
            className="focus-ring flex w-full items-center gap-3 rounded-2xl border border-white/8 bg-white/[0.025] p-3 text-left transition hover:bg-white/[0.055]"
            onClick={() => {
              onOpenSettings("/profile");
              onClose();
            }}
          >
            <ProfileAvatar profile={workspace.profile} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-white">{workspace.profile.name}</p>
              <p className="mt-0.5 flex items-center gap-1.5 text-xs capitalize text-slate-500">
                <StatusIndicator status={connectionStatus} />
                Services {connectionStatus}
              </p>
            </div>
            <Settings className="h-4 w-4 text-slate-500" />
          </button>
        </div>
      </aside>
    </>
  );
}

function WorkspaceDocuments({
  documents,
  loading,
  attachedDocumentIds,
  onToggle,
  onOpenLibrary
}: {
  documents: DocumentItem[];
  loading: boolean;
  attachedDocumentIds: string[];
  onToggle: (documentId: string) => void;
  onOpenLibrary: () => void;
}) {
  return (
    <div>
      <div className="flex items-center justify-between gap-2 px-1 py-2">
        <div>
          <p className="text-xs font-semibold text-slate-300">Query sources</p>
          <p className="mt-1 text-[11px] leading-4 text-slate-500">Attach indexed documents to narrow answers.</p>
        </div>
        <button className="focus-ring rounded-lg px-2 py-1 text-[11px] font-semibold text-cyan-200 hover:bg-white/5" onClick={onOpenLibrary}>
          Manage
        </button>
      </div>
      <div className="mt-1 space-y-1">
        {loading ? [0, 1, 2].map((item) => <div key={item} className="loading-shimmer h-12 rounded-xl" />) : null}
        {!loading && !documents.length ? <p className="px-2 py-6 text-center text-xs leading-5 text-slate-500">Index documents to attach them to chat.</p> : null}
        {documents.map((document) => {
          const attached = attachedDocumentIds.includes(document.id);
          return (
            <button
              key={document.id}
              aria-pressed={attached}
              className={cn(
                "focus-ring flex w-full items-center gap-2 rounded-xl border px-2.5 py-2 text-left transition",
                attached ? "border-cyan-300/40 bg-cyan-300/10" : "border-transparent hover:border-white/8 hover:bg-white/[0.045]"
              )}
              onClick={() => onToggle(document.id)}
            >
              <span className={cn("grid h-7 w-7 shrink-0 place-items-center rounded-lg", attached ? "bg-cyan-300 text-slate-950" : "bg-white/[0.055] text-slate-400")}>
                {attached ? <Check className="h-3.5 w-3.5" /> : <FileText className="h-3.5 w-3.5" />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-xs font-semibold text-slate-300">{document.filename}</span>
                <span className="mt-0.5 block text-[11px] text-slate-500">{document.chunks} indexed chunks</span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function WorkspaceSessions({
  groups,
  loading,
  openActions,
  showArchived,
  onOpenActions,
  onOpenSession,
  onRename,
  onArchive,
  onDelete,
  onToggleArchived
}: {
  groups: Record<string, any[]>;
  loading: boolean;
  openActions: string;
  showArchived: boolean;
  onOpenActions: (sessionId: string) => void;
  onOpenSession: (sessionId: string) => void;
  onRename: (session: any) => void;
  onArchive: (session: any) => void;
  onDelete: (session: any) => void;
  onToggleArchived: () => void;
}) {
  const orderedGroups = ["Today", "Yesterday", "Previous 7 days", "Earlier"];
  return (
    <div>
      <div className="flex items-center justify-between gap-2 px-1 py-2">
        <div>
          <p className="text-xs font-semibold text-slate-300">{showArchived ? "Archived chats" : "Recent chats"}</p>
          <p className="mt-1 text-[11px] leading-4 text-slate-500">Resume or organize conversations.</p>
        </div>
        <button className="focus-ring rounded-lg px-2 py-1 text-[11px] font-semibold text-cyan-200 hover:bg-white/5" onClick={onToggleArchived}>
          {showArchived ? "Recent" : "Archive"}
        </button>
      </div>
      {loading ? [0, 1, 2].map((item) => <div key={item} className="loading-shimmer mb-1 h-12 rounded-xl" />) : null}
      {!loading && !Object.keys(groups).length ? <p className="px-2 py-6 text-center text-xs leading-5 text-slate-500">No {showArchived ? "archived" : "recent"} chats yet.</p> : null}
      {orderedGroups.map((group) =>
        groups[group]?.length ? (
          <div className="mt-3" key={group}>
            <p className="px-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600">{group}</p>
            <div className="mt-1 space-y-0.5">
              {groups[group].map((session) => (
                <div className="relative" key={session.id}>
                  <button
                    className="focus-ring w-full rounded-xl px-2.5 py-2 pr-9 text-left transition hover:bg-white/[0.055]"
                    onClick={() => onOpenSession(String(session.id))}
                  >
                    <span className="block truncate text-xs font-semibold text-slate-300">{session.title || "Untitled chat"}</span>
                    <span className="mt-0.5 block text-[11px] text-slate-500">{session.interaction_count || 0} messages</span>
                  </button>
                  <button
                    aria-label={`Open actions for ${session.title || "chat"}`}
                    className="focus-ring absolute right-1 top-2 rounded-lg p-1.5 text-slate-500 hover:bg-white/8 hover:text-white"
                    onClick={() => onOpenActions(openActions === String(session.id) ? "" : String(session.id))}
                  >
                    <MoreHorizontal className="h-3.5 w-3.5" />
                  </button>
                  {openActions === String(session.id) ? (
                    <div className="menu-surface absolute right-0 top-9 z-20 w-36 rounded-xl border border-white/10 p-1 shadow-xl">
                      <button className="w-full rounded-lg px-2 py-1.5 text-left text-xs text-slate-300 hover:bg-white/8" onClick={() => onRename(session)}>Rename</button>
                      <button className="w-full rounded-lg px-2 py-1.5 text-left text-xs text-slate-300 hover:bg-white/8" onClick={() => onArchive(session)}>
                        {session.archived ? "Restore" : "Archive"}
                      </button>
                      <button className="w-full rounded-lg px-2 py-1.5 text-left text-xs text-rose-200 hover:bg-rose-400/10" onClick={() => onDelete(session)}>Delete</button>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        ) : null
      )}
    </div>
  );
}

function SettingsMenu({ activePath, onNavigate }: { activePath: string; onNavigate: (path: string) => void }) {
  return (
    <nav className="flex gap-1 overflow-x-auto p-2 md:flex-col md:overflow-visible" aria-label="Workspace settings sections">
      {settingsLinks.map((item) => (
        <button
          key={item.path}
          aria-current={activePath === item.path ? "page" : undefined}
          className={cn(
            "focus-ring flex shrink-0 items-center gap-2.5 rounded-xl px-2.5 py-2.5 text-left transition md:w-full",
            activePath === item.path ? "active-nav" : "hover:bg-white/8"
          )}
          onClick={() => onNavigate(item.path)}
        >
          <span className="accent-icon grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-cyan-300/10 text-cyan-200">
            <item.icon className="h-4 w-4" />
          </span>
          <span className="min-w-0">
            <span className="block text-xs font-semibold text-slate-300">{item.label}</span>
            <span className="mt-0.5 hidden truncate text-[11px] text-slate-500 md:block">{item.description}</span>
          </span>
        </button>
      ))}
    </nav>
  );
}

function WorkspaceSettingsDialog({
  activePath,
  open,
  onChange,
  onClose
}: {
  activePath: string;
  open: boolean;
  onChange: (path: string) => void;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-[80] grid place-items-center bg-black/55 p-2 backdrop-blur-sm sm:p-5"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          role="presentation"
          onMouseDown={onClose}
        >
          <motion.section
            aria-labelledby="workspace-settings-title"
            aria-modal="true"
            className="menu-surface flex h-[min(900px,calc(100vh-16px))] w-full max-w-[1280px] flex-col overflow-hidden rounded-[22px] border border-white/10 shadow-2xl sm:h-[min(900px,calc(100vh-40px))]"
            initial={{ opacity: 0, scale: 0.985, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.985, y: 8 }}
            transition={{ duration: 0.16 }}
            role="dialog"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <header className="flex items-center justify-between gap-4 border-b border-white/10 px-4 py-3 sm:px-5">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">MindMesh workspace</p>
                <h2 className="mt-1 text-lg font-semibold text-white" id="workspace-settings-title">Settings</h2>
              </div>
              <button
                autoFocus
                aria-label="Close workspace settings"
                className="focus-ring rounded-xl border border-white/10 bg-white/[0.035] p-2.5 text-slate-400 transition hover:border-white/20 hover:bg-white/[0.075] hover:text-white"
                onClick={onClose}
              >
                <X className="h-4 w-4" />
              </button>
            </header>
            <div className="grid min-h-0 min-w-0 flex-1 grid-rows-[auto_minmax(0,1fr)] md:grid-cols-[232px_minmax(0,1fr)] md:grid-rows-1">
              <div className="min-w-0 overflow-hidden border-b border-white/10 md:border-b-0 md:border-r">
                <SettingsMenu activePath={activePath} onNavigate={onChange} />
              </div>
              <div className="min-w-0 overflow-x-hidden overflow-y-auto p-4 sm:p-6">
                <SettingsDialogPage path={activePath} />
              </div>
            </div>
          </motion.section>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

function SettingsDialogPage({ path }: { path: string }) {
  switch (path) {
    case "/admin/prompts":
      return <PromptLibraryPage />;
    case "/admin":
      return <AdminPage />;
    case "/api-connection":
      return <ApiConnectionPage />;
    case "/personalization":
      return <PersonalizationPage />;
    default:
      return <ProfilePage />;
  }
}

function ProfileAvatar({ profile, className = "" }: { profile: UserProfile; className?: string }) {
  return (
    <div className={cn("grid h-10 w-10 shrink-0 place-items-center overflow-hidden rounded-xl bg-cyan-300 text-sm font-bold text-slate-950", className)}>
      {profile.avatar_url ? <img className="h-full w-full object-cover" src={profile.avatar_url} alt="" /> : profile.name.slice(0, 1)}
    </div>
  );
}

function TopBar({
  onMenu,
  onOpenSettings,
  onToggleTheme,
  theme
}: {
  onMenu: () => void;
  onOpenSettings: () => void;
  onToggleTheme: () => void;
  theme: Theme;
}) {
  const location = useLocation();
  const workspace = useWorkspace();
  const currentPage = pageLabels[location.pathname] || "Workspace";

  return (
    <header className="topbar-shell sticky top-0 z-30 border-b border-white/8 backdrop-blur-xl">
      <div className="flex h-[64px] items-center gap-3 px-4 sm:px-6 lg:px-8">
        <button aria-label="Open workspace rail" className="focus-ring rounded-xl p-2 text-slate-300 hover:bg-white/6 hover:text-white lg:hidden" onClick={onMenu}>
          <Menu className="h-5 w-5" />
        </button>
        <div>
          <p className="text-sm font-semibold text-slate-300">{currentPage}</p>
          {location.pathname === "/chat" ? (
            <p className="mt-0.5 hidden text-xs text-slate-500 sm:block">
              {workspace.attachedDocumentIds.length ? `${workspace.attachedDocumentIds.length} document${workspace.attachedDocumentIds.length === 1 ? "" : "s"} attached` : "Ask across your indexed knowledge"}
            </p>
          ) : null}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <button
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            className="focus-ring inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/[0.035] text-slate-400 transition hover:border-white/20 hover:bg-white/[0.075] hover:text-white"
            onClick={onToggleTheme}
            title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
          <button
            aria-haspopup="dialog"
            aria-label="Open workspace settings"
            className="focus-ring inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/[0.035] text-slate-400 transition hover:border-white/20 hover:bg-white/[0.075] hover:text-white"
            onClick={onOpenSettings}
          >
            <Settings className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  );
}

function DashboardPage() {
  const { data: rawDashboard, loading, error, reload } = useAsyncData<any>(() => api.dashboard(), {});
  const { data: rawDocs } = useAsyncData<any[]>(async () => {
    const response: any = await api.documents();
    return Array.isArray(response) ? response : response.documents || [];
  }, []);

  const documents = rawDocs.map(toDocumentItem);
  const indexed = documents.filter((doc) => doc.status === "indexed").length;
  const failed = documents.filter((doc) => doc.status === "failed").length;
  const totalChunks = documents.reduce((sum, doc) => sum + doc.chunks, 0);
  const totalBytes = documents.reduce((sum, doc) => sum + doc.sizeBytes, 0);
  const avgSize = documents.length ? totalBytes / documents.length / 1024 / 1024 : 0;
  const storageBytes = rawDashboard.storage?.total_bytes ?? totalBytes;
  const retrievalScore = rawDashboard.retrieval?.average_score ?? rawDashboard.retrieval?.score ?? 0;
  const recentQueries = rawDashboard.recent_queries || [];
  const recentFailed = rawDashboard.recent_failed_documents?.length
    ? rawDashboard.recent_failed_documents.map(toDocumentItem)
    : documents.filter((doc) => doc.status === "failed");

  const metrics = [
    { label: "Documents uploaded", value: dashboardTotal(rawDashboard, ["documents", "total_documents"], documents.length), trend: "Live registry", icon: FileText },
    { label: "Documents indexed", value: dashboardTotal(rawDashboard, ["indexed_documents"], indexed), trend: "Vector-ready", icon: Database },
    { label: "Failed documents", value: rawDashboard.failed_documents ?? failed, trend: failed ? "Needs review" : "Clear", icon: AlertCircle },
    { label: "Retrieval score", value: retrievalScore ? `${Math.round(retrievalScore * 100)}%` : "N/A", trend: retrievalScore ? "Recent average" : "Awaiting queries", icon: Gauge }
  ];
  const supportingMetrics = [
    { label: "Chat sessions", value: dashboardTotal(rawDashboard, ["chat_sessions", "sessions"], 0), trend: "Stored sessions", icon: MessageSquare },
    { label: "Retrieved chunks", value: dashboardTotal(rawDashboard, ["retrieved_chunks"], totalChunks), trend: "Indexed chunks", icon: Layers3 },
    { label: "Storage", value: `${(storageBytes / 1024 / 1024).toFixed(1)} MB`, trend: "Object storage", icon: Archive },
    { label: "Avg document size", value: `${avgSize.toFixed(1)} MB`, trend: "Computed live", icon: BarChart3 }
  ];

  const analytics = (rawDashboard.document_status?.length ? rawDashboard.document_status : countBy(documents.map((doc) => doc.status))).map(
    (item: any) => ({ name: item.status || item.name || item.label, documents: item.count || item.value || 0 })
  );
  const tagDistribution = rawDashboard.document_tags?.length
    ? rawDashboard.document_tags.map((item: any) => ({ name: item.tag || item.name || "untagged", value: item.count || item.value || 0 }))
    : countBy(documents.flatMap((doc) => doc.tags.length ? doc.tags : ["untagged"]));
  const versionDistribution = rawDashboard.document_versions?.length
    ? rawDashboard.document_versions.map((item: any) => ({ name: item.version || item.name || "unknown", value: item.count || item.value || 0 }))
    : countBy(documents.map((doc) => doc.version));
  const largestDocuments = [...documents].sort((a, b) => b.sizeBytes - a.sizeBytes).slice(0, 5);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Workspace intelligence"
        title="Dashboard"
        description="A live view of indexing health, retrieval quality, document growth, and usage across MindMesh."
        actions={
          <>
            <Button variant="secondary" onClick={reload}>
              <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
              Refresh
            </Button>
            <Button onClick={() => downloadJson("mindmesh-dashboard.json", { dashboard: rawDashboard, documents })}>
              <ArrowUpRight className="h-4 w-4" />
              Export
            </Button>
          </>
        }
      />
      {error ? <InlineNotice tone="warn" message={`Dashboard API error: ${error}`} /> : null}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <MetricCard key={metric.label} {...metric} />
        ))}
      </div>
      <Card className="p-4 sm:p-5">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {supportingMetrics.map((metric) => (
            <div key={metric.label} className="flex items-center gap-3 border-white/8 xl:border-r xl:last:border-r-0">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-cyan-300/10 text-cyan-200">
                <metric.icon className="h-4 w-4" />
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">{metric.label}</p>
                <p className="mt-1 text-lg font-semibold text-white">{metric.value}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>
      <div className="grid gap-4 xl:grid-cols-[1.45fr_0.85fr]">
        <Card className="min-h-[360px]">
          <SectionTitle icon={Activity} title="Document analytics" subtitle="Indexed documents and retrieval activity" />
          <div className="mt-6 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={analytics}>
                <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
                <XAxis dataKey="name" stroke="var(--text-faint)" tickLine={false} axisLine={false} />
                <YAxis stroke="var(--text-faint)" tickLine={false} axisLine={false} width={34} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="documents" fill="var(--chart-1)" isAnimationActive={false} radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-1">
          <DistributionCard title="Tag distribution" data={tagDistribution} />
          <DistributionCard title="Version distribution" data={versionDistribution} />
        </div>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <SectionTitle icon={MessageSquare} title="Recent queries" subtitle="Latest retrieval requests" />
          <div className="mt-5 space-y-3">
            {recentQueries.length ? (
              recentQueries.map((query: any, index: number) => (
                <div key={query.id || query.query || index} className="flex items-center justify-between rounded-2xl border border-white/8 bg-white/[0.025] p-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-white">{query.query || query.question || "Untitled query"}</p>
                    <p className="text-xs text-slate-500">{query.context_count ?? query.sources ?? 0} sources retrieved</p>
                  </div>
                  <Badge tone={index === 0 ? "success" : "neutral"}>{query.score ? Number(query.score).toFixed(2) : "Live"}</Badge>
                </div>
              ))
            ) : (
              <EmptyState icon={MessageSquare} title="No recent queries" description="Chat activity will appear here after users ask questions." />
            )}
          </div>
        </Card>
        <Card>
          <SectionTitle icon={AlertCircle} title="Failed documents" subtitle="Items that need attention" />
          <div className="mt-5 space-y-3">
            {recentFailed.length ? (
              recentFailed.map((doc: DocumentItem) => <DocumentRowCompact key={doc.id} doc={doc} />)
            ) : (
              <EmptyState icon={CheckCircle2} title="No failed documents" description="All recent uploads are healthy." />
            )}
          </div>
        </Card>
      </div>
      <Card>
        <SectionTitle icon={Archive} title="Largest documents" subtitle="Storage-heavy files in the corpus" />
        {largestDocuments.length ? (
          <DataTable
            columns={["Document", "Status", "Chunks", "Size", "Updated"]}
            rows={largestDocuments.map((doc) => [
              <DocumentName doc={doc} />,
              <StatusBadge status={doc.status} />,
              doc.chunks,
              doc.size,
              formatTimestamp(doc.updatedAt)
            ])}
          />
        ) : (
          <EmptyState icon={Archive} title="No documents yet" description="Uploaded documents will be ranked here by storage size." />
        )}
      </Card>
    </div>
  );
}

function DocumentsPage() {
  const [searchParams] = useSearchParams();
  const [tab, setTab] = useState<Status | "all">("all");
  const [selected, setSelected] = useState<string[]>([]);
  const [openActions, setOpenActions] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState("");
  const [pendingRemoval, setPendingRemoval] = useState<{ ids: string[]; label: string } | null>(null);
  const [tags, setTags] = useState("policy, product");
  const [owner, setOwner] = useState("Knowledge Ops");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const docsState = useAsyncData<DocumentItem[]>(
    async () => {
      const response: any = await api.documents();
      const docs = Array.isArray(response) ? response : response.documents || [];
      return docs.map(toDocumentItem);
    },
    []
  );

  const documents = docsState.data;
  const query = searchParams.get("q") || "";
  const visibleDocs = (tab === "all" ? documents : documents.filter((doc) => doc.status === tab)).filter((doc) =>
    matchesSearch([doc.filename, doc.status, doc.version, ...doc.tags], query)
  );

  const executeDocumentAction = async (targetIds: string[], action: "index" | "removeVectors" | "removeDocuments") => {
    if (!targetIds.length) return;
    setNotice("");
    try {
      if (action === "index") await api.indexDocuments(targetIds);
      if (action === "removeVectors") await api.removeVectors(targetIds);
      if (action === "removeDocuments") await api.removeDocuments(targetIds);
      setNotice("Document action completed.");
      setSelected([]);
      docsState.reload();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Document action failed.");
    }
  };

  const runDocumentAction = async (action: "index" | "removeVectors" | "removeDocuments") => {
    if (!selected.length) return;
    if (action === "removeDocuments") {
      setPendingRemoval({ ids: selected, label: `${selected.length} selected document${selected.length === 1 ? "" : "s"}` });
      return;
    }
    await executeDocumentAction(selected, action);
  };

  const runSingleDocumentAction = async (doc: DocumentItem, action: "index" | "removeVectors" | "removeDocuments") => {
    setOpenActions("");
    if (action === "removeDocuments") {
      setPendingRemoval({ ids: [doc.id], label: doc.filename });
      return;
    }
    await executeDocumentAction([doc.id], action);
  };

  const uploadFiles = async () => {
    if (!files.length) return;
    setUploading(true);
    setNotice("");
    const form = new FormData();
    files.forEach((file) => {
      form.append("files", file);
      form.append("filenames", file.name);
      form.append("tags", tags);
    });
    try {
      await api.uploadDocuments(form);
      setFiles([]);
      setNotice("Upload completed and queued for indexing.");
      docsState.reload();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Corpus management"
        title="Documents"
        description="Upload, enrich, index, and maintain the documents that power retrieval."
        actions={
          <>
            <Button variant="secondary" onClick={docsState.reload}>
              <RefreshCw className={cn("h-4 w-4", docsState.loading && "animate-spin")} />
              Refresh
            </Button>
            <Button onClick={() => fileInputRef.current?.click()}>
              <UploadCloud className="h-4 w-4" />
              Upload
            </Button>
          </>
        }
      />
      {notice ? <InlineNotice tone={notice.includes("failed") || notice.includes("Unable") ? "warn" : "success"} message={notice} /> : null}
      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.4fr]">
        <div className="space-y-4">
          <UploadDropzone
            files={files}
            inputRef={fileInputRef}
            uploading={uploading}
            onFiles={(next) => setFiles((current) => [...current, ...next])}
            onUpload={uploadFiles}
            onClear={() => setFiles([])}
          />
          <Card>
            <SectionTitle icon={Tags} title="Metadata editor" subtitle="Applied to the current upload queue" />
            <div className="mt-5 space-y-4">
              <Input label="Owner" value={owner} onChange={(event) => setOwner(event.target.value)} />
              <Input label="Tags" value={tags} onChange={(event) => setTags(event.target.value)} />
              <div className="flex flex-wrap gap-2">
                {tags
                  .split(",")
                  .map((tag) => tag.trim())
                  .filter(Boolean)
                  .map((tag) => (
                    <TagChip key={tag}>{tag}</TagChip>
                  ))}
              </div>
            </div>
          </Card>
        </div>
        <Card className="min-w-0">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <SectionTitle icon={Library} title="Document library" subtitle={`${documents.length} documents in the workspace`} />
            <div className={cn("flex flex-wrap items-center gap-2 transition", !selected.length && "opacity-60")}>
              <span className="mr-1 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                {selected.length ? `${selected.length} selected` : "Select files to manage"}
              </span>
              <Button variant="secondary" onClick={() => runDocumentAction("index")} disabled={!selected.length}>
                <Database className="h-4 w-4" />
                Index
              </Button>
              <Button variant="secondary" onClick={() => runDocumentAction("removeVectors")} disabled={!selected.length}>
                <Trash2 className="h-4 w-4" />
                Clear vectors
              </Button>
              <Button variant="danger" onClick={() => runDocumentAction("removeDocuments")} disabled={!selected.length}>
                <Trash2 className="h-4 w-4" />
                Delete
              </Button>
            </div>
          </div>
          <Tabs
            className="mt-6"
            value={tab}
            onChange={(value) => setTab(value as Status | "all")}
            items={[
              { value: "all", label: "All" },
              { value: "indexed", label: "Indexed" },
              { value: "not_indexed", label: "Not indexed" },
              { value: "failed", label: "Failed" }
            ]}
          />
          <div className="mt-5 overflow-x-auto rounded-2xl border border-white/10">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-white/[0.035] text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="w-12 px-4 py-3">
                    <input
                      aria-label="Select all visible documents"
                      className="focus-ring h-4 w-4 rounded border-white/20 bg-transparent accent-cyan-300"
                      type="checkbox"
                      checked={Boolean(visibleDocs.length) && visibleDocs.every((doc) => selected.includes(doc.id))}
                      onChange={(event) => {
                        const visibleIds = visibleDocs.map((doc) => doc.id);
                        setSelected((current) =>
                          event.target.checked ? Array.from(new Set([...current, ...visibleIds])) : current.filter((id) => !visibleIds.includes(id))
                        );
                      }}
                    />
                  </th>
                  <th className="px-4 py-3">Document</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Tags</th>
                  <th className="px-4 py-3">Chunks</th>
                  <th className="px-4 py-3">Size</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/8">
                {docsState.loading ? [0, 1, 2].map((item) => (
                  <tr key={item}>
                    <td className="px-4 py-4" colSpan={7}>
                      <div className="loading-shimmer h-10 rounded-xl" />
                    </td>
                  </tr>
                )) : visibleDocs.map((doc) => (
                  <tr key={doc.id} className="transition hover:bg-white/[0.025]">
                    <td className="px-4 py-4">
                      <input
                        aria-label={`Select ${doc.filename}`}
                        className="focus-ring h-4 w-4 rounded border-white/20 bg-transparent accent-cyan-300"
                        type="checkbox"
                        checked={selected.includes(doc.id)}
                        onChange={() =>
                          setSelected((current) =>
                            current.includes(doc.id) ? current.filter((id) => id !== doc.id) : [...current, doc.id]
                          )
                        }
                      />
                    </td>
                    <td className="px-4 py-4">
                      <DocumentName doc={doc} />
                    </td>
                    <td className="px-4 py-4">
                      <StatusBadge status={doc.status} />
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex flex-wrap gap-1.5">
                        {(doc.tags.length ? doc.tags : ["untagged"]).slice(0, 2).map((tag) => (
                          <TagChip key={tag}>{tag}</TagChip>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-4 text-slate-300">{doc.chunks}</td>
                    <td className="px-4 py-4 text-slate-300">{doc.size}</td>
                    <td className="relative px-4 py-4 text-right">
                      <button
                        aria-label={`Open actions for ${doc.filename}`}
                        className="focus-ring rounded-xl p-2 text-slate-400 hover:bg-white/6 hover:text-white"
                        onClick={() => setOpenActions((current) => (current === doc.id ? "" : doc.id))}
                      >
                        <MoreHorizontal className="h-4 w-4" />
                      </button>
                      {openActions === doc.id ? (
                        <div className="menu-surface absolute right-4 top-12 z-20 w-44 rounded-xl border border-white/10 p-1 shadow-2xl">
                          <button className="w-full rounded-xl px-3 py-2 text-left text-sm text-slate-300 hover:bg-white/8" onClick={() => runSingleDocumentAction(doc, "index")}>
                            Index document
                          </button>
                          <button className="w-full rounded-xl px-3 py-2 text-left text-sm text-slate-300 hover:bg-white/8" onClick={() => runSingleDocumentAction(doc, "removeVectors")}>
                            Remove vectors
                          </button>
                          <button className="w-full rounded-xl px-3 py-2 text-left text-sm text-rose-200 hover:bg-rose-400/10" onClick={() => runSingleDocumentAction(doc, "removeDocuments")}>
                            Remove document
                          </button>
                        </div>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!docsState.loading && !visibleDocs.length ? (
            <div className="mt-5">
              <EmptyState
                icon={FileText}
                title={query ? "No matching documents" : "No documents yet"}
                description={query ? "Clear or change the search query to see more documents." : "Upload files to populate the document library."}
              />
            </div>
          ) : null}
        </Card>
      </div>
      <ConfirmDialog
        open={Boolean(pendingRemoval)}
        title="Delete documents?"
        description={`${pendingRemoval?.label || "This document"} will be removed from the workspace. This cannot be undone.`}
        confirmLabel="Delete permanently"
        onCancel={() => setPendingRemoval(null)}
        onConfirm={async () => {
          const ids = pendingRemoval?.ids || [];
          setPendingRemoval(null);
          await executeDocumentAction(ids, "removeDocuments");
        }}
      />
    </div>
  );
}

function ChatPage() {
  const [searchParams] = useSearchParams();
  const workspace = useWorkspace();
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeSession, setActiveSession] = useState("");
  const [input, setInput] = useState("");
  const [topK, setTopK] = useState(6);
  const [threshold, setThreshold] = useState(0.72);
  const [sourceMode, setSourceMode] = useState("balanced");
  const [webSearchEnabled, setWebSearchEnabled] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const newChat = () => {
    setActiveSession("");
    setMessages([]);
    setInput("");
  };

  const loadSession = async (session: any) => {
    const sessionId = String(session.id || session.session_id || "");
    if (!sessionId) return;
    setActiveSession(sessionId);
    setLoading(true);
    try {
      const response: any = await api.interactions(sessionId);
      const interactions = Array.isArray(response) ? response : response.interactions || [];
      setMessages(
        interactions.flatMap((interaction: any) => {
          if (interaction.query && interaction.answer) {
            return [
              { id: `${interaction.id || interaction.interaction_id || crypto.randomUUID()}-q`, role: "user", content: interaction.query },
              toMessage({ ...interaction, role: "assistant" })
            ] as Message[];
          }
          return [toMessage(interaction)];
        })
      );
    } catch (err) {
      setMessages([{ id: crypto.randomUUID(), role: "assistant", content: err instanceof Error ? err.message : "Unable to load chat session." }]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (searchParams.get("new")) {
      newChat();
      return;
    }
    const sessionId = searchParams.get("session");
    if (sessionId && sessionId !== activeSession) loadSession({ id: sessionId });
  }, [searchParams]);

  const sendMessage = async () => {
    const question = input.trim();
    if (!question) return;
    setInput("");
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: "user", content: question }]);
    setLoading(true);
    try {
      const response: any = await api.generate({
        query: question,
        top_k: topK,
        score_threshold: threshold,
        route_mode: sourceMode,
        session_id: activeSession || undefined,
        document_ids: workspace.attachedDocumentIds,
        web_search_enabled: webSearchEnabled
      });
      if (response.session_id) setActiveSession(response.session_id);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.answer || response.response || "I found relevant source material and prepared a grounded answer.",
          sources: (response.sources || response.citations || []).slice(0, 4).map((source: any) => ({
            title: source.filename || source.title || source.source || "Retrieved source",
            score: source.score || source.relevance || 0.82,
            page: source.page || source.location || source.metadata?.page || "source"
          }))
        }
      ]);
    } catch {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content:
            "I could not reach the generation endpoint, but the workspace is ready. Try again once the API connection is healthy.",
          sources: [{ title: "API connection", score: 0, page: "status" }]
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative">
      <Card className="chat-stage relative flex min-h-[calc(100vh-104px)] min-w-0 max-w-full flex-col overflow-hidden p-0">
        <div className="border-b border-white/10 p-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <SectionTitle icon={Bot} title="Ask MindMesh" subtitle="Grounded answers from your documents and optional web search" />
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="success">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Provenance on
              </Badge>
              <Button variant="secondary" onClick={() => setSettingsOpen((current) => !current)}>
                <SlidersHorizontal className="h-4 w-4" />
                Retrieval
              </Button>
            </div>
          </div>
        </div>
        {settingsOpen ? (
          <div className="chat-settings-panel absolute right-4 top-[86px] z-20 w-[min(320px,calc(100%-32px))] rounded-2xl border border-white/10 p-4 shadow-2xl">
            <div className="flex items-start justify-between gap-3">
              <SectionTitle icon={SlidersHorizontal} title="Retrieval settings" subtitle="Tune source selection for this chat" />
              <button aria-label="Close retrieval settings" className="focus-ring rounded-lg p-1.5 text-slate-500 hover:bg-white/8 hover:text-white" onClick={() => setSettingsOpen(false)}>
                <X className="h-4 w-4" />
              </button>
            </div>
            <RetrievalControls
              topK={topK}
              threshold={threshold}
              sourceMode={sourceMode}
              onTopK={setTopK}
              onThreshold={setThreshold}
              onSourceMode={setSourceMode}
            />
          </div>
        ) : null}
        <div className="flex-1 space-y-5 overflow-y-auto px-4 py-6 sm:px-6">
          {messages.length === 0 ? (
            <div className="grid min-h-[420px] place-items-center py-10">
              <div className="max-w-xl text-center">
                <div className="accent-icon mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-cyan-300/10 text-cyan-200">
                  <Sparkles className="h-6 w-6" />
                </div>
                <h1 className="mt-5 text-xl font-semibold tracking-[-0.03em] text-white sm:text-2xl">What would you like to explore?</h1>
                <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-slate-400">
                  Ask a question across your indexed knowledge. Attach specific documents from the left rail when you want a narrower answer.
                </p>
              </div>
            </div>
          ) : (
            messages.map((message) => <ChatBubble key={message.id} message={message} />)
          )}
          {loading ? (
            <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.035] px-4 py-3 text-sm text-slate-400">
              <Loader2 className="h-4 w-4 animate-spin text-sky-300" />
              Retrieving chunks and composing answer
            </div>
          ) : null}
        </div>
        <div className="composer-footer border-t border-white/10 p-4">
          {workspace.attachedDocumentIds.length ? (
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-slate-500">Attached sources</span>
              {workspace.attachedDocumentIds.slice(0, 3).map((documentId) => (
                <button
                  key={documentId}
                  className="tag-chip focus-ring inline-flex max-w-[220px] items-center gap-1.5 rounded-full border border-cyan-300/10 bg-cyan-300/10 px-2.5 py-1 text-[11px] font-semibold text-cyan-100"
                  onClick={() => workspace.toggleDocument(documentId)}
                  title="Detach document"
                >
                  <FileText className="h-3 w-3" />
                  <span className="truncate">{documentId.split("/").pop()}</span>
                  <X className="h-3 w-3" />
                </button>
              ))}
              {workspace.attachedDocumentIds.length > 3 ? <span className="text-xs text-slate-500">+{workspace.attachedDocumentIds.length - 3} more</span> : null}
            </div>
          ) : null}
          {messages.length === 0 ? <div className="mb-3 flex flex-wrap gap-2">
            {["Summarize the latest roadmap risks", "Which documents mention API limits?", "Show sources for onboarding claims"].map(
              (suggestion) => (
                <button
                  key={suggestion}
                  className="focus-ring rounded-full border border-white/10 bg-white/[0.035] px-3 py-1.5 text-xs text-slate-300 transition hover:bg-white/8 hover:text-white"
                  onClick={() => setInput(suggestion)}
                >
                  {suggestion}
                </button>
              )
            )}
          </div> : null}
          <ChatComposer
            value={input}
            onChange={setInput}
            onSubmit={sendMessage}
            loading={loading}
            webSearchEnabled={webSearchEnabled}
            onToggleWebSearch={() => setWebSearchEnabled((current) => !current)}
          />
        </div>
      </Card>
    </div>
  );
}

function SessionList({
  sessions,
  activeSession,
  onLoad
}: {
  sessions: any[];
  activeSession: string;
  onLoad: (session: any) => void;
}) {
  if (!sessions.length) return <EmptyState icon={MessageSquare} title="No chat sessions" description="Saved sessions appear here after a chat is created." />;
  return (
    <div className="grid gap-2 sm:grid-cols-2 2xl:grid-cols-1">
      {sessions.map((session, index) => {
        const sessionId = String(session.id || session.session_id || "");
        return (
          <button
            key={sessionId || index}
            className={cn(
              "focus-ring w-full rounded-xl border px-3 py-3 text-left text-sm transition",
              activeSession === sessionId
                ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-50"
                : "border-transparent text-slate-400 hover:border-white/8 hover:bg-white/[0.045] hover:text-white"
            )}
            onClick={() => onLoad(session)}
          >
            <span className="block truncate font-medium">{session.title || session.name || session.query || "Untitled session"}</span>
            <span className="mt-1 block text-xs text-slate-500">{session.message_count || session.interactions || 0} messages</span>
          </button>
        );
      })}
    </div>
  );
}

function RetrievalControls({
  topK,
  threshold,
  sourceMode,
  onTopK,
  onThreshold,
  onSourceMode
}: {
  topK: number;
  threshold: number;
  sourceMode: string;
  onTopK: (value: number) => void;
  onThreshold: (value: number) => void;
  onSourceMode: (value: string) => void;
}) {
  return (
    <div className="mt-6 space-y-6">
      <RangeControl label="Top K" value={topK} min={2} max={12} step={1} onChange={onTopK} />
      <RangeControl label="Score threshold" value={threshold} min={0.1} max={0.95} step={0.01} onChange={onThreshold} />
      <Select label="Source mode" value={sourceMode} onChange={(event) => onSourceMode(event.target.value)}>
        <option value="balanced">Balanced</option>
        <option value="strict">Strict citations</option>
        <option value="broad">Broad recall</option>
      </Select>
      <div className="rounded-xl border border-cyan-300/15 bg-cyan-300/[0.055] p-4">
        <p className="text-sm font-medium text-cyan-50">Answer provenance</p>
        <p className="mt-2 text-sm leading-6 text-slate-400">
          Responses expose retrieved chunks, source confidence, and document origin for inspection.
        </p>
      </div>
    </div>
  );
}

function ProfilePage() {
  const workspace = useWorkspace();
  const [name, setName] = useState(workspace.profile.name);
  const [avatar, setAvatar] = useState(workspace.profile.avatar_url);
  const [bio, setBio] = useState(workspace.profile.bio);
  const [nicknames, setNicknames] = useState(workspace.profile.nicknames.join(", "));
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setName(workspace.profile.name);
    setAvatar(workspace.profile.avatar_url);
    setBio(workspace.profile.bio);
    setNicknames(workspace.profile.nicknames.join(", "));
  }, [workspace.profile]);

  const saveProfile = async () => {
    setSaving(true);
    setNotice("");
    try {
      const response: any = await api.updateUserProfile({
        name,
        avatar,
        bio,
        nicknames: nicknames.split(",").map((nickname) => nickname.trim()).filter(Boolean),
        highlight_color: workspace.profile.highlight_color
      });
      workspace.setProfile(normalizeProfile(response.profile || response));
      setNotice("Profile saved.");
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Unable to save profile.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Workspace identity"
        title="Profile"
        description="Keep the local workspace recognizable and add lightweight context for personalized responses."
        actions={
          <Button onClick={saveProfile} disabled={saving}>
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
            Save profile
          </Button>
        }
      />
      {notice ? <InlineNotice tone={notice.includes("Unable") || notice.includes("cannot") ? "warn" : "success"} message={notice} /> : null}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <Card>
          <SectionTitle icon={UserRound} title="Profile details" subtitle="Used throughout this local workspace" />
          <div className="mt-6 grid gap-4">
            <Input label="Display name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Local user" />
            <Input label="Avatar URL" value={avatar} onChange={(event) => setAvatar(event.target.value)} placeholder="https://..." />
            <Textarea
              label="Bio"
              className="font-sans"
              rows={4}
              value={bio}
              onChange={(event) => setBio(event.target.value)}
              placeholder="A short description of your role, preferences, or working style."
            />
            <Input
              label="Nicknames"
              value={nicknames}
              onChange={(event) => setNicknames(event.target.value)}
              placeholder="Comma-separated names"
            />
            <p className="text-xs leading-5 text-slate-500">Bio and nicknames are stored with your local profile so future personalized prompt flows can use them.</p>
          </div>
        </Card>
        <Card>
          <SectionTitle icon={Sparkles} title="Preview" subtitle="How you appear in the workspace" />
          <div className="mt-7 flex flex-col items-center rounded-2xl border border-white/10 bg-white/[0.025] px-5 py-7 text-center">
            <ProfileAvatar profile={{ ...workspace.profile, name, avatar_url: avatar }} className="h-16 w-16 text-lg" />
            <h2 className="mt-4 text-lg font-semibold text-white">{name || "Local user"}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">{bio || "Add a short bio to make this workspace feel like yours."}</p>
          </div>
        </Card>
      </div>
    </div>
  );
}

function PersonalizationPage() {
  const workspace = useWorkspace();
  const [highlight, setHighlight] = useState<UserProfile["highlight_color"]>(workspace.profile.highlight_color);
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const options: Array<{ id: UserProfile["highlight_color"]; label: string; description: string; swatch: string }> = [
    { id: "mist", label: "Mist", description: "A quiet blue-gray for focused work.", swatch: "#83adbd" },
    { id: "sage", label: "Sage", description: "A measured green with a softer presence.", swatch: "#7eac99" },
    { id: "lavender", label: "Lavender", description: "A restrained violet with gentle warmth.", swatch: "#a79cc0" }
  ];

  useEffect(() => setHighlight(workspace.profile.highlight_color), [workspace.profile.highlight_color]);

  const saveHighlight = async () => {
    setSaving(true);
    setNotice("");
    try {
      const response: any = await api.updateUserProfile({
        name: workspace.profile.name,
        avatar: workspace.profile.avatar_url,
        bio: workspace.profile.bio,
        nicknames: workspace.profile.nicknames,
        highlight_color: highlight
      });
      workspace.setProfile(normalizeProfile(response.profile || response));
      setNotice("Interface highlight saved.");
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Unable to save interface highlight.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Personalization"
        title="Interface highlight"
        description="Choose a calm accent that helps primary controls stand out without making the workspace louder."
        actions={
          <Button onClick={saveHighlight} disabled={saving}>
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
            Save preference
          </Button>
        }
      />
      {notice ? <InlineNotice tone={notice.includes("Unable") ? "warn" : "success"} message={notice} /> : null}
      <Card>
        <SectionTitle icon={Palette} title="Highlight color" subtitle="Applied consistently in light and dark mode" />
        <div className="mt-6 grid gap-3 lg:grid-cols-3">
          {options.map((option) => {
            const active = option.id === highlight;
            return (
              <button
                key={option.id}
                className={cn(
                  "focus-ring rounded-2xl border p-4 text-left transition",
                  active ? "accent-choice-active border-cyan-300/40 bg-cyan-300/[0.09]" : "border-white/10 bg-white/[0.025] hover:border-white/20 hover:bg-white/[0.05]"
                )}
                onClick={() => setHighlight(option.id)}
              >
                <span className="flex items-center justify-between gap-3">
                  <span className="grid h-10 w-10 place-items-center rounded-xl border border-white/10" style={{ background: option.swatch }}>
                    {active ? <Check className="h-4 w-4 text-slate-950" /> : null}
                  </span>
                  {active ? <Badge tone="success">Selected</Badge> : null}
                </span>
                <span className="mt-5 block font-semibold text-white">{option.label}</span>
                <span className="mt-2 block text-sm leading-6 text-slate-400">{option.description}</span>
              </button>
            );
          })}
        </div>
      </Card>
    </div>
  );
}

function AdminPage() {
  const [provider, setProvider] = useState("openai");
  const [model, setModel] = useState("gpt-4.1-mini");
  const [apiKey, setApiKey] = useState("");
  const [temperature, setTemperature] = useState(0.2);
  const [maxTokens, setMaxTokens] = useState(1600);
  const [models, setModels] = useState<string[]>([]);
  const [notice, setNotice] = useState("");
  const adminState = useAsyncData<any>(() => api.aiAdmin(), { keys: [], settings: {} });

  useEffect(() => {
    const settings = adminState.data.settings || adminState.data;
    if (settings.provider) setProvider(settings.provider);
    if (settings.model) setModel(settings.model);
    if (settings.temperature !== undefined) setTemperature(Number(settings.temperature));
    if (settings.max_tokens || settings.maxTokens) setMaxTokens(Number(settings.max_tokens || settings.maxTokens));
  }, [adminState.data]);

  useEffect(() => {
    api
      .aiModels(provider)
      .then((response: any) => {
        const nextModels = response.models || [];
        setModels(nextModels);
        if (nextModels.length && !nextModels.includes(model)) setModel(nextModels[0]);
      })
      .catch(() => setModels([]));
  }, [provider]);

  const saveSettings = async () => {
    setNotice("");
    try {
      if (apiKey.trim()) {
        await api.addAiKey({ provider, api_key: apiKey.trim(), label: `${provider} production` });
      }
      await api.saveAiSettings({ provider, model, temperature, max_tokens: maxTokens });
      setApiKey("");
      setNotice("Settings saved.");
      adminState.reload();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Unable to save settings.");
    }
  };

  const deleteKey = async (keyId: string) => {
    setNotice("");
    try {
      await api.deleteAiKey(keyId);
      setNotice("API key removed.");
      adminState.reload();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Unable to remove API key.");
    }
  };

  const providers = adminState.data.providers?.length ? adminState.data.providers : ["openai", "anthropic", "google", "ollama"];
  const keys = adminState.data.keys || adminState.data.provider_keys || [];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Model operations"
        title="Admin settings"
        description="Configure providers, API keys, active models, and generation defaults for MindMesh."
        actions={
          <Button onClick={saveSettings}>
            <CheckCircle2 className="h-4 w-4" />
            Save settings
          </Button>
        }
      />
      {notice ? <InlineNotice tone={notice.includes("Unable") ? "warn" : "success"} message={notice} /> : null}
      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Card>
          <SettingsSection icon={Brain} title="LLM configuration" description="Choose the model that powers chat and indexing assistants.">
            <div className="grid gap-4 md:grid-cols-2">
              <Select label="LLM provider" value={provider} onChange={(event) => setProvider(event.target.value)}>
                {providers.map((item: string) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </Select>
              <Select label="Active model" value={model} onChange={(event) => setModel(event.target.value)}>
                {(models.length ? models : [model]).map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </Select>
            </div>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <RangeControl label="Temperature" value={temperature} min={0} max={1} step={0.05} onChange={setTemperature} />
              <RangeControl label="Max tokens" value={maxTokens} min={256} max={8192} step={128} onChange={setMaxTokens} />
            </div>
          </SettingsSection>
          <SettingsSection icon={KeyRound} title="API key configuration" description="Keys are stored by the backend and masked in the interface.">
            <Input
              label="New API key"
              type="password"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder="sk-..."
            />
          </SettingsSection>
        </Card>
        <Card>
          <SectionTitle icon={ShieldCheck} title="API keys" subtitle="Configured provider credentials" />
          <div className="mt-5 space-y-3">
            {keys.length ? keys.map((key: any) => (
              <div key={key.id || key.label} className="rounded-2xl border border-white/10 bg-white/[0.035] p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-white">{key.label || `${key.provider} key`}</p>
                    <p className="mt-1 text-sm text-slate-500">{key.provider} | {formatTimestamp(key.created_at || key.createdAt)}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone={key.is_active || key.active ? "success" : "neutral"}>{key.is_active || key.active ? "Active" : "Stored"}</Badge>
                    {key.id ? (
                      <button aria-label={`Remove ${key.label || `${key.provider} key`}`} className="focus-ring rounded-xl p-2 text-slate-500 hover:bg-rose-400/10 hover:text-rose-200" onClick={() => deleteKey(String(key.id))}>
                        <Trash2 className="h-4 w-4" />
                      </button>
                    ) : null}
                  </div>
                </div>
              </div>
            )) : <EmptyState icon={KeyRound} title="No API keys" description="Add a provider key to enable live model generation." />}
          </div>
        </Card>
      </div>
    </div>
  );
}

function PromptLibraryPage() {
  const [searchParams] = useSearchParams();
  const promptsState = useAsyncData<PromptItem[]>(
    async () => {
      const response: any = await api.prompts();
      const prompts = Array.isArray(response) ? response : response.prompts || [];
      return prompts.map(toPromptItem);
    },
    []
  );
  const query = searchParams.get("q") || "";
  const prompts = promptsState.data.filter((prompt) => matchesSearch([prompt.name, prompt.description, prompt.status, prompt.version], query));
  const [activeName, setActiveName] = useState("");
  const active = prompts.find((prompt) => prompt.name === activeName) || prompts[0];
  const [body, setBody] = useState("");
  const [note, setNote] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (active) {
      setActiveName(active.name);
      setBody(active.body);
    } else {
      setBody("");
    }
  }, [active?.name]);

  const savePrompt = async () => {
    if (!active) return;
    setNotice("");
    try {
      await api.savePrompt(active.name, { content: body, change_note: note });
      setNotice("Prompt saved.");
      promptsState.reload();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Unable to save prompt.");
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Developer workspace"
        title="Prompt library"
        description="Edit, version, and review system prompts used by retrieval, chat, and indexing flows."
        actions={
          <Button onClick={savePrompt} disabled={!active || !body.trim()}>
            <CheckCircle2 className="h-4 w-4" />
            Save prompt
          </Button>
        }
      />
      {notice ? <InlineNotice tone={notice.includes("Unable") ? "warn" : "success"} message={notice} /> : null}
      <div className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <Card>
          <SectionTitle icon={Library} title="Prompts" subtitle={`${prompts.length} templates`} />
          <div className="mt-5 space-y-3">
            {prompts.length ? prompts.map((prompt) => (
              <PromptCard key={prompt.name} prompt={prompt} active={prompt.name === active.name} onClick={() => setActiveName(prompt.name)} />
            )) : <EmptyState icon={TerminalSquare} title="No prompts found" description={query ? "No prompts match the current search." : "Prompt records will appear after the backend seeds them."} />}
          </div>
        </Card>
        {active ? <Card>
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-xl font-semibold text-white">{active.name}</h2>
                <Badge tone="success">{active.status}</Badge>
                <Badge>{active.version}</Badge>
              </div>
              <p className="mt-2 text-sm text-slate-400">{active.description}</p>
            </div>
            <Badge>
              <Clock3 className="h-3.5 w-3.5" />
              {formatTimestamp(active.updatedAt)}
            </Badge>
          </div>
          <div className="mt-6 grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
            <Textarea label="Prompt editor" value={body} onChange={(event) => setBody(event.target.value)} rows={18} />
            <div className="space-y-4">
              <Textarea label="Change note" value={note} onChange={(event) => setNote(event.target.value)} rows={5} />
              <Card className="inset-panel p-4">
                <SectionTitle icon={History} title="Version history" />
                <div className="mt-4 space-y-3">
                  <div className="rounded-xl border border-white/10 bg-white/[0.025] px-3 py-2 text-sm text-slate-300">
                    {active.version} current
                  </div>
                  {note ? (
                    <div className="rounded-xl border border-sky-300/20 bg-sky-300/10 px-3 py-2 text-sm text-sky-100">
                      Pending note: {note}
                    </div>
                  ) : null}
                </div>
              </Card>
            </div>
          </div>
        </Card> : <Card><EmptyState icon={TerminalSquare} title="Select a prompt" description="Choose a prompt from the list to edit its content." /></Card>}
      </div>
    </div>
  );
}

function ApiConnectionPage() {
  const [testing, setTesting] = useState(false);
  const [checks, setChecks] = useState([
    { name: "Backend API", status: "warn", detail: "Not tested yet" },
    { name: "Postgres", status: "warn", detail: "Not tested yet" },
    { name: "Qdrant", status: "warn", detail: "Not tested yet" },
    { name: "Object storage", status: "warn", detail: "Not tested yet" }
  ]);
  const [events, setEvents] = useState<string[]>([]);

  const testConnection = async () => {
    setTesting(true);
    const nextEvents: string[] = [];
    const test = async (name: string, run: () => Promise<any>, okDetail: string) => {
      try {
        await run();
        nextEvents.push(`${name} check passed`);
        return { name, status: "online", detail: okDetail };
      } catch (err) {
        nextEvents.push(`${name} check failed`);
        return { name, status: "offline", detail: err instanceof Error ? err.message : "Unavailable" };
      }
    };
    const nextChecks = await Promise.all([
      test("Backend API", () => api.health(), "/api/v1/health returned healthy"),
      test("Postgres", () => api.user(), "User table responded"),
      test("Qdrant", () => api.dashboard(), "Dashboard analytics responded"),
      test("Object storage", () => api.documents(), "Document registry responded")
    ]);
    setChecks(nextChecks);
    setEvents(nextEvents);
    setTesting(false);
  };

  useEffect(() => {
    testConnection();
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Infrastructure"
        title="API connection"
        description="Monitor the local services that keep MindMesh document intelligence responsive."
        actions={
          <Button variant="secondary" onClick={testConnection} disabled={testing}>
            <RefreshCw className={cn("h-4 w-4", testing && "animate-spin")} />
            Test connection
          </Button>
        }
      />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {checks.map((service) => (
          <Card key={service.name}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-medium text-white">{service.name}</p>
                <p className="mt-2 text-sm text-slate-500">{service.detail}</p>
              </div>
              <StatusIndicator status={service.status as "online" | "offline" | "warn"} />
            </div>
          </Card>
        ))}
      </div>
      <Card>
        <SectionTitle icon={Activity} title="Connection timeline" subtitle="Recent service checks and startup events" />
        <div className="mt-5 space-y-3">
          {(events.length ? events : ["Run a connection test to populate live service events."]).map(
            (event, index) => (
              <div key={event} className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.025] p-3">
                <div className={cn("grid h-8 w-8 place-items-center rounded-xl", event.includes("failed") ? "bg-rose-400/10 text-rose-200" : "bg-emerald-400/10 text-emerald-300")}>
                  {event.includes("failed") ? <AlertCircle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
                </div>
                <div>
                  <p className="text-sm font-medium text-white">{event}</p>
                  <p className="text-xs text-slate-500">{index + 1} minute{index ? "s" : ""} ago</p>
                </div>
              </div>
            )
          )}
        </div>
      </Card>
    </div>
  );
}

function BrandMark() {
  return (
    <div className="brand-mark grid h-10 w-10 shrink-0 place-items-center rounded-xl text-slate-950">
      <Brain className="h-5 w-5" strokeWidth={2.4} />
    </div>
  );
}

function PageHeader({
  eyebrow,
  title,
  description,
  actions
}: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div className="max-w-3xl">
        <p className="text-xs font-semibold uppercase tracking-[0.15em] text-cyan-300">{eyebrow}</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.035em] text-white sm:text-[34px]">{title}</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400 sm:text-base">{description}</p>
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={cn("premium-card rounded-[20px] p-5 sm:p-6", className)}>{children}</section>;
}

function Button({
  children,
  variant = "primary",
  size = "default",
  className = "",
  ariaLabel,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger";
  size?: "default" | "icon";
  ariaLabel?: string;
}) {
  return (
    <button
      aria-label={ariaLabel}
      className={cn(
        "focus-ring inline-flex items-center justify-center gap-2 rounded-xl text-sm font-semibold transition active:scale-[0.99] disabled:opacity-50",
        size === "icon" ? "h-10 w-10" : "h-10 px-4",
        variant === "primary" && "button-primary bg-cyan-300 text-slate-950 hover:bg-cyan-200",
        variant === "secondary" && "button-secondary border border-white/10 bg-white/[0.035] text-slate-200 hover:border-white/20 hover:bg-white/[0.075] hover:text-white",
        variant === "danger" && "button-danger border border-rose-300/20 bg-rose-400/10 text-rose-200 hover:bg-rose-400/15",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

function Input({ label, className = "", ...props }: React.InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-300">{label}</span>
      <input
        className={cn(
          "field-control focus-ring h-11 w-full rounded-xl border border-white/10 bg-black/20 px-3 text-sm text-white placeholder:text-slate-500 transition hover:border-white/20",
          className
        )}
        {...props}
      />
    </label>
  );
}

function Select({ label, children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement> & { label: string }) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-300">{label}</span>
      <select
        className="field-control focus-ring h-11 w-full rounded-xl border border-white/10 bg-black/20 px-3 text-sm text-white transition hover:border-white/20"
        {...props}
      >
        {children}
      </select>
    </label>
  );
}

function Textarea({ label, className = "", ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string }) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-300">{label}</span>
      <textarea
        className={cn("field-control focus-ring w-full resize-y rounded-xl border border-white/10 bg-black/20 p-3 font-mono text-sm leading-6 text-white placeholder:text-slate-500 transition hover:border-white/20", className)}
        {...props}
      />
    </label>
  );
}

function MetricCard({ label, value, trend, icon: Icon }: { label: string; value: React.ReactNode; trend: string; icon: any }) {
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm text-slate-500">{label}</p>
          <p className="mt-2 text-2xl font-semibold tracking-tight text-white">{value}</p>
        </div>
        <div className="accent-icon grid h-10 w-10 place-items-center rounded-xl bg-cyan-300/10 text-cyan-200">
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <p className="mt-4 text-xs font-medium uppercase tracking-[0.1em] text-slate-500">{trend}</p>
    </Card>
  );
}

function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "success" | "warn" }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold",
        tone === "neutral" && "border-white/10 bg-white/[0.04] text-slate-300",
        tone === "success" && "border-emerald-300/20 bg-emerald-400/10 text-emerald-300",
        tone === "warn" && "border-amber-300/20 bg-amber-400/10 text-amber-200"
      )}
    >
      {children}
    </span>
  );
}

function TagChip({ children }: { children: React.ReactNode }) {
  return <span className="tag-chip rounded-full border border-cyan-300/10 bg-cyan-300/10 px-2.5 py-1 text-[11px] font-semibold text-cyan-100">{children}</span>;
}

function Tabs({
  items,
  value,
  onChange,
  className = ""
}: {
  items: { value: string; label: string }[];
  value: string;
  onChange: (value: string) => void;
  className?: string;
}) {
  return (
    <div className={cn("tabs-shell flex flex-wrap gap-1 rounded-xl border border-white/10 bg-black/20 p-1", className)}>
      {items.map((item) => (
        <button
          key={item.value}
          className={cn(
            "focus-ring rounded-lg px-3 py-2 text-sm font-medium transition",
            value === item.value ? "tab-active bg-cyan-300 text-slate-950" : "text-slate-400 hover:bg-white/6 hover:text-white"
          )}
          onClick={() => onChange(item.value)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

function StatusIndicator({ status }: { status: "online" | "offline" | "warn" }) {
  return (
    <span
      className={cn(
        "inline-flex h-2.5 w-2.5 rounded-full",
        status === "online" && "status-online bg-emerald-300",
        status === "warn" && "bg-amber-300",
        status === "offline" && "bg-rose-300"
      )}
    />
  );
}

function StatusBadge({ status }: { status: Status }) {
  const label = status === "not_indexed" ? "Not indexed" : status[0].toUpperCase() + status.slice(1);
  return <Badge tone={status === "indexed" ? "success" : status === "failed" ? "warn" : "neutral"}>{label}</Badge>;
}

function SectionTitle({ icon: Icon, title, subtitle }: { icon: any; title: string; subtitle?: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="accent-icon mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-cyan-300/10 text-cyan-200">
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0">
        <h2 className="text-sm font-semibold text-white sm:text-base">{title}</h2>
        {subtitle ? <p className="mt-1 text-sm text-slate-500">{subtitle}</p> : null}
      </div>
    </div>
  );
}

function EmptyState({ icon: Icon, title, description }: { icon: any; title: string; description: string }) {
  return (
    <div className="empty-state rounded-2xl border border-dashed border-white/12 bg-white/[0.02] p-7 text-center">
      <div className="accent-icon mx-auto grid h-12 w-12 place-items-center rounded-xl bg-cyan-300/10 text-cyan-200">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="mt-4 font-semibold text-white">{title}</h3>
      <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-slate-400">{description}</p>
    </div>
  );
}

function InlineNotice({ tone, message }: { tone: "success" | "warn"; message: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "rounded-xl border px-4 py-3 text-sm",
        tone === "success" ? "notice-success border-emerald-300/20 bg-emerald-400/10 text-emerald-200" : "notice-warn border-amber-300/20 bg-amber-400/10 text-amber-100"
      )}
    >
      {message}
    </div>
  );
}

function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  onCancel,
  onConfirm
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[70] grid place-items-center bg-black/70 px-4 backdrop-blur-sm" role="presentation" onMouseDown={onCancel}>
      <div
        aria-describedby="confirm-dialog-description"
        aria-labelledby="confirm-dialog-title"
        aria-modal="true"
        className="premium-card w-full max-w-md rounded-[20px] p-6 shadow-2xl"
        role="dialog"
        tabIndex={-1}
        onKeyDown={(event) => event.key === "Escape" && onCancel()}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="grid h-11 w-11 place-items-center rounded-xl bg-rose-400/10 text-rose-200">
          <AlertCircle className="h-5 w-5" />
        </div>
        <h2 className="mt-5 text-xl font-semibold text-white" id="confirm-dialog-title">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-slate-400" id="confirm-dialog-description">{description}</p>
        <div className="mt-6 flex justify-end gap-2">
          <Button autoFocus variant="secondary" onClick={onCancel}>Cancel</Button>
          <Button variant="danger" onClick={onConfirm}>{confirmLabel}</Button>
        </div>
      </div>
    </div>
  );
}

function UploadDropzone({
  files,
  inputRef,
  uploading,
  onFiles,
  onUpload,
  onClear
}: {
  files: File[];
  inputRef: React.RefObject<HTMLInputElement>;
  uploading: boolean;
  onFiles: (files: File[]) => void;
  onUpload: () => void;
  onClear: () => void;
}) {
  return (
    <Card>
      <div
        className="dropzone rounded-2xl border border-dashed border-white/16 bg-white/[0.025] p-7 text-center transition hover:border-cyan-300/50 hover:bg-cyan-300/[0.035]"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          onFiles(Array.from(event.dataTransfer.files));
        }}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(event) => onFiles(Array.from(event.target.files || []))}
        />
        <div className="dropzone-icon mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-cyan-300 text-slate-950">
          <UploadCloud className="h-6 w-6" />
        </div>
        <h2 className="mt-5 text-lg font-semibold text-white">Drop documents to upload</h2>
        <p className="mt-2 text-sm text-slate-500">PDF, DOCX, TXT, CSV, and markdown files are supported.</p>
        <Button className="mt-5" variant="secondary" onClick={() => inputRef.current?.click()}>
          Browse files
        </Button>
      </div>
      <div className="mt-5 space-y-3">
        {files.length ? (
          files.map((file) => (
            <div key={`${file.name}-${file.size}`} className="rounded-xl border border-white/10 bg-white/[0.035] p-3">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-white">{file.name}</p>
                  <p className="text-xs text-slate-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
                <Badge>Queued</Badge>
              </div>
              <p className="mt-2 text-xs text-slate-500">Ready to upload</p>
            </div>
          ))
        ) : (
          <p className="text-sm text-slate-500">Upload queue is empty.</p>
        )}
      </div>
      <div className="mt-5 flex gap-2">
        <Button onClick={onUpload} disabled={!files.length || uploading}>
          {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
          Start upload
        </Button>
        <Button variant="secondary" onClick={onClear} disabled={!files.length}>
          Clear
        </Button>
      </div>
    </Card>
  );
}

function ChatComposer({
  value,
  onChange,
  onSubmit,
  loading,
  webSearchEnabled,
  onToggleWebSearch
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  loading: boolean;
  webSearchEnabled: boolean;
  onToggleWebSearch: () => void;
}) {
  return (
    <div className="chat-composer min-w-0 rounded-2xl border border-white/10 bg-black/25 p-2">
      <div className="flex items-end gap-2">
        <textarea
          aria-label="Ask MindMesh"
          className="focus-ring max-h-36 min-h-12 min-w-0 flex-1 resize-none rounded-xl bg-transparent px-3 py-3 text-sm leading-6 text-white placeholder:text-slate-500"
          placeholder="Ask across your indexed knowledge..."
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              onSubmit();
            }
          }}
        />
        <Button size="icon" ariaLabel="Send message" onClick={onSubmit} disabled={loading || !value.trim()}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </Button>
      </div>
      <div className="mt-1 flex min-w-0 items-center justify-between gap-2 border-t border-white/8 px-2 pt-2">
        <button
          aria-pressed={webSearchEnabled}
          className={cn(
            "focus-ring inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-semibold transition",
            webSearchEnabled ? "bg-cyan-300/10 text-cyan-100" : "text-slate-500 hover:bg-white/5 hover:text-white"
          )}
          onClick={onToggleWebSearch}
        >
          <Globe2 className="h-3.5 w-3.5" />
          Web search {webSearchEnabled ? "on" : "off"}
        </button>
        <p className="hidden text-right text-[11px] text-slate-500 sm:block">Enter to send | Shift + Enter for a new line</p>
      </div>
    </div>
  );
}

function ChatBubble({ message }: { message: Message }) {
  const assistant = message.role === "assistant";
  return (
    <div className={cn("flex", assistant ? "justify-start" : "justify-end")}>
      <div className={cn("max-w-3xl rounded-2xl p-4", assistant ? "assistant-bubble border border-white/10 bg-white/[0.04]" : "user-bubble bg-cyan-300 text-slate-950")}>
        <p className="whitespace-pre-wrap text-sm leading-6">{message.content}</p>
        {assistant && message.sources?.length ? (
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {message.sources.map((source) => (
              <div key={`${source.title}-${source.page}`} className="source-card rounded-xl border border-white/10 bg-black/20 p-3">
                <div className="flex items-start justify-between gap-2">
                  <p className="line-clamp-2 text-sm font-medium text-white">{source.title}</p>
                  <Badge>{source.score ? source.score.toFixed(2) : "N/A"}</Badge>
                </div>
                <p className="mt-2 text-xs text-slate-500">{source.page}</p>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function PromptCard({ prompt, active, onClick }: { prompt: PromptItem; active: boolean; onClick: () => void }) {
  return (
    <button
      aria-pressed={active}
      className={cn(
        "focus-ring w-full rounded-xl border p-4 text-left transition",
        active ? "prompt-card-active border-cyan-300/50 bg-cyan-300/10" : "prompt-card-idle border-white/10 bg-white/[0.025] hover:bg-white/[0.05]"
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-medium text-white">{prompt.name}</p>
          <p className="mt-1 line-clamp-2 text-sm text-slate-500">{prompt.description}</p>
        </div>
        <Badge tone={prompt.status === "active" ? "success" : "neutral"}>{prompt.version}</Badge>
      </div>
    </button>
  );
}

function SettingsSection({
  icon,
  title,
  description,
  children
}: {
  icon: any;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="border-b border-white/10 py-6 first:pt-0 last:border-b-0 last:pb-0">
      <SectionTitle icon={icon} title={title} subtitle={description} />
      <div className="mt-5">{children}</div>
    </div>
  );
}

function RangeControl({
  label,
  value,
  min,
  max,
  step,
  onChange
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="block">
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="text-sm font-medium text-slate-300">{label}</span>
        <span className="rounded-full bg-white/[0.055] px-2.5 py-1 text-xs text-slate-300">{value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="w-full accent-cyan-300"
      />
    </label>
  );
}

function DataTable({ columns, rows }: { columns: string[]; rows: React.ReactNode[][] }) {
  return (
    <div className="mt-5 overflow-x-auto rounded-2xl border border-white/10">
      <table className="w-full min-w-[680px] text-left text-sm">
        <thead className="bg-white/[0.035] text-xs uppercase tracking-wide text-slate-500">
          <tr>{columns.map((column) => <th key={column} className="px-4 py-3">{column}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-white/8">
          {rows.map((row, index) => (
            <tr key={index} className="transition hover:bg-white/[0.025]">
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} className="px-4 py-4 text-slate-300">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DocumentName({ doc }: { doc: DocumentItem }) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <div className="accent-icon grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-cyan-300/10 text-cyan-200">
        <FileText className="h-5 w-5" />
      </div>
      <div className="min-w-0">
        <p className="truncate font-medium text-white">{doc.filename}</p>
        <p className="text-xs text-slate-500">{doc.version}</p>
      </div>
    </div>
  );
}

function DocumentRowCompact({ doc }: { doc: DocumentItem }) {
  return (
    <div className="subtle-panel rounded-2xl border border-white/10 bg-white/[0.025] p-3">
      <div className="flex items-start justify-between gap-3">
        <DocumentName doc={doc} />
        <StatusBadge status={doc.status} />
      </div>
      {doc.error ? <p className="mt-3 text-sm text-amber-200">{doc.error}</p> : null}
    </div>
  );
}

function DistributionCard({ title, data }: { title: string; data: { name: string; value: number }[] }) {
  return (
    <Card>
      <SectionTitle icon={Tags} title={title} />
      <div className="mt-5 grid grid-cols-[130px_minmax(0,1fr)] items-center gap-3">
        <div className="h-32">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} dataKey="value" innerRadius={34} isAnimationActive={false} outerRadius={58} paddingAngle={4}>
                {data.map((entry, index) => (
                  <Cell key={entry.name} fill={palette[index % palette.length]} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="space-y-2">
          {data.map((item, index) => (
            <div key={item.name} className="flex items-center justify-between gap-2 text-sm">
              <span className="flex min-w-0 items-center gap-2 text-slate-400">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: palette[index % palette.length] }} />
                <span className="truncate">{item.name}</span>
              </span>
              <span className="font-medium text-white">{item.value}</span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="menu-surface rounded-xl border border-white/10 p-3 shadow-xl">
      <p className="mb-2 text-sm font-medium text-white">{label}</p>
      {payload.map((item: any) => (
        <p key={item.dataKey} className="text-xs text-slate-400">
          {item.dataKey}: <span className="text-white">{item.value}</span>
        </p>
      ))}
    </div>
  );
}

function countBy(items: string[]) {
  const counts = items.reduce<Record<string, number>>((acc, item) => {
    acc[item] = (acc[item] || 0) + 1;
    return acc;
  }, {});
  return Object.entries(counts).map(([name, value]) => ({ name, value }));
}

export default App;
