import { BookOpenText, FileText, Globe2, Image, Loader2, MessageSquare, Trash2, Upload } from "lucide-react";
import { ChangeEvent, FormEvent, useMemo, useState } from "react";
import { EmptyState } from "../components/Feedback";
import { api } from "../lib/api";
import type { ConversationSummary, DocumentResource, Journal, Note, PreviewTarget } from "../types";

type Props = {
  journals: Journal[];
  notes: Note[];
  documents: DocumentResource[];
  conversations: ConversationSummary[];
  selectedConversationId: string | null;
  token: string;
  onRefresh: () => Promise<void>;
  onPreviewTargetChange: (target: PreviewTarget | null) => void;
};

type UploadState = {
  state: "idle" | "loading" | "indexed" | "failed";
  message: string;
};

export function KnowledgeDashboard({ notes, documents, conversations, selectedConversationId, token, onRefresh, onPreviewTargetChange }: Props) {
  const [mediaTitle, setMediaTitle] = useState("");
  const [mediaUrl, setMediaUrl] = useState("");
  const [mediaDescription, setMediaDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [activeTab, setActiveTab] = useState<"notes" | "documents">("notes");
  const [uploadStatus, setUploadStatus] = useState<UploadState>({ state: "idle", message: "" });
  const media = useMemo(() => notes.filter((note) => note.tags.includes("media")), [notes]);
  const regularNotes = useMemo(() => notes.filter((note) => !note.tags.includes("media")), [notes]);

  async function uploadDocument(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    setBusy(true);
    const timers = startUploadStatus(setUploadStatus);
    try {
      for (const file of files) {
        await api.uploadDocument(token, file, { scope: "global" });
      }
      clearUploadStatusTimers(timers);
      setUploadStatus({
        state: "indexed",
        message: "Indexed"
      });
      await onRefresh();
    } catch (error) {
      clearUploadStatusTimers(timers);
      setUploadStatus({ state: "failed", message: error instanceof Error ? error.message : "Failed" });
    } finally {
      event.target.value = "";
      setBusy(false);
    }
  }

  async function createMediaReference(event: FormEvent) {
    event.preventDefault();
    if (!mediaTitle.trim() || !mediaUrl.trim()) return;
    setBusy(true);
    try {
      await api.createNote(token, {
        title: mediaTitle,
        source: mediaUrl,
        content: mediaDescription || mediaUrl,
        tags: ["media"],
        metadata: { type: "media", url: mediaUrl }
      });
      setMediaTitle("");
      setMediaUrl("");
      setMediaDescription("");
      await onRefresh();
    } finally {
      setBusy(false);
    }
  }

  async function deleteNote(noteId: string) {
    await api.deleteNote(token, noteId);
    await onRefresh();
  }

  async function setNoteScope(noteId: string, scope: "chat" | "global") {
    if (scope === "chat" && !selectedConversationId) return;
    await api.updateNoteScope(token, noteId, { scope, chat_id: scope === "chat" ? selectedConversationId : null });
    await onRefresh();
  }

  async function deleteDocument(documentId: string) {
    await api.deleteDocument(token, documentId);
    await onRefresh();
  }

  async function setDocumentScope(documentId: string, scope: "chat" | "global") {
    if (scope === "chat" && !selectedConversationId) return;
    await api.updateDocumentScope(token, documentId, { scope, chat_id: scope === "chat" ? selectedConversationId : null });
    await onRefresh();
  }

  return (
    <div className="library-page">
      <div className="mb-5">
        <p className="mb-1 text-xs font-medium text-muted">Library</p>
        <h1 className="text-2xl font-semibold">Knowledge Library</h1>
        <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">
          Notes and documents that MindMesh can search during conversations.
        </p>
      </div>

      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Notes", value: regularNotes.length, icon: BookOpenText },
          { label: "Documents", value: documents.length, icon: FileText },
          { label: "Media", value: media.length, icon: Image },
          { label: "Chats", value: conversations.length, icon: MessageSquare }
        ].map((item) => {
          const Icon = item.icon;
          return (
            <article key={item.label} className="metric-card flex items-center gap-3">
              <Icon size={17} className="text-muted" />
              <div>
                <p className="text-xl font-semibold">{item.value}</p>
                <p className="text-xs text-muted">{item.label}</p>
              </div>
            </article>
          );
        })}
      </div>

      <div className="mt-5">
        <div className="library-tabs" role="tablist" aria-label="Knowledge library sections">
          <button className={`library-tab ${activeTab === "notes" ? "library-tab-active" : ""}`} onClick={() => setActiveTab("notes")} role="tab" aria-selected={activeTab === "notes"}>
            <BookOpenText size={16} />
            Notes
          </button>
          <button className={`library-tab ${activeTab === "documents" ? "library-tab-active" : ""}`} onClick={() => setActiveTab("documents")} role="tab" aria-selected={activeTab === "documents"}>
            <FileText size={16} />
            Documents
          </button>
        </div>

        {activeTab === "notes" ? (
          <section className="library-card mt-4" role="tabpanel" aria-label="Notes">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-semibold">Notes</h2>
              <BookOpenText size={18} className="text-muted" />
            </div>
            <div className="space-y-2">
              {regularNotes.map((note) => (
                <div
                  key={note.id}
                  className="library-list-item"
                >
                  <button className="min-w-0 flex-1 text-left" onClick={() => onPreviewTargetChange({ type: "note", id: note.id })}>
                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                      <p className="truncate font-medium">{note.title}</p>
                      <span className="badge">{note.scope === "chat" ? "Chat" : "Global"}</span>
                    </div>
                    <p className="mt-1 text-xs text-muted">
                      {new Date(note.updated_at || note.created_at).toLocaleDateString()}
                      {note.tags.length ? ` - ${note.tags.slice(0, 3).join(", ")}` : ""}
                    </p>
                    <p className="mt-1 line-clamp-1 text-sm text-muted">{note.content}</p>
                  </button>
                  <div className="flex flex-wrap gap-2">
                    <button className="button-ghost h-8 px-2 text-xs" onClick={() => void setNoteScope(note.id, "global")} disabled={note.scope === "global"}>
                      <Globe2 size={14} />
                      Global
                    </button>
                    <button className="button-ghost h-8 px-2 text-xs" onClick={() => void setNoteScope(note.id, "chat")} disabled={!selectedConversationId || note.scope === "chat"}>
                      <MessageSquare size={14} />
                      Chat
                    </button>
                    <button className="button-ghost h-8 px-2 text-xs text-danger" onClick={() => void deleteNote(note.id)}>
                      <Trash2 size={14} />
                      Delete
                    </button>
                  </div>
                </div>
              ))}
              {!regularNotes.length && (
                <EmptyState
                  icon={<BookOpenText size={20} />}
                  title="No notes yet"
                  description="Create notes from the right panel to build a searchable personal memory."
                />
              )}
            </div>

            <details className="library-disclosure mt-5">
              <summary>Media references</summary>
              <div className="mt-4 grid gap-5 lg:grid-cols-[1fr_0.9fr]">
                <section>
                  <div className="mb-3 flex items-center gap-2">
                    <Image size={17} className="text-muted" />
                    <h3 className="text-sm font-semibold">Save reference</h3>
                  </div>
                  <form onSubmit={createMediaReference} className="space-y-2">
                    <input className="control" value={mediaTitle} onChange={(event) => setMediaTitle(event.target.value)} placeholder="Title" />
                    <input className="control" value={mediaUrl} onChange={(event) => setMediaUrl(event.target.value)} placeholder="URL or local path" />
                    <textarea className="control min-h-24 py-2" value={mediaDescription} onChange={(event) => setMediaDescription(event.target.value)} placeholder="Description" />
                    <button className="button-primary w-full" disabled={busy || !mediaTitle.trim() || !mediaUrl.trim()}>Save Media</button>
                  </form>
                </section>

                <section>
                  <div className="mb-3 flex items-center gap-2">
                    <Image size={18} className="text-muted" />
                    <h3 className="text-sm font-semibold">Saved media</h3>
                  </div>
                  <div className="space-y-2">
                    {media.slice(0, 4).map((item) => (
                      <article key={item.id} className="rounded-xl bg-elevated p-3">
                        <p className="truncate text-sm font-medium">{item.title}</p>
                        <p className="truncate text-xs text-muted">{item.source}</p>
                      </article>
                    ))}
                    {!media.length && (
                      <p className="rounded-xl bg-elevated p-3 text-sm text-muted">No media references saved.</p>
                    )}
                  </div>
                </section>
              </div>
            </details>
          </section>
        ) : (
          <section className="library-card mt-4" role="tabpanel" aria-label="Documents">
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="font-semibold">Documents</h2>
              <label className={`upload-action cursor-pointer ${busy ? "opacity-70" : ""}`} title="Upload documents">
                <span className="file-picker-icon h-8 w-8">
                  {busy ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
                </span>
                <span className="hidden text-sm font-medium sm:inline">{busy ? "Working..." : "Upload"}</span>
                <input className="hidden" type="file" accept=".pdf,.txt,.doc,.docx,.png,.jpg,.jpeg,.webp,.ppt,.pptx,image/*,text/plain,application/pdf" multiple onChange={uploadDocument} disabled={busy} />
              </label>
            </div>
            {uploadStatus.message && (
              <div className={`upload-status upload-status-${uploadStatus.state} mb-4`}>
                {uploadStatus.state === "loading" && <Loader2 size={16} className="animate-spin" />}
                <span>{uploadStatus.message}</span>
              </div>
            )}
            <div className="space-y-2">
              {documents.map((document) => (
                <div
                  key={document.document_id}
                  className="library-list-item"
                >
                  <button className="min-w-0 flex-1 text-left" onClick={() => onPreviewTargetChange({ type: "document", id: document.document_id })}>
                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                      <FileText size={18} className="shrink-0 text-muted" />
                      <p className="truncate text-sm font-medium">{document.file_name}</p>
                      <span className="badge">{document.scope === "chat" ? "Chat" : "Global"}</span>
                    </div>
                    <p className="mt-1 truncate text-xs text-muted">{document.minio_object_path}</p>
                    <p className="mt-1 text-xs text-muted">{document.chunk_count} chunks indexed</p>
                  </button>
                  <div className="flex flex-wrap gap-2">
                    <button className="button-ghost h-8 px-2 text-xs" onClick={() => void setDocumentScope(document.document_id, "global")} disabled={document.scope === "global"}>
                      <Globe2 size={14} />
                      Global
                    </button>
                    <button className="button-ghost h-8 px-2 text-xs" onClick={() => void setDocumentScope(document.document_id, "chat")} disabled={!selectedConversationId || document.scope === "chat"}>
                      <MessageSquare size={14} />
                      Chat
                    </button>
                    <button className="button-ghost h-8 px-2 text-xs text-danger" onClick={() => void deleteDocument(document.document_id)}>
                      <Trash2 size={14} />
                      Delete
                    </button>
                  </div>
                </div>
              ))}
              {!documents.length && (
                <EmptyState
                  icon={<FileText size={20} />}
                  title="No documents indexed"
                  description="Upload PDFs, text files, decks, docs, or images to make them available for retrieval."
                />
              )}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

function startUploadStatus(setUploadStatus: (state: UploadState) => void) {
  setUploadStatus({ state: "loading", message: "Preparing upload..." });
  return [
    window.setTimeout(() => setUploadStatus({ state: "loading", message: "Uploading document..." }), 350),
    window.setTimeout(() => setUploadStatus({ state: "loading", message: "Processing file..." }), 900),
    window.setTimeout(() => setUploadStatus({ state: "loading", message: "Indexing document..." }), 1500)
  ];
}

function clearUploadStatusTimers(timers: number[]) {
  timers.forEach((timer) => window.clearTimeout(timer));
}
