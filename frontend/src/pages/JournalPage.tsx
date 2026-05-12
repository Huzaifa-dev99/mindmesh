import { FormEvent, useState } from "react";
import { WandSparkles } from "lucide-react";
import { SectionHeader } from "../components/SectionHeader";
import { api } from "../lib/api";
import type { Journal } from "../types";

type Props = {
  token: string;
  journals: Journal[];
  onRefresh: () => Promise<void>;
};

export function JournalPage({ token, journals, onRefresh }: Props) {
  const [title, setTitle] = useState("");
  const [mood, setMood] = useState("");
  const [tags, setTags] = useState("");
  const [content, setContent] = useState("");
  const [summary, setSummary] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api.createJournal(token, {
        title: title || undefined,
        mood: mood || undefined,
        content,
        tags: tags.split(",").map((tag) => tag.trim()).filter(Boolean)
      });
      setTitle("");
      setMood("");
      setTags("");
      setContent("");
      await onRefresh();
    } finally {
      setBusy(false);
    }
  }

  async function summarize(id: string) {
    setSummary("Thinking...");
    const result = await api.summarizeJournal(token, id);
    setSummary(result.summary);
  }

  return (
    <section>
      <SectionHeader eyebrow="Journal" title="Capture the day" description="Write in markdown, tag important themes, and index entries into your private semantic memory." />
      <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
        <form onSubmit={submit} className="glass-panel rounded-2xl p-5">
          <div className="grid gap-3 sm:grid-cols-2">
            <input className="control" placeholder="Entry title" value={title} onChange={(event) => setTitle(event.target.value)} />
            <input className="control" placeholder="Mood" value={mood} onChange={(event) => setMood(event.target.value)} />
          </div>
          <input className="control mt-3" placeholder="Tags, separated by commas" value={tags} onChange={(event) => setTags(event.target.value)} />
          <textarea className="control mt-3 min-h-[340px] resize-y leading-6" placeholder="What is on your mind?" value={content} onChange={(event) => setContent(event.target.value)} />
          <button className="button-primary mt-4 w-full" disabled={busy || !content.trim()}>
            Save and index
          </button>
        </form>

        <div className="space-y-4">
          {summary && <div className="glass-panel rounded-2xl p-5 text-sm leading-6 text-white/70">{summary}</div>}
          {journals.map((entry) => (
            <article key={entry.id} className="glass-panel rounded-2xl p-5">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold">{entry.title || "Untitled reflection"}</h2>
                  <p className="text-xs text-white/40">{new Date(entry.created_at).toLocaleString()}</p>
                </div>
                <button className="button-ghost" onClick={() => void summarize(entry.id)}>
                  <WandSparkles size={16} />
                  Summary
                </button>
              </div>
              <p className="whitespace-pre-wrap text-sm leading-6 text-white/60">{entry.content}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {entry.tags.map((tag) => <span className="badge" key={tag}>{tag}</span>)}
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
