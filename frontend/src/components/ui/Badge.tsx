import type { ReactNode } from "react";

import { cn } from "./cn";

export type BadgeTone = "neutral" | "emerald" | "amber" | "red" | "blue";

const TONES: Record<BadgeTone, string> = {
  neutral: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300",
  emerald: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300",
  amber: "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300",
  red: "bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300",
  blue: "bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300",
};

export function Badge({ tone = "neutral", children }: { tone?: BadgeTone; children: ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        TONES[tone],
      )}
    >
      {children}
    </span>
  );
}
