import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { Button } from "./button";
import { Combobox } from "./combobox";
import { type Column, DataTable } from "./data-table";
import { Dialog } from "./dialog";
import { Field, TextInput } from "./field";
import { DateInput, type DobValue, DoseInput, IdentifierInput, MoneyInput, PhoneInput } from "./inputs";
import { Select } from "./select";
import { Callout, StatusPill, TriageTag } from "./status";
import { Tabs } from "./tabs";
import { ToastProvider, useToast } from "./toast";

describe("Button", () => {
  it("is a verb-labelled button that keeps its width while saving", () => {
    const { rerender } = render(<Button>Open visit</Button>);
    expect(screen.getByRole("button", { name: "Open visit" })).toHaveAttribute("type", "button");
    rerender(<Button loading>Open visit</Button>);
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(button).toHaveTextContent("Saving…");
    expect(within(button).getByText("Open visit")).toHaveClass("invisible");
  });

  it("renders a link with asChild", () => {
    render(
      <Button asChild variant="secondary">
        <a href="/reception">Go to reception</a>
      </Button>,
    );
    expect(screen.getByRole("link", { name: "Go to reception" })).toHaveClass("border-border-strong");
  });
});

describe("Field", () => {
  it("labels the control, marks it required in words and describes hint and error", () => {
    render(
      <Field label="Given name" required hint="As on the ID" error="Enter the given name.">
        {(control) => <TextInput {...control} />}
      </Field>,
    );
    const input = screen.getByLabelText(/Given name/);
    expect(screen.getByText("(required)")).toBeInTheDocument();
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("As on the ID Enter the given name.");
    expect(input).toHaveClass("border-danger");
  });
});

describe("input variants", () => {
  it("MoneyInput emits decimal strings and formats on blur", async () => {
    const onValueChange = vi.fn();
    render(<MoneyInput id="m" aria-label="Amount" value="" onValueChange={onValueChange} />);
    const input = screen.getByLabelText("Amount");
    await userEvent.type(input, "1500.5");
    expect(onValueChange).toHaveBeenLastCalledWith("1500.50");
    fireEvent.blur(input);
    expect(input).toHaveValue("1,500.50");
  });

  it("PhoneInput normalises to E.164 and masks when not editing", async () => {
    const onValueChange = vi.fn();
    render(<PhoneInput id="p" aria-label="Phone" masked value="" onValueChange={onValueChange} />);
    const input = screen.getByLabelText("Phone");
    await userEvent.type(input, "0712345678");
    expect(onValueChange).toHaveBeenLastCalledWith("+254712345678", "0712345678");
    fireEvent.blur(input);
    expect(input).toHaveValue("+254 7•• ••• 678");
  });

  it("IdentifierInput changes type and upper-cases the number", async () => {
    function Harness() {
      const [value, setValue] = useState({ type: "national_id", value: "" });
      return <IdentifierInput id="i" aria-label="Identifier" value={value} onValueChange={setValue} />;
    }
    render(<Harness />);
    await userEvent.selectOptions(screen.getByLabelText("Identifier type"), "passport");
    await userEvent.type(screen.getByLabelText("Identifier"), "ak12");
    expect(screen.getByLabelText("Identifier")).toHaveValue("AK12");
    expect(screen.getByLabelText("Identifier type")).toHaveValue("passport");
  });

  it("DateInput parses DD/MM/YYYY or switches to an age estimate", async () => {
    const changes: DobValue[] = [];
    function Harness() {
      const [value, setValue] = useState<DobValue>({ date: null, estimated: false });
      return (
        <DateInput
          id="d"
          aria-label="Date of birth"
          value={value}
          onValueChange={(v) => {
            changes.push(v);
            setValue(v);
          }}
        />
      );
    }
    render(<Harness />);
    await userEvent.type(screen.getByLabelText("Date of birth"), "12/04/1990");
    expect(changes.at(-1)).toEqual({ date: "1990-04-12", estimated: false });
    await userEvent.click(screen.getByLabelText(/Date of birth unknown/));
    await userEvent.type(screen.getByLabelText("Age in years"), "34");
    expect(changes.at(-1)).toMatchObject({ estimated: true, years: 34 });
  });

  it("DoseInput offers units without error-prone abbreviations", async () => {
    const onValueChange = vi.fn();
    render(
      <DoseInput
        id="dose"
        aria-label="Dose"
        value={{ quantity: "", unit: "mg", frequency: "once daily", durationDays: "" }}
        onValueChange={onValueChange}
      />,
    );
    await userEvent.type(screen.getByLabelText("Dose quantity"), "5");
    expect(onValueChange).toHaveBeenLastCalledWith(expect.objectContaining({ quantity: "5" }));
    const units = within(screen.getByLabelText("Dose unit")).getAllByRole("option").map((o) => o.textContent);
    expect(units).toContain("units");
    expect(units).not.toContain("U");
  });
});

