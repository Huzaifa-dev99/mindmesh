import { AlertCircle, CheckCircle2, Loader2, Sparkles } from "lucide-react";
import type { ReactNode } from "react";

type ToastTone = "success" | "error" | "info";

export function Toast({ tone = "info", children }: { tone?: ToastTone; children: ReactNode }) {
  const Icon = tone === "error" ? AlertCircle : tone === "success" ? CheckCircle2 : Sparkles;
  return (
    <div className={`toast toast-${tone}`} role={tone === "error" ? "alert" : "status"} aria-live="polite">
      <Icon size={16} />
      <span>{children}</span>
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action
}: {
  icon?: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">{icon || <Sparkles size={20} />}</div>
      <p className="text-sm font-semibold text-foreground">{title}</p>
      <p className="mt-1 max-w-sm text-sm leading-6 text-muted">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function SkeletonRows({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3" aria-label="Loading content">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="skeleton-row">
          <span className="skeleton-dot" />
          <span className="skeleton-line flex-1" />
          <span className="skeleton-line hidden max-w-[7rem] sm:block" />
        </div>
      ))}
    </div>
  );
}

export function LoadingDots({ label = "Working" }: { label?: string }) {
  return (
    <span className="loading-dots" role="status" aria-live="polite">
      <Loader2 size={15} className="animate-spin" />
      <span>{label}</span>
      <span className="dot" />
      <span className="dot" />
      <span className="dot" />
    </span>
  );
}
