// Home-made SVG donut: sentiment breakdown, no charting library.

const COLORS: Record<string, string> = {
  positif: "#10b981", // emerald-500
  mitigé: "#f59e0b", // amber-500
  négatif: "#ef4444", // red-500
};
const FALLBACK = "#a1a1aa"; // zinc-400

interface Slice {
  label: string;
  value: number;
  color: string;
  offset: number;
  fraction: number;
}

export function SentimentDonut({ data }: { data: Record<string, number> }) {
  const entries = Object.entries(data);
  const total = entries.reduce((sum, [, value]) => sum + value, 0);

  if (total === 0) {
    return <p className="text-sm text-zinc-500 dark:text-zinc-400">Pas encore de données.</p>;
  }

  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  let cumulative = 0;
  const slices: Slice[] = entries.map(([label, value]) => {
    const fraction = value / total;
    const slice = {
      label,
      value,
      color: COLORS[label] ?? FALLBACK,
      offset: cumulative,
      fraction,
    };
    cumulative += fraction;
    return slice;
  });

  return (
    <div className="flex items-center gap-6">
      <svg viewBox="0 0 160 160" className="h-36 w-36 -rotate-90">
        {slices.map((slice) => (
          <circle
            key={slice.label}
            cx="80"
            cy="80"
            r={radius}
            fill="none"
            stroke={slice.color}
            strokeWidth="20"
            strokeDasharray={`${slice.fraction * circumference} ${circumference}`}
            strokeDashoffset={-slice.offset * circumference}
          />
        ))}
      </svg>
      <ul className="space-y-1 text-sm">
        {slices.map((slice) => (
          <li key={slice.label} className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-sm" style={{ backgroundColor: slice.color }} />
            <span className="capitalize text-zinc-700 dark:text-zinc-300">{slice.label}</span>
            <span className="text-zinc-400">
              {slice.value} ({Math.round(slice.fraction * 100)}%)
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
