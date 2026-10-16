import { describe, expect, it, vi } from "vitest";

import { csrfMiddleware, problemMessage, readCookie } from "./client";

describe("readCookie", () => {
  it("finds a cookie among others and decodes it", () => {
    expect(readCookie("csrftoken", "a=1; csrftoken=abc%3D; b=2")).toBe("abc=");
    expect(readCookie("missing", "a=1")).toBeUndefined();
  });
});

describe("csrfMiddleware", () => {
  it("adds the CSRF header to unsafe methods only", async () => {
    document.cookie = "csrftoken=token-123";
    const onRequest = csrfMiddleware.onRequest!;
    const post = (await onRequest({ request: new Request("http://x/api/v1/auth/login", { method: "POST" }) } as never)) as Request;
    const get = (await onRequest({ request: new Request("http://x/api/v1/me") } as never)) as Request;
    expect(post.headers.get("X-CSRFToken")).toBe("token-123");
    expect(get.headers.get("X-CSRFToken")).toBeNull();
  });

  it("fetches a token when the cookie is missing", async () => {
    document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ csrf_token: "fresh" })));
    vi.stubGlobal("fetch", fetchMock);
    const request = (await csrfMiddleware.onRequest!({ request: new Request("http://x/api", { method: "PATCH" }) } as never)) as Request;
    expect(request.headers.get("X-CSRFToken")).toBe("fresh");
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/auth/csrf", { credentials: "same-origin" });
    vi.unstubAllGlobals();
  });
});

describe("problemMessage", () => {
  it("prefers field errors, then detail, then the fallback", () => {
    expect(problemMessage({ errors: [{ field: "q", message: "Type at least 3 characters." }] })).toBe(
      "Type at least 3 characters.",
    );
    expect(problemMessage({ detail: "Not allowed." })).toBe("Not allowed.");
    expect(problemMessage(null, "Try again.")).toBe("Try again.");
  });
});
