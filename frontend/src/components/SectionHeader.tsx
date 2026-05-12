import type { ReactNode } from "react";

type Props = {
  eyebrow: string;
  title: string;
  description?: string;
  action?: ReactNode;
};

export function SectionHeader({ eyebrow, title, description, action }: Props) {
  return (
    <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-mint">{eyebrow}</p>
        <h1 className="text-3xl font-semibold text-white">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-sm leading-6 text-white/55">{description}</p>}
      </div>
      {action}
    </div>
  );
}
