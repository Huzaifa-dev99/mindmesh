import { Activity, BookOpenText, FileText, Image, Lightbulb, MessageSquare, Upload } from "lucide-react";
import { ChangeEvent, FormEvent, useMemo, useState } from "react";
import { api } from "../lib/api";
import type { ConversationSummary, DocumentResource, Journal, Note, PreviewTarget } from "../types";

type Props = {
  journals: Journal[];
  notes: Note[];
  documents: DocumentResource[];
  conversations: ConversationSummary[];
  token: string;
  onRefresh: () => Promise<void>;
  onPreviewTargetChange: (target: PreviewTarget | null) => void;
};

export function KnowledgeDashboard({ journals, notes, documents, conversations, token, onRefresh, onPreviewTargetChange }: Props) {
  const [mediaTitle, setMediaTitle] = useState("");
  const [mediaUrl, setMediaUrl] = useState("");
  const [mediaDescription, setMediaDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const media = useMemo(() => notes.filter((note) => note.tags.includes("media")), [notes]);
  const regularNotes = useMemo(() => notes.filter((note) => !note.tags.includes("media")), [notes]);
  const themes = useMemo(() => {
    const tagCounts = [...notes, ...journals].reduce<Record<string, number>>((counts, item) => {
      item.tags.forEach((tag) => {
        counts[tag] = (counts[tag] || 0) + 1;
      });
      return counts;
    }, {});
    return Object.entries(tagCounts)
      .sort(([, left], [, right]) => right - left)
      .slice(0, 6);
  }, [journals, notes]);
  const recentActivity = useMemo(
    () =>
      [
        ...notes.map((note) => ({ id: note.id, label: `Saved note: ${note.title}`, date: note.updated_at || note.created_at })),
        ...journals.map((journal) => ({ id: journal.id, label: `Saved journal: ${journal.title || "Untitled journal"}`, date: journal.created_at })),
        ...conversations.map((conversation) => ({
          id: conversation.id,
          label: `Chat: ${conversation.title || "Untitled chat"}`,
          date: conversation.last_message_at || conversation.created_at
        }))
      ]
        .sort((left, right) => new Date(right.date).getTime() - new Date(left.date).getTime())
        .slice(0, 6),
    [conversations, journals, notes]
  );

  async function uploadDocument(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    setBusy(true);
    try {
      for (const file of files) {
        await api.uploadDocument(token, file, { scope: "global" });
      }
      await onRefresh();
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

  return (
    <div className="library-page">
      <div className="mb-6">
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-muted">Library</p>
        <h1 className="text-3xl font-semibold tracking-tight">Knowledge Library</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Notes, imported documents, media references, insights, and chat relationships in one organized view.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Notes", value: regularNotes.length, icon: BookOpenText },
          { label: "Documents", value: documents.length, icon: FileText },
          { label: "Media", value: media.length, icon: Image },
          { label: "Chats", value: conversations.length, icon: MessageSquare }
        ].map((item) => {
          const Icon = item.icon;
          return (
            <article key={item.label} className="metric-card">
              <Icon size={18} className="text-muted" />
              <p className="mt-4 text-3xl font-semibold">{item.value}</p>
              <p className="text-sm text-muted">{item.label}</p>
            </article>
          );
        })}
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_0.9fr]">
        <section className="library-card">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold">Notes</h2>
            <BookOpenText size={18} className="text-muted" />
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {regularNotes.map((note) => (
              <button
                key={note.id}
                className="rounded-xl bg-elevated p-4 text-left transition hover:-translate-y-0.5 hover:bg-panel"
                onClick={() => onPreviewTargetChange({ type: "note", id: note.id })}
              >
                <p className="truncate font-medium">{note.title}</p>
                <p className="mt-1 text-xs text-muted">
                  {new Date(note.updated_at || note.created_at).toLocaleDateString()}
                  {note.tags.length ? ` · ${note.tags.slice(0, 3).join(", ")}` : ""}
                </p>
                <p className="mt-2 line-clamp-3 text-sm leading-6 text-muted">{note.content}</p>
              </button>
            ))}
            {!regularNotes.length && <p className="text-sm text-muted">Create notes from the right panel to build your library.</p>}
          </div>
        </section>

        <section className="library-card">
          <div className="mb-4 flex items-center gap-2">
            <Lightbulb size={18} className="text-muted" />
            <h2 className="font-semibold">Insights</h2>
          </div>
          <div className="space-y-2">
            {themes.map(([theme, count]) => (
              <div key={theme} className="flex items-center justify-between rounded-xl bg-elevated p-3">
                <span className="text-sm">{theme}</span>
                <span className="text-xs text-muted">{count} {count === 1 ? "memory" : "memories"}</span>
              </div>
            ))}
            {!themes.length && <p className="rounded-xl bg-elevated p-4 text-sm text-muted">Tag notes or journals to generate topic insights.</p>}
          </div>
        </section>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        <section className="library-card xl:col-span-2">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="font-semibold">Documents</h2>
            <label className="button-ghost cursor-pointer">
              <Upload size={16} />
              {busy ? "Working..." : "Upload Document"}
              <input className="hidden" type="file" accept=".pdf,.txt,.doc,.docx,.png,.jpg,.jpeg,.webp,.ppt,.pptx,image/*,text/plain,application/pdf" multiple onChange={uploadDocument} disabled={busy} />
            </label>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {documents.map((document) => (
              <button
                key={document.document_id}
                className="rounded-xl border border-border bg-elevated p-4 text-left transition hover:-translate-y-0.5 hover:bg-panel"
                onClick={() => onPreviewTargetChange({ type: "document", id: document.document_id })}
              >
                <FileText size={18} className="text-muted" />
                <p className="mt-3 truncate text-sm font-medium">{document.file_name}</p>
                <p className="mt-1 truncate text-xs text-muted">{document.minio_object_path}</p>
                <p className="mt-1 text-xs text-muted">{document.chunk_count} chunks indexed</p>
              </button>
            ))}
            {!documents.length && <p className="rounded-xl bg-elevated p-4 text-sm text-muted">Upload documents to make them searchable by MindMesh.</p>}
          </div>
        </section>

        <section className="library-card">
          <div className="mb-4 flex items-center gap-2">
            <Image size={18} className="text-muted" />
            <h2 className="font-semibold">Media References</h2>
          </div>
          <form onSubmit={createMediaReference} className="space-y-2">
            <input className="control" value={mediaTitle} onChange={(event) => setMediaTitle(event.target.value)} placeholder="Title" />
            <input className="control" value={mediaUrl} onChange={(event) => setMediaUrl(event.target.value)} placeholder="URL or local path" />
            <textarea className="control min-h-24" value={mediaDescription} onChange={(event) => setMediaDescription(event.target.value)} placeholder="Description" />
            <button className="button-primary w-full" disabled={busy || !mediaTitle.trim() || !mediaUrl.trim()}>Save Media</button>
          </form>
          <div className="mt-4 space-y-2">
            {media.slice(0, 4).map((item) => (
              <article key={item.id} className="rounded-xl bg-elevated p-3">
                <p className="truncate text-sm font-medium">{item.title}</p>
                <p className="truncate text-xs text-muted">{item.source}</p>
              </article>
            ))}
          </div>
        </section>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="library-card">
          <div className="mb-4 flex items-center gap-2">
            <MessageSquare size={18} className="text-muted" />
            <h2 className="font-semibold">Recent Chats</h2>
          </div>
          <div className="space-y-2">
            {conversations.slice(0, 5).map((conversation) => (
              <article key={conversation.id} className="rounded-xl bg-elevated p-3">
                <p className="truncate text-sm font-medium">{conversation.title || "Untitled chat"}</p>
                <p className="text-xs text-muted">{conversation.message_count} messages</p>
              </article>
            ))}
            {!conversations.length && <p className="rounded-xl bg-elevated p-4 text-sm text-muted">Chats will appear here after you talk with MindMesh.</p>}
          </div>
        </section>

        <section className="library-card">
          <div className="mb-4 flex items-center gap-2">
            <Activity size={18} className="text-muted" />
            <h2 className="font-semibold">Activity</h2>
          </div>
          {recentActivity.map((item) => (
            <div key={item.id} className="relative border-l border-border pb-5 pl-4 last:pb-0">
              <span className="absolute -left-1 top-1 h-2 w-2 rounded-full bg-foreground" />
              <p className="text-sm">{item.label}</p>
              <p className="text-xs text-muted">{new Date(item.date).toLocaleDateString()}</p>
            </div>
          ))}
          {!recentActivity.length && <p className="rounded-xl bg-elevated p-4 text-sm text-muted">No activity yet.</p>}
        </section>
      </div>
    </div>
  );
}