describe("Select", () => {
  it("shows the chosen option with its code", () => {
    render(
      <Select
        aria-label="Diagnosis"
        value="DA42.Z"
        onValueChange={() => undefined}
        options={[{ value: "DA42.Z", code: "DA42.Z", label: "Gastritis, unspecified" }]}
      />,
    );
    expect(screen.getByRole("combobox", { name: "Diagnosis" })).toHaveTextContent("DA42.Z Gastritis, unspecified");
  });
});

describe("Combobox", () => {
  it("searches after typing and selects with the keyboard", async () => {
    const search = vi.fn().mockResolvedValue([
      { value: "1", code: "DA42.Z", label: "Gastritis, unspecified" },
      { value: "2", code: "CA40.0", label: "Bacterial pneumonia" },
    ]);
    const onSelect = vi.fn();
    render(<Combobox aria-label="Diagnosis" search={search} onSelect={onSelect} debounceMs={0} />);
    const input = screen.getByRole("combobox", { name: "Diagnosis" });
    await userEvent.type(input, "gas");
    expect(await screen.findByRole("option", { name: /Gastritis/ })).toHaveAttribute("aria-selected", "true");
    await userEvent.keyboard("{ArrowDown}{Enter}");
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ code: "CA40.0" }));
    expect(input).toHaveValue("CA40.0 Bacterial pneumonia");
    expect(search).toHaveBeenLastCalledWith("gas");
  });
});

type Row = { id: string; ticket: string; amount: string };
const columns: Column<Row>[] = [
  { key: "ticket", header: "Ticket", cell: (r) => r.ticket, sortValue: (r) => r.ticket },
  { key: "amount", header: "Amount", cell: (r) => r.amount, numeric: true },
];

describe("DataTable", () => {
  it("sorts, navigates with the keyboard and opens with Enter", async () => {
    const onOpen = vi.fn();
    const rows = [
      { id: "b", ticket: "C2-015", amount: "800.00" },
      { id: "a", ticket: "C2-014", amount: "1,500.00" },
    ];
    render(<DataTable caption="Due now" columns={columns} rows={rows} rowKey={(r) => r.id} onOpen={onOpen} empty="Nobody waiting." />);
    await userEvent.click(screen.getByRole("button", { name: "Ticket" }));
    const bodyRows = screen.getAllByRole("row").slice(1);
    expect(bodyRows[0]).toHaveTextContent("C2-014");
    expect(screen.getByRole("columnheader", { name: /Ticket/ })).toHaveAttribute("aria-sort", "ascending");
    expect(screen.getByText("800.00")).toHaveClass("text-right");
    act(() => bodyRows[0]!.focus());
    await userEvent.keyboard("{ArrowDown}");
    expect(bodyRows[1]).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(onOpen).toHaveBeenCalledWith(rows[0]);
  });

  it("shows the empty state", () => {
    render(<DataTable caption="Due now" columns={columns} rows={[]} rowKey={(r) => r.id} empty="No patients waiting." />);
    expect(screen.getByText("No patients waiting.")).toBeInTheDocument();
  });
});

describe("Tabs", () => {
  it("switches panels", async () => {
    render(
      <Tabs
        label="Record"
        tabs={[
          { value: "a", label: "Summary", content: "Summary panel" },
          { value: "b", label: "Documents", content: "Documents panel" },
        ]}
      />,
    );
    expect(screen.getByText("Summary panel")).toBeVisible();
    await userEvent.click(screen.getByRole("tab", { name: "Documents" }));
    expect(screen.getByRole("tab", { name: "Documents" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Documents panel")).toBeVisible();
  });
});

describe("StatusPill, Callout and TriageTag", () => {
  it("never rely on colour alone", () => {
    render(
      <>
        <StatusPill tone="success">Paid</StatusPill>
        <Callout tone="danger" title="Critical value">Potassium 7.1 mmol/L</Callout>
        <TriageTag level="red" />
        <TriageTag level="yellow" scale="paediatric" />
      </>,
    );
    expect(screen.getByText("Paid")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Critical value");
    expect(screen.getByText("Red (emergency)")).toHaveClass("bg-triage-red");
    expect(screen.getByText("Priority")).toBeInTheDocument();
  });
});

describe("Toast", () => {
  it("repeats the action verb", async () => {
    function Trigger() {
      const toast = useToast();
      return <Button onClick={() => toast({ title: "Result released", tone: "success" })}>Release result</Button>;
    }
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Release result" }));
    expect(await screen.findByText("Result released")).toBeInTheDocument();
  });
});

describe("Dialog", () => {
  it("asks before discarding unsaved work", async () => {
    const onOpenChange = vi.fn();
    const confirmDiscard = vi.fn().mockReturnValue(false);
    render(
      <Dialog open title="Record vitals" onOpenChange={onOpenChange} dirty confirmDiscard={confirmDiscard}>
        form
      </Dialog>,
    );
    expect(screen.getByRole("dialog", { name: "Record vitals" })).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(confirmDiscard).toHaveBeenCalled();
    expect(onOpenChange).not.toHaveBeenCalled();
    confirmDiscard.mockReturnValue(true);
    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
