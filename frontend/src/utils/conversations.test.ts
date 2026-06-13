import { describe, expect, it } from "vitest";

import type { Conversation } from "../api/types";
import { aggregateStats, filterConversations } from "./conversations";

function conv(overrides: Partial<Conversation>): Conversation {
  return {
    id: crypto.randomUUID(),
    user_id: "u1",
    agent_type: "collector",
    status: "completed",
    extracted_data: null,
    total_tokens: 0,
    started_at: "2026-06-10T10:00:00Z",
    ended_at: "2026-06-10T10:05:00Z",
    ...overrides,
  };
}

const SAMPLE: Conversation[] = [
  conv({
    user_id: "sofia",
    extracted_data: {
      sentiment: "positif",
      client_name: "Pharma-Plus",
      objections: ["prix élevé"],
      competitors: [{ name: "NaturaPlus", price_mentioned: true, price_detail: "-10%" }],
    },
  }),
  conv({
    user_id: "sofia",
    extracted_data: {
      sentiment: "négatif",
      client_name: "BioMarket",
      objections: ["prix élevé", "délais"],
      product_knowledge_gap: true,
    },
  }),
  conv({
    user_id: "karim",
    agent_type: "trainer",
    status: "active",
    extracted_data: null,
  }),
];

describe("filterConversations", () => {
  it("filtre par type d'agent", () => {
    expect(filterConversations(SAMPLE, { agentType: "trainer" })).toHaveLength(1);
    expect(filterConversations(SAMPLE, { agentType: "collector" })).toHaveLength(2);
  });

  it("filtre par statut et par commercial", () => {
    expect(filterConversations(SAMPLE, { status: "active" })).toHaveLength(1);
    expect(filterConversations(SAMPLE, { userId: "sofia" })).toHaveLength(2);
  });

  it("recherche dans le client, les objections et les concurrents", () => {
    expect(filterConversations(SAMPLE, { search: "pharma" })).toHaveLength(1);
    expect(filterConversations(SAMPLE, { search: "naturaplus" })).toHaveLength(1);
    expect(filterConversations(SAMPLE, { search: "délais" })).toHaveLength(1);
  });

  it("« all » et champ vide ne filtrent pas", () => {
    expect(filterConversations(SAMPLE, { agentType: "all", status: "all", search: "" })).toHaveLength(
      3,
    );
  });
});

describe("aggregateStats", () => {
  it("compte sentiments, lacunes et classe objections/concurrents", () => {
    const stats = aggregateStats(SAMPLE);
    expect(stats.count).toBe(3);
    expect(stats.completed).toBe(2);
    expect(stats.sentiments).toEqual({ positif: 1, négatif: 1 });
    expect(stats.positiveRate).toBeCloseTo(0.5);
    expect(stats.knowledgeGaps).toBe(1);
    expect(stats.topObjections[0]).toEqual({ label: "prix élevé", count: 2 });
    expect(stats.topCompetitors[0]).toEqual({ label: "NaturaPlus", count: 1 });
  });

  it("ignore les extractions en erreur et les données absentes", () => {
    const stats = aggregateStats([
      conv({ extracted_data: { error: "extraction_failed" } }),
      conv({ extracted_data: null }),
    ]);
    expect(stats.positiveRate).toBe(0);
    expect(stats.topObjections).toEqual([]);
  });
});
