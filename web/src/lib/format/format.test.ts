import { describe, expect, it } from "vitest";

import { ageText, formatDate, formatDateTime, formatKES, maskPhone, normalisePhone, parseDate, parseKES } from ".";

describe("money", () => {
  it("formats API decimal strings without floats", () => {
    expect(formatKES("1500")).toBe("KES 1,500.00");
    expect(formatKES("1234567.5")).toBe("KES 1,234,567.50");
    expect(formatKES("0.10")).toBe("KES 0.10");
    expect(formatKES("-12.00", { currency: false })).toBe("-12.00");
    expect(formatKES("-0.00")).toBe("KES 0.00");
    expect(formatKES("9007199254740993.99")).toBe("KES 9,007,199,254,740,993.99"); // beyond float precision
    expect(() => formatKES("1.234")).toThrow();
  });

  it("parses typed amounts to decimal strings", () => {
    expect(parseKES("1,500.5")).toBe("1500.50");
    expect(parseKES("KES 20")).toBe("20.00");
    expect(parseKES("007")).toBe("7.00");
    expect(parseKES("-5")).toBeNull();
    expect(parseKES("12.345")).toBeNull();
  });
});

describe("dates", () => {
  it("shows DD/MM/YYYY and 24-hour time in Nairobi", () => {
    expect(formatDate("1990-04-12")).toBe("12/04/1990");
    expect(formatDateTime("2026-10-16T21:30:00Z")).toBe("17/10/2026 00:30");
  });

  it("parses typed dates strictly", () => {
    expect(parseDate("12/04/1990")).toBe("1990-04-12");
    expect(parseDate("31/02/2020")).toBeNull();
    expect(parseDate("1990-04-12")).toBeNull();
  });

  it("gives ages in years, or months under two", () => {
    const today = new Date("2026-10-16T09:00:00Z");
    expect(ageText("1990-04-12", today)).toBe("36y");
    expect(ageText("2025-04-20", today)).toBe("17m");
  });
});

describe("phones", () => {
  it("normalises Kenyan numbers to E.164 and masks them", () => {
    expect(normalisePhone("0712 345 678")).toBe("+254712345678");
    expect(normalisePhone("+254 112 345678")).toBe("+254112345678");
    expect(normalisePhone("12345")).toBeNull();
    expect(maskPhone("+254712345678")).toBe("+254 7•• ••• 678");
  });
});
