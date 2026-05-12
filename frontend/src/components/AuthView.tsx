import { BrainCircuit, LockKeyhole, Sparkles } from "lucide-react";
import { FormEvent, useState } from "react";
import { api } from "../lib/api";
import type { User } from "../types";

type Props = {
  onSession: (token: string, user: User) => void;
};

export function AuthView({ onSession }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (mode === "register") {
        await api.register({ email, username, full_name: fullName, password });
      }
      const session = await api.login(email, password);
      onSession(session.access_token, session.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen p-4 text-white sm:p-6">
      <section className="mx-auto grid min-h-[calc(100vh-3rem)] max-w-6xl items-center gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-8">
          <div className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-white/70">
            <Sparkles size={16} className="text-mint" />
            Private AI journaling workspace
          </div>
          <div className="space-y-5">
            <h1 className="max-w-3xl text-5xl font-semibold leading-tight text-white sm:text-6xl">
              MindMesh
            </h1>
            <p className="max-w-2xl text-lg leading-8 text-white/62">
              A calm command center for journals, long-term memories, semantic search, and RAG chat.
            </p>
          </div>
          <div className="grid max-w-3xl gap-3 sm:grid-cols-3">
            {["Journals", "Memory RAG", "Semantic recall"].map((item) => (
              <div key={item} className="glass-panel rounded-xl p-4">
                <div className="mb-3 h-1.5 w-10 rounded-full bg-mint" />
                <p className="text-sm font-medium text-white">{item}</p>
                <p className="mt-2 text-xs leading-5 text-white/50">Self-hosted and built for private knowledge.</p>
              </div>
            ))}
          </div>
        </div>

        <form onSubmit={submit} className="glass-panel rounded-2xl p-6 shadow-glow">
          <div className="mb-6 flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-xl bg-mint/15 text-mint">
              <BrainCircuit size={24} />
            </div>
            <div>
              <h2 className="text-xl font-semibold">{mode === "login" ? "Welcome back" : "Create workspace"}</h2>
              <p className="text-sm text-white/50">Connect to your local MindMesh API.</p>
            </div>
          </div>

          <div className="mb-5 grid grid-cols-2 rounded-lg border border-white/10 bg-ink-950/45 p-1">
            <button type="button" onClick={() => setMode("login")} className={`rounded-md py-2 text-sm ${mode === "login" ? "bg-white/10 text-white" : "text-white/45"}`}>
              Login
            </button>
            <button type="button" onClick={() => setMode("register")} className={`rounded-md py-2 text-sm ${mode === "register" ? "bg-white/10 text-white" : "text-white/45"}`}>
              Register
            </button>
          </div>

          <div className="space-y-3">
            {mode === "register" && (
              <>
                <input className="control" placeholder="Username" value={username} onChange={(event) => setUsername(event.target.value)} />
                <input className="control" placeholder="Full name" value={fullName} onChange={(event) => setFullName(event.target.value)} />
              </>
            )}
            <input className="control" placeholder="Email" value={email} onChange={(event) => setEmail(event.target.value)} />
            <input className="control" placeholder="Password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </div>

          {error && <p className="mt-4 rounded-lg border border-coral/30 bg-coral/10 px-3 py-2 text-sm text-coral">{error}</p>}

          <button disabled={submitting} className="button-primary mt-5 w-full">
            <LockKeyhole size={16} />
            {submitting ? "Connecting..." : mode === "login" ? "Enter MindMesh" : "Create and enter"}
          </button>
        </form>
      </section>
    </main>
  );
}
