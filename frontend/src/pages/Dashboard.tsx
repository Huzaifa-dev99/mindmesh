import { Activity, BookOpenText, MessageSquareText, Search, Tags } from "lucide-react";
import { SectionHeader } from "../components/SectionHeader";
import type { Journal, Note } from "../types";

type Props = {
  journals: Journal[];
  notes: Note[];
  tagCount: number;
};

export function Dashboard({ journals, notes, tagCount }: Props) {
  const latest = journals[0];

  return (
    <section>
      <SectionHeader
        eyebrow="Command Center"
        title="Daily knowledge cockpit"
        description="Track writing momentum, recent memories, and retrieval health from one quiet workspace."
      />

      <div className="grid gap-4 md:grid-cols-4">
        {[
          { label: "Journal entries", value: journals.length, icon: BookOpenText, tone: "text-mint" },
          { label: "Notes", value: notes.length, icon: MessageSquareText, tone: "text-coral" },
          { label: "Tags", value: tagCount, icon: Tags, tone: "text-gold" },
          { label: "Search surface", value: journals.length + notes.length, icon: Search, tone: "text-sky-300" }
        ].map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="glass-panel rounded-xl p-5">
              <div className={`mb-4 inline-flex rounded-lg bg-white/[0.06] p-2 ${item.tone}`}>
                <Icon size={20} />
              </div>
              <p className="text-3xl font-semibold">{item.value}</p>
              <p className="mt-1 text-sm text-white/48">{item.label}</p>
            </div>
          );
        })}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="glass-panel rounded-2xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold">Recent timeline</h2>
            <span className="badge">Live memory</span>
          </div>
          <div className="space-y-3">
            {journals.slice(0, 5).map((entry) => (
              <article key={entry.id} className="rounded-xl border border-white/10 bg-ink-950/35 p-4">
                <div className="mb-2 flex items-center justify-between gap-3">
                  <h3 className="font-medium">{entry.title || "Untitled reflection"}</h3>
                  <span className="text-xs text-white/38">{new Date(entry.created_at).toLocaleDateString()}</span>
                </div>
                <p className="line-clamp-2 text-sm leading-6 text-white/55">{entry.content}</p>
              </article>
            ))}
            {!journals.length && <p className="text-sm text-white/45">No journal entries yet.</p>}
          </div>
        </div>

        <div className="glass-panel rounded-2xl p-5">
          <div className="mb-4 flex items-center gap-2">
            <Activity size={18} className="text-mint" />
            <h2 className="font-semibold">Latest signal</h2>
          </div>
          {latest ? (
            <div className="space-y-4">
              <p className="text-2xl font-semibold">{latest.title || "Untitled reflection"}</p>
              <p className="text-sm leading-6 text-white/58">{latest.content.slice(0, 420)}</p>
              <div className="flex flex-wrap gap-2">
                {latest.tags.map((tag) => (
                  <span className="badge" key={tag}>{tag}</span>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-white/45">Start with one journal entry and MindMesh will build from there.</p>
          )}
        </div>
      </div>
    </section>
  );
}
