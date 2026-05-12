import { Server } from "lucide-react";
import { useEffect, useState } from "react";
import { SectionHeader } from "../components/SectionHeader";
import { api } from "../lib/api";
import type { User } from "../types";

type Props = {
  user: User;
};

export function SettingsPage({ user }: Props) {
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  return (
    <section>
      <SectionHeader eyebrow="System" title="Settings" description="Connection details for your local self-hosted MindMesh stack." />
      <div className="grid gap-5 lg:grid-cols-2">
        <div className="glass-panel rounded-2xl p-5">
          <h2 className="mb-4 font-semibold">Profile</h2>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between gap-4"><dt className="text-white/45">Username</dt><dd>{user.username}</dd></div>
            <div className="flex justify-between gap-4"><dt className="text-white/45">Email</dt><dd>{user.email}</dd></div>
          </dl>
        </div>
        <div className="glass-panel rounded-2xl p-5">
          <div className="mb-4 flex items-center gap-2">
            <Server size={18} className="text-mint" />
            <h2 className="font-semibold">Backend health</h2>
          </div>
          <pre className="overflow-auto rounded-xl bg-ink-950/65 p-4 text-xs leading-6 text-white/62">{JSON.stringify(health, null, 2)}</pre>
        </div>
      </div>
    </section>
  );
}
