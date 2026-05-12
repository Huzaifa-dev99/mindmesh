import { useState } from "react";
import { AppShell, type PageKey } from "./components/AppShell";
import { PrivacyLockscreen } from "./components/PrivacyLockscreen";
import { useMindMesh } from "./hooks/useMindMesh";
import { KnowledgeDashboard } from "./pages/KnowledgeDashboard";
import { ProductivityWorkspace } from "./pages/ProductivityWorkspace";

export function App() {
  const state = useMindMesh();
  const [page, setPage] = useState<PageKey>("chats");

  if (!state.authenticated || !state.user || !state.token) {
    return <PrivacyLockscreen onUnlock={state.setSession} />;
  }

  return (
    <AppShell page={page} onPage={setPage} notes={state.notes} journals={state.journals}>
      {state.error && (
        <div className="fixed left-1/2 top-4 z-50 -translate-x-1/2 rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200 shadow-panel">
          {state.error}
        </div>
      )}

      {page === "dashboard" ? (
        <KnowledgeDashboard journals={state.journals} notes={state.notes} />
      ) : (
        <ProductivityWorkspace
          token={state.token}
          mode={page}
          journals={state.journals}
          notes={state.notes}
          onRefresh={state.refresh}
        />
      )}
    </AppShell>
  );
}
