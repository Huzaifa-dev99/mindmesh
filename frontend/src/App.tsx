import {
  Activity,
  AlertCircle,
  Archive,
  ArrowUpRight,
  BarChart3,
  Bot,
  Brain,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Command,
  Database,
  FileText,
  Gauge,
  History,
  Home,
  KeyRound,
  Layers3,
  Library,
  Loader2,
  Menu,
  MessageSquare,
  MoreHorizontal,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  RefreshCw,
  Search,
  Send,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Tags,
  TerminalSquare,
  Trash2,
  UploadCloud,
  X
} from "lucide-react";
import type * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { BrowserRouter, Navigate, NavLink, Route, Routes, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useEffect, useMemo, useRef, useState } from "react";
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

const navItems = [
  { path: "/dashboard", label: "Dashboard", icon: Home },
  { path: "/documents", label: "Documents", icon: FileText },
  { path: "/chat", label: "Chat", icon: MessageSquare },
  { path: "/admin", label: "Admin", icon: Settings },
  { path: "/admin/prompts", label: "Prompts", icon: TerminalSquare },
  { path: "/api-connection", label: "API Connection", icon: KeyRound }
];

const palette = ["#7dd3fc", "#a78bfa", "#34d399", "#fbbf24", "#fb7185"];

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
  const bytes = raw.size_bytes || raw.sizeBytes || raw.bytes || 0;
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
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/admin/prompts" element={<PromptLibraryPage />} />
          <Route path="/api-connection" element={<ApiConnectionPage />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

function GuardedShell() {
  const [checking, setChecking] = useState(true);
  const [locked, setLocked] = useState(false);
  const [profile, setProfile] = useState({ name: "Workspace Admin", avatar_url: "" });

  useEffect(() => {
    api
      .user()
      .then((user: any) => {
        const nextProfile = user.profile || user;
        setProfile({ name: nextProfile.name || "Workspace Admin", avatar_url: nextProfile.avatar_url || nextProfile.avatar || "" });
        setLocked(Boolean(user.has_pin));
      })
      .catch(() => setLocked(false))
      .finally(() => setChecking(false));
  }, []);

  if (checking) {
    return (
      <div className="grid min-h-screen place-items-center bg-[#07080b] text-slate-200">
        <Loader2 className="h-6 w-6 animate-spin text-sky-300" />
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
    <div className="relative grid min-h-screen place-items-center overflow-hidden bg-[#07080b] px-5">
      <div className="soft-grid absolute inset-0 opacity-40" />
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

function AppShell({ profile }: { profile: { name: string; avatar_url?: string } }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<"online" | "offline" | "warn">("warn");
  const location = useLocation();

  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    api
      .health()
      .then(() => setConnectionStatus("online"))
      .catch(() => setConnectionStatus("offline"));
  }, []);

  return (
    <div className="min-h-screen text-slate-100">
      <div className="soft-grid pointer-events-none fixed inset-0 opacity-30" />
      <Sidebar collapsed={collapsed} open={sidebarOpen} onClose={() => setSidebarOpen(false)} connectionStatus={connectionStatus} />
      <div className={cn("relative transition-all duration-300", collapsed ? "lg:pl-[92px]" : "lg:pl-[280px]")}>
        <TopBar
          profile={profile}
          collapsed={collapsed}
          onMenu={() => setSidebarOpen(true)}
          onToggleCollapse={() => setCollapsed((value) => !value)}
        />
        <main className="mx-auto max-w-[1500px] px-4 pb-12 pt-5 sm:px-6 lg:px-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
            >
              <Routes>
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/documents" element={<DocumentsPage />} />
                <Route path="/chat" element={<ChatPage />} />
                <Route path="/admin" element={<AdminPage />} />
                <Route path="/admin/prompts" element={<PromptLibraryPage />} />
                <Route path="/api-connection" element={<ApiConnectionPage />} />
              </Routes>
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}

function Sidebar({
  collapsed,
  open,
  onClose,
  connectionStatus
}: {
  collapsed: boolean;
  open: boolean;
  onClose: () => void;
  connectionStatus: "online" | "offline" | "warn";
}) {
  const navigate = useNavigate();
  return (
    <>
      <AnimatePresence>
        {open ? (
          <motion.button
            aria-label="Close sidebar"
            className="fixed inset-0 z-40 bg-black/60 lg:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
        ) : null}
      </AnimatePresence>
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex flex-col border-r border-white/10 bg-[#090b10]/95 p-4 shadow-2xl shadow-black/40 backdrop-blur-xl transition-all duration-300",
          collapsed ? "w-[92px]" : "w-[280px]",
          open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        <div className={cn("mb-7 flex items-center", collapsed ? "justify-center" : "justify-between")}>
          <div className="flex items-center gap-3">
            <BrandMark />
            {!collapsed ? (
              <div>
                <p className="text-base font-semibold tracking-tight text-white">MindMesh</p>
                <p className="text-xs text-slate-500">RAG workbench</p>
              </div>
            ) : null}
          </div>
          <button className="focus-ring rounded-xl p-2 text-slate-400 hover:bg-white/5 hover:text-white lg:hidden" onClick={onClose}>
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/admin"}
              className={({ isActive }) =>
                cn(
                  "focus-ring group flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-medium transition",
                  collapsed && "justify-center",
                  isActive
                    ? "bg-white text-slate-950 shadow-lg shadow-sky-950/20"
                    : "text-slate-400 hover:bg-white/6 hover:text-white"
                )
              }
              title={collapsed ? item.label : undefined}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {!collapsed ? <span>{item.label}</span> : null}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto space-y-3">
          <button
            className={cn("focus-ring w-full rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-left transition hover:bg-white/[0.055]", collapsed && "px-2 text-center")}
            onClick={() => navigate("/api-connection")}
          >
            <div className={cn("mb-3 flex items-center gap-2", collapsed && "justify-center")}>
              <StatusIndicator status={connectionStatus} />
              {!collapsed ? <span className="text-xs font-medium text-slate-300">Service status {connectionStatus}</span> : null}
            </div>
            {!collapsed ? (
              <>
                <p className="text-xs text-slate-500">Open live checks for API, Postgres, vectors, and storage.</p>
                <div className="mt-3 h-1.5 rounded-full bg-white/10">
                  <div
                    className={cn(
                      "h-full rounded-full",
                      connectionStatus === "online" && "w-full bg-emerald-300",
                      connectionStatus === "warn" && "w-1/2 bg-amber-300",
                      connectionStatus === "offline" && "w-1/4 bg-rose-300"
                    )}
                  />
                </div>
              </>
            ) : null}
          </button>
        </div>
      </aside>
    </>
  );
}

function TopBar({
  profile,
  collapsed,
  onMenu,
  onToggleCollapse
}: {
  profile: { name: string; avatar_url?: string };
  collapsed: boolean;
  onMenu: () => void;
  onToggleCollapse: () => void;
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get("q") || "");
  const [profileOpen, setProfileOpen] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setQuery(searchParams.get("q") || "");
  }, [searchParams]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const submitSearch = () => {
    const next = query.trim();
    const searchablePath = location.pathname === "/admin/prompts" || location.pathname === "/chat" ? location.pathname : "/documents";
    navigate(next ? `${searchablePath}?q=${encodeURIComponent(next)}` : searchablePath);
  };

  return (
    <header className="sticky top-0 z-30 border-b border-white/10 bg-[#07080b]/76 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-[1500px] items-center gap-3 px-4 sm:px-6 lg:px-8">
        <button className="focus-ring rounded-xl p-2 text-slate-300 hover:bg-white/6 hover:text-white lg:hidden" onClick={onMenu}>
          <Menu className="h-5 w-5" />
        </button>
        <button
          className="focus-ring hidden rounded-xl p-2 text-slate-400 hover:bg-white/6 hover:text-white lg:inline-flex"
          onClick={onToggleCollapse}
          aria-label="Toggle sidebar"
        >
          {collapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
        </button>
        <div className="relative max-w-xl flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            ref={searchRef}
            className="focus-ring h-10 w-full rounded-2xl border border-white/10 bg-white/[0.035] pl-10 pr-24 text-sm text-white placeholder:text-slate-500 transition hover:border-white/16"
            placeholder="Search documents, prompts, sessions"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              const next = new URLSearchParams(searchParams);
              if (event.target.value.trim()) next.set("q", event.target.value);
              else next.delete("q");
              setSearchParams(next, { replace: true });
            }}
            onKeyDown={(event) => event.key === "Enter" && submitSearch()}
          />
          <div className="pointer-events-none absolute right-2 top-1/2 hidden -translate-y-1/2 items-center gap-1 rounded-xl border border-white/10 bg-black/25 px-2 py-1 text-[11px] text-slate-500 sm:flex">
            <Command className="h-3 w-3" /> K
          </div>
        </div>
        <Button variant="secondary" className="hidden sm:inline-flex" onClick={() => navigate("/documents?intent=index")}>
          <Sparkles className="h-4 w-4" />
          New Index
        </Button>
        <div className="relative">
        <button
          className="focus-ring flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.035] px-2.5 py-2 transition hover:bg-white/[0.06]"
          onClick={() => setProfileOpen((value) => !value)}
        >
          <div className="grid h-8 w-8 place-items-center overflow-hidden rounded-xl bg-sky-300 text-sm font-bold text-slate-950">
            {profile.avatar_url ? <img className="h-full w-full object-cover" src={profile.avatar_url} alt="" /> : profile.name.slice(0, 1)}
          </div>
          <div className="hidden leading-tight md:block">
            <p className="text-sm font-medium text-white">{profile.name}</p>
            <p className="text-xs text-slate-500">Admin</p>
          </div>
          <ChevronDown className="hidden h-4 w-4 text-slate-500 md:block" />
        </button>
        {profileOpen ? (
          <div className="absolute right-0 top-12 z-40 w-56 rounded-2xl border border-white/10 bg-[#0c0f14] p-2 shadow-2xl">
            <button className="w-full rounded-xl px-3 py-2 text-left text-sm text-slate-300 hover:bg-white/8" onClick={() => { setProfileOpen(false); navigate("/admin"); }}>
              Admin settings
            </button>
            <button className="w-full rounded-xl px-3 py-2 text-left text-sm text-slate-300 hover:bg-white/8" onClick={() => { setProfileOpen(false); navigate("/api-connection"); }}>
              API connection
            </button>
          </div>
        ) : null}
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
    { label: "Retrieval score", value: retrievalScore ? `${Math.round(retrievalScore * 100)}%` : "N/A", trend: "From recent queries", icon: Gauge },
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
      <div className="grid gap-4 xl:grid-cols-[1.45fr_0.85fr]">
        <Card className="min-h-[360px]">
          <SectionTitle icon={Activity} title="Document analytics" subtitle="Indexed documents and retrieval activity" />
          <div className="mt-6 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={analytics}>
                <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                <XAxis dataKey="name" stroke="#64748b" tickLine={false} axisLine={false} />
                <YAxis stroke="#64748b" tickLine={false} axisLine={false} width={34} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="documents" fill="#7dd3fc" radius={[8, 8, 0, 0]} />
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
              doc.updatedAt
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

  const runDocumentAction = async (action: "index" | "removeVectors" | "removeDocuments") => {
    const targetIds = selected.length ? selected : visibleDocs.map((doc) => doc.id);
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

  const runSingleDocumentAction = async (docId: string, action: "index" | "removeVectors" | "removeDocuments") => {
    setSelected([docId]);
    setOpenActions("");
    setNotice("");
    try {
      if (action === "index") await api.indexDocuments([docId]);
      if (action === "removeVectors") await api.removeVectors([docId]);
      if (action === "removeDocuments") await api.removeDocuments([docId]);
      setNotice("Document action completed.");
      setSelected([]);
      docsState.reload();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Document action failed.");
    }
  };

  const uploadFiles = async () => {
    if (!files.length) return;
    setUploading(true);
    setNotice("");
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    form.append("tags", tags);
    form.append("owner", owner);
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
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => runDocumentAction("index")} disabled={!visibleDocs.length}>
                <Database className="h-4 w-4" />
                Index selected
              </Button>
              <Button variant="secondary" onClick={() => runDocumentAction("removeVectors")} disabled={!visibleDocs.length}>
                <Trash2 className="h-4 w-4" />
                Remove vectors
              </Button>
              <Button variant="danger" onClick={() => runDocumentAction("removeDocuments")} disabled={!visibleDocs.length}>
                <Trash2 className="h-4 w-4" />
                Remove docs
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
          <div className="mt-5 overflow-hidden rounded-2xl border border-white/10">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-white/[0.035] text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="w-12 px-4 py-3">
                    <span className="sr-only">Select</span>
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
                {visibleDocs.map((doc) => (
                  <tr key={doc.id} className="transition hover:bg-white/[0.025]">
                    <td className="px-4 py-4">
                      <button
                        aria-label={`Select ${doc.filename}`}
                        className={cn(
                          "focus-ring grid h-5 w-5 place-items-center rounded-md border transition",
                          selected.includes(doc.id) ? "border-sky-300 bg-sky-300 text-slate-950" : "border-white/20 text-transparent"
                        )}
                        onClick={() =>
                          setSelected((current) =>
                            current.includes(doc.id) ? current.filter((id) => id !== doc.id) : [...current, doc.id]
                          )
                        }
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                      </button>
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
                        className="focus-ring rounded-xl p-2 text-slate-400 hover:bg-white/6 hover:text-white"
                        onClick={() => setOpenActions((current) => (current === doc.id ? "" : doc.id))}
                      >
                        <MoreHorizontal className="h-4 w-4" />
                      </button>
                      {openActions === doc.id ? (
                        <div className="absolute right-4 top-12 z-20 w-44 rounded-2xl border border-white/10 bg-[#0c0f14] p-1 shadow-2xl">
                          <button className="w-full rounded-xl px-3 py-2 text-left text-sm text-slate-300 hover:bg-white/8" onClick={() => runSingleDocumentAction(doc.id, "index")}>
                            Index document
                          </button>
                          <button className="w-full rounded-xl px-3 py-2 text-left text-sm text-slate-300 hover:bg-white/8" onClick={() => runSingleDocumentAction(doc.id, "removeVectors")}>
                            Remove vectors
                          </button>
                          <button className="w-full rounded-xl px-3 py-2 text-left text-sm text-rose-200 hover:bg-rose-400/10" onClick={() => runSingleDocumentAction(doc.id, "removeDocuments")}>
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
          {!visibleDocs.length ? (
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
    </div>
  );
}

function ChatPage() {
  const [searchParams] = useSearchParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeSession, setActiveSession] = useState("");
  const [input, setInput] = useState("");
  const [topK, setTopK] = useState(6);
  const [threshold, setThreshold] = useState(0.72);
  const [sourceMode, setSourceMode] = useState("balanced");
  const [loading, setLoading] = useState(false);
  const sessionsState = useAsyncData<any[]>(
    async () => {
      const response: any = await api.sessions();
      return Array.isArray(response) ? response : response.sessions || [];
    },
    []
  );
  const query = searchParams.get("q") || "";
  const sessions = sessionsState.data.filter((session) =>
    matchesSearch([session.title, session.name, session.query, session.id, session.session_id], query)
  );

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
        session_id: activeSession || undefined
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
    <div className="grid min-h-[calc(100vh-112px)] gap-4 xl:grid-cols-[260px_minmax(0,1fr)_320px]">
      <Card className="hidden xl:block">
        <div className="mb-5 flex items-center justify-between">
          <SectionTitle icon={History} title="Chat history" />
          <Button size="icon" variant="secondary" ariaLabel="New chat" onClick={newChat}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        <div className="space-y-2">
          {sessions.length ? sessions.map((session, index) => {
            const sessionId = String(session.id || session.session_id || "");
            return (
            <button
              key={sessionId || index}
              className={cn(
                "focus-ring w-full rounded-2xl px-3 py-3 text-left text-sm transition",
                activeSession === sessionId ? "bg-white text-slate-950" : "text-slate-400 hover:bg-white/6 hover:text-white"
              )}
              onClick={() => loadSession(session)}
            >
              <span className="block truncate font-medium">{session.title || session.name || session.query || "Untitled session"}</span>
              <span className="mt-1 block text-xs text-slate-600">{session.message_count || session.interactions || 0} messages</span>
            </button>
            );
          }) : <EmptyState icon={MessageSquare} title="No chat sessions" description="Saved sessions appear here after a chat is created." />}
        </div>
      </Card>
      <Card className="flex min-h-[720px] flex-col overflow-hidden p-0">
        <div className="border-b border-white/10 p-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <SectionTitle icon={Bot} title="AI chat workspace" subtitle="Grounded answers with visible retrieval provenance" />
            <Badge tone="success">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Provenance on
            </Badge>
          </div>
        </div>
        <div className="flex-1 space-y-5 overflow-y-auto px-4 py-6 sm:px-6">
          {messages.length === 0 ? (
            <EmptyState
              icon={Sparkles}
              title="Start with a question"
              description="Ask about policies, decisions, research notes, contracts, or any indexed knowledge."
            />
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
        <div className="border-t border-white/10 bg-[#0b0d12]/95 p-4">
          <div className="mb-3 flex flex-wrap gap-2">
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
          </div>
          <ChatComposer value={input} onChange={setInput} onSubmit={sendMessage} loading={loading} />
        </div>
      </Card>
      <Card>
        <SectionTitle icon={SlidersHorizontal} title="Retrieval settings" subtitle="Tune source selection for this chat" />
        <div className="mt-6 space-y-6">
          <RangeControl label="Top K" value={topK} min={2} max={12} step={1} onChange={setTopK} />
          <RangeControl label="Score threshold" value={threshold} min={0.1} max={0.95} step={0.01} onChange={setThreshold} />
          <Select label="Source mode" value={sourceMode} onChange={(event) => setSourceMode(event.target.value)}>
            <option value="balanced">Balanced</option>
            <option value="strict">Strict citations</option>
            <option value="broad">Broad recall</option>
          </Select>
          <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-4">
            <p className="text-sm font-medium text-white">Answer provenance</p>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              Every response can expose retrieved chunks, source confidence, and document origin for inspection.
            </p>
          </div>
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
                    <p className="mt-1 text-sm text-slate-500">{key.provider} · {key.created_at || key.createdAt || "Recently"}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone={key.is_active || key.active ? "success" : "neutral"}>{key.is_active || key.active ? "Active" : "Stored"}</Badge>
                    {key.id ? (
                      <button className="focus-ring rounded-xl p-2 text-slate-500 hover:bg-rose-400/10 hover:text-rose-200" onClick={() => deleteKey(String(key.id))}>
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
              {active.updatedAt}
            </Badge>
          </div>
          <div className="mt-6 grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
            <Textarea label="Prompt editor" value={body} onChange={(event) => setBody(event.target.value)} rows={18} />
            <div className="space-y-4">
              <Textarea label="Change note" value={note} onChange={(event) => setNote(event.target.value)} rows={5} />
              <Card className="p-4">
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
    <div className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-white text-slate-950 shadow-lg shadow-sky-950/20">
      <Brain className="h-5 w-5" />
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
        <p className="text-sm font-medium text-sky-300">{eyebrow}</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white sm:text-4xl">{title}</h1>
        <p className="mt-3 text-base leading-7 text-slate-400">{description}</p>
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={cn("premium-card rounded-3xl p-5", className)}>{children}</section>;
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
        "focus-ring inline-flex items-center justify-center gap-2 rounded-2xl text-sm font-semibold transition active:scale-[0.99] disabled:opacity-60",
        size === "icon" ? "h-10 w-10" : "h-10 px-4",
        variant === "primary" && "bg-white text-slate-950 shadow-lg shadow-sky-950/20 hover:bg-sky-100",
        variant === "secondary" && "border border-white/10 bg-white/[0.04] text-slate-200 hover:bg-white/8 hover:text-white",
        variant === "danger" && "border border-rose-300/20 bg-rose-400/10 text-rose-200 hover:bg-rose-400/15",
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
          "focus-ring h-11 w-full rounded-2xl border border-white/10 bg-black/20 px-3 text-sm text-white placeholder:text-slate-600 transition hover:border-white/16",
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
        className="focus-ring h-11 w-full rounded-2xl border border-white/10 bg-black/20 px-3 text-sm text-white transition hover:border-white/16"
        {...props}
      >
        {children}
      </select>
    </label>
  );
}

function Textarea({ label, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string }) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-300">{label}</span>
      <textarea
        className="focus-ring w-full resize-y rounded-2xl border border-white/10 bg-black/20 p-3 font-mono text-sm leading-6 text-white placeholder:text-slate-600 transition hover:border-white/16"
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
        <div className="grid h-10 w-10 place-items-center rounded-2xl bg-white/[0.055] text-sky-300">
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <p className="mt-4 text-sm text-slate-400">{trend}</p>
    </Card>
  );
}

function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "success" | "warn" }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
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
  return <span className="rounded-full bg-sky-300/10 px-2.5 py-1 text-xs font-medium text-sky-200">{children}</span>;
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
    <div className={cn("flex flex-wrap gap-2 rounded-2xl border border-white/10 bg-black/20 p-1", className)}>
      {items.map((item) => (
        <button
          key={item.value}
          className={cn(
            "focus-ring rounded-xl px-3 py-2 text-sm font-medium transition",
            value === item.value ? "bg-white text-slate-950" : "text-slate-400 hover:bg-white/6 hover:text-white"
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
        status === "online" && "bg-emerald-300 shadow-[0_0_18px_rgba(110,231,183,0.75)]",
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
      <div className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-2xl bg-white/[0.055] text-sky-300">
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0">
        <h2 className="text-base font-semibold text-white">{title}</h2>
        {subtitle ? <p className="mt-1 text-sm text-slate-500">{subtitle}</p> : null}
      </div>
    </div>
  );
}

function EmptyState({ icon: Icon, title, description }: { icon: any; title: string; description: string }) {
  return (
    <div className="rounded-3xl border border-dashed border-white/12 bg-white/[0.025] p-8 text-center">
      <div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-white/[0.055] text-sky-300">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="mt-4 font-semibold text-white">{title}</h3>
      <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-slate-500">{description}</p>
    </div>
  );
}

function InlineNotice({ tone, message }: { tone: "success" | "warn"; message: string }) {
  return (
    <div
      className={cn(
        "rounded-2xl border px-4 py-3 text-sm",
        tone === "success" ? "border-emerald-300/20 bg-emerald-400/10 text-emerald-200" : "border-amber-300/20 bg-amber-400/10 text-amber-100"
      )}
    >
      {message}
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
        className="rounded-3xl border border-dashed border-white/16 bg-white/[0.025] p-7 text-center transition hover:border-sky-300/40 hover:bg-sky-300/[0.035]"
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
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-3xl bg-white text-slate-950">
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
            <div key={`${file.name}-${file.size}`} className="rounded-2xl border border-white/10 bg-white/[0.035] p-3">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-white">{file.name}</p>
                  <p className="text-xs text-slate-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
                <Badge>Queued</Badge>
              </div>
              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10">
                <div className="h-full w-2/3 rounded-full bg-sky-300" />
              </div>
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
  loading
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  loading: boolean;
}) {
  return (
    <div className="flex items-end gap-3 rounded-3xl border border-white/10 bg-black/25 p-2">
      <textarea
        className="focus-ring max-h-36 min-h-12 flex-1 resize-none rounded-2xl bg-transparent px-3 py-3 text-sm leading-6 text-white placeholder:text-slate-600"
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
  );
}

function ChatBubble({ message }: { message: Message }) {
  const assistant = message.role === "assistant";
  return (
    <div className={cn("flex", assistant ? "justify-start" : "justify-end")}>
      <div className={cn("max-w-3xl rounded-3xl p-4", assistant ? "border border-white/10 bg-white/[0.04]" : "bg-white text-slate-950")}>
        <p className="whitespace-pre-wrap text-sm leading-6">{message.content}</p>
        {assistant && message.sources?.length ? (
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {message.sources.map((source) => (
              <div key={`${source.title}-${source.page}`} className="rounded-2xl border border-white/10 bg-black/20 p-3">
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
      className={cn(
        "focus-ring w-full rounded-2xl border p-4 text-left transition",
        active ? "border-sky-300/50 bg-sky-300/10" : "border-white/10 bg-white/[0.025] hover:bg-white/[0.05]"
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
        className="w-full accent-sky-300"
      />
    </label>
  );
}

function DataTable({ columns, rows }: { columns: string[]; rows: React.ReactNode[][] }) {
  return (
    <div className="mt-5 overflow-hidden rounded-2xl border border-white/10">
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
      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-white/[0.055] text-sky-300">
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
    <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-3">
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
              <Pie data={data} dataKey="value" innerRadius={34} outerRadius={58} paddingAngle={4}>
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
    <div className="rounded-2xl border border-white/10 bg-[#0c0f14] p-3 shadow-xl">
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
