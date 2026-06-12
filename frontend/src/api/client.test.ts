import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "./client";

function mockFetch(status: number, body: unknown) {
  // A fresh Response per call: a body can only be consumed once
  const spy = vi.fn().mockImplementation(() =>
    Promise.resolve(
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
  vi.stubGlobal("fetch", spy);
  return spy;
}

afterEach(() => vi.unstubAllGlobals());

describe("api", () => {
  it("renvoie le JSON décodé en cas de succès", async () => {
    mockFetch(200, { status: "ok" });
    await expect(api("/health")).resolves.toEqual({ status: "ok" });
  });

  it("lève une ApiError avec le détail français du backend", async () => {
    mockFetch(404, { detail: "Conversation introuvable" });
    const promise = api("/conversations/xxx/messages");
    await expect(promise).rejects.toBeInstanceOf(ApiError);
    await expect(api("/conversations/xxx/messages")).rejects.toMatchObject({
      status: 404,
      message: "Conversation introuvable",
    });
  });

  it("sérialise le corps et le method", async () => {
    const spy = mockFetch(201, { id: "1" });
    await api("/directives/", { method: "POST", body: { content: "test" } });
    const [, init] = spy.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ content: "test" });
  });
});
