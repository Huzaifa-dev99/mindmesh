import { Brain, Fingerprint, LockKeyhole } from "lucide-react";
import { FormEvent, useState } from "react";
import { api } from "../lib/api";
import type { User } from "../types";

const WORKSPACE_PIN = import.meta.env.VITE_WORKSPACE_PIN || "0000";
const LOCAL_EMAIL = import.meta.env.VITE_SINGLE_USER_EMAIL || "local@mindmesh.local";
const LOCAL_PASSWORD = import.meta.env.VITE_SINGLE_USER_PASSWORD || "mindmesh-local-workspace-password";

type Props = {
  onUnlock: (token: string, user: User) => void;
};

export function PrivacyLockscreen({ onUnlock }: Props) {
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [unlocking, setUnlocking] = useState(false);

  async function unlock(event?: FormEvent) {
    event?.preventDefault();
    setError(null);
    if (pin !== WORKSPACE_PIN) {
      setError("Passcode did not match this local workspace.");
      return;
    }

    setUnlocking(true);
    try {
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
      onUnlock(session.access_token, session.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not unlock workspace");
    } finally {
      setUnlocking(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center overflow-hidden px-6 py-10 text-foreground">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_50%_0%,rgba(255,255,255,0.10),transparent_32rem),linear-gradient(135deg,#0b0c0f,#17191f_46%,#0f1115)]" />
      <div className="absolute left-1/2 top-1/2 -z-10 h-[34rem] w-[34rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/[0.035] blur-3xl" />

      <section className="w-full max-w-md rounded-[2rem] border border-white/10 bg-[#111318]/80 p-8 shadow-[0_30px_120px_rgba(0,0,0,0.45)] backdrop-blur-2xl">
        <div className="mx-auto mb-8 grid h-16 w-16 place-items-center rounded-2xl border border-white/10 bg-white/[0.06] text-white">
          <Brain size={30} />
        </div>
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-semibold tracking-tight">MindMesh</h1>
          <p className="mt-3 text-sm leading-6 text-muted">
            Private local workspace. Your journals, notes, and retrieval context stay on your machine.
          </p>
        </div>

        <form onSubmit={unlock} className="space-y-4">
          <label className="block text-xs font-medium uppercase tracking-[0.18em] text-muted">Workspace Passcode</label>
          <input
            className="control h-[3.25rem] text-center text-lg tracking-[0.45em]"
            value={pin}
            onChange={(event) => setPin(event.target.value)}
            placeholder="0000"
            type="password"
            autoFocus
          />
          {error && <p className="rounded-xl border border-red-400/20 bg-red-400/10 px-3 py-2 text-sm text-red-200">{error}</p>}
          <button className="button-primary h-12 w-full" disabled={unlocking}>
            <LockKeyhole size={17} />
            {unlocking ? "Unlocking..." : "Unlock Workspace"}
          </button>
        </form>

        <button type="button" onClick={() => void unlock()} className="button-ghost mt-3 h-12 w-full">
          <Fingerprint size={18} />
          Use local quick unlock
        </button>

        <div className="mt-6 flex items-center justify-between text-xs text-muted">
          <span>Default PIN: 0000</span>
          <button className="hover:text-foreground">Forgot Passcode</button>
        </div>
      </section>
    </main>
  );
}
