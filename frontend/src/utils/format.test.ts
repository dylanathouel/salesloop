import { describe, expect, it } from "vitest";

import { resultLabel, sentimentStyle, summarizeExtraction } from "./format";

describe("summarizeExtraction", () => {
  it("renvoie un tiret sans données", () => {
    expect(summarizeExtraction(null)).toBe("—");
    expect(summarizeExtraction({})).toBe("—");
  });

  it("signale une extraction échouée", () => {
    expect(summarizeExtraction({ error: "extraction_failed" })).toBe("Extraction indisponible");
  });

  it("assemble client, résultat, objections et concurrents", () => {
    const summary = summarizeExtraction({
      client_name: "Pharma-Corp",
      order_result: "commande",
      objections: ["prix"],
      competitors: [{ name: "ConcurrentX", price_mentioned: true, price_detail: "-10%" }],
    });
    expect(summary).toBe("Pharma-Corp · Commande · Objections : prix · Concurrents : ConcurrentX");
  });
});

describe("resultLabel", () => {
  it("traduit les résultats connus et tolère l'inconnu", () => {
    expect(resultLabel("commande")).toBe("Commande");
    expect(resultLabel("refus")).toBe("Refus");
    expect(resultLabel("autre")).toBe("—");
    expect(resultLabel(null)).toBe("—");
  });
});

describe("sentimentStyle", () => {
  it("mappe chaque sentiment à un style", () => {
    expect(sentimentStyle("positif")).toContain("emerald");
    expect(sentimentStyle("négatif")).toContain("red");
    expect(sentimentStyle("inconnu")).toContain("zinc");
  });
});
