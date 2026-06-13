import type { RankedItem } from "../../utils/conversations";

/** Horizontal bar list (top objections, competitors…), proportional widths. */
export function BarList({ items, emptyLabel }: { items: RankedItem[]; emptyLabel: string }) {
  if (items.length === 0) {
    return <p className="text-sm text-zinc-500 dark:text-zinc-400">{emptyLabel}</p>;
  }
  const max = Math.max(...items.map((item) => item.count));

  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={item.label}>
          <div className="flex items-center justify-between text-sm">
            <span className="truncate text-zinc-700 dark:text-zinc-300">{item.label}</span>
            <span className="ml-2 shrink-0 tabular-nums text-zinc-400">{item.count}</span>
          </div>
          <div className="mt-1 h-2 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
            <div
              className="h-full rounded-full bg-emerald-500"
              style={{ width: `${(item.count / max) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
