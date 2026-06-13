import { useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";

import { ApiError } from "../api/client";
import {
  useCloseConversation,
  useConversations,
  useMessages,
  useSendMessage,
  useStartConversation,
} from "../api/hooks";
import type { AgentType, Conversation, ConversationStatus, ExtractedData } from "../api/types";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { cn } from "../components/ui/cn";
import { EmptyState } from "../components/ui/EmptyState";
import { Input, Select } from "../components/ui/Field";
import { MessageSquare, Plus, Search, Send, Sparkles } from "../components/ui/icons";
import { Skeleton } from "../components/ui/Skeleton";
import { useToast } from "../components/ui/Toast";
import { filterConversations } from "../utils/conversations";
import {
  AGENT_LABELS,
  STATUS_LABELS,
  formatDate,
  resultLabel,
  sentimentTone,
} from "../utils/format";

export function ChatPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [agentFilter, setAgentFilter] = useState<AgentType | "all">("all");
  const [statusFilter, setStatusFilter] = useState<ConversationStatus | "all">("all");

  const conversationsQuery = useConversations();
  const startMutation = useStartConversation();
  const toast = useToast();

  const conversations = conversationsQuery.data ?? [];
  const visible = useMemo(
    () => filterConversations(conversations, { search, agentType: agentFilter, status: statusFilter }),
    [conversations, search, agentFilter, statusFilter],
  );
  const selected = conversations.find((c) => c.id === selectedId) ?? null;

  function startConversation(agentType: AgentType) {
    startMutation.mutate(agentType, {
      onSuccess: (conversation) => setSelectedId(conversation.id),
      onError: (err) =>
        toast.error(err instanceof ApiError ? err.message : "Création impossible"),
    });
  }

  return (
    <div className="flex h-full">
      <aside className="flex w-80 shrink-0 flex-col border-r border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
        <div className="space-y-2 border-b border-zinc-200 p-3 dark:border-zinc-800">
          <div className="flex gap-2">
            <Button
              onClick={() => startConversation("collector")}
              loading={startMutation.isPending}
              icon={<Plus className="h-4 w-4" />}
              className="flex-1"
            >
              Debriefing
            </Button>
            <Button
              onClick={() => startConversation("trainer")}
              loading={startMutation.isPending}
              variant="secondary"
              icon={<Sparkles className="h-4 w-4" />}
              className="flex-1"
            >
              Entraînement
            </Button>
          </div>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Rechercher…"
              className="pl-9"
            />
          </div>
          <div className="flex gap-2">
            <Select
              value={agentFilter}
              onChange={(e) => setAgentFilter(e.target.value as AgentType | "all")}
            >
              <option value="all">Tous les agents</option>
              <option value="collector">Debriefing</option>
              <option value="trainer">Entraînement</option>
            </Select>
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as ConversationStatus | "all")}
            >
              <option value="all">Tous statuts</option>
              <option value="active">En cours</option>
              <option value="completed">Terminées</option>
            </Select>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          {conversationsQuery.isLoading && (
            <div className="space-y-2 p-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          )}
          {conversationsQuery.isError && (
            <p className="p-4 text-sm text-red-600 dark:text-red-400">
              Impossible de charger l'historique
            </p>
          )}
          {conversationsQuery.isSuccess && conversations.length === 0 && (
            <EmptyState
              icon={MessageSquare}
              title="Aucune conversation"
              description="Lance ton premier debriefing ou une session d'entraînement."
            />
          )}
          {conversationsQuery.isSuccess && conversations.length > 0 && visible.length === 0 && (
            <p className="p-4 text-sm text-zinc-500 dark:text-zinc-400">
              Aucun résultat pour ces filtres.
            </p>
          )}
          {visible.map((conversation) => (
            <button
              key={conversation.id}
              onClick={() => setSelectedId(conversation.id)}
              className={cn(
                "block w-full border-b border-zinc-100 px-4 py-3 text-left transition-colors dark:border-zinc-800",
                conversation.id === selectedId
                  ? "bg-emerald-50 dark:bg-emerald-950/40"
                  : "hover:bg-zinc-50 dark:hover:bg-zinc-800/50",
              )}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{AGENT_LABELS[conversation.agent_type]}</span>
                <Badge tone={conversation.status === "active" ? "emerald" : "neutral"}>
                  {STATUS_LABELS[conversation.status]}
                </Badge>
              </div>
              <p className="mt-1 truncate text-xs text-zinc-500 dark:text-zinc-400">
                {conversation.extracted_data?.client_name
                  ? conversation.extracted_data.client_name
                  : formatDate(conversation.started_at)}
              </p>
            </button>
          ))}
        </div>
      </aside>

      {selected ? (
        <ChatWindow key={selected.id} conversation={selected} />
      ) : (
        <div className="flex flex-1 items-center justify-center text-sm text-zinc-400 dark:text-zinc-500">
          Sélectionne une conversation ou lances-en une nouvelle
        </div>
      )}
    </div>
  );
}

