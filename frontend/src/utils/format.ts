// Pure presentation helpers (unit-tested with Vitest).

import type { ExtractedData } from "../api/types";

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDay(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

const SENTIMENT_STYLES: Record<string, string> = {
  positif: "bg-emerald-100 text-emerald-800",
  mitigé: "bg-amber-100 text-amber-800",
  négatif: "bg-red-100 text-red-800",
};

export function sentimentStyle(sentiment: string | null | undefined): string {
  return SENTIMENT_STYLES[sentiment ?? ""] ?? "bg-zinc-100 text-zinc-600";
}

const RESULT_LABELS: Record<string, string> = {
  commande: "Commande",
  refus: "Refus",
  en_attente: "En attente",
};

export function resultLabel(result: string | null | undefined): string {
  return RESULT_LABELS[result ?? ""] ?? "—";
}

/** One-line summary of a debriefing extraction for tables and lists. */
export function summarizeExtraction(data: ExtractedData | null): string {
  if (!data || Object.keys(data).length === 0) return "—";
  if (data.error) return "Extraction indisponible";

  const parts: string[] = [];
  if (data.client_name) parts.push(data.client_name);
  if (data.order_result) parts.push(resultLabel(data.order_result));
  if (data.objections?.length) parts.push(`Objections : ${data.objections.join(", ")}`);
  if (data.competitors?.length)
    parts.push(`Concurrents : ${data.competitors.map((c) => c.name).join(", ")}`);
  return parts.length > 0 ? parts.join(" · ") : "—";
}

export const AGENT_LABELS = { collector: "Debriefing", trainer: "Entraînement" } as const;

export const STATUS_LABELS = {
  active: "En cours",
  completed: "Terminée",
  abandoned: "Abandonnée",
} as const;

export const PRIORITY_LABELS = { low: "Basse", medium: "Moyenne", high: "Haute" } as const;

export const PERIOD_LABELS = {
  daily: "Journalier",
  weekly: "Hebdomadaire",
  monthly: "Mensuel",
} as const;
