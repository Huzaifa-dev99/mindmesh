import {
  Brain,
  ChevronLeft,
  ChevronRight,
  Library,
  LockKeyhole,
  Menu,
  MessageSquare,
  PanelRightClose,
  Plus,
  Search,
  Settings,
  Trash2,
  X
} from "lucide-react";
import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import type { ConversationSummary, DocumentResource, Journal, Note, PreviewTarget, SearchResult } from "../types";
import { SettingsDialog } from "./SettingsDialog";

export type PageKey = "chats" | "library";

type Props = {
  page: PageKey;
  onPage: (page: PageKey) => void;
  notes: Note[];
  documents: DocumentResource[];
  journals: Journal[];
  storedTags: Array<{ id: string; name: string }>;
  conversations: ConversationSummary[];
  selectedConversationId: string | null;
  token: string;
  theme: "dark" | "light";
  onThemeChange: (theme: "dark" | "light") => void;
  onRefresh: () => Promise<void>;
  onLock: () => void;
  onNewChat: () => void;
  onSelectConversation: (conversationId: string) => void;
  previewTarget: PreviewTarget | null;
  onPreviewTargetChange: (target: PreviewTarget | null) => void;
  children: ReactNode;
};

export function AppShell({
  page,
  onPage,
  notes,
  documents,
  journals,
  storedTags,
  conversations,
  selectedConversationId,
  token,
  theme,
  onThemeChange,
  onRefresh,
  onLock,
  onNewChat,
  onSelectConversation,
  previewTarget,
  onPreviewTargetChange,
  children
}: Props) {
  const [sidebarOpen, setSidebarOpen] = useState(() => localStorage.getItem("mindmesh.sidebar") !== "collapsed");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const [editingNote, setEditingNote] = useState(false);
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchBusy, setSearchBusy] = useState(false);
  const [noteTitle, setNoteTitle] = useState("");
  const [noteContent, setNoteContent] = useState("");
  const [noteTags, setNoteTags] = useState("");

  useEffect(() => {
    localStorage.setItem("mindmesh.sidebar", sidebarOpen ? "expanded" : "collapsed");
  }, [sidebarOpen]);

  useEffect(() => {
    const query = searchQuery.trim();
    if (query.length < 2) {
      setSearchResults([]);
      setSearchBusy(false);
      return;
    }

    let cancelled = false;
    setSearchBusy(true);
    const timer = window.setTimeout(() => {
      api
        .search(token, query, [])
        .then((payload) => {
          if (!cancelled) setSearchResults(payload.results.slice(0, 5));
        })
        .catch(() => {
          if (!cancelled) setSearchResults([]);
        })
        .finally(() => {
          if (!cancelled) setSearchBusy(false);
        });
    }, 250);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [searchQuery, token]);

  const groupedNotes = useMemo(() => groupByDate(notes, (note) => note.updated_at || note.created_at), [notes]);
  const groupedConversations = useMemo(() => groupConversations(conversations), [conversations]);
  const tagOptions = useMemo(() => {
    const names = new Set<string>();
    storedTags.forEach((tag) => names.add(tag.name));
    notes.forEach((note) => note.tags.forEach((tag) => names.add(tag)));
    journals.forEach((journal) => journal.tags.forEach((tag) => names.add(tag)));
    return [...names].sort((left, right) => left.localeCompare(right));
  }, [journals, notes, storedTags]);
  const tagSuggestions = useMemo(() => getTagSuggestions(noteTags, tagOptions), [noteTags, tagOptions]);
  const memoryCount = journals.length + notes.length;
  const sidebarWidth = sidebarOpen ? "w-72" : "w-[4.75rem]";
  const previewNote = previewTarget?.type === "note" ? notes.find((note) => note.id === previewTarget.id) : null;
  const previewDocument = previewTarget?.type === "document" ? documents.find((document) => document.document_id === previewTarget.id) : null;

  useEffect(() => {
    if (previewTarget) {
      setRightPanelOpen(true);
      setEditingNote(false);
    }
  }, [previewTarget]);

  function openNewNote() {
    setRightPanelOpen(true);
    setEditingNote(true);
    onPreviewTargetChange(null);
    setEditingNoteId(null);
    setNoteTitle("");
    setNoteContent("");
    setNoteTags("");
  }

  function openExistingNote(note: Note) {
    onPreviewTargetChange({ type: "note", id: note.id });
  }

  function editNote(note: Note) {
    setRightPanelOpen(true);
    setEditingNote(true);
    onPreviewTargetChange(null);
    setEditingNoteId(note.id);
    setNoteTitle(note.title);
    setNoteContent(note.content);
    setNoteTags(note.tags.join(", "));
  }

  async function createNote(event: FormEvent) {
    event.preventDefault();
    if (!noteTitle.trim() || !noteContent.trim()) return;
    const payload = {
      title: noteTitle,
      content: noteContent,
      tags: parseTags(noteTags),
      source: "Right panel"
    };
    if (editingNoteId) {
      await api.updateNote(token, editingNoteId, payload);
    } else {
      await api.createNote(token, payload);
    }
    setNoteTitle("");
    setNoteContent("");
    setNoteTags("");
    setEditingNoteId(null);
    setEditingNote(false);
    await onRefresh();
  }

  async function deleteCurrentNote() {
    if (!editingNoteId) return;
    await api.deleteNote(token, editingNoteId);
    setNoteTitle("");
    setNoteContent("");
    setNoteTags("");
    setEditingNoteId(null);
    setEditingNote(false);
    await onRefresh();
  }

  function selectTagSuggestion(tag: string) {
    setNoteTags((current) => applyTagSuggestion(current, tag));
  }

  return (
    <div className="app-frame">
      {mobileNavOpen && (
        <button
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
          onClick={() => setMobileNavOpen(false)}
          aria-label="Close navigation overlay"
        />
      )}

      <aside className={`app-sidebar ${sidebarWidth} ${mobileNavOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}>
        <button
          className="sidebar-edge-toggle hidden md:grid"
          onClick={() => setSidebarOpen((value) => !value)}
          aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
        >
          {sidebarOpen ? <ChevronLeft size={17} /> : <ChevronRight size={17} />}
        </button>

        <div className={`mb-3 flex gap-2 ${sidebarOpen ? "items-center justify-between" : "flex-col items-center"}`}>
          <button
            className={`flex min-w-0 items-center gap-3 rounded-xl p-2 text-left hover:bg-panel ${sidebarOpen ? "" : "justify-center"}`}
            onClick={() => onPage("chats")}
            aria-label="Open chats"
          >
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-foreground text-app">
              <Brain size={20} />
            </div>
            {sidebarOpen && (
              <div className="min-w-0">
                <p className="truncate font-semibold">MindMesh</p>
                <p className="truncate text-xs text-muted">Local AI workspace</p>
              </div>
            )}
          </button>
        </div>

        {sidebarOpen && (
          <div className="mb-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" size={16} />
              <input
                className="control h-10 pl-9"
                placeholder="Search workspace"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
              />
            </div>
            {searchQuery.trim().length >= 2 && (
              <div className="mt-2 rounded-xl border border-border bg-panel p-2">
                {searchBusy && <p className="px-2 py-2 text-xs text-muted">Searching...</p>}
                {!searchBusy && searchResults.length === 0 && <p className="px-2 py-2 text-xs text-muted">No matching memories.</p>}
                {!searchBusy &&
                  searchResults.map((result) => (
                    <button
                      key={`${result.source_type}-${result.source_id}`}
                      className="block w-full rounded-lg px-2 py-2 text-left hover:bg-elevated"
                      onClick={() => {
                        onPage("library");
                        if (result.source_type === "note") {
                          onPreviewTargetChange({ type: "note", id: result.source_id });
                        } else if (result.source_type === "document") {
                          const documentId = typeof result.metadata?.document_id === "string" ? result.metadata.document_id : result.source_id;
                          onPreviewTargetChange({ type: "document", id: documentId });
                        }
                        setSearchQuery("");
                      }}
                    >
                      <p className="truncate text-sm font-medium">{result.title || result.source_type}</p>
                      <p className="line-clamp-2 text-xs leading-5 text-muted">{result.snippet}</p>
                    </button>
                  ))}
              </div>
            )}
          </div>
        )}

        <div className="mb-3 grid gap-2">
          <button onClick={onNewChat} className={`button-primary h-10 ${sidebarOpen ? "" : "px-0"}`}>
            <Plus size={16} />
            {sidebarOpen && "New Chat"}
          </button>
        </div>

        <nav className="space-y-1">
          {[
            { key: "chats" as const, label: "Chats", icon: MessageSquare },
            { key: "library" as const, label: "Library", icon: Library }
          ].map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                onClick={() => onPage(item.key)}
                className={`sidebar-item ${page === item.key ? "sidebar-item-active" : ""} ${sidebarOpen ? "" : "justify-center px-0"}`}
              >
                <Icon size={17} />
                {sidebarOpen && item.label}
              </button>
            );
          })}
        </nav>

        {sidebarOpen && (
          <div className="mt-5 flex-1 overflow-y-auto pr-1">
            <p className="mb-2 px-2 text-xs font-medium uppercase tracking-[0.16em] text-muted">Chat History</p>
            {groupedConversations.map((section) => (
              <div key={section.label} className="mb-4">
                <p className="mb-1 px-2 text-xs text-muted">{section.label}</p>
                <div className="space-y-1">
                  {section.items.map((conversation) => (
                    <button
                      key={conversation.id}
                      onClick={() => onSelectConversation(conversation.id)}
                      className={`w-full truncate rounded-lg px-2 py-2 text-left text-sm hover:bg-panel ${
                        selectedConversationId === conversation.id ? "bg-panel text-foreground" : "text-soft"
                      }`}
                    >
                      {conversation.title || "Untitled chat"}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            {!conversations.length && <p className="rounded-xl bg-panel px-3 py-3 text-sm leading-5 text-muted">No saved chats yet.</p>}
          </div>
        )}

        <div className="mt-auto border-t border-border pt-3">
          <div className={`flex items-center gap-2 ${sidebarOpen ? "" : "flex-col"}`}>
            <button
              onClick={() => setSettingsOpen(true)}
              className={`flex min-w-0 flex-1 items-center gap-3 rounded-xl p-2 hover:bg-panel ${sidebarOpen ? "" : "justify-center"}`}
              aria-label="Open profile settings"
            >
              <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-panel text-sm text-soft">L</div>
              {sidebarOpen && (
                <>
                  <div className="min-w-0 flex-1 text-left">
                    <p className="truncate text-sm font-medium">Local Workspace</p>
                    <p className="truncate text-xs text-muted">Settings</p>
                  </div>
                  <Settings size={17} className="text-muted" />
                </>
              )}
            </button>
            <button className="icon-button shrink-0" onClick={onLock} aria-label="Lock workspace" title="Lock workspace">
              <LockKeyhole size={17} />
            </button>
          </div>
        </div>
      </aside>

      <main className="app-main">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-3 md:px-4">
          <button className="icon-button md:hidden" onClick={() => setMobileNavOpen(true)} aria-label="Open navigation">
            <Menu size={19} />
          </button>
          <div className="min-w-0 flex-1 px-2">
            <p className="truncate text-sm font-medium">{page === "chats" ? "Chats" : "Library"}</p>
            <p className="truncate text-xs text-muted">{page === "chats" ? "Ask and organize your private knowledge" : "Notes, documents, media, and insights"}</p>
          </div>
          <button className="icon-button" onClick={() => setRightPanelOpen((value) => !value)} aria-label="Toggle context panel">
            <PanelRightClose size={18} />
          </button>
        </header>
        {children}
      </main>

      <aside className={`right-panel ${rightPanelOpen ? "translate-x-0" : "translate-x-full lg:translate-x-0 lg:w-0 lg:border-l-0 lg:p-0"}`}>
        <div className="flex h-14 items-center justify-between border-b border-border px-4">
          <div>
            <p className="text-sm font-semibold">{editingNote ? "Note Editor" : previewTarget ? "Preview" : "Context"}</p>
            <p className="text-xs text-muted">{editingNote ? "Linked to workspace" : previewTarget ? "Source details" : "Notes grouped by date"}</p>
          </div>
          <button className="icon-button" onClick={() => (editingNote ? setEditingNote(false) : setRightPanelOpen(false))} aria-label="Close right panel">
            <X size={18} />
          </button>
        </div>

        <div className="h-[calc(100vh-3.5rem)] overflow-y-auto p-4">
          {editingNote ? (
            <form onSubmit={createNote} className="space-y-3">
              <input className="control" placeholder="Note title" value={noteTitle} onChange={(event) => setNoteTitle(event.target.value)} />
              <div className="relative">
                <input
                  className="control"
                  placeholder="Tags, comma separated"
                  value={noteTags}
                  onChange={(event) => setNoteTags(event.target.value)}
                  aria-label="Note tags"
                  autoComplete="off"
                />
                {tagSuggestions.length > 0 && (
                  <div className="tag-suggestion-popover" role="listbox" aria-label="Stored tag suggestions">
                    {tagSuggestions.map((tag) => (
                      <button key={tag} type="button" className="tag-suggestion" onClick={() => selectTagSuggestion(tag)}>
                        {tag}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <textarea className="control min-h-[16rem] resize-y leading-6" placeholder="Write a note..." value={noteContent} onChange={(event) => setNoteContent(event.target.value)} />
              <div className="flex flex-wrap gap-2">
                <button className="button-primary" disabled={!noteTitle.trim() || !noteContent.trim()}>
                  {editingNoteId ? "Update Note" : "Save Note"}
                </button>
                <button type="button" className="button-ghost" onClick={() => setEditingNote(false)}>
                  Cancel
                </button>
                {editingNoteId && (
                  <button type="button" className="button-ghost text-danger" onClick={deleteCurrentNote}>
                    <Trash2 size={16} />
                    Delete
                  </button>
                )}
              </div>
            </form>
          ) : previewNote ? (
            <PreviewShell title={previewNote.title} type="Note" onClose={() => onPreviewTargetChange(null)}>
              <Metadata label="Created" value={formatDate(previewNote.created_at)} />
              <Metadata label="Updated" value={previewNote.updated_at ? formatDate(previewNote.updated_at) : "Not updated"} />
              <Metadata label="Source" value={previewNote.source || "MindMesh note"} />
              <Metadata label="Tags" value={previewNote.tags.length ? previewNote.tags.join(", ") : "None"} />
              <div className="mt-4 rounded-xl bg-elevated p-3">
                <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">Snippet</p>
                <p className="mt-2 line-clamp-6 text-sm leading-6 text-soft">{previewNote.content}</p>
              </div>
              <button className="button-primary mt-4 w-full" onClick={() => editNote(previewNote)}>Edit Note</button>
            </PreviewShell>
          ) : previewDocument ? (
            <PreviewShell title={previewDocument.file_name} type="Document" onClose={() => onPreviewTargetChange(null)}>
              <Metadata label="Type" value={previewDocument.file_type || "Document"} />
              <Metadata label="Uploaded" value={previewDocument.uploaded_date ? formatDate(previewDocument.uploaded_date) : "Unknown"} />
              <Metadata label="Chunks" value={`${previewDocument.chunk_count}`} />
              <Metadata label="MinIO path" value={previewDocument.minio_object_path} />
            </PreviewShell>
          ) : (
            <div className="space-y-5">
              <section>
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-sm font-semibold">Notes</h3>
                  <button className="button-ghost h-8 px-2 text-xs" onClick={openNewNote}>
                    <Plus size={14} />
                    New
                  </button>
                </div>
                <div className="space-y-4">
                  {groupedNotes.map((section) => (
                    <div key={section.label}>
                      <p className="mb-2 text-xs font-medium text-muted">{section.label}</p>
                      <div className="space-y-2">
                        {section.items.map((note) => (
                          <button key={note.id} onClick={() => openExistingNote(note)} className="block w-full rounded-xl border border-border bg-panel p-3 text-left hover:bg-elevated">
                            <p className="truncate text-sm font-medium">{note.title}</p>
                            <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted">{note.content}</p>
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                  {!notes.length && <p className="rounded-xl bg-panel p-3 text-sm text-muted">No notes yet.</p>}
                </div>
              </section>

              <section className="rounded-2xl border border-border bg-panel p-4">
                <h3 className="text-sm font-semibold">Quick Insight</h3>
                <p className="mt-2 text-sm leading-6 text-muted">
                  {memoryCount} {memoryCount === 1 ? "memory" : "memories"} available for retrieval across your local workspace.
                </p>
              </section>
            </div>
          )}
        </div>
      </aside>

      <SettingsDialog open={settingsOpen} onClose={() => setSettingsOpen(false)} theme={theme} onThemeChange={onThemeChange} />
    </div>
  );
}

function parseTags(raw: string) {
  const tags = raw
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
  return tags.length ? tags : ["workspace"];
}

function getTagSuggestions(raw: string, options: string[]) {
  const parts = raw.split(",");
  const active = parts[parts.length - 1]?.trim().toLowerCase() || "";
  const selected = new Set(
    raw
      .split(",")
      .map((tag) => tag.trim().toLowerCase())
      .filter(Boolean)
  );

  if (!active) return [];

  return options
    .filter((tag) => tag.toLowerCase().includes(active) && !selected.has(tag.toLowerCase()))
    .slice(0, 6);
}

function applyTagSuggestion(raw: string, tag: string) {
  const parts = raw.split(",");
  parts[parts.length - 1] = ` ${tag}`;
  return parts.map((part) => part.trim()).filter(Boolean).join(", ") + ", ";
}

function groupConversations(conversations: ConversationSummary[]) {
  return groupByDate(conversations, (conversation) => conversation.last_message_at || conversation.created_at);
}

function groupByDate<T>(items: T[], getDate: (item: T) => string | null | undefined) {
  const today = startOfDay(new Date());
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  const previousWeek = new Date(today);
  previousWeek.setDate(today.getDate() - 7);
  const previousMonth = new Date(today);
  previousMonth.setDate(today.getDate() - 30);

  const sections = [
    { label: "Today", items: [] as T[] },
    { label: "Yesterday", items: [] as T[] },
    { label: "Previous 7 Days", items: [] as T[] },
    { label: "Previous 30 Days", items: [] as T[] },
    { label: "Older", items: [] as T[] }
  ];

  [...items]
    .sort((left, right) => new Date(getDate(right) || 0).getTime() - new Date(getDate(left) || 0).getTime())
    .forEach((item) => {
      const date = new Date(getDate(item) || 0);
      if (date >= today) sections[0].items.push(item);
      else if (date >= yesterday) sections[1].items.push(item);
      else if (date >= previousWeek) sections[2].items.push(item);
      else if (date >= previousMonth) sections[3].items.push(item);
      else sections[4].items.push(item);
    });

  return sections.filter((section) => section.items.length > 0);
}

function startOfDay(date: Date) {
  const next = new Date(date);
  next.setHours(0, 0, 0, 0);
  return next;
}

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

function PreviewShell({ title, type, onClose, children }: { title: string; type: string; onClose: () => void; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-border bg-panel p-4">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">{type}</p>
          <h3 className="mt-1 truncate text-base font-semibold">{title}</h3>
        </div>
        <button className="icon-button shrink-0" onClick={onClose} aria-label="Close preview">
          <X size={16} />
        </button>
      </div>
      {children}
    </section>
  );
}

function Metadata({ label, value }: { label: string; value: string }) {
  return (
    <div className="mb-2 rounded-xl bg-elevated px-3 py-2">
      <p className="text-[0.68rem] font-medium uppercase tracking-[0.14em] text-muted">{label}</p>
      <p className="mt-1 break-words text-sm text-soft">{value}</p>
    </div>
  );
}
