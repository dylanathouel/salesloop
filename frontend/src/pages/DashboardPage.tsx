import { useState, type FormEvent } from "react";

import { ApiError } from "../api/client";
import {
  useConversations,
  useCreateDirective,
  useDeleteDirective,
  useDirectives,
  useGenerateReport,
  useReports,
  useUpdateDirective,
  useUsers,
} from "../api/hooks";
import type { DirectivePriority, Report, ReportPeriodType } from "../api/types";
import {
  AGENT_LABELS,
  PERIOD_LABELS,
  PRIORITY_LABELS,
  STATUS_LABELS,
  formatDate,
  formatDay,
  sentimentStyle,
  summarizeExtraction,
} from "../utils/format";

type Tab = "conversations" | "reports" | "directives";

const TABS: { id: Tab; label: string }[] = [
  { id: "conversations", label: "Conversations" },
  { id: "reports", label: "Rapports" },
  { id: "directives", label: "Directives" },
];

export function DashboardPage() {
  const [tab, setTab] = useState<Tab>("conversations");

  return (
    <div className="mx-auto h-full max-w-6xl overflow-y-auto p-6">
      <div className="flex gap-1 border-b border-zinc-200">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`rounded-t-md px-4 py-2 text-sm font-medium ${
              tab === t.id
                ? "border border-b-0 border-zinc-200 bg-white text-zinc-900"
                : "text-zinc-500 hover:text-zinc-800"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="mt-4">
        {tab === "conversations" && <ConversationsTab />}
        {tab === "reports" && <ReportsTab />}
        {tab === "directives" && <DirectivesTab />}
      </div>
    </div>
  );
}

// --- Conversations -----------------------------------------------------

function ConversationsTab() {
  const conversationsQuery = useConversations();
  const usersQuery = useUsers();

  if (conversationsQuery.isLoading) return <p className="text-sm text-zinc-500">Chargement…</p>;
  if (conversationsQuery.isError)
    return <p className="text-sm text-red-600">Impossible de charger les conversations</p>;

  const conversations = conversationsQuery.data ?? [];
  if (conversations.length === 0)
    return <p className="text-sm text-zinc-500">Aucune conversation dans ton équipe.</p>;

  const userNames = new Map((usersQuery.data ?? []).map((u) => [u.id, u.full_name]));

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-200 bg-white">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-200 text-left text-xs uppercase text-zinc-500">
            <th className="px-4 py-3">Date</th>
            <th className="px-4 py-3">Commercial</th>
            <th className="px-4 py-3">Type</th>
            <th className="px-4 py-3">Statut</th>
            <th className="px-4 py-3">Sentiment</th>
            <th className="px-4 py-3">Synthèse</th>
          </tr>
        </thead>
        <tbody>
          {conversations.map((conversation) => (
            <tr key={conversation.id} className="border-b border-zinc-100 last:border-0">
              <td className="px-4 py-3 whitespace-nowrap text-zinc-600">
                {formatDate(conversation.started_at)}
              </td>
              <td className="px-4 py-3">{userNames.get(conversation.user_id) ?? "—"}</td>
              <td className="px-4 py-3">{AGENT_LABELS[conversation.agent_type]}</td>
              <td className="px-4 py-3">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${
                    conversation.status === "active"
                      ? "bg-emerald-100 text-emerald-700"
                      : "bg-zinc-100 text-zinc-500"
                  }`}
                >
                  {STATUS_LABELS[conversation.status]}
                </span>
              </td>
              <td className="px-4 py-3">
                {conversation.extracted_data?.sentiment ? (
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${sentimentStyle(
                      conversation.extracted_data.sentiment,
                    )}`}
                  >
                    {conversation.extracted_data.sentiment}
                  </span>
                ) : (
                  <span className="text-zinc-400">—</span>
                )}
              </td>
              <td className="max-w-md truncate px-4 py-3 text-zinc-600">
                {summarizeExtraction(conversation.extracted_data)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --- Reports -------------------------------------------------------------

function ReportsTab() {
  const reportsQuery = useReports();
  const generateMutation = useGenerateReport();
  const [selected, setSelected] = useState<Report | null>(null);
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({
    period_type: "weekly" as ReportPeriodType,
    period_start: today,
    period_end: today,
  });

  function handleGenerate(event: FormEvent) {
    event.preventDefault();
    generateMutation.mutate(form, { onSuccess: (report) => setSelected(report) });
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
      <div className="space-y-4">
        <form
          onSubmit={handleGenerate}
          className="space-y-3 rounded-lg border border-zinc-200 bg-white p-4"
        >
          <h3 className="text-sm font-medium">Générer un rapport</h3>
          <select
            value={form.period_type}
            onChange={(e) =>
              setForm((f) => ({ ...f, period_type: e.target.value as ReportPeriodType }))
            }
            className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
          >
            {Object.entries(PERIOD_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <div className="flex gap-2">
            <input
              type="date"
              value={form.period_start}
              onChange={(e) => setForm((f) => ({ ...f, period_start: e.target.value }))}
              className="w-full rounded-md border border-zinc-300 px-2 py-2 text-sm"
            />
            <input
              type="date"
              value={form.period_end}
              onChange={(e) => setForm((f) => ({ ...f, period_end: e.target.value }))}
              className="w-full rounded-md border border-zinc-300 px-2 py-2 text-sm"
            />
          </div>
          {generateMutation.isError && (
            <p className="text-sm text-red-600">
              {generateMutation.error instanceof ApiError
                ? generateMutation.error.message
                : "Génération impossible"}
            </p>
          )}
          <button
            type="submit"
            disabled={generateMutation.isPending}
            className="w-full rounded-md bg-zinc-900 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
          >
            {generateMutation.isPending ? "Génération en cours…" : "Générer"}
          </button>
        </form>

        <div className="rounded-lg border border-zinc-200 bg-white">
          {reportsQuery.isLoading && <p className="p-4 text-sm text-zinc-500">Chargement…</p>}
          {reportsQuery.isSuccess && (reportsQuery.data ?? []).length === 0 && (
            <p className="p-4 text-sm text-zinc-500">Aucun rapport généré.</p>
          )}
          {(reportsQuery.data ?? []).map((report) => (
            <button
              key={report.id}
              onClick={() => setSelected(report)}
              className={`block w-full border-b border-zinc-100 px-4 py-3 text-left text-sm last:border-0 hover:bg-zinc-50 ${
                selected?.id === report.id ? "bg-emerald-50" : ""
              }`}
            >
              <span className="font-medium">{PERIOD_LABELS[report.period_type]}</span>
              <span className="block text-xs text-zinc-500">
                {formatDay(report.period_start)} → {formatDay(report.period_end)}
              </span>
            </button>
          ))}
        </div>
      </div>

      {selected ? (
        <ReportDetail report={selected} />
      ) : (
        <p className="text-sm text-zinc-400">Sélectionne un rapport pour le consulter.</p>
      )}
    </div>
  );
}

const INSIGHT_SECTIONS = [
  { key: "trends" as const, label: "Tendances" },
  { key: "recurring_objections" as const, label: "Objections récurrentes" },
  { key: "competitor_alerts" as const, label: "Alertes concurrence" },
  { key: "training_needs" as const, label: "Besoins de formation" },
];

function ReportDetail({ report }: { report: Report }) {
  const metrics = report.metrics;
  return (
    <article className="space-y-4 rounded-lg border border-zinc-200 bg-white p-6">
      <header>
        <h2 className="font-semibold">
          Rapport {PERIOD_LABELS[report.period_type].toLowerCase()} —{" "}
          {formatDay(report.period_start)} au {formatDay(report.period_end)}
        </h2>
        <p className="text-xs text-zinc-500">
          {metrics.conversation_count ?? 0} conversation(s) analysée(s) ·{" "}
          {metrics.knowledge_gap_count ?? 0} lacune(s) produit
        </p>
      </header>

      <p className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-700">{report.summary}</p>

      <div className="grid gap-4 sm:grid-cols-2">
        {INSIGHT_SECTIONS.map(({ key, label }) => {
          const items = report.insights[key] ?? [];
          if (items.length === 0) return null;
          return (
            <div key={key} className="rounded-md bg-zinc-50 p-3">
              <h3 className="text-xs font-semibold uppercase text-zinc-500">{label}</h3>
              <ul className="mt-1 list-inside list-disc space-y-0.5 text-sm text-zinc-700">
                {items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>

      {!!metrics.sentiments && Object.keys(metrics.sentiments).length > 0 && (
        <div className="flex flex-wrap gap-2 text-xs">
          {Object.entries(metrics.sentiments).map(([sentiment, count]) => (
            <span key={sentiment} className={`rounded-full px-2 py-1 ${sentimentStyle(sentiment)}`}>
              {sentiment} : {count}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}

// --- Directives ----------------------------------------------------------

function DirectivesTab() {
  const directivesQuery = useDirectives();
  const createMutation = useCreateDirective();
  const updateMutation = useUpdateDirective();
  const deleteMutation = useDeleteDirective();
  const [content, setContent] = useState("");
  const [priority, setPriority] = useState<DirectivePriority>("medium");

  function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (content.trim().length < 3) return;
    createMutation.mutate(
      { content: content.trim(), priority },
      { onSuccess: () => setContent("") },
    );
  }

  return (
    <div className="space-y-4">
      <form
        onSubmit={handleCreate}
        className="flex flex-col gap-2 rounded-lg border border-zinc-200 bg-white p-4 sm:flex-row"
      >
        <input
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Nouvelle consigne pour les commerciaux…"
          className="flex-1 rounded-md border border-zinc-300 px-3 py-2 text-sm"
        />
        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value as DirectivePriority)}
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm"
        >
          {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <button
          type="submit"
          disabled={createMutation.isPending}
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
        >
          Publier
        </button>
      </form>

      {directivesQuery.isLoading && <p className="text-sm text-zinc-500">Chargement…</p>}
      {directivesQuery.isSuccess && (directivesQuery.data ?? []).length === 0 && (
        <p className="text-sm text-zinc-500">
          Aucune directive. Les directives actives sont transmises aux agents de tes commerciaux.
        </p>
      )}

      <ul className="space-y-2">
        {(directivesQuery.data ?? []).map((directive) => (
          <li
            key={directive.id}
            className="flex items-center justify-between gap-4 rounded-lg border border-zinc-200 bg-white px-4 py-3"
          >
            <div className="min-w-0">
              <p className={`text-sm ${directive.status === "archived" ? "text-zinc-400" : ""}`}>
                {directive.content}
              </p>
              <p className="mt-0.5 text-xs text-zinc-500">
                Priorité {PRIORITY_LABELS[directive.priority].toLowerCase()} ·{" "}
                {formatDate(directive.created_at)}
                {directive.status === "archived" && " · archivée"}
              </p>
            </div>
            <div className="flex shrink-0 gap-2 text-sm">
              <button
                onClick={() =>
                  updateMutation.mutate({
                    directiveId: directive.id,
                    status: directive.status === "active" ? "archived" : "active",
                  })
                }
                className="rounded-md border border-zinc-300 px-2 py-1 text-zinc-600 hover:bg-zinc-100"
              >
                {directive.status === "active" ? "Archiver" : "Réactiver"}
              </button>
              <button
                onClick={() => deleteMutation.mutate(directive.id)}
                className="rounded-md border border-red-200 px-2 py-1 text-red-600 hover:bg-red-50"
              >
                Supprimer
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
