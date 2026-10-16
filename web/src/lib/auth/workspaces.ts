import type { LucideIcon } from "lucide-react";
import {
  Banknote,
  BedDouble,
  ClipboardList,
  FileBarChart,
  FlaskConical,
  HeartPulse,
  Pill,
  Receipt,
  ScanLine,
  Settings,
  Stethoscope,
  UserRoundSearch,
  Warehouse,
} from "lucide-react";

export type Workspace = {
  key: string;
  label: string;
  icon: LucideIcon;
  /** Any of these permissions shows the workspace (prefix "x.y." matches every action). */
  anyOf: string[];
  /** Built in Phase 1; the others show what is coming. */
  ready: boolean;
};

export const WORKSPACES: Workspace[] = [
  { key: "reception", label: "Reception", icon: UserRoundSearch, anyOf: ["patients.patient.search", "patients.patient.create"], ready: true },
  { key: "triage", label: "Triage", icon: HeartPulse, anyOf: ["clinical.triage.record"], ready: false },
  { key: "consult", label: "Consultation", icon: Stethoscope, anyOf: ["clinical.note.write"], ready: false },
  { key: "lab", label: "Laboratory", icon: FlaskConical, anyOf: ["laboratory.result.enter", "laboratory.result.validate"], ready: false },
  { key: "imaging", label: "Imaging", icon: ScanLine, anyOf: ["imaging.study.perform", "imaging.report.sign"], ready: false },
  { key: "pharmacy", label: "Pharmacy", icon: Pill, anyOf: ["pharmacy.medicine.dispense", "pharmacy.prescription.verify"], ready: false },
  { key: "wards", label: "Wards", icon: BedDouble, anyOf: ["pharmacy.mar.record", "inpatient.admission.create"], ready: false },
  { key: "cashier", label: "Cashier", icon: Banknote, anyOf: ["payments.receive."], ready: false },
  { key: "billing", label: "Billing", icon: Receipt, anyOf: ["billing.invoice.", "billing.charge."], ready: false },
  { key: "claims", label: "Claims", icon: ClipboardList, anyOf: ["insurance.claim."], ready: false },
  { key: "inventory", label: "Inventory", icon: Warehouse, anyOf: ["inventory.stock.read"], ready: true },
  { key: "reports", label: "Reports", icon: FileBarChart, anyOf: ["reports.aggregate.read", "reporting.moh.read"], ready: true },
  { key: "admin", label: "Administration", icon: Settings, anyOf: ["admin.user.read", "access.assignment.read", "facilities.facility.read", "audit.log.read", "access.breakglass.review"], ready: true },
];

export function can(permissions: readonly string[], code: string): boolean {
  return code.endsWith(".") ? permissions.some((p) => p.startsWith(code)) : permissions.includes(code);
}

export function workspacesFor(permissions: readonly string[]): Workspace[] {
  return WORKSPACES.filter((w) => w.anyOf.some((code) => can(permissions, code)));
}
