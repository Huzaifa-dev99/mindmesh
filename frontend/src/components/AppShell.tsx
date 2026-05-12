import {
  Archive,
  BookOpenText,
  Brain,
  ChevronDown,
  File,
  Image,
  Lightbulb,
  Menu,
  MessageSquare,
  Mic,
  Moon,
  Plus,
  Search,
  Settings,
  Shield,
  SlidersHorizontal,
  Sparkles,
  StickyNote,
  Sun,
  Trash2,
  Upload
} from "lucide-react";
import { ReactNode, useState } from "react";
import type { Journal, Note } from "../types";

export type PageKey = "chats" | "notes" | "media" | "documents" | "insights" | "dashboard";

const navItems: Array<{ key: PageKey; label: string; icon: typeof MessageSquare }> = [
  { key: "chats", label: "Chats", icon: MessageSquare },
  { key: "notes", label: "Notes", icon: StickyNote },
  { key: "media", label: "Media Library", icon: Image },
  { key: "documents", label: "Documents", icon: File },
  { key: "insights", label: "Insights", icon: Lightbulb },
  { key: "dashboard", label: "Knowledge Dashboard", icon: BookOpenText }
];

type Props = {
  page: PageKey;
  onPage: (page: PageKey) => void;
  notes: Note[];
  journals: Journal[];
  children: ReactNode;
};

