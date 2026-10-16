import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { JourneyRail } from "./journey-rail";
import { type BannerPatient, BreakGlassBanner, PatientBanner } from "./patient-banner";

const patient: BannerPatient = {
  displayName: "Synthetic Patient",
  sex: "female",
  dateOfBirth: "1990-04-12",
  mrn: "90001-26-000412",
  secondIdentifier: { label: "National ID", value: "•••••456" },
  allergies: { state: "recorded", items: ["Penicillin"] },
  alerts: ["Pregnant"],
  payer: { name: "SHA (SHIF)", status: "verified" },
};

describe("PatientBanner", () => {
  it("always shows two identifiers, allergies, alerts and payer", () => {
    render(<PatientBanner patient={patient} />);
    expect(screen.getByRole("heading", { name: "Synthetic Patient" })).toBeInTheDocument();
    expect(screen.getByText("90001-26-000412")).toBeInTheDocument();
    expect(screen.getByText("•••••456")).toBeInTheDocument();
    expect(screen.getByText("Allergy: Penicillin")).toBeInTheDocument();
    expect(screen.getByText("Alert: Pregnant")).toBeInTheDocument();
    expect(screen.getByText(/Payer: SHA \(SHIF\) verified/)).toBeInTheDocument();
    expect(screen.getByText(/DOB 12\/04\/1990/)).toBeInTheDocument();
  });

  it("tells 'no known allergies' apart from 'not recorded'", () => {
    const { rerender } = render(<PatientBanner patient={{ ...patient, allergies: { state: "none_known" } }} />);
    expect(screen.getByText("No known allergies")).toBeInTheDocument();
    rerender(<PatientBanner patient={{ ...patient, allergies: { state: "not_recorded" } }} />);
    expect(screen.getByText("Allergies not recorded")).toBeInTheDocument();
  });
});

describe("BreakGlassBanner", () => {
  it("states the expiry and lets the clinician end access", async () => {
    const onEnd = vi.fn();
    render(<BreakGlassBanner expiresAt="2026-10-16T11:35:00Z" onEnd={onEnd} />);
    expect(screen.getByRole("status")).toHaveTextContent("Emergency access until 14:35");
    await userEvent.click(screen.getByRole("button", { name: "End emergency access" }));
    expect(onEnd).toHaveBeenCalled();
  });
});

describe("JourneyRail", () => {
  it("marks completed, current and future steps; completed steps open their record", async () => {
    const onSelect = vi.fn();
    render(<JourneyRail current="Consultation" emergency onSelect={onSelect} />);
    expect(screen.getByText("Emergency")).toBeInTheDocument();
    expect(screen.getByText("Consultation").closest("li")).toHaveAttribute("aria-current", "step");
    await userEvent.click(screen.getByRole("button", { name: /Triage \(completed\)/ }));
    expect(onSelect).toHaveBeenCalledWith("Triage");
    expect(screen.queryByRole("button", { name: /Settlement/ })).not.toBeInTheDocument();
  });
});
