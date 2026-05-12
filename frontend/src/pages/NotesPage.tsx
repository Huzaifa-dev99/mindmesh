import { FormEvent, useState } from "react";
import { SectionHeader } from "../components/SectionHeader";
import { api } from "../lib/api";
import type { Note } from "../types";

type Props = {
  token: string;
  notes: Note[];
  onRefresh: () => Promise<void>;
};

export function NotesPage({ token, notes, onRefresh }: Props) {
  const [title, setTitle] = useState("");
  const [source, setSource] = useState("");
  const [tags, setTags] = useState("");
  const [content, setContent] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    await api.createNote(token, {
      title,
      source: source || undefined,
      content,
      tags: tags.split(",").map((tag) => tag.trim()).filter(Boolean)
    });
    setTitle("");
    setSource("");
    setTags("");
    setContent("");
    await onRefresh();
  }

  return (
    <section>
      <SectionHeader eyebrow="Knowledge" title="Notes explorer" description="Store structured markdown notes and make them retrievable through semantic search and chat." />
      <div className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
        <form onSubmit={submit} className="glass-panel rounded-2xl p-5">
          <input className="control" placeholder="Note title" value={title} onChange={(event) => setTitle(event.target.value)} />
          <input className="control mt-3" placeholder="Source or URL" value={source} onChange={(event) => setSource(event.target.value)} />
          <input className="control mt-3" placeholder="Tags, separated by commas" value={tags} onChange={(event) => setTags(event.target.value)} />
          <textarea className="control mt-3 min-h-[280px] resize-y leading-6" placeholder="Markdown note" value={content} onChange={(event) => setContent(event.target.value)} />
          <button className="button-primary mt-4 w-full" disabled={!title.trim() || !content.trim()}>
            Save note
          </button>
        </form>

        <div className="grid gap-4 md:grid-cols-2">
          {notes.map((note) => (
            <article key={note.id} className="glass-panel rounded-2xl p-5">
              <p className="mb-2 text-xs text-white/40">{note.source || "Personal note"}</p>
              <h2 className="text-lg font-semibold">{note.title}</h2>
              <p className="mt-3 line-clamp-6 whitespace-pre-wrap text-sm leading-6 text-white/58">{note.content}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {note.tags.map((tag) => <span className="badge" key={tag}>{tag}</span>)}
              </div>
            </article>
          ))}
          {!notes.length && <p className="text-sm text-white/45">No notes yet.</p>}
        </div>
      </div>
    </section>
  );
}
