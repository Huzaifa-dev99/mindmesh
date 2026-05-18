import {
  BarChart3,
  Bot,
  BrainCircuit,
  Check,
  ChevronRight,
  FileText,
  Globe2,
  KeyRound,
  Library,
  LockKeyhole,
  Menu,
  MessageSquarePlus,
  Paperclip,
  RefreshCcw,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  Upload,
  UserRound,
  X
} from "lucide-react";
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

const PIN_KEY = "mindmesh_privacy_pin";
const PROFILE_KEY = "mindmesh_profile";
const CHART_COLORS = ["#d65cff", "#7c3cff", "#20e3b2", "#ffb86c", "#7aa8ff"];

const defaultProfile = {
  name: "Local user",
  avatar: "https://api.dicebear.com/9.x/shapes/svg?seed=mindmesh&backgroundColor=16091f"
};

function compactNumber(value) {
  const number = Number(value || 0);
  if (number >= 1000000) return `${(number / 1000000).toFixed(1)}M`;
  if (number >= 1000) return `${(number / 1000).toFixed(1)}k`;
  return String(number);
}

function uniqueTags(documents) {
  return [...new Set(documents.flatMap((doc) => doc.tags || []))].sort((a, b) => a.localeCompare(b));
}

function formatDate(value) {
  if (!value) return "No date";
  return new Date(value).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function sourceLabel(source) {
  const metadata = source.metadata || {};
  const page = metadata.page_number ? ` p. ${metadata.page_number}` : "";
  return metadata.filename ? `${metadata.filename}${page}` : source.source;
}

function App() {
  const [hasPin, setHasPin] = useState(Boolean(localStorage.getItem(PIN_KEY)));
  const [unlocked, setUnlocked] = useState(false);
  const [view, setView] = useState("chat");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [profile, setProfile] = useState(() => {
    const saved = localStorage.getItem(PROFILE_KEY);
    return saved ? JSON.parse(saved) : defaultProfile;
  });
  const [sessions, setSessions] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [admin, setAdmin] = useState(null);
  const [prompts, setPrompts] = useState([]);
  const [modelOptions, setModelOptions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [chatSearch, setChatSearch] = useState("");
  const [attachedDocumentIds, setAttachedDocumentIds] = useState([]);
  const [attachedTags, setAttachedTags] = useState([]);
  const [retrievalEnabled, setRetrievalEnabled] = useState(true);
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const [routeMode, setRouteMode] = useState("auto");
  const [selectedModel, setSelectedModel] = useState("");
  const [topK, setTopK] = useState(4);
  const [scoreThreshold, setScoreThreshold] = useState(0);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  async function refreshAll() {
    try {
      const [sessionData, documentData, dashboardData, adminData, promptData] = await Promise.allSettled([
        api.sessions(),
        api.documents(),
        api.dashboard(),
        api.aiAdmin(),
        api.prompts()
      ]);
      if (sessionData.status === "fulfilled") setSessions(sessionData.value.sessions || []);
      if (documentData.status === "fulfilled") setDocuments(documentData.value.documents || []);
      if (dashboardData.status === "fulfilled") setDashboard(dashboardData.value);
      if (adminData.status === "fulfilled") {
        setAdmin(adminData.value);
        setSelectedModel(adminData.value.settings?.active_model || "");
      }
      if (promptData.status === "fulfilled") setPrompts(promptData.value.prompts || []);
    } catch (error) {
      setNotice(error.message);
    }
  }

  useEffect(() => {
    if (unlocked) refreshAll();
  }, [unlocked]);

  async function loadSession(sessionId) {
    setActiveSessionId(sessionId);
    setBusy(true);
    try {
      const payload = await api.interactions(sessionId);
      const loadedMessages = (payload.interactions || []).flatMap((interaction) => [
        { id: `${interaction.id}-user`, role: "user", content: interaction.query },
        {
          id: `${interaction.id}-assistant`,
          role: "assistant",
          content: interaction.answer,
          route: interaction.route,
          routeReasoning: interaction.route_reasoning,
          sources: interaction.sources || []
        }
      ]);
      setMessages(loadedMessages);
      setView("chat");
      setMobileMenuOpen(false);
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  function startNewChat() {
    setActiveSessionId(null);
    setMessages([]);
    setAttachedDocumentIds([]);
    setAttachedTags([]);
    setView("chat");
    setMobileMenuOpen(false);
  }

  function attachDocument(documentId) {
    setAttachedDocumentIds((current) => (current.includes(documentId) ? current : [...current, documentId]));
    setRetrievalEnabled(true);
    setView("chat");
  }

  function attachTag(tag) {
    setAttachedTags((current) => (current.includes(tag) ? current : [...current, tag]));
    setRetrievalEnabled(true);
    setView("chat");
  }

  function clearAttachment(id) {
    setAttachedDocumentIds((current) => current.filter((item) => item !== id));
  }

  async function sendMessage(text) {
    if (!text.trim() || busy) return;
    const userMessage = { id: crypto.randomUUID(), role: "user", content: text.trim() };
    setMessages((current) => [...current, userMessage]);
    setBusy(true);
    try {
      const payload = await api.generate({
        query: text.trim(),
        session_id: activeSessionId,
        top_k: topK,
        score_threshold: scoreThreshold,
        document_ids: attachedDocumentIds,
        tags: attachedTags,
        retrieval_enabled: retrievalEnabled,
        web_search_enabled: webSearchEnabled,
        route_mode: routeMode,
        model: selectedModel || undefined
      });
      setActiveSessionId(payload.session_id || activeSessionId);
      setMessages((current) => [
        ...current,
        {
          id: payload.interaction_id || crypto.randomUUID(),
          role: "assistant",
          content: payload.answer,
          route: payload.route,
          routeReasoning: payload.route_reasoning,
          contextualizedQuery: payload.contextualized_query,
          sources: payload.sources || []
        }
      ]);
      api.sessions().then((data) => setSessions(data.sessions || [])).catch(() => {});
    } catch (error) {
      setMessages((current) => [...current, { id: crypto.randomUUID(), role: "assistant", content: `API error: ${error.message}`, error: true }]);
    } finally {
      setBusy(false);
    }
  }

  async function uploadToChat(files, tags) {
    if (!files.length) return;
    setBusy(true);
    const formData = new FormData();
    [...files].forEach((file) => {
      formData.append("files", file);
      formData.append("filenames", file.name);
      formData.append("tags", tags || "chat-upload");
    });
    try {
      const uploaded = await api.uploadDocuments(formData);
      const ids = (uploaded.documents || []).map((doc) => doc.id);
      if (ids.length) {
        await api.indexDocuments(ids);
        setAttachedDocumentIds((current) => [...new Set([...current, ...ids])]);
        setRetrievalEnabled(true);
      }
      await refreshAll();
      setNotice(`Uploaded and indexed ${ids.length} document(s).`);
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  if (!unlocked) {
    return <LockScreen hasPin={hasPin} onPinCreated={() => setHasPin(true)} onUnlock={() => setUnlocked(true)} />;
  }

  return (
    <div className="app-shell">
      <div className="grid-glow" />
      <button className="mobile-menu" onClick={() => setMobileMenuOpen(true)} aria-label="Open navigation">
        <Menu size={20} />
      </button>
      <Sidebar
        open={mobileMenuOpen}
        sessions={sessions}
        activeSessionId={activeSessionId}
        search={chatSearch}
        onSearch={setChatSearch}
        onClose={() => setMobileMenuOpen(false)}
        onNewChat={startNewChat}
        onLoadSession={loadSession}
        view={view}
        onView={setView}
      />
      <main className="workspace">
        <TopBar profile={profile} onView={setView} onRefresh={refreshAll} />
        {notice && (
          <div className="notice">
            <Sparkles size={16} />
            <span>{notice}</span>
            <button onClick={() => setNotice("")} aria-label="Dismiss notice"><X size={16} /></button>
          </div>
        )}
        {view === "chat" && (
          <ChatView
            busy={busy}
            messages={messages}
            documents={documents}
            attachedDocumentIds={attachedDocumentIds}
            attachedTags={attachedTags}
            retrievalEnabled={retrievalEnabled}
            webSearchEnabled={webSearchEnabled}
            routeMode={routeMode}
            selectedModel={selectedModel}
            modelOptions={modelOptions}
            topK={topK}
            scoreThreshold={scoreThreshold}
            onSend={sendMessage}
            onUpload={uploadToChat}
            onAttachDocument={attachDocument}
            onAttachTag={attachTag}
            onClearAttachment={clearAttachment}
            onClearTag={(tag) => setAttachedTags((current) => current.filter((item) => item !== tag))}
            onRetrieval={setRetrievalEnabled}
            onWeb={setWebSearchEnabled}
            onRoute={setRouteMode}
            onModel={setSelectedModel}
            onTopK={setTopK}
            onScore={setScoreThreshold}
          />
        )}
        {view === "documents" && (
          <DocumentsView
            documents={documents}
            onSync={async () => {
              const result = await api.syncDocuments();
              setDocuments(result.documents || []);
            }}
            onAttachDocument={attachDocument}
            onAttachAll={() => {
              setAttachedDocumentIds(documents.map((doc) => doc.id).filter(Boolean));
              setRetrievalEnabled(true);
              setView("chat");
            }}
            onAttachTag={attachTag}
          />
        )}
        {view === "dashboard" && <DashboardView dashboard={dashboard} documents={documents} />}
        {view === "settings" && (
          <SettingsView
            admin={admin}
            prompts={prompts}
            profile={profile}
            modelOptions={modelOptions}
            selectedModel={selectedModel}
            onProfile={(next) => {
              setProfile(next);
              localStorage.setItem(PROFILE_KEY, JSON.stringify(next));
            }}
            onModelOptions={setModelOptions}
            onSelectedModel={setSelectedModel}
            onAdmin={setAdmin}
            onPrompts={setPrompts}
          />
        )}
      </main>
    </div>
  );
}

function LockScreen({ hasPin, onPinCreated, onUnlock }) {
  const [pin, setPin] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");

  function submit(event) {
    event.preventDefault();
    if (!/^\d{4}$/.test(pin)) {
      setError("Enter a 4 digit PIN.");
      return;
    }
    if (!hasPin) {
      if (pin !== confirm) {
        setError("PIN confirmation does not match.");
        return;
      }
      localStorage.setItem(PIN_KEY, pin);
      onPinCreated();
      onUnlock();
      return;
    }
    if (pin !== localStorage.getItem(PIN_KEY)) {
      setError("Incorrect PIN.");
      return;
    }
    onUnlock();
  }

  return (
    <div className="lock-screen">
      <div className="lock-orbit" />
      <form className="lock-card" onSubmit={submit}>
        <div className="brand-mark">
          <BrainCircuit size={26} />
          <span>MindMesh</span>
        </div>
        <div className="lock-icon"><LockKeyhole size={30} /></div>
        <h1>{hasPin ? "Unlock workspace" : "Set your privacy PIN"}</h1>
        <p>{hasPin ? "Your local chats stay behind a quick lockscreen." : "Create a local 4 digit PIN for this browser."}</p>
        <input
          inputMode="numeric"
          maxLength={4}
          value={pin}
          onChange={(event) => setPin(event.target.value.replace(/\D/g, ""))}
          placeholder="4 digit PIN"
          type="password"
          autoFocus
        />
        {!hasPin && (
          <input
            inputMode="numeric"
            maxLength={4}
            value={confirm}
            onChange={(event) => setConfirm(event.target.value.replace(/\D/g, ""))}
            placeholder="Confirm PIN"
            type="password"
          />
        )}
        {error && <div className="form-error">{error}</div>}
        <button className="primary-button" type="submit">
          <ShieldCheck size={18} />
          {hasPin ? "Unlock" : "Create PIN"}
        </button>
      </form>
    </div>
  );
}

function Sidebar({ open, sessions, activeSessionId, search, onSearch, onClose, onNewChat, onLoadSession, view, onView }) {
  const filtered = sessions.filter((session) => (session.title || "").toLowerCase().includes(search.toLowerCase()));
  return (
    <aside className={`sidebar ${open ? "is-open" : ""}`}>
      <div className="sidebar-header">
        <div className="brand-mark">
          <BrainCircuit size={22} />
          <span>MindMesh</span>
        </div>
        <button className="icon-button mobile-only" onClick={onClose} aria-label="Close navigation"><X size={18} /></button>
      </div>
      <button className="new-chat" onClick={onNewChat}>
        <MessageSquarePlus size={18} />
        New chat
      </button>
      <label className="search-box">
        <Search size={16} />
        <input value={search} onChange={(event) => onSearch(event.target.value)} placeholder="Search chats" />
      </label>
      <nav className="view-nav">
        {[
          ["chat", Bot, "Chat"],
          ["documents", Library, "Documents"],
          ["dashboard", BarChart3, "Dashboard"],
          ["settings", Settings, "Settings"]
        ].map(([key, Icon, label]) => (
          <button key={key} className={view === key ? "active" : ""} onClick={() => onView(key)}>
            <Icon size={17} />
            {label}
          </button>
        ))}
      </nav>
      <div className="chat-list">
        <span className="section-label">Recent chats</span>
        {filtered.map((session) => (
          <button
            key={session.id}
            className={`chat-row ${activeSessionId === session.id ? "active" : ""}`}
            onClick={() => onLoadSession(session.id)}
          >
            <span>{session.title || "Untitled chat"}</span>
            <small>{session.interaction_count || 0} turns</small>
          </button>
        ))}
      </div>
    </aside>
  );
}

function TopBar({ profile, onView, onRefresh }) {
  return (
    <header className="topbar">
      <div>
        <span className="eyebrow">Local private RAG workspace</span>
        <h2>Ask, attach, search, and inspect</h2>
      </div>
      <div className="topbar-actions">
        <button className="icon-button" onClick={onRefresh} aria-label="Refresh data"><RefreshCcw size={18} /></button>
        <button className="icon-button" onClick={() => onView("settings")} aria-label="Settings"><Settings size={18} /></button>
        <button className="profile-pill" onClick={() => onView("settings")}>
          <img src={profile.avatar} alt="" />
          <span>{profile.name}</span>
        </button>
      </div>
    </header>
  );
}

function ChatView(props) {
  const [draft, setDraft] = useState("");
  const [uploadTags, setUploadTags] = useState("chat-upload");
  const fileInputRef = useRef(null);
  const attachedDocs = props.documents.filter((doc) => props.attachedDocumentIds.includes(doc.id));
  const availableTags = uniqueTags(props.documents);

  function submit(event) {
    event.preventDefault();
    props.onSend(draft);
    setDraft("");
  }

  return (
    <section className="chat-layout">
      <div className="chat-panel">
        <div className="attachment-strip">
          <div className="mini-stat">
            <Paperclip size={16} />
            <span>{attachedDocs.length || "All"} docs</span>
          </div>
          {attachedDocs.map((doc) => (
            <button key={doc.id} className="chip" onClick={() => props.onClearAttachment(doc.id)}>
              {doc.filename}
              <X size={13} />
            </button>
          ))}
          {props.attachedTags.map((tag) => (
            <button key={tag} className="chip tag" onClick={() => props.onClearTag(tag)}>
              #{tag}
              <X size={13} />
            </button>
          ))}
        </div>
        <div className="messages">
          {!props.messages.length && <EmptyChat />}
          {props.messages.map((message) => <MessageBubble key={message.id} message={message} />)}
          {props.busy && <div className="typing">Thinking through the mesh...</div>}
        </div>
        <form className="composer" onSubmit={submit}>
          <div className="composer-controls">
            <select value={props.selectedModel} onChange={(event) => props.onModel(event.target.value)}>
              <option value="">Active model</option>
              {props.selectedModel && <option value={props.selectedModel}>{props.selectedModel}</option>}
              {props.modelOptions.filter((model) => model !== props.selectedModel).map((model) => (
                <option key={model} value={model}>{model}</option>
              ))}
            </select>
            <select value={props.routeMode} onChange={(event) => props.onRoute(event.target.value)}>
              <option value="auto">Auto route</option>
              <option value="retrieval">Retrieval</option>
              <option value="web_search">Web search</option>
              <option value="direct">Direct</option>
            </select>
            <label className="toggle-pill">
              <input type="checkbox" checked={props.retrievalEnabled} onChange={(event) => props.onRetrieval(event.target.checked)} />
              Retrieval
            </label>
            <label className="toggle-pill">
              <input type="checkbox" checked={props.webSearchEnabled} onChange={(event) => props.onWeb(event.target.checked)} />
              Web
            </label>
          </div>
          <div className="composer-input">
            <button type="button" className="icon-button" onClick={() => fileInputRef.current?.click()} aria-label="Upload document">
              <Upload size={18} />
            </button>
            <input ref={fileInputRef} type="file" multiple hidden accept=".pdf,.docx,.ppt,.pptx,.txt,.md" onChange={(event) => props.onUpload(event.target.files, uploadTags)} />
            <input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask about your documents or the web..." />
            <button className="send-button" type="submit" disabled={props.busy || !draft.trim()} aria-label="Send message">
              <Send size={18} />
            </button>
          </div>
          <div className="composer-footer">
            <input value={uploadTags} onChange={(event) => setUploadTags(event.target.value)} placeholder="Upload tags" />
            <label>Top K <input type="number" min="1" max="20" value={props.topK} onChange={(event) => props.onTopK(Number(event.target.value))} /></label>
            <label>Score <input type="number" min="0" max="1" step="0.05" value={props.scoreThreshold} onChange={(event) => props.onScore(Number(event.target.value))} /></label>
          </div>
        </form>
      </div>
      <aside className="context-panel">
        <DocumentQuickAttach documents={props.documents} tags={availableTags} onAttachDocument={props.onAttachDocument} onAttachTag={props.onAttachTag} />
      </aside>
    </section>
  );
}

function EmptyChat() {
  return (
    <div className="empty-chat">
      <div className="halo-icon"><Sparkles size={26} /></div>
      <h1>Start with a question or a file</h1>
      <p>Attach a document for scoped retrieval, use all indexed knowledge by default, or enable web search when you need current context.</p>
    </div>
  );
}

function MessageBubble({ message }) {
  return (
    <article className={`message ${message.role} ${message.error ? "error" : ""}`}>
      <div className="message-avatar">{message.role === "assistant" ? <Bot size={18} /> : <UserRound size={18} />}</div>
      <div className="message-body">
        {message.route && <span className="route-pill">{message.route.replace("_", " ")}</span>}
        {message.contextualizedQuery && <small className="context-note">Retrieved as: {message.contextualizedQuery}</small>}
        <p>{message.content}</p>
        {!!message.sources?.length && (
          <div className="sources">
            {message.sources.map((source, index) => (
              <span key={`${source.source}-${index}`}>
                [{index + 1}] {sourceLabel(source)}
              </span>
            ))}
          </div>
        )}
      </div>
    </article>
  );
}

function DocumentQuickAttach({ documents, tags, onAttachDocument, onAttachTag }) {
  return (
    <>
      <div className="panel-heading">
        <h3>Knowledge scope</h3>
        <span>{documents.length} files</span>
      </div>
      <div className="tag-cloud">
        {tags.slice(0, 10).map((tag) => (
          <button key={tag} className="tag-button" onClick={() => onAttachTag(tag)}>#{tag}</button>
        ))}
      </div>
      <div className="doc-stack">
        {documents.slice(0, 8).map((doc) => (
          <button key={doc.id} className="doc-card" onClick={() => onAttachDocument(doc.id)}>
            <FileText size={18} />
            <span>{doc.filename}</span>
            <small>{doc.status} · {doc.chunk_count || 0} chunks</small>
          </button>
        ))}
      </div>
    </>
  );
}

function DocumentsView({ documents, onSync, onAttachDocument, onAttachAll, onAttachTag }) {
  const tags = uniqueTags(documents);
  return (
    <section className="surface-page">
      <div className="page-title-row">
        <div>
          <span className="eyebrow">MinIO library</span>
          <h1>Documents</h1>
        </div>
        <div className="button-row">
          <button className="ghost-button" onClick={onSync}><RefreshCcw size={16} /> Sync</button>
          <button className="primary-button" onClick={onAttachAll}><Check size={16} /> Chat with all</button>
        </div>
      </div>
      <div className="tag-cloud wide">
        {tags.map((tag) => <button key={tag} className="tag-button" onClick={() => onAttachTag(tag)}>Chat with #{tag}</button>)}
      </div>
      <div className="document-grid">
        {documents.map((doc) => (
          <article key={doc.id} className="library-card">
            <div className="file-icon"><FileText size={22} /></div>
            <h3>{doc.filename}</h3>
            <p>{doc.key}</p>
            <div className="meta-row">
              <span>{doc.status}</span>
              <span>{doc.chunk_count || 0} chunks</span>
              <span>{compactNumber(doc.size)} bytes</span>
            </div>
            <div className="tag-cloud compact">
              {(doc.tags || []).slice(0, 4).map((tag) => <span key={tag}>#{tag}</span>)}
            </div>
            <button className="ghost-button" onClick={() => onAttachDocument(doc.id)}>Attach to current chat <ChevronRight size={16} /></button>
          </article>
        ))}
      </div>
    </section>
  );
}

function DashboardView({ dashboard, documents }) {
  const totals = dashboard?.totals || {};
  const status = dashboard?.document_status || [];
  const tags = dashboard?.document_tags || [];
  const recent = (dashboard?.recent_queries || []).slice().reverse().map((item, index) => ({ name: `Q${index + 1}`, contexts: item.context_count || 0, chunks: item.retrieved_chunk_count || 0 }));

  return (
    <section className="surface-page">
      <div className="page-title-row">
        <div>
          <span className="eyebrow">Analytics command deck</span>
          <h1>Dashboard</h1>
        </div>
      </div>
      <div className="metric-grid">
        <Metric label="Uploaded" value={totals.total_documents_uploaded ?? documents.length} note="Registry entries" />
        <Metric label="Indexed" value={totals.total_documents_indexed || 0} note="Ready for retrieval" />
        <Metric label="Queries" value={totals.total_queries || 0} note="Recorded interactions" />
        <Metric label="Chunks" value={totals.total_indexed_chunks || 0} note="Indexed vectors" />
      </div>
      <div className="chart-grid">
        <ChartCard title="Document status">
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={status} dataKey="count" nameKey="label" innerRadius={64} outerRadius={96}>
                {status.map((entry, index) => <Cell key={entry.status} fill={CHART_COLORS[index % CHART_COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Top tags">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={tags.slice(0, 8)}>
              <CartesianGrid stroke="#281a38" />
              <XAxis dataKey="tag" stroke="#9b8bad" />
              <YAxis stroke="#9b8bad" />
              <Tooltip />
              <Bar dataKey="count" fill="#d65cff" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Recent retrieval depth">
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={recent}>
              <defs>
                <linearGradient id="queryGlow" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#d65cff" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#d65cff" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="name" stroke="#9b8bad" />
              <YAxis stroke="#9b8bad" />
              <Tooltip />
              <Area type="monotone" dataKey="contexts" stroke="#d65cff" fill="url(#queryGlow)" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </section>
  );
}

function Metric({ label, value, note }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{compactNumber(value)}</strong>
      <small>{note}</small>
    </div>
  );
}

function ChartCard({ title, children }) {
  return (
    <div className="chart-card">
      <h3>{title}</h3>
      {children}
    </div>
  );
}

function SettingsView({ admin, prompts, profile, modelOptions, selectedModel, onProfile, onModelOptions, onSelectedModel, onAdmin, onPrompts }) {
  const [provider, setProvider] = useState(admin?.settings?.active_provider || "groq");
  const [keyId, setKeyId] = useState(admin?.settings?.active_key_id || "");
  const [manualModel, setManualModel] = useState(selectedModel || admin?.settings?.active_model || "");
  const [temperature, setTemperature] = useState(admin?.settings?.temperature || 0);
  const [maxTokens, setMaxTokens] = useState(admin?.settings?.max_tokens || 1024);
  const [newKey, setNewKey] = useState({ provider: "groq", label: "", base_url: "", api_key: "" });
  const [promptDrafts, setPromptDrafts] = useState({});
  const [status, setStatus] = useState("");

  useEffect(() => {
    setProvider(admin?.settings?.active_provider || "groq");
    setKeyId(admin?.settings?.active_key_id || "");
    setManualModel(selectedModel || admin?.settings?.active_model || "");
  }, [admin, selectedModel]);

  async function loadModels() {
    try {
      const data = await api.aiModels(provider, keyId || undefined);
      onModelOptions(data.models || []);
      setStatus(`Loaded ${data.models?.length || 0} model(s).`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function saveSettings() {
    try {
      const data = await api.saveAiSettings({
        provider,
        key_id: keyId || null,
        model: manualModel,
        temperature: Number(temperature),
        max_tokens: Number(maxTokens)
      });
      onAdmin(data);
      onSelectedModel(manualModel);
      setStatus("AI settings saved.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function addKey() {
    try {
      const data = await api.addAiKey(newKey);
      onAdmin(data);
      setNewKey({ provider: "groq", label: "", base_url: "", api_key: "" });
      setStatus("Provider key saved.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function savePrompt(prompt) {
    try {
      const updated = await api.savePrompt(prompt.name, {
        content: promptDrafts[prompt.name] ?? prompt.content,
        change_note: "Updated from React console"
      });
      const next = prompts.map((item) => (item.name === prompt.name ? updated.prompt : item));
      onPrompts(next);
      setStatus(`Saved ${updated.prompt.title}.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  return (
    <section className="surface-page settings-page">
      <div className="page-title-row">
        <div>
          <span className="eyebrow">Control plane</span>
          <h1>Settings</h1>
        </div>
        {status && <span className="settings-status">{status}</span>}
      </div>
      <div className="settings-grid">
        <div className="settings-card">
          <h3>Profile</h3>
          <label>Name<input value={profile.name} onChange={(event) => onProfile({ ...profile, name: event.target.value })} /></label>
          <label>Avatar URL<input value={profile.avatar} onChange={(event) => onProfile({ ...profile, avatar: event.target.value })} /></label>
        </div>
        <div className="settings-card">
          <h3>AI provider</h3>
          <label>Provider
            <select value={provider} onChange={(event) => setProvider(event.target.value)}>
              {(admin?.providers || ["groq", "openai", "gemini", "vllm"]).map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <label>Saved key
            <select value={keyId || ""} onChange={(event) => setKeyId(event.target.value)}>
              <option value="">Environment fallback</option>
              {(admin?.keys || []).filter((key) => key.provider === provider).map((key) => <option key={key.id} value={key.id}>{key.label}</option>)}
            </select>
          </label>
          <div className="inline-fields">
            <label>Temperature<input type="number" step="0.1" value={temperature} onChange={(event) => setTemperature(event.target.value)} /></label>
            <label>Max tokens<input type="number" value={maxTokens} onChange={(event) => setMaxTokens(event.target.value)} /></label>
          </div>
          <label>Model
            <input list="models" value={manualModel} onChange={(event) => setManualModel(event.target.value)} />
            <datalist id="models">{modelOptions.map((model) => <option key={model} value={model} />)}</datalist>
          </label>
          <div className="button-row">
            <button className="ghost-button" onClick={loadModels}><RefreshCcw size={16} /> Models</button>
            <button className="primary-button" onClick={saveSettings}><Check size={16} /> Save</button>
          </div>
        </div>
        <div className="settings-card">
          <h3>Add API key</h3>
          <label>Provider<input value={newKey.provider} onChange={(event) => setNewKey({ ...newKey, provider: event.target.value })} /></label>
          <label>Label<input value={newKey.label} onChange={(event) => setNewKey({ ...newKey, label: event.target.value })} /></label>
          <label>Base URL<input value={newKey.base_url} onChange={(event) => setNewKey({ ...newKey, base_url: event.target.value })} /></label>
          <label>API key<input type="password" value={newKey.api_key} onChange={(event) => setNewKey({ ...newKey, api_key: event.target.value })} /></label>
          <button className="primary-button" onClick={addKey}><KeyRound size={16} /> Save key</button>
        </div>
      </div>
      <div className="prompt-grid">
        {prompts.map((prompt) => (
          <div key={prompt.name} className="prompt-card">
            <div>
              <h3>{prompt.title}</h3>
              <span>{prompt.name} · v{prompt.active_version}</span>
            </div>
            <textarea value={promptDrafts[prompt.name] ?? prompt.content} onChange={(event) => setPromptDrafts({ ...promptDrafts, [prompt.name]: event.target.value })} />
            <button className="ghost-button" onClick={() => savePrompt(prompt)}>Save prompt</button>
          </div>
        ))}
      </div>
    </section>
  );
}

export default App;
