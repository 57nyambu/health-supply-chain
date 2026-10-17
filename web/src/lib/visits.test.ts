import { describe, expect, it } from "vitest";

import { journeyStep, statusTone, triageLevel, waitText } from "./visits";

describe("visit helpers", () => {
  it("maps every visit status to a journey step", () => {
    expect(journeyStep(undefined)).toBe("Reception");
    expect(journeyStep("awaiting_triage")).toBe("Triage");
    expect(journeyStep("in_consultation")).toBe("Consultation");
    expect(journeyStep("in_service")).toBe("Services");
    expect(journeyStep("awaiting_review")).toBe("Review");
    expect(journeyStep("admitted")).toBe("Disposition");
    expect(journeyStep("closed")).toBe("Settlement");
  });

  it("formats waits and tones", () => {
    const now = Date.parse("2026-10-17T10:00:00Z");
    expect(waitText("2026-10-17T09:48:00Z", now)).toBe("12 min");
    expect(waitText("2026-10-17T08:55:00Z", now)).toBe("1 h 05 min");
    expect(statusTone("awaiting_triage")).toBe("warning");
    expect(statusTone("closed")).toBe("success");
    expect(triageLevel("red")).toBe("red");
    expect(triageLevel("purple")).toBeNull();
  });
});
