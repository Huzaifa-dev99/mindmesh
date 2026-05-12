import {
  BrainCircuit,
  CalendarDays,
  FileText,
  LayoutDashboard,
  LogOut,
  MessageSquareText,
  Search,
  Settings,
  StickyNote
} from "lucide-react";
import type { ReactNode } from "react";
import type { User } from "../types";

export type PageKey = "dashboard" | "journal" | "notes" | "chat" | "search" | "settings";

const navItems: Array<{ key: PageKey; label: string; icon: typeof LayoutDashboard }> = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { key: "journal", label: "Journal", icon: CalendarDays },
  { key: "notes", label: "Notes", icon: StickyNote },
  { key: "chat", label: "AI Chat", icon: MessageSquareText },
  { key: "search", label: "Search", icon: Search },
  { key: "settings", label: "Settings", icon: Settings }
];

type Props = {
  page: PageKey;
  onPage: (page: PageKey) => void;
  user: User;
  onLogout: () => void;
  children: ReactNode;
};

export function AppShell({ page, onPage, user, onLogout, children }: Props) {
  return (
    <div className="min-h-screen text-white">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-72 border-r border-white/10 bg-ink-950/75 p-4 backdrop-blur-xl lg:block">
        <div className="mb-8 flex items-center gap-3 px-2">
          <div className="grid h-11 w-11 place-items-center rounded-xl bg-mint text-ink-950">
            <BrainCircuit size={24} />
          </div>
          <div>
            <p className="text-lg font-semibold">MindMesh</p>
            <p className="text-xs text-white/45">AI Journaling Platform</p>
          </div>
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = page === item.key;
            return (
              <button
                key={item.key}
                onClick={() => onPage(item.key)}
                className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm transition ${
                  active ? "bg-white/10 text-white shadow-glow" : "text-white/55 hover:bg-white/[0.06] hover:text-white"
                }`}
              >
                <Icon size={18} />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="absolute bottom-4 left-4 right-4 rounded-xl border border-white/10 bg-white/[0.04] p-4">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-full bg-coral/15 text-coral">
              <FileText size={17} />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{user.username}</p>
              <p className="truncate text-xs text-white/45">{user.email}</p>
            </div>
          </div>
          <button className="button-ghost mt-4 w-full" onClick={onLogout}>
            <LogOut size={16} />
            Logout
          </button>
        </div>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-10 border-b border-white/10 bg-ink-950/55 px-4 py-3 backdrop-blur-xl lg:hidden">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 font-semibold">
              <BrainCircuit className="text-mint" />
              MindMesh
            </div>
            <button className="button-ghost" onClick={onLogout}>
              <LogOut size={16} />
            </button>
          </div>
          <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
            {navItems.map((item) => (
              <button key={item.key} onClick={() => onPage(item.key)} className={`badge shrink-0 ${page === item.key ? "border-mint/50 text-mint" : ""}`}>
                {item.label}
              </button>
            ))}
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
