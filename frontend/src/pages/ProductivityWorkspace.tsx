import { FormEvent, useEffect, useRef, useState } from "react";
import { Bot, SendHorizontal, UserRound } from "lucide-react";
import { api } from "../lib/api";
import type { AIModel, ChatMessage, PreviewTarget, SearchResult } from "../types";

type Props = {
  token: string;
  conversationId: string | null;
  onConversationChange: (conversationId: string) => void;
  onRefresh: () => Promise<void>;
  onPreviewTargetChange: (target: PreviewTarget | null) => void;
};

const welcomeMessage: ChatMessage = {
  role: "assistant",
  content: "Welcome back. Ask me to search your notes, summarize a thread, or organize your knowledge."
};

export function ProductivityWorkspace({ token, conversationId, onConversationChange, onRefresh, onPreviewTargetChange }: Props) {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([welcomeMessage]);
  const [busy, setBusy] = useState(false);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [models, setModels] = useState<AIModel[]>([]);
  const [provider, setProvider] = useState(localStorage.getItem("mindmesh.provider") || "Groq");
  const [selectedModelId, setSelectedModelId] = useState(localStorage.getItem("mindmesh.currentModel") || localStorage.getItem("mindmesh.defaultModel") || "");
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const selectedModel = models.find((model) => model.id === selectedModelId);

  useEffect(() => {
    api.aiConfig(token).then((config) => {
      if (!config) return api.aiModels(token, provider).then(setModels);
      setProvider(config.provider);
      setModels(config.models);
      const nextModel = selectedModelId || config.default_model_id || config.models[0]?.id || "";
      setSelectedModelId(nextModel);
      if (nextModel) localStorage.setItem("mindmesh.currentModel", nextModel);
    }).catch(() => undefined);
  }, [provider, selectedModelId, token]);

  useEffect(() => {
    if (!conversationId) return;
    api.getChatModel(token, conversationId).then((selection) => {
      if (selection.provider) setProvider(selection.provider);
      if (selection.model_id) {
        setSelectedModelId(selection.model_id);
        localStorage.setItem("mindmesh.currentModel", selection.model_id);
      }
    }).catch(() => undefined);
  }, [conversationId, token]);

  useEffect(() => {
    if (!conversationId) {
      setMessages([welcomeMessage]);
      return;
    }

    let cancelled = false;
    setLoadingConversation(true);
    api
      .conversation(token, conversationId)
      .then((conversation) => {
        if (!cancelled) {
          setMessages(conversation.messages.length ? conversation.messages : [welcomeMessage]);
        }
      })
      .catch(() => {
        if (!cancelled) setMessages([{ role: "assistant", content: "I couldn't open that chat. It may have been deleted." }]);
      })
      .finally(() => {
        if (!cancelled) setLoadingConversation(false);
      });

    return () => {
      cancelled = true;
    };
  }, [conversationId, token]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function submitChat(event?: FormEvent) {
    event?.preventDefault();
    const prompt = message;
    if (!prompt.trim()) return;
    setMessage("");
    setMessages((current) => [...current, { role: "user", content: prompt }]);
    setBusy(true);
    try {
      const response = await api.chat(token, prompt, conversationId, localStorage.getItem("mindmesh.tavilyApiKey"), { provider, modelId: selectedModelId });
      onConversationChange(response.conversation_id);
      if (selectedModelId) {
        await api.setChatModel(token, response.conversation_id, { provider, model_id: selectedModelId }).catch(() => undefined);
      }
      setMessages((current) => [...current, { role: "assistant", content: response.answer, citations: response.citations.slice(0, 5) }]);
      await onRefresh();
    } finally {
      setBusy(false);
    }
  }

  async function changeModel(modelId: string) {
    setSelectedModelId(modelId);
    localStorage.setItem("mindmesh.currentModel", modelId);
    if (conversationId) {
      await api.setChatModel(token, conversationId, { provider, model_id: modelId }).catch(() => undefined);
    }
  }

  return (
    <div className="chat-layout">
      <div ref={scrollRef} className="chat-scroll">
        <div className="mx-auto w-full max-w-3xl px-4 py-6">
          <div className="mb-6">
            <h1 className="text-2xl font-semibold tracking-tight">Personal Knowledge Chat</h1>
            <p className="mt-1 text-sm text-muted">Clear, focused conversations grounded in your local memory.</p>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <select className="control max-w-xs" value={selectedModelId} onChange={(event) => void changeModel(event.target.value)} aria-label="Select chat model">
                {models.map((model) => <option key={model.id} value={model.id}>{model.display_name}</option>)}
              </select>
              {selectedModel?.capabilities.map((capability) => <span key={capability} className="badge">{capability}</span>)}
            </div>
            {selectedModel && !selectedModel.supports_vision && (
              <p className="mt-2 text-xs text-muted">This model does not support multimodal input. Image documents require a Vision or Multimodal model.</p>
            )}
          </div>

          <div className="space-y-5">
            {loadingConversation && <p className="text-sm text-muted">Opening chat...</p>}
            {messages.map((item, index) => (
              <article key={`${item.role}-${index}`} className={`message-row ${item.role === "user" ? "message-row-user" : ""}`}>
                <div className={`message-avatar ${item.role === "user" ? "message-avatar-user" : ""}`}>
                  {item.role === "user" ? <UserRound size={16} /> : <Bot size={16} />}
                </div>
                <div className={`message-bubble ${item.role === "user" ? "message-bubble-user" : ""}`}>
                  {item.content}
                  {item.role === "assistant" && item.citations && item.citations.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {item.citations.slice(0, 5).map((citation, citationIndex) => (
                        <button
                          key={`${citation.source_type}-${citation.source_id}-${citationIndex}`}
                          className="reference-pill"
                          onClick={() => openCitation(citation, onPreviewTargetChange)}
                          type="button"
                          title={citation.title || citation.source_type}
                        >
                          <span>{citationIndex + 1}</span>
                          {citation.title || citation.source_type}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>

      <div className="composer-wrap">
        <form onSubmit={submitChat} className="composer">
          <textarea
            className="composer-input"
            placeholder="Message MindMesh..."
            value={message}
            rows={1}
            onChange={(event) => setMessage(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void submitChat();
              }
            }}
          />
          <div className="flex items-center justify-between pt-2">
            <span className="px-2 text-xs text-muted">Shift + Enter for a new line</span>
            <button className="button-primary h-9 w-9 rounded-full p-0" disabled={busy || !message.trim()} aria-label="Send message">
              <SendHorizontal size={16} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function openCitation(citation: SearchResult, onPreviewTargetChange: (target: PreviewTarget | null) => void) {
  if (citation.source_type === "web") {
    const url = citation.metadata?.url;
    if (typeof url === "string") window.open(url, "_blank", "noopener,noreferrer");
    return;
  }
  if (citation.source_type === "document") {
    const documentId = typeof citation.metadata?.document_id === "string" ? citation.metadata.document_id : citation.source_id;
    onPreviewTargetChange({ type: "document", id: documentId });
    return;
  }
  if (citation.source_type === "note") {
    onPreviewTargetChange({ type: "note", id: citation.source_id });
  }
}
