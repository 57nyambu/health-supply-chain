import { describe, expect, it } from "vitest";

import { type Me, nextStep } from "./me";
import { can, workspacesFor } from "./workspaces";

const me = (patch: Partial<Me>): Me => ({
  id: 1, email: "a@seed.afyasync.test", first_name: "A", last_name: "B", must_change_password: false,
  facility: { id: 1, name: "Synthetic", mfl_code: "99999" }, facilities: [], roles: [], permissions: [],
  session: { idle_minutes: 30, absolute_hours: 12, lock_minutes: 5 },
  mfa: { enrolled: false, required: false, verified: false }, workstation: { locked: false, pin_set: false },
  ...patch,
});

describe("nextStep", () => {
  it("orders lock, MFA enrolment, MFA challenge and password change before the workspace", () => {
    expect(nextStep(me({ workstation: { locked: true, pin_set: true } }))).toBe("locked");
    expect(nextStep(me({ mfa: { enrolled: false, required: true, verified: false } }))).toBe("mfa-setup");
    expect(nextStep(me({ mfa: { enrolled: true, required: true, verified: false } }))).toBe("mfa");
    expect(nextStep(me({ must_change_password: true }))).toBe("password");
    expect(nextStep(me({}))).toBe("workspace");
  });
});

describe("workspaces", () => {
  it("are built from effective permissions only", () => {
    expect(workspacesFor(["patients.patient.search"]).map((w) => w.key)).toEqual(["reception"]);
    expect(workspacesFor(["payments.receive.cash", "audit.log.read"]).map((w) => w.key)).toEqual(["cashier", "admin"]);
    expect(workspacesFor([])).toEqual([]);
    expect(can(["billing.charge.adjust_request"], "billing.charge.")).toBe(true);
  });
});
