import { useMemo, useState, type FormEvent } from "react";

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
import type {
  AgentType,
  ConversationStatus,
  DirectivePriority,
  Report,
  ReportPeriodType,
} from "../api/types";
import { BarList } from "../components/charts/BarList";
import { SentimentDonut } from "../components/charts/SentimentDonut";
import { StatCard } from "../components/charts/StatCard";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { cn } from "../components/ui/cn";
import { EmptyState } from "../components/ui/EmptyState";
import { Input, Select } from "../components/ui/Field";
import { BarChart3, MessageSquare, Search, Sparkles } from "../components/ui/icons";
import { SkeletonRows } from "../components/ui/Skeleton";
import { useToast } from "../components/ui/Toast";
import { aggregateStats, filterConversations } from "../utils/conversations";
import {
  AGENT_LABELS,
  PERIOD_LABELS,
  PRIORITY_LABELS,
  STATUS_LABELS,
  formatDate,
  formatDay,
  priorityTone,
  sentimentTone,
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
      <h1 className="mb-4 text-xl font-semibold">Tableau de bord équipe</h1>
      <div className="flex gap-1 border-b border-zinc-200 dark:border-zinc-800">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors",
              tab === t.id
                ? "border-emerald-500 text-emerald-700 dark:text-emerald-400"
                : "border-transparent text-zinc-500 hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-200",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="mt-5">
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
  const [search, setSearch] = useState("");
  const [userId, setUserId] = useState<string>("all");
  const [status, setStatus] = useState<ConversationStatus | "all">("all");
  const [agentType, setAgentType] = useState<AgentType | "all">("all");

  const conversations = conversationsQuery.data ?? [];
  const filtered = useMemo(
    () => filterConversations(conversations, { search, userId, status, agentType }),
    [conversations, search, userId, status, agentType],
  );
  const stats = useMemo(() => aggregateStats(filtered), [filtered]);

  const userNames = new Map((usersQuery.data ?? []).map((u) => [u.id, u.full_name]));
  const commercials = (usersQuery.data ?? []).filter((u) => u.role === "commercial");

  if (conversationsQuery.isLoading) return <SkeletonRows rows={6} />;
  if (conversationsQuery.isError)
    return <p className="text-sm text-red-600 dark:text-red-400">Impossible de charger les conversations</p>;
  if (conversations.length === 0)
    return (
      <EmptyState
        icon={MessageSquare}
        title="Aucune conversation dans ton équipe"
        description="Les debriefings de tes commerciaux apparaîtront ici."
      />
    );

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Conversations" value={stats.count} icon={MessageSquare} />
        <StatCard
          label="Sentiment positif"
          value={`${Math.round(stats.positiveRate * 100)}%`}
          icon={BarChart3}
        />
        <StatCard label="Terminées" value={stats.completed} />
        <StatCard label="Lacunes produit" value={stats.knowledgeGaps} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-4">
          <h3 className="mb-3 text-sm font-medium">Répartition des sentiments</h3>
          <SentimentDonut data={stats.sentiments} />
        </Card>
        <Card className="p-4">
          <h3 className="mb-3 text-sm font-medium">Objections les plus fréquentes</h3>
          <BarList items={stats.topObjections} emptyLabel="Aucune objection relevée." />
        </Card>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-48 flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Rechercher client, objection, concurrent…"
            className="pl-9"
          />
        </div>
        <Select value={userId} onChange={(e) => setUserId(e.target.value)} className="w-auto">
          <option value="all">Tous les commerciaux</option>
          {commercials.map((c) => (
            <option key={c.id} value={c.id}>
              {c.full_name}
            </option>
          ))}
        </Select>
        <Select
          value={agentType}
          onChange={(e) => setAgentType(e.target.value as AgentType | "all")}
          className="w-auto"
        >
          <option value="all">Tous types</option>
          <option value="collector">Debriefing</option>
          <option value="trainer">Entraînement</option>
        </Select>
        <Select
          value={status}
          onChange={(e) => setStatus(e.target.value as ConversationStatus | "all")}
          className="w-auto"
        >
          <option value="all">Tous statuts</option>
          <option value="active">En cours</option>
          <option value="completed">Terminées</option>
        </Select>
      </div>

      <Card className="overflow-hidden">
        {filtered.length === 0 ? (
          <p className="p-6 text-center text-sm text-zinc-500 dark:text-zinc-400">
            Aucun résultat pour ces filtres.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-200 text-left text-xs uppercase text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Commercial</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Statut</th>
                <th className="px-4 py-3">Sentiment</th>
                <th className="px-4 py-3">Synthèse</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((conversation) => (
                <tr
                  key={conversation.id}
                  className="border-b border-zinc-100 last:border-0 dark:border-zinc-800"
                >
                  <td className="whitespace-nowrap px-4 py-3 text-zinc-600 dark:text-zinc-400">
                    {formatDate(conversation.started_at)}
                  </td>
                  <td className="px-4 py-3">{userNames.get(conversation.user_id) ?? "—"}</td>
                  <td className="px-4 py-3">{AGENT_LABELS[conversation.agent_type]}</td>
                  <td className="px-4 py-3">
                    <Badge tone={conversation.status === "active" ? "emerald" : "neutral"}>
                      {STATUS_LABELS[conversation.status]}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    {conversation.extracted_data?.sentiment ? (
                      <Badge tone={sentimentTone(conversation.extracted_data.sentiment)}>
                        {conversation.extracted_data.sentiment}
                      </Badge>
                    ) : (
                      <span className="text-zinc-400">—</span>
                    )}
                  </td>
                  <td className="max-w-md truncate px-4 py-3 text-zinc-600 dark:text-zinc-400">
                    {summarizeExtraction(conversation.extracted_data)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

// --- Reports -------------------------------------------------------------

function ReportsTab() {
  const reportsQuery = useReports();
  const generateMutation = useGenerateReport();
  const toast = useToast();
  const [selected, setSelected] = useState<Report | null>(null);
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({
    period_type: "weekly" as ReportPeriodType,
    period_start: today,
    period_end: today,
  });

  function handleGenerate(event: FormEvent) {
    event.preventDefault();
    generateMutation.mutate(form, {
      onSuccess: (report) => {
        setSelected(report);
        toast.success("Rapport généré");
      },
      onError: (err) =>
        toast.error(err instanceof ApiError ? err.message : "Génération impossible"),
    });
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
      <div className="space-y-4">
        <Card className="space-y-3 p-4">
          <h3 className="text-sm font-medium">Générer un rapport</h3>
          <form onSubmit={handleGenerate} className="space-y-3">
            <Select
              value={form.period_type}
              onChange={(e) =>
                setForm((f) => ({ ...f, period_type: e.target.value as ReportPeriodType }))
              }
            >
              {Object.entries(PERIOD_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
            <div className="flex gap-2">
              <Input
                type="date"
                value={form.period_start}
                onChange={(e) => setForm((f) => ({ ...f, period_start: e.target.value }))}
              />
              <Input
                type="date"
                value={form.period_end}
                onChange={(e) => setForm((f) => ({ ...f, period_end: e.target.value }))}
              />
            </div>
            <Button type="submit" loading={generateMutation.isPending} className="w-full">
              Générer
            </Button>
          </form>
        </Card>

        <Card className="overflow-hidden">
          {reportsQuery.isLoading && <div className="p-3"><SkeletonRows rows={3} /></div>}
          {reportsQuery.isSuccess && (reportsQuery.data ?? []).length === 0 && (
            <p className="p-4 text-sm text-zinc-500 dark:text-zinc-400">Aucun rapport généré.</p>
          )}
          {(reportsQuery.data ?? []).map((report) => (
            <button
              key={report.id}
              onClick={() => setSelected(report)}
              className={cn(
                "block w-full border-b border-zinc-100 px-4 py-3 text-left text-sm last:border-0 dark:border-zinc-800",
                selected?.id === report.id
                  ? "bg-emerald-50 dark:bg-emerald-950/40"
                  : "hover:bg-zinc-50 dark:hover:bg-zinc-800/50",
              )}
            >
              <span className="font-medium">{PERIOD_LABELS[report.period_type]}</span>
              <span className="block text-xs text-zinc-500 dark:text-zinc-400">
                {formatDay(report.period_start)} → {formatDay(report.period_end)}
              </span>
            </button>
          ))}
        </Card>
      </div>

      {selected ? (
        <ReportDetail report={selected} />
      ) : (
        <EmptyState icon={BarChart3} title="Sélectionne un rapport" description="Ou génère-en un nouveau pour la période de ton choix." />
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
    <Card className="space-y-4 p-6">
      <header>
        <h2 className="font-semibold">
          Rapport {PERIOD_LABELS[report.period_type].toLowerCase()} — {formatDay(report.period_start)}{" "}
          au {formatDay(report.period_end)}
        </h2>
        <p className="text-xs text-zinc-500 dark:text-zinc-400">
          {metrics.conversation_count ?? 0} conversation(s) analysée(s) ·{" "}
          {metrics.knowledge_gap_count ?? 0} lacune(s) produit
        </p>
      </header>

      <p className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
        {report.summary}
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        {INSIGHT_SECTIONS.map(({ key, label }) => {
          const items = report.insights[key] ?? [];
          if (items.length === 0) return null;
          return (
            <div key={key} className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800/50">
              <h3 className="text-xs font-semibold uppercase text-zinc-500 dark:text-zinc-400">
                {label}
              </h3>
              <ul className="mt-1 list-inside list-disc space-y-0.5 text-sm text-zinc-700 dark:text-zinc-300">
                {items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>

      {!!metrics.sentiments && Object.keys(metrics.sentiments).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(metrics.sentiments).map(([sentiment, count]) => (
            <Badge key={sentiment} tone={sentimentTone(sentiment)}>
              {sentiment} : {count}
            </Badge>
          ))}
        </div>
      )}
    </Card>
  );
}

// --- Directives ----------------------------------------------------------

function DirectivesTab() {
  const directivesQuery = useDirectives();
  const createMutation = useCreateDirective();
  const updateMutation = useUpdateDirective();
  const deleteMutation = useDeleteDirective();
  const toast = useToast();
  const [content, setContent] = useState("");
  const [priority, setPriority] = useState<DirectivePriority>("medium");

  function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (content.trim().length < 3) return;
    createMutation.mutate(
      { content: content.trim(), priority },
      {
        onSuccess: () => {
          setContent("");
          toast.success("Directive publiée");
        },
        onError: (err) =>
          toast.error(err instanceof ApiError ? err.message : "Publication impossible"),
      },
    );
  }

  return (
    <div className="space-y-4">
      <Card className="p-4">
        <form onSubmit={handleCreate} className="flex flex-col gap-2 sm:flex-row">
          <Input
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Nouvelle consigne pour les commerciaux…"
            className="flex-1"
          />
          <Select
            value={priority}
            onChange={(e) => setPriority(e.target.value as DirectivePriority)}
            className="sm:w-40"
          >
            {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
          <Button type="submit" loading={createMutation.isPending}>
            Publier
          </Button>
        </form>
      </Card>

      {directivesQuery.isLoading && <SkeletonRows rows={3} />}
      {directivesQuery.isSuccess && (directivesQuery.data ?? []).length === 0 && (
        <EmptyState
          icon={Sparkles}
          title="Aucune directive"
          description="Les directives actives sont transmises aux agents de tes commerciaux."
        />
      )}

      <ul className="space-y-2">
        {(directivesQuery.data ?? []).map((directive) => (
          <Card
            key={directive.id}
            className="flex items-center justify-between gap-4 px-4 py-3"
          >
            <div className="min-w-0">
              <p
                className={cn(
                  "text-sm",
                  directive.status === "archived" && "text-zinc-400 dark:text-zinc-500",
                )}
              >
                {directive.content}
              </p>
              <p className="mt-1 flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
                <Badge tone={priorityTone(directive.priority)}>
                  {PRIORITY_LABELS[directive.priority]}
                </Badge>
                {formatDate(directive.created_at)}
                {directive.status === "archived" && " · archivée"}
              </p>
            </div>
            <div className="flex shrink-0 gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() =>
                  updateMutation.mutate({
                    directiveId: directive.id,
                    status: directive.status === "active" ? "archived" : "active",
                  })
                }
              >
                {directive.status === "active" ? "Archiver" : "Réactiver"}
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() =>
                  deleteMutation.mutate(directive.id, {
                    onSuccess: () => toast.success("Directive supprimée"),
                  })
                }
              >
                Supprimer
              </Button>
            </div>
          </Card>
        ))}
      </ul>
    </div>
  );
}