function ChatWindow({ conversation }: { conversation: Conversation }) {
  const messagesQuery = useMessages(conversation.id);
  const sendMutation = useSendMessage(conversation.id);
  const closeMutation = useCloseConversation(conversation.id);
  const toast = useToast();
  const [draft, setDraft] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const messages = messagesQuery.data ?? [];
  const isActive = conversation.status === "active";

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, sendMutation.isPending]);

  function handleSend(event: FormEvent) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || sendMutation.isPending) return;
    setDraft("");
    sendMutation.mutate(content, {
      onError: (err) =>
        toast.error(err instanceof ApiError ? err.message : "Message non envoyé"),
    });
  }

  function handleClose() {
    closeMutation.mutate(undefined, {
      onSuccess: () => toast.success("Conversation clôturée"),
      onError: (err) =>
        toast.error(err instanceof ApiError ? err.message : "Clôture impossible"),
    });
  }

  return (
    <div className="flex min-w-0 flex-1 flex-col bg-zinc-50 dark:bg-zinc-950">
      <div className="flex items-center justify-between border-b border-zinc-200 bg-white px-4 py-2.5 dark:border-zinc-800 dark:bg-zinc-900">
        <span className="text-sm font-medium">
          {AGENT_LABELS[conversation.agent_type]} · {formatDate(conversation.started_at)}
        </span>
        {isActive && (
          <Button variant="secondary" size="sm" onClick={handleClose} loading={closeMutation.isPending}>
            {conversation.agent_type === "collector" ? "Terminer le debriefing" : "Terminer"}
          </Button>
        )}
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-4">
        {messagesQuery.isLoading && (
          <div className="space-y-2">
            <Skeleton className="h-10 w-2/3" />
            <Skeleton className="ml-auto h-10 w-1/2" />
            <Skeleton className="h-10 w-3/5" />
          </div>
        )}
        {messages.map((message) => (
          <div
            key={message.id}
            className={cn("flex", message.sender === "user" ? "justify-end" : "justify-start")}
          >
            <div
              className={cn(
                "max-w-[70%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm shadow-sm",
                message.sender === "user"
                  ? "rounded-br-sm bg-emerald-600 text-white"
                  : "rounded-bl-sm border border-zinc-200 bg-white text-zinc-800 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100",
              )}
            >
              {message.content}
            </div>
          </div>
        ))}
        {sendMutation.isPending && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-sm border border-zinc-200 bg-white px-4 py-2 text-sm text-zinc-400 dark:border-zinc-700 dark:bg-zinc-800">
              L'agent écrit…
            </div>
          </div>
        )}
        {conversation.status === "completed" && conversation.agent_type === "collector" && (
          <ExtractionSummary data={conversation.extracted_data} />
        )}
        <div ref={bottomRef} />
      </div>

      {isActive ? (
        <form
          onSubmit={handleSend}
          className="flex gap-2 border-t border-zinc-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-900"
        >
          <Input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ton message…"
            className="rounded-full"
          />
          <Button
            type="submit"
            disabled={sendMutation.isPending || draft.trim() === ""}
            icon={<Send className="h-4 w-4" />}
            className="rounded-full"
          >
            Envoyer
          </Button>
        </form>
      ) : (
        <p className="border-t border-zinc-200 bg-white p-3 text-center text-sm text-zinc-400 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-500">
          Conversation terminée
        </p>
      )}
    </div>
  );
}

function ExtractionSummary({ data }: { data: ExtractedData | null }) {
  if (!data || Object.keys(data).length === 0) return null;
  if (data.error) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300">
        L'extraction automatique a échoué pour cette conversation.
      </div>
    );
  }

  const rows: { label: string; value: ReactNode }[] = [];
  if (data.sentiment)
    rows.push({ label: "Sentiment", value: <Badge tone={sentimentTone(data.sentiment)}>{data.sentiment}</Badge> });
  if (data.client_name) rows.push({ label: "Client", value: data.client_name });
  if (data.order_result) rows.push({ label: "Résultat", value: resultLabel(data.order_result) });
  if (data.objections?.length) rows.push({ label: "Objections", value: data.objections.join(", ") });
  if (data.competitors?.length)
    rows.push({ label: "Concurrents", value: data.competitors.map((c) => c.name).join(", ") });
  if (data.knowledge_gap_detail)
    rows.push({ label: "À travailler", value: data.knowledge_gap_detail });

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 text-sm dark:border-zinc-700 dark:bg-zinc-900">
      <h3 className="font-medium">Résumé du debriefing</h3>
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-zinc-700 dark:text-zinc-300">
        {rows.map((row, i) => (
          <div key={i} className="contents">
            <dt className="text-zinc-500 dark:text-zinc-400">{row.label}</dt>
            <dd>{row.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
