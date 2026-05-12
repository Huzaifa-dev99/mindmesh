import {
  Activity,
  Archive,
  BarChart3,
  BookOpenText,
  Circle,
  FileText,
  FolderKanban,
  Image,
  Link2,
  MessageSquare,
  PieChart,
  Search,
  Trash2
} from "lucide-react";
import type { Journal, Note } from "../types";

type Props = {
  journals: Journal[];
  notes: Note[];
};

export function KnowledgeDashboard({ journals, notes }: Props) {
  const totalDocs = notes.length + 3;
  const themes = ["Memory retrieval", "AI workflows", "Journaling", "Product design", "Local privacy"];

  return (
    <div className="min-h-screen overflow-y-auto px-5 py-6">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-muted">Knowledge Dashboard</p>
          <h1 className="text-3xl font-semibold tracking-tight">Media, documents, and insights</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
            A single-user control room for managing documents, chats, notes, and knowledge relationships.
          </p>
        </div>
        <div className="flex gap-2">
          <button className="button-ghost"><Search size={16} /> Filter</button>
          <button className="button-primary"><FolderKanban size={16} /> Organize</button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Documents", value: totalDocs, icon: FileText },
          { label: "Chats", value: journals.length + 6, icon: MessageSquare },
          { label: "Notes", value: notes.length, icon: BookOpenText },
          { label: "Media", value: 12, icon: Image }
        ].map((item) => {
          const Icon = item.icon;
          return (
            <article key={item.label} className="rounded-2xl border border-border bg-panel p-5">
              <div className="mb-4 flex items-center justify-between">
                <Icon size={19} className="text-muted" />
                <span className="badge">+{Math.max(1, item.value % 5)} this week</span>
              </div>
              <p className="text-3xl font-semibold">{item.value}</p>
              <p className="mt-1 text-sm text-muted">{item.label}</p>
            </article>
          );
        })}
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-2xl border border-border bg-panel p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold">Storage and activity</h2>
            <BarChart3 size={18} className="text-muted" />
          </div>
          <div className="grid gap-4 md:grid-cols-[14rem_1fr]">
            <div className="grid place-items-center">
              <div className="relative grid h-44 w-44 place-items-center rounded-full border-[18px] border-border">
                <div className="absolute inset-[-18px] rounded-full border-[18px] border-t-foreground border-r-accent border-b-transparent border-l-transparent" />
                <div className="text-center">
                  <p className="text-2xl font-semibold">61%</p>
                  <p className="text-xs text-muted">storage used</p>
                </div>
              </div>
            </div>
            <div className="space-y-3">
              {["PDFs", "Images", "Text files", "Docs"].map((item, index) => (
                <div key={item}>
                  <div className="mb-1 flex justify-between text-sm"><span>{item}</span><span className="text-muted">{24 - index * 4}%</span></div>
                  <div className="h-2 rounded-full bg-elevated"><div className="h-2 rounded-full bg-foreground" style={{ width: `${24 - index * 4}%` }} /></div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-border bg-panel p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold">Detected interests</h2>
            <PieChart size={18} className="text-muted" />
          </div>
          <div className="space-y-3">
            {themes.map((theme, index) => (
              <div key={theme} className="flex items-center gap-3 rounded-xl bg-elevated p-3">
                <Circle size={10} className={index % 2 ? "fill-muted text-muted" : "fill-foreground text-foreground"} />
                <div className="flex-1">
                  <p className="text-sm font-medium">{theme}</p>
                  <p className="text-xs text-muted">{18 - index * 2} related memories</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        <section className="rounded-2xl border border-border bg-panel p-5 xl:col-span-2">
          <div className="mb-4 flex items-center gap-2">
            <Link2 size={18} className="text-muted" />
            <h2 className="font-semibold">Chat-document relationships</h2>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {["Project planning", "Journal synthesis", "Research assistant", "Weekly review"].map((chat, index) => (
              <article key={chat} className="rounded-xl border border-border bg-elevated p-4">
                <p className="font-medium">{chat}</p>
                <p className="mt-1 text-xs text-muted">{index + 2} documents attached</p>
                <div className="mt-4 flex items-center gap-2">
                  <span className="h-2 w-12 rounded-full bg-foreground" />
                  <span className="h-px flex-1 bg-border" />
                  <span className="rounded-lg bg-panel px-2 py-1 text-xs text-muted">Knowledge cluster</span>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-border bg-panel p-5">
          <div className="mb-4 flex items-center gap-2">
            <Activity size={18} className="text-muted" />
            <h2 className="font-semibold">Activity timeline</h2>
          </div>
          {["Uploaded product notes", "Created memory summary", "Archived old PDF", "Tagged journal themes"].map((item) => (
            <div key={item} className="relative border-l border-border pb-5 pl-4 last:pb-0">
              <span className="absolute -left-1.5 top-1 h-3 w-3 rounded-full bg-foreground" />
              <p className="text-sm">{item}</p>
              <p className="text-xs text-muted">Today</p>
            </div>
          ))}
        </section>
      </div>

      <div className="mt-5 rounded-2xl border border-border bg-panel p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-semibold">Management</h2>
          <div className="flex gap-2">
            <button className="button-ghost"><Archive size={16} /> Archive</button>
            <button className="button-ghost"><Trash2 size={16} /> Delete unused</button>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          {notes.slice(0, 3).map((note) => (
            <article key={note.id} className="rounded-xl bg-elevated p-4">
              <p className="truncate font-medium">{note.title}</p>
              <p className="mt-2 line-clamp-3 text-sm leading-6 text-muted">{note.content}</p>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}
