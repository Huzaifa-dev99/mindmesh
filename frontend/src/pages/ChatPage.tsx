import { SendHorizontal } from "lucide-react";
import { FormEvent, useState } from "react";
import { SectionHeader } from "../components/SectionHeader";
import { api } from "../lib/api";
import type { ChatMessage, SearchResult } from "../types";

type Props = {
  token: string;
};

export function ChatPage({ token }: Props) {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [citations, setCitations] = useState<SearchResult[]>([]);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!message.trim()) return;
    const nextMessage = message;
    setMessage("");
    setMessages((current) => [...current, { role: "user", content: nextMessage }]);
    setBusy(true);
    try {
      const response = await api.chat(token, nextMessage, conversationId);
      setConversationId(response.conversation_id);
      setCitations(response.citations);
      setMessages((current) => [...current, { role: "assistant", content: response.answer }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <SectionHeader eyebrow="RAG Chat" title="Talk to your knowledge" description="Retrieve relevant memories, inject them as context, and answer through the Groq provider." />
      <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
        <div className="glass-panel flex min-h-[620px] flex-col rounded-2xl p-4">
          <div className="flex-1 space-y-4 overflow-y-auto pr-1">
            {messages.map((item, index) => (
              <div key={`${item.role}-${index}`} className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-6 ${item.role === "user" ? "ml-auto bg-mint text-ink-950" : "bg-white/[0.07] text-white/70"}`}>
                {item.content}
              </div>
            ))}
            {!messages.length && <p className="p-8 text-center text-sm text-white/42">Ask about themes, memories, decisions, or anything you have written.</p>}
          </div>
          <form onSubmit={submit} className="mt-4 flex gap-3">
            <input className="control" placeholder="Ask MindMesh..." value={message} onChange={(event) => setMessage(event.target.value)} />
            <button className="button-primary w-14" disabled={busy}>
              <SendHorizontal size={17} />
            </button>
          </form>
        </div>

        <aside className="glass-panel rounded-2xl p-5">
          <h2 className="mb-4 font-semibold">Retrieved context</h2>
          <div className="space-y-3">
            {citations.map((citation) => (
              <div key={`${citation.source_id}-${citation.score}`} className="rounded-xl border border-white/10 bg-ink-950/35 p-3">
                <p className="text-sm font-medium">{citation.title || citation.source_type}</p>
                <p className="mt-2 line-clamp-4 text-xs leading-5 text-white/48">{citation.snippet}</p>
              </div>
            ))}
            {!citations.length && <p className="text-sm text-white/45">Context will appear after your first RAG question.</p>}
          </div>
        </aside>
      </div>
    </section>
  );
}
