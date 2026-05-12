import { FormEvent, useState } from "react";
import {
  Bot,
  Clock3,
  FilePlus2,
  Mic,
  Paperclip,
  Pencil,
  SendHorizontal,
  Sparkles,
  Tag,
  UserRound
} from "lucide-react";
import { api } from "../lib/api";
import type { ChatMessage, Journal, Note, SearchResult } from "../types";

type Props = {
  token: string;
  mode: "chats" | "notes" | "media" | "documents" | "insights";
  journals: Journal[];
  notes: Note[];
  onRefresh: () => Promise<void>;
};

const suggestions = [
  "Summarize my latest journal themes",
  "Find notes about memory retrieval",
  "Turn today into a project plan",
  "What topics keep repeating?"
];

export function ProductivityWorkspace({ token, mode, journals, notes, onRefresh }: Props) {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [title, setTitle] = useState("Personal Knowledge Chat");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Welcome back. I can search your journals and notes, summarize documents, and help organize your personal knowledge."
    }
  ]);
  const [citations, setCitations] = useState<SearchResult[]>([]);
  const [noteTitle, setNoteTitle] = useState("");
  const [noteContent, setNoteContent] = useState("");
  const [busy, setBusy] = useState(false);

  async function submitChat(event?: FormEvent, override?: string) {
    event?.preventDefault();
    const prompt = override || message;
    if (!prompt.trim()) return;
    setMessage("");
    setMessages((current) => [...current, { role: "user", content: prompt }]);
    setBusy(true);
    try {
      const response = await api.chat(token, prompt, conversationId);
      setConversationId(response.conversation_id);
      setCitations(response.citations);
      setMessages((current) => [...current, { role: "assistant", content: response.answer }]);
    } finally {
      setBusy(false);
    }
  }

  async function createNote(event: FormEvent) {
    event.preventDefault();
    if (!noteTitle.trim() || !noteContent.trim()) return;
    await api.createNote(token, {
      title: noteTitle,
      content: noteContent,
      tags: ["chat-context", mode],
      source: "Workspace"
    });
    setNoteTitle("");
    setNoteContent("");
    await onRefresh();
  }

  const pageCopy = {
    chats: "Ask, retrieve, summarize, and create from your private memory.",
    notes: "Draft and connect notes to the active conversation.",
    media: "Preview image and media context linked to conversations.",
    documents: "Attach PDFs, docs, and text files for AI-assisted reading.",
    insights: "Review generated themes, tags, and knowledge patterns."
  }[mode];

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex h-16 items-center justify-between border-b border-border px-5">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <input
              className="max-w-[32rem] bg-transparent text-lg font-semibold outline-none"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
            <Pencil size={15} className="text-muted" />
          </div>
          <p className="text-xs text-muted">{pageCopy}</p>
        </div>
        <div className="hidden items-center gap-2 md:flex">
          <span className="badge"><Clock3 size={13} /> Live</span>
          <span className="badge"><Tag size={13} /> personal-rag</span>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col px-4 py-6">
        <div className="mb-5 rounded-2xl border border-border bg-panel p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-medium">
            <Sparkles size={16} className="text-accent" />
            Suggested workflows
          </div>
          <div className="grid gap-2 md:grid-cols-2">
            {suggestions.map((item) => (
              <button key={item} onClick={() => void submitChat(undefined, item)} className="rounded-xl border border-border bg-elevated px-3 py-3 text-left text-sm text-soft hover:border-foreground/20">
                {item}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto pb-6">
          {messages.map((item, index) => (
            <article key={`${item.role}-${index}`} className={`flex gap-3 ${item.role === "user" ? "justify-end" : ""}`}>
              {item.role === "assistant" && (
                <div className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-panel text-soft">
                  <Bot size={17} />
                </div>
              )}
              <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm ${item.role === "user" ? "bg-foreground text-app" : "border border-border bg-panel text-soft"}`}>
                {item.content}
              </div>
              {item.role === "user" && (
                <div className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-foreground text-app">
                  <UserRound size={17} />
                </div>
              )}
            </article>
          ))}
        </div>

        {citations.length > 0 && (
          <div className="mb-4 flex gap-2 overflow-x-auto pb-1">
            {citations.map((citation) => (
              <div key={`${citation.source_id}-${citation.score}`} className="min-w-56 rounded-xl border border-border bg-panel p-3">
                <p className="truncate text-sm font-medium">{citation.title || citation.source_type}</p>
                <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted">{citation.snippet}</p>
              </div>
            ))}
          </div>
        )}

        {mode === "notes" && (
          <form onSubmit={createNote} className="mb-4 rounded-2xl border border-border bg-panel p-3">
            <input className="control mb-2" placeholder="Note title" value={noteTitle} onChange={(event) => setNoteTitle(event.target.value)} />
            <textarea className="control min-h-24" placeholder="Write a contextual note..." value={noteContent} onChange={(event) => setNoteContent(event.target.value)} />
            <button className="button-ghost mt-2"><FilePlus2 size={15} /> Save note</button>
          </form>
        )}

        <form onSubmit={submitChat} className="sticky bottom-4 rounded-[1.65rem] border border-border bg-elevated p-3 shadow-panel">
          <textarea
            className="min-h-12 max-h-40 w-full resize-none bg-transparent px-2 py-2 text-sm leading-6 text-foreground outline-none placeholder:text-muted"
            placeholder="Message MindMesh..."
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void submitChat();
              }
            }}
          />
          <div className="flex items-center justify-between border-t border-border pt-2">
            <div className="flex gap-1">
              <button type="button" className="icon-button"><Paperclip size={17} /></button>
              <button type="button" className="icon-button"><FilePlus2 size={17} /></button>
              <button type="button" className="icon-button"><Mic size={17} /></button>
            </div>
            <button className="button-primary h-9 w-9 rounded-full p-0" disabled={busy || !message.trim()}>
              <SendHorizontal size={16} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
