import { Brain, LockKeyhole, ShieldCheck } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import type { User } from "../types";

const LOCAL_EMAIL = import.meta.env.VITE_SINGLE_USER_EMAIL || "local@mindmesh.app";
const LOCAL_PASSWORD = import.meta.env.VITE_SINGLE_USER_PASSWORD || "mindmesh-local-workspace-password";
const PIN_KEY = "mindmesh.workspace.pin";
const LEGACY_PIN_KEY = "mindmesh.pin";
const CONFIGURED_PIN = import.meta.env.VITE_WORKSPACE_PIN || "";

type Props = {
  mode?: "initial" | "session";
  onAuthenticated?: (token: string, user: User) => void;
  onUnlock?: () => void;
};

export function hasWorkspacePin() {
  return Boolean(readWorkspacePin());
}

function readWorkspacePin() {
  const localPin = localStorage.getItem(PIN_KEY);
  if (localPin) return localPin;

  const legacyPin = localStorage.getItem(LEGACY_PIN_KEY);
  if (legacyPin) {
    localStorage.setItem(PIN_KEY, legacyPin);
    localStorage.removeItem(LEGACY_PIN_KEY);
    return legacyPin;
  }

  return CONFIGURED_PIN;
}

export function PrivacyLockscreen({ mode = "initial", onAuthenticated, onUnlock }: Props) {
  const [pin, setPin] = useState("");
  const [confirmPin, setConfirmPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [unlocking, setUnlocking] = useState(false);
  const [storedPin, setStoredPin] = useState(() => readWorkspacePin());
  const shouldCreatePin = !storedPin;

  useEffect(() => {
    const refreshPin = () => setStoredPin(readWorkspacePin());
    window.addEventListener("storage", refreshPin);
    window.addEventListener("focus", refreshPin);
    return () => {
      window.removeEventListener("storage", refreshPin);
      window.removeEventListener("focus", refreshPin);
    };
  }, []);

  const title = useMemo(() => {
    if (shouldCreatePin) return "Create Workspace PIN";
    return mode === "session" ? "Workspace Locked" : "Unlock Workspace";
  }, [mode, shouldCreatePin]);

  async function ensureLocalSession() {
    let session;
    try {
      session = await api.login(LOCAL_EMAIL, LOCAL_PASSWORD);
    } catch {
      await api.register({
        email: LOCAL_EMAIL,
        username: "local-user",
        full_name: "Local Workspace",
        password: LOCAL_PASSWORD
      });
      session = await api.login(LOCAL_EMAIL, LOCAL_PASSWORD);
    }
    onAuthenticated?.(session.access_token, session.user);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (shouldCreatePin) {
      if (pin.length < 4) {
        setError("Use at least 4 digits or characters.");
        return;
      }
      if (pin !== confirmPin) {
        setError("PIN confirmation does not match.");
        return;
      }
      localStorage.setItem(PIN_KEY, pin);
      setStoredPin(pin);
    } else if (pin !== storedPin) {
      setError("PIN did not match this workspace.");
      return;
    }

    setUnlocking(true);
    try {
      if (mode === "session") {
        onUnlock?.();
      } else {
        await ensureLocalSession();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not unlock workspace");
    } finally {
      setUnlocking(false);
    }
  }

  return (
    <main className="lockscreen min-h-screen text-foreground">
      <section className="lock-card">
        <div className="mx-auto mb-7 grid h-14 w-14 place-items-center rounded-2xl bg-foreground text-app shadow-sm">
          <Brain size={27} />
        </div>
        <div className="mb-7 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">MindMesh</h1>
          <p className="mt-2 text-sm leading-6 text-muted">{title}</p>
        </div>

        <form onSubmit={submit} className="space-y-3">
          <input
            className="control h-12 text-center text-lg tracking-[0.35em]"
            value={pin}
            onChange={(event) => setPin(event.target.value)}
            placeholder="PIN"
            type="password"
            autoFocus
          />
          {shouldCreatePin && (
            <input
              className="control h-12 text-center text-lg tracking-[0.35em]"
              value={confirmPin}
              onChange={(event) => setConfirmPin(event.target.value)}
              placeholder="Confirm"
              type="password"
            />
          )}
          {error && <p className="rounded-xl border border-danger/20 bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>}
          <button className="button-primary h-11 w-full" disabled={unlocking}>
            <LockKeyhole size={16} />
            {unlocking ? "Unlocking..." : shouldCreatePin ? "Create PIN" : "Unlock Workspace"}
          </button>
        </form>

        <div className="mt-5 flex items-center justify-center gap-2 text-xs text-muted">
          <ShieldCheck size={14} />
          Local-only privacy lock. No signup required.
        </div>
      </section>
    </main>
  );
}
