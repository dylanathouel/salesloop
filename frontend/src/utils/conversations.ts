// Pure helpers for filtering and aggregating conversations (unit-tested).

import type { AgentType, Conversation, ConversationStatus } from "../api/types";

export interface ConversationFilters {
  search?: string;
  agentType?: AgentType | "all";
  status?: ConversationStatus | "all";
  userId?: string | "all";
}

function haystack(conversation: Conversation): string {
  const data = conversation.extracted_data ?? {};
  return [
    data.client_name,
    data.order_result,
    ...(data.objections ?? []),
    ...(data.competitors ?? []).map((c) => c.name),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

export function filterConversations(
  conversations: Conversation[],
  filters: ConversationFilters,
): Conversation[] {
  const search = filters.search?.trim().toLowerCase();
  return conversations.filter((conversation) => {
    if (filters.agentType && filters.agentType !== "all") {
      if (conversation.agent_type !== filters.agentType) return false;
    }
    if (filters.status && filters.status !== "all") {
      if (conversation.status !== filters.status) return false;
    }
    if (filters.userId && filters.userId !== "all") {
      if (conversation.user_id !== filters.userId) return false;
    }
    if (search && !haystack(conversation).includes(search)) return false;
    return true;
  });
}

export interface RankedItem {
  label: string;
  count: number;
}

export interface ConversationStats {
  count: number;
  completed: number;
  sentiments: Record<string, number>;
  positiveRate: number; // share of analysed conversations with a positive sentiment
  knowledgeGaps: number;
  topObjections: RankedItem[];
  topCompetitors: RankedItem[];
}

function rank(counter: Map<string, number>, limit: number): RankedItem[] {
  return [...counter.entries()]
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, limit);
}

export function aggregateStats(conversations: Conversation[]): ConversationStats {
  const sentiments: Record<string, number> = {};
  const objections = new Map<string, number>();
  const competitors = new Map<string, number>();
  let knowledgeGaps = 0;
  let completed = 0;
  let analysed = 0;
  let positives = 0;

  for (const conversation of conversations) {
    if (conversation.status === "completed") completed += 1;
    const data = conversation.extracted_data;
    if (!data || data.error) continue;

    if (data.sentiment) {
      sentiments[data.sentiment] = (sentiments[data.sentiment] ?? 0) + 1;
      analysed += 1;
      if (data.sentiment === "positif") positives += 1;
    }
    for (const objection of data.objections ?? []) {
      objections.set(objection, (objections.get(objection) ?? 0) + 1);
    }
    for (const competitor of data.competitors ?? []) {
      if (competitor.name) {
        competitors.set(competitor.name, (competitors.get(competitor.name) ?? 0) + 1);
      }
    }
    if (data.product_knowledge_gap) knowledgeGaps += 1;
  }

  return {
    count: conversations.length,
    completed,
    sentiments,
    positiveRate: analysed > 0 ? positives / analysed : 0,
    knowledgeGaps,
    topObjections: rank(objections, 5),
    topCompetitors: rank(competitors, 5),
  };
}
