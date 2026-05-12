import { useState } from "react";
import { AppShell, type PageKey } from "./components/AppShell";
import { AuthView } from "./components/AuthView";
import { useMindMesh } from "./hooks/useMindMesh";
import { ChatPage } from "./pages/ChatPage";
import { Dashboard } from "./pages/Dashboard";
import { JournalPage } from "./pages/JournalPage";
import { NotesPage } from "./pages/NotesPage";
import { SearchPage } from "./pages/SearchPage";
import { SettingsPage } from "./pages/SettingsPage";

export function App() {
  const state = useMindMesh();
  const [page, setPage] = useState<PageKey>("dashboard");

  if (!state.authenticated || !state.user || !state.token) {
    return <AuthView onSession={state.setSession} />;
  }

  return (
    <AppShell page={page} onPage={setPage} user={state.user} onLogout={state.logout}>
      {state.error && (
        <div className="mb-5 rounded-xl border border-coral/30 bg-coral/10 px-4 py-3 text-sm text-coral">
          {state.error}
        </div>
      )}

      {page === "dashboard" && (
        <Dashboard journals={state.journals} notes={state.notes} tagCount={state.tags.length} />
      )}
      {page === "journal" && (
        <JournalPage token={state.token} journals={state.journals} onRefresh={state.refresh} />
      )}
      {page === "notes" && (
        <NotesPage token={state.token} notes={state.notes} onRefresh={state.refresh} />
      )}
      {page === "chat" && <ChatPage token={state.token} />}
      {page === "search" && <SearchPage token={state.token} />}
      {page === "settings" && <SettingsPage user={state.user} />}
    </AppShell>
  );
}
