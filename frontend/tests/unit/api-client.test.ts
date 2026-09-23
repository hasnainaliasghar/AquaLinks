import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BackendError, api } from "@/lib/api-client";

const originalFetch = globalThis.fetch;

describe("api-client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("returns parsed JSON for successful responses", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    ) as typeof fetch;
    const result = await api.health();
    expect(result).toEqual({ status: "ok" });
  });

  it("throws a BackendError when the response is not ok", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Not found" }), {
        status: 404,
        headers: { "content-type": "application/json" },
      }),
    ) as typeof fetch;
    await expect(api.health()).rejects.toBeInstanceOf(BackendError);
  });

  it("builds the correct report URL", () => {
    expect(api.reportUrl("abc-123")).toMatch(/\/api\/v1\/sessions\/abc-123\/report$/);
  });
});
