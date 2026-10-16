import { describe, expect, it } from "vitest";

import { guessQuery, identifierLabel, maskIdentifier, prefillFrom } from "./patients";

describe("guessQuery", () => {
  it("tells phones, identifiers and names apart", () => {
    expect(guessQuery("0712 345 678").kind).toBe("phone");
    expect(guessQuery("+254712345678").kind).toBe("phone");
    expect(guessQuery("00000001")).toEqual({ kind: "number", value: "00000001" });
    expect(guessQuery("99999-26-000412").kind).toBe("number");
    expect(guessQuery("sha-syn-0001")).toEqual({ kind: "number", value: "SHA-SYN-0001" });
    expect(guessQuery("  Wanjiru Kamau ").kind).toBe("name");
  });
});

describe("prefillFrom", () => {
  it("splits a searched name into given, middle and family names", () => {
    expect(prefillFrom("wanjiru njeri kamau")).toMatchObject({ given_name: "Wanjiru", middle_name: "Njeri", family_name: "Kamau" });
    expect(prefillFrom("Otieno")).toMatchObject({ given_name: "Otieno", family_name: "" });
  });

  it("puts a searched number or phone where it belongs, and nothing for no search", () => {
    expect(prefillFrom("00000001")).toMatchObject({ identifier: "00000001", given_name: "" });
    expect(prefillFrom("0712345678")).toMatchObject({ phone: "0712345678", identifier: "" });
    expect(prefillFrom(undefined)).toEqual({ given_name: "", middle_name: "", family_name: "", phone: "", identifier: "" });
  });
});

describe("identifiers", () => {
  it("masks all but the last four characters and labels types", () => {
    expect(maskIdentifier("00123456")).toBe("••••3456");
    expect(maskIdentifier("123")).toBe("123");
    expect(identifierLabel("national_id")).toBe("National ID");
    expect(identifierLabel("cr_id")).toBe("CR ID");
    expect(identifierLabel("temporary")).toBe("Temporary ID");
  });
});