export function AppShell({ page, onPage, notes, journals, children }: Props) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [provider, setProvider] = useState("Groq");

  const groupedChats = [
    { group: "Today", items: ["Morning planning", "RAG search tuning", "Document summary"] },
    { group: "Yesterday", items: ["Knowledge cleanup", "Weekly reflection"] },
    { group: "Previous 7 days", items: ["Project memory map", "Reading notes synthesis"] }
  ];

  return (
    <div className="flex min-h-screen bg-app text-foreground">
      <aside className="hidden w-[19rem] shrink-0 border-r border-border bg-sidebar/92 p-3 backdrop-blur-xl xl:flex xl:flex-col">
        <div className="mb-3 flex items-center gap-3 rounded-2xl px-3 py-2">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-foreground text-app">
            <Brain size={20} />
          </div>
          <div>
            <p className="font-semibold tracking-tight">MindMesh</p>
            <p className="text-xs text-muted">Personal AI workspace</p>
          </div>
        </div>

        <div className="relative mb-3">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" size={16} />
          <input className="control h-10 pl-9" placeholder="Search chats, notes, files" />
        </div>

        <div className="grid grid-cols-2 gap-2">
          <button onClick={() => onPage("chats")} className="button-primary h-10">
            <Plus size={16} />
            New Chat
          </button>
          <button onClick={() => onPage("notes")} className="button-ghost h-10">
            <StickyNote size={16} />
            New Note
          </button>
        </div>

        <nav className="mt-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = page === item.key;
            return (
              <button
                key={item.key}
                onClick={() => onPage(item.key)}
                className={`sidebar-item ${active ? "sidebar-item-active" : ""}`}
              >
                <Icon size={17} />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="mt-5 flex-1 overflow-y-auto pr-1">
          <p className="mb-2 px-2 text-xs font-medium uppercase tracking-[0.16em] text-muted">Chat History</p>
          {groupedChats.map((section) => (
            <div key={section.group} className="mb-4">
              <p className="mb-1 px-2 text-xs text-muted">{section.group}</p>
              {section.items.map((item) => (
                <button key={item} className="w-full truncate rounded-lg px-2 py-2 text-left text-sm text-soft hover:bg-panel">
                  {item}
                </button>
              ))}
            </div>
          ))}

          <p className="mb-2 px-2 text-xs font-medium uppercase tracking-[0.16em] text-muted">Categories</p>
          {["Research", "Personal", "Workflows", "Journal", "Documents"].map((item) => (
            <button key={item} className="mb-1 flex w-full items-center justify-between rounded-lg px-2 py-2 text-sm text-soft hover:bg-panel">
              {item}
              <span className="text-xs text-muted">{Math.floor(Math.random() * 8) + 1}</span>
            </button>
          ))}
        </div>

        <div className="relative mt-3 border-t border-border pt-3">
          <button onClick={() => setSettingsOpen((value) => !value)} className="flex w-full items-center gap-3 rounded-xl p-2 hover:bg-panel">
            <div className="grid h-9 w-9 place-items-center rounded-full bg-panel text-soft">A</div>
            <div className="min-w-0 flex-1 text-left">
              <p className="text-sm font-medium">Local Workspace</p>
              <p className="text-xs text-muted">Single-user mode</p>
            </div>
            <Settings size={17} className="text-muted" />
          </button>
          {settingsOpen && (
            <div className="absolute bottom-14 left-0 right-0 z-30 rounded-2xl border border-border bg-elevated p-4 shadow-panel">
              <div className="mb-4 flex items-center justify-between">
                <p className="font-medium">Workspace Settings</p>
                <ChevronDown size={16} className="text-muted" />
              </div>
              <label className="text-xs text-muted">LLM provider</label>
              <select className="control mt-2" value={provider} onChange={(event) => setProvider(event.target.value)}>
                {["OpenAI", "Gemini", "Claude", "Groq"].map((item) => <option key={item}>{item}</option>)}
              </select>
              <label className="mt-3 block text-xs text-muted">API key</label>
              <input className="control mt-2" placeholder={`${provider} API key`} type="password" />
              <label className="mt-3 block text-xs text-muted">Custom instructions</label>
              <textarea className="control mt-2 min-h-24" placeholder="Name, bio, personality, response preferences..." />
              <div className="mt-3 flex items-center justify-between rounded-xl bg-panel p-2 text-sm">
                <span className="flex items-center gap-2 text-soft"><Shield size={15} /> Local privacy</span>
                <span className="text-xs text-muted">Enabled</span>
              </div>
              <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")} className="button-ghost mt-3 w-full">
                {theme === "dark" ? <Moon size={16} /> : <Sun size={16} />}
                {theme === "dark" ? "Dark mode" : "Light mode"}
              </button>
            </div>
          )}
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-border bg-app/80 px-4 backdrop-blur-xl xl:hidden">
          <div className="flex items-center gap-2 font-semibold"><Menu size={18} /> MindMesh</div>
          <button className="button-ghost h-9"><Settings size={16} /></button>
        </header>
        {children}
      </main>

      <aside className="hidden w-[22rem] shrink-0 border-l border-border bg-sidebar/86 p-4 backdrop-blur-xl 2xl:block">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="font-semibold">Context Workspace</p>
            <p className="text-xs text-muted">Notes, files, summaries</p>
          </div>
          <button className="button-ghost h-9 w-9 p-0"><SlidersHorizontal size={16} /></button>
        </div>

        <div className="space-y-3">
          <button className="button-primary h-10 w-full">
            <Upload size={16} />
            Attach Document
          </button>
          <div className="rounded-2xl border border-dashed border-border bg-panel/60 p-4 text-center text-sm text-muted">
            Drop PDFs, images, text files, or docs
          </div>
        </div>

        <section className="mt-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold">Linked Notes</h3>
            <Plus size={16} className="text-muted" />
          </div>
          <div className="space-y-2">
            {notes.slice(0, 4).map((note) => (
              <article key={note.id} className="rounded-xl border border-border bg-panel p-3">
                <p className="truncate text-sm font-medium">{note.title}</p>
                <p className="mt-1 text-xs text-muted">{new Date(note.created_at).toLocaleDateString()}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {note.tags.slice(0, 2).map((tag) => <span key={tag} className="badge">{tag}</span>)}
                </div>
              </article>
            ))}
            {!notes.length && <p className="rounded-xl bg-panel p-3 text-sm text-muted">No notes linked yet.</p>}
          </div>
        </section>

        <section className="mt-5">
          <h3 className="mb-3 text-sm font-semibold">Uploaded Documents</h3>
          {["MindMesh PRD.pdf", "meeting-notes.txt", "vision-board.png"].map((file, index) => (
            <div key={file} className="mb-2 flex items-center gap-3 rounded-xl bg-panel p-3">
              <File size={17} className="text-muted" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm">{file}</p>
                <p className="text-xs text-muted">{index + 1}.{index * 7 + 2} MB</p>
              </div>
            </div>
          ))}
        </section>

        <section className="mt-5 rounded-2xl border border-border bg-panel p-4">
          <div className="mb-3 flex items-center gap-2">
            <Sparkles size={16} className="text-accent" />
            <h3 className="text-sm font-semibold">Quick Insights</h3>
          </div>
          <p className="text-sm leading-6 text-soft">
            Your recent workspace activity is centered on memory retrieval, journal structure, and AI-native productivity.
          </p>
          <div className="mt-3 flex gap-2">
            <button className="button-ghost h-8 px-2 text-xs"><Archive size={13} /> Archive</button>
            <button className="button-ghost h-8 px-2 text-xs"><Trash2 size={13} /> Clean</button>
          </div>
        </section>
      </aside>
    </div>
  );
}
