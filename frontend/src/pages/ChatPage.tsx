import { useEffect, useRef, useState, type FormEvent } from "react";

import { ApiError } from "../api/client";
import {
  useCloseConversation,
  useConversations,
  useMessages,
  useSendMessage,
  useStartConversation,
} from "../api/hooks";
import type { Conversation, ExtractedData } from "../api/types";
import { AGENT_LABELS, STATUS_LABELS, formatDate, resultLabel, sentimentStyle } from "../utils/format";

export function ChatPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const conversationsQuery = useConversations();
  const startMutation = useStartConversation();

  const conversations = conversationsQuery.data ?? [];
  const selected = conversations.find((c) => c.id === selectedId) ?? null;

  function startConversation(agentType: "collector" | "trainer") {
    startMutation.mutate(agentType, {
      onSuccess: (conversation) => setSelectedId(conversation.id),
    });
  }

  return (
    <div className="flex h-full">
      <aside className="flex w-72 shrink-0 flex-col border-r border-zinc-200 bg-white">
        <div className="space-y-2 border-b border-zinc-200 p-3">
          <button
            onClick={() => startConversation("collector")}
            disabled={startMutation.isPending}
            className="w-full rounded-md bg-emerald-600 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
          >
            + Nouveau debriefing
          </button>
          <button
            onClick={() => startConversation("trainer")}
            disabled={startMutation.isPending}
            className="w-full rounded-md bg-zinc-800 py-2 text-sm font-medium text-white hover:bg-zinc-600 disabled:opacity-50"
          >
            + Entraînement
          </button>
          {startMutation.isError && (
            <p className="text-xs text-red-600">
              {startMutation.error instanceof ApiError
                ? startMutation.error.message
                : "Création impossible"}
            </p>
          )}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          {conversationsQuery.isLoading && (
            <p className="p-4 text-sm text-zinc-500">Chargement…</p>
          )}
          {conversationsQuery.isError && (
            <p className="p-4 text-sm text-red-600">Impossible de charger l'historique</p>
          )}
          {conversationsQuery.isSuccess && conversations.length === 0 && (
            <p className="p-4 text-sm text-zinc-500">
              Aucune conversation. Lance ton premier debriefing !
            </p>
          )}
          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              onClick={() => setSelectedId(conversation.id)}
              className={`block w-full border-b border-zinc-100 px-4 py-3 text-left hover:bg-zinc-50 ${
                conversation.id === selectedId ? "bg-emerald-50" : ""
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{AGENT_LABELS[conversation.agent_type]}</span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${
                    conversation.status === "active"
                      ? "bg-emerald-100 text-emerald-700"
                      : "bg-zinc-100 text-zinc-500"
                  }`}
                >
                  {STATUS_LABELS[conversation.status]}
                </span>
              </div>
              <p className="mt-1 text-xs text-zinc-500">{formatDate(conversation.started_at)}</p>
            </button>
          ))}
        </div>
      </aside>

      {selected ? (
        <ChatWindow key={selected.id} conversation={selected} />
      ) : (
        <div className="flex flex-1 items-center justify-center text-sm text-zinc-400">
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
    sendMutation.mutate(content);
  }

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <div className="flex items-center justify-between border-b border-zinc-200 bg-white px-4 py-2">
        <span className="text-sm font-medium">
          {AGENT_LABELS[conversation.agent_type]} · {formatDate(conversation.started_at)}
        </span>
        {isActive && (
          <button
            onClick={() => closeMutation.mutate()}
            disabled={closeMutation.isPending}
            className="rounded-md border border-zinc-300 px-3 py-1 text-sm text-zinc-700 hover:bg-zinc-100 disabled:opacity-50"
          >
            {closeMutation.isPending
              ? "Clôture…"
              : conversation.agent_type === "collector"
                ? "Terminer le debriefing"
                : "Terminer la session"}
          </button>
        )}
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-4">
        {messagesQuery.isLoading && <p className="text-sm text-zinc-500">Chargement…</p>}
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[70%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm shadow-sm ${
                message.sender === "user"
                  ? "rounded-br-sm bg-emerald-600 text-white"
                  : "rounded-bl-sm border border-zinc-200 bg-white text-zinc-800"
              }`}
            >
              {message.content}
            </div>
          </div>
        ))}
        {sendMutation.isPending && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-sm border border-zinc-200 bg-white px-4 py-2 text-sm text-zinc-400">
              L'agent écrit…
            </div>
          </div>
        )}
        {sendMutation.isError && (
          <p className="text-sm text-red-600">
            {sendMutation.error instanceof ApiError
              ? sendMutation.error.message
              : "Message non envoyé"}
          </p>
        )}
        {conversation.status === "completed" && conversation.agent_type === "collector" && (
          <ExtractionSummary data={conversation.extracted_data} />
        )}
        <div ref={bottomRef} />
      </div>

      {isActive ? (
        <form onSubmit={handleSend} className="flex gap-2 border-t border-zinc-200 bg-white p-3">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ton message…"
            className="flex-1 rounded-full border border-zinc-300 px-4 py-2 text-sm focus:border-emerald-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={sendMutation.isPending || draft.trim() === ""}
            className="rounded-full bg-emerald-600 px-5 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
          >
            Envoyer
          </button>
        </form>
      ) : (
        <p className="border-t border-zinc-200 bg-white p-3 text-center text-sm text-zinc-400">
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
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        L'extraction automatique a échoué pour cette conversation.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 text-sm">
      <h3 className="font-medium">Résumé du debriefing</h3>
      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-zinc-700">
        {data.sentiment && (
          <>
            <dt className="text-zinc-500">Sentiment</dt>
            <dd>
              <span className={`rounded-full px-2 py-0.5 text-xs ${sentimentStyle(data.sentiment)}`}>
                {data.sentiment}
              </span>
            </dd>
          </>
        )}
        {data.client_name && (
          <>
            <dt className="text-zinc-500">Client</dt>
            <dd>{data.client_name}</dd>
          </>
        )}
        {data.order_result && (
          <>
            <dt className="text-zinc-500">Résultat</dt>
            <dd>{resultLabel(data.order_result)}</dd>
          </>
        )}
        {!!data.objections?.length && (
          <>
            <dt className="text-zinc-500">Objections</dt>
            <dd>{data.objections.join(", ")}</dd>
          </>
        )}
        {!!data.competitors?.length && (
          <>
            <dt className="text-zinc-500">Concurrents</dt>
            <dd>{data.competitors.map((c) => c.name).join(", ")}</dd>
          </>
        )}
        {data.knowledge_gap_detail && (
          <>
            <dt className="text-zinc-500">À travailler</dt>
            <dd>{data.knowledge_gap_detail}</dd>
          </>
        )}
      </dl>
    </div>
  );
}
