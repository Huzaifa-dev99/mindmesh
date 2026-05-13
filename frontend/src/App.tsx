import { useEffect, useRef, useState } from "react";
import { AppShell, type PageKey } from "./components/AppShell";
import { PrivacyLockscreen } from "./components/PrivacyLockscreen";
import { useMindMesh } from "./hooks/useMindMesh";
import { KnowledgeDashboard } from "./pages/KnowledgeDashboard";
import { ProductivityWorkspace } from "./pages/ProductivityWorkspace";
import type { PreviewTarget } from "./types";

const INACTIVITY_MS = Number(import.meta.env.VITE_INACTIVITY_MINUTES || 10) * 60 * 1000;
const LOCK_KEY = "mindmesh.sessionLocked";

export function App() {
  const state = useMindMesh();
  const [page, setPage] = useState<PageKey>("chats");
  const [chatSessionKey, setChatSessionKey] = useState(0);
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [previewTarget, setPreviewTarget] = useState<PreviewTarget | null>(null);
  const [theme, setTheme] = useState<"dark" | "light">(() => (localStorage.getItem("mindmesh.theme") as "dark" | "light") || "dark");
  const [sessionLocked, setSessionLocked] = useState(() => localStorage.getItem(LOCK_KEY) === "true");
  const inactivityTimer = useRef<number | null>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("mindmesh.theme", theme);
  }, [theme]);

  useEffect(() => {
    if (!state.authenticated) return;

    const resetTimer = () => {
      if (inactivityTimer.current) window.clearTimeout(inactivityTimer.current);
      inactivityTimer.current = window.setTimeout(() => lockWorkspace(), INACTIVITY_MS);
    };

    const events = ["mousemove", "mousedown", "keydown", "scroll", "touchstart"];
    events.forEach((eventName) => window.addEventListener(eventName, resetTimer, { passive: true }));
    resetTimer();

    return () => {
      if (inactivityTimer.current) window.clearTimeout(inactivityTimer.current);
      events.forEach((eventName) => window.removeEventListener(eventName, resetTimer));
    };
  }, [state.authenticated]);

  function lockWorkspace() {
    localStorage.setItem(LOCK_KEY, "true");
    setSessionLocked(true);
  }

  function unlockWorkspace() {
    localStorage.removeItem(LOCK_KEY);
    setSessionLocked(false);
  }

  function startNewChat() {
    setPage("chats");
    setSelectedConversationId(null);
    setChatSessionKey((value) => value + 1);
  }

  function selectConversation(conversationId: string) {
    setPage("chats");
    setSelectedConversationId(conversationId);
    setChatSessionKey((value) => value + 1);
  }

  if (!state.authenticated || !state.user || !state.token) {
    return <PrivacyLockscreen onAuthenticated={state.setSession} />;
  }

  if (sessionLocked) {
    return <PrivacyLockscreen mode="session" onUnlock={unlockWorkspace} />;
  }

  return (
    <AppShell
      page={page}
      onPage={setPage}
      notes={state.notes}
      documents={state.documents}
      journals={state.journals}
      storedTags={state.tags}
      conversations={state.conversations}
      selectedConversationId={selectedConversationId}
      token={state.token}
      theme={theme}
      onThemeChange={setTheme}
      onRefresh={state.refresh}
      onLock={lockWorkspace}
      onNewChat={startNewChat}
      onSelectConversation={selectConversation}
      previewTarget={previewTarget}
      onPreviewTargetChange={setPreviewTarget}
    >
      {state.error && (
        <div className="fixed left-1/2 top-4 z-50 -translate-x-1/2 rounded-xl border border-danger/20 bg-danger/10 px-4 py-3 text-sm text-danger shadow-panel">
          {state.error}
        </div>
      )}

      {page === "library" ? (
        <KnowledgeDashboard
          journals={state.journals}
          notes={state.notes}
          documents={state.documents}
          conversations={state.conversations}
          token={state.token}
          onRefresh={state.refresh}
          onPreviewTargetChange={setPreviewTarget}
        />
      ) : (
        <ProductivityWorkspace
          key={chatSessionKey}
          token={state.token}
          conversationId={selectedConversationId}
          onConversationChange={setSelectedConversationId}
          onRefresh={state.refresh}
          onPreviewTargetChange={setPreviewTarget}
        />
      )}
    </AppShell>
  );
}
