# Design System — Flat 2.0, High-Contrast Light

The interface is used by receptionists, nurses, clinicians, lab and pharmacy staff, and cashiers — often on shared, ageing monitors in bright rooms, often in a hurry, often with a queue in front of them. The system's one job is to move a patient safely to the next step without anyone misreading a name, a dose, a result or an amount.

**Flat 2.0** here means: flat surfaces and solid colours, with depth used only where it explains layering (menus, dialogs, sticky headers). **High-contrast light mode** means: light surfaces, near-black ink, every text pair ≥ 7:1 (WCAG 2.2 AAA 1.4.6), every interactive boundary and focus indicator ≥ 3:1. There is no dark mode.

## 1. Direction

- **Subject.** A Kenyan hospital's patient journey: tickets, triage colours, ICD-11 codes, KES amounts, M-Pesa codes, ward beds.
- **The one memorable thing.** The *journey rail* — a stepped bar under the patient banner showing where this visit is (Reception → Triage → Consultation → Services → Review → Disposition → Settlement). Everything else stays quiet.
- **What we avoid.** Card soup (identical rounded cards with soft shadows), decorative gradients, all-caps labels, accent-one-word headlines, monospace used as decoration, arrows appended to every button, cream/terracotta palettes.
- **Density.** Comfortable by default; "compact" density toggle for clinicians and cashiers who live in tables.

## 2. Colour tokens

Every ratio below was computed with the WCAG 2.x relative-luminance formula; §2.4 describes the CI check that keeps them true. Do not introduce colours outside this table; propose a token change instead.

### 2.1 Base

| Token | Hex | Use |
|---|---|---|
| `--canvas` | `#F4F6F8` | app background (cool grey, never cream) |
| `--surface` | `#FFFFFF` | panels, tables, inputs, dialogs |
| `--surface-sunken` | `#E6EAEF` | table headers, read-only fields, side rails |
| `--surface-hover` | `#EEF2F6` | row hover |
| `--selected` | `#DCE9F8` | selected rows, active nav item (ink text only) |
| `--ink` | `#0B1220` | primary text and icons (deep blue-black: less halation than pure black on glossy screens, harmonises with primary) |
| `--ink-muted` | `#3A4556` | secondary text, helper text — the lightest colour allowed for text |
| `--ink-disabled` | `#5B6575` | disabled text (exempt from contrast rules, still legible) |
| `--border-strong` | `#6B7685` | input and control boundaries, table outer border |
| `--border-subtle` | `#C9CFD8` | decorative separators only — never the only cue for a control |
| `--primary` | `#0B4F9C` | primary actions, links, current journey step |
| `--primary-hover` | `#083D7A` | hover/pressed primary |
| `--primary-tint` | `#E8F1FB` | info callouts, completed journey steps |
| `--on-primary` | `#FFFFFF` | text on primary |
| `--danger` | `#A3121A` | destructive actions, critical values |
| `--danger-tint` / `--danger-ink` | `#FDECEC` / `#9B1111` | error callouts, field errors |
| `--success` | `#086129` | confirm/complete actions |
| `--success-tint` / `--success-ink` | `#E7F4EC` / `#0A5C2B` | success callouts |
| `--warning` | `#FFC20E` | warning solid (ink text only) |
| `--warning-tint` / `--warning-ink` | `#FFF4D6` / `#6B4500` | warning callouts |
| `--focus-inner` | `#0B1220` | 2 px inner focus ring |
| `--focus-outer` | `#FFD400` | 2 px outer focus halo |
| `--link-visited` | `#5B2A86` | visited links in documents/reports |

### 2.2 Triage

Staff say "she's a red". Show the colour **and** the word **and** a shape icon; never colour alone.

| Token | Background | Text | Label (adult, SATS-style) | Label (paediatric, ETAT+) | Icon |
|---|---|---|---|---|---|
| `--triage-red` | `#B00020` | `#FFFFFF` | Red (emergency) | Emergency | octagon |
| `--triage-orange` | `#F28C28` | `#0B1220` | Orange (very urgent) | — | triangle |
| `--triage-yellow` | `#FFD100` | `#0B1220` | Yellow (urgent) | Priority | diamond |
| `--triage-green` | `#3FB86B` | `#0B1220` | Green (routine) | Non-urgent | circle |
| `--triage-blue` | `#0050B5` | `#FFFFFF` | Blue (dead on arrival) | — | square |

Scales and labels are facility configuration (KE-MOH-05); tokens stay fixed.

### 2.3 Verified contrast (selected pairs)

| Pair | Ratio | Requirement |
|---|---|---|
| ink on surface / canvas | 18.72 / 17.28 | ≥ 7 ✔ |
| ink-muted on surface / canvas / sunken | 9.70 / 8.95 / 8.03 | ≥ 7 ✔ |
| ink on selected / sunken / hover | 15.21 / 15.50 / 16.64 | ≥ 7 ✔ |
| on-primary on primary / primary-hover | 8.04 / 10.72 | ≥ 7 ✔ |
| primary text on surface / canvas | 8.04 / 7.42 | ≥ 7 ✔ |
| primary on primary-tint | 7.04 | ≥ 7 ✔ |
| white on danger / success | 7.90 / 7.63 | ≥ 7 ✔ |
| danger-ink on danger-tint / success-ink on success-tint / warning-ink on warning-tint | 7.41 / 7.19 / 7.74 | ≥ 7 ✔ |
| ink on warning | 11.57 | ≥ 7 ✔ |
| triage text on red / orange / yellow / green / blue | 7.33 / 7.63 / 12.81 / 7.38 / 7.46 | ≥ 7 ✔ |
| border-strong on surface / canvas / sunken | 4.61 / 4.26 / 3.82 | ≥ 3 ✔ |
| focus: inner ink on surface; outer yellow on primary / danger / ink | 18.72; 5.61 / 5.52 / 13.08 | ≥ 3 ✔ (one ring always contrasts with its neighbour) |
| primary text on selected | 6.53 | ✘ — use ink on `--selected` |
| divider on surface | 1.57 | decorative only |

### 2.4 Contrast check script
`web/scripts/check-contrast.mjs` recomputes every pair from `tokens.css` in CI and fails below the thresholds above. Write it in Phase 1 (P1-WEB-02).

## 3. Typography

- **Family: Atkinson Hyperlegible Next** (Braille Institute; Google Fonts; self-hosted through `next/font`). Chosen because it separates confusable glyphs (I l 1, O 0, rn m) — the errors that matter in drug names, doses, IDs and M-Pesa codes. One family for everything.
- **Numbers:** `font-variant-numeric: tabular-nums` in tables, money, vitals and doses. If the installed font build lacks tabular figures (check in Phase 1), use **Atkinson Hyperlegible Mono** for numeric table cells and amounts only — for alignment, not decoration.
- **Scale (major third upward from a 16 px base):** 16 (body, inputs), 20 (section headings), 25 (page title), 31 (dashboard headline numbers), 39+ (queue boards; ticket numbers at 96 px). Secondary text and table meta use 14 px, which is also the floor — nothing smaller.
- **Weights:** 400 body, 600 labels and emphasis, 700 headings and the patient name.
- **Line height:** 1.5 body, 1.25 headings, 1.35 dense tables. Line length ≤ 75 characters for notes and reports.
- **Case:** sentence case everywhere — headings, buttons, labels, tabs. No all-caps labels.

## 4. Space, shape, depth, motion

- **Spacing scale (px):** 4, 8, 12, 16, 20, 24, 32, 40, 48, 64. Layout gutters 24 (comfortable) / 16 (compact).
- **Radius by hierarchy:** controls (inputs, buttons, chips) 4 px; panels and tables 0 (they sit flush on the canvas, separated by rules); floating overlays (menus, popovers, dialogs, toasts) 8 px; status pills full round. Never one radius for everything.
- **Borders:** 1 px `--border-strong` for controls; 1 px `--border-subtle` for separators; 4 px coloured left rail for status on list rows (triage colour on queue rows, red rail on critical results).
- **Depth (Flat 2.0):** level 0 page content — no shadow; level 1 sticky table headers and the patient banner — `0 1px 0 var(--border-subtle)`; level 2 menus/popovers — `0 4px 12px rgb(11 18 32 / 16%)` + 1 px border; level 3 dialogs — `0 12px 32px rgb(11 18 32 / 24%)` over a `rgb(11 18 32 / 55%)` scrim.
- **Motion:** 120 ms ease-out for state changes, 200 ms for overlays. Motion only answers user actions (open, expand, confirm). No entrance animations, parallax or decorative loops. `prefers-reduced-motion: reduce` → 0 ms.

## 5. Focus, states and accessibility

- **Focus ring:** `outline: 2px solid var(--focus-inner); outline-offset: 0; box-shadow: 0 0 0 4px var(--focus-outer);` on `:focus-visible`. Never remove outlines.
- **States:** hover changes background (`--surface-hover`) not just colour of text; pressed darkens primary to `--primary-hover`; selected uses `--selected` + a 4 px primary left rail; disabled uses `--ink-disabled` and keeps a visible border; invalid fields use a 2 px `--danger` border + icon + message below (never colour alone).
- **Targets:** ≥ 24 × 24 px everywhere (WCAG 2.5.8); ≥ 44 × 44 px on touch stations (triage tablets, ward tablets).
- **Forced colours:** support `@media (forced-colors: active)`: use system colours, keep borders on all controls, triage tags keep their text and icon.
- **Screen readers:** every icon-only button has an accessible name; live regions for queue calls, toasts and critical alerts (`aria-live="assertive"` only for critical lab values and emergency arrivals).
- **Gate:** axe-core (serious + critical = 0) on every Playwright scenario page; the contrast script in CI.

## 6. Layout

### 6.1 App shell

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Facility ▾   Workspace: Consultation ▾          Search patient (/)   Dr. A ▾│  top bar 56px
├────────┬─────────────────────────────────────────────────────────────────┤
│ Nav    │ Patient banner: Wanjiru Kamau · F · 34y · MRN 13019-26-000412     │  only in patient context
│ rail   │ Allergy: Penicillin │ Alert: Pregnant │ Payer: SHA (SHIF) verified │
│ 72px   ├─────────────────────────────────────────────────────────────────┤
│ icons  │ Journey: Reception ✓ ─ Triage ✓ ─ Consultation ● ─ Services ─ Review ─ Disposition ─ Settlement │
│ +labels├───────────────────────┬─────────────────────────────────────────┤
│        │ Worklist (360px)      │ Work pane                                │
│        │ queue / tasks         │ forms, notes, results                    │
└────────┴───────────────────────┴─────────────────────────────────────────┘
```

Content is left-aligned. Numbers in tables are right-aligned. The patient banner and journey rail are sticky inside the work pane.

### 6.2 Reception (keyboard-first)

```
┌ Search: [ ID / name / phone / MRN ____________ ]  [Search registry]  ┐
│ Results (local first, then Client Registry):                         │
│  ▸ Wanjiru Kamau  F 34y  ID ••••5678  MRN …412  last visit 02/10/26  │
│  ▸ (Client Registry) Wanjiru K. Kamau  F 34y  CR…-4                  │
│ [Register new patient]  (enabled after a search)                     │
├──────────────────────────────────────────────────────────────────────┤
│ Visit: type [OPD ▾] service point [Consultation 2 ▾] payer [SHA ▾]   │
│ Eligibility: ✓ SHIF active · consent: [Send OTP] [Use biometrics]    │
│ [Open visit] → prints ticket C2-014                                  │
└──────────────────────────────────────────────────────────────────────┘
```

### 6.3 Cashier

```
┌ Shift: open since 07:58 · float 5,000.00 ─────────────── [Close shift] ┐
│ Due now (queue)                │ Bill for C2-014 Wanjiru Kamau         │
│  C2-014  consultation 1,500.00 │  Consultation           1,500.00      │
│  L-009   lab FBC        800.00 │  Patient pays           1,500.00      │
│                                │  Method: (•) M-Pesa ( ) Cash ( ) Card │
│                                │  Phone +254 7•• ••• 678 [Send prompt] │
│                                │  Status: waiting for PIN … 00:23      │
└────────────────────────────────┴──────────────────────────────────────┘
```

### 6.4 Queue board (TV, read-only)
Two columns: "Now serving" (ticket, room, 96 px numerals) and "Next" (tickets only). No names. Audible chime + spoken ticket number (Web Speech, optional).

## 7. Components

Build in `web/src/components/ui/` on Radix primitives; restyle to these tokens. Each component ships with a Vitest test and a catalogue entry on `/design`.

| Component | Spec |
|---|---|
| Button | Variants: primary (solid), secondary (surface + strong border), quiet (no border, underline on hover), danger (solid), success (solid). Height 40 (comfortable) / 32 (compact). Label is the verb: "Open visit", "Record vitals", "Release result", "Dispense", "Receive payment". Loading state keeps width and shows a spinner + "Saving…". |
| Field | Label above input (never placeholder-as-label), optional hint below, error below with icon. Required marked with "(required)" text, not just an asterisk. |
| Input variants | MoneyInput (KES, 2 dp, right-aligned, tabular), PhoneInput (+254 normalisation, masked display), IdentifierInput (type select + value + checksum hints), DateInput (DD/MM/YYYY typed entry + picker; estimated DOB toggle with age in years/months), DoseInput (quantity + unit + frequency + duration). |
| Select / Combobox | Typeahead with keyboard selection; async search for patients, ICD-11, drugs, services; shows code + title for coded items (`DA42.Z Gastritis, unspecified`). |
| DataTable | Sticky header on `--surface-sunken`; zebra off; row hover `--surface-hover`; selection with left rail; keyboard row navigation (↑/↓, Enter opens); column sort; right-aligned numbers; empty state with the next action. |
| Tabs | Underline style (2 px primary under the active tab); sentence case. |
| StatusPill | Full-round chip with text + icon; colour from semantic tokens. |
| TriageTag | Solid triage colour, text label, shape icon; also used as a 4 px rail on queue rows. |
| Callout | Tinted background + left 4 px rail + icon + title + body; info/success/warning/danger. |
| Toast | Bottom-right, 8 px radius, level-2 shadow; text repeats the action verb ("Dispensed 2 items"); critical toasts persist until dismissed. |
| Dialog / Drawer | Level-3; focus trapped; Esc closes unless it would lose unsaved clinical data (then ask). |
| PatientBanner | Name (700 weight, 20 px), sex, age (and DOB on hover/focus), MRN, CR/SHA badge, allergies (danger tint when present; "No known allergies" explicitly recorded vs "Allergies not recorded" warning), alerts, payer + verification state. Two identifiers always visible. |
| JourneyRail | The signature element. Seven steps; completed steps tinted `--primary-tint` with a check; current step solid `--primary` with on-primary text; future steps outlined. Clicking a completed step opens its record. Emergency visits show a red "Emergency" marker at the start. |
| QueueList | Ticket, name, age/sex, wait time, triage rail, payer chip; "Call next" primary button; overdue waits highlighted with warning tint after the facility threshold. |
| VitalsGrid | Values with units and reference flags (↑ ↓ in text, not colour alone); critical values red rail + assertive announcement. |
| ResultView | Lab results table with reference range, flag, unit; amended results show "Amended" pill and history. |
| Timeline | Visit/encounter history; filter by type; sensitive items hidden unless permitted ("1 item hidden — sensitive category"). |
| Print layouts | `@media print` styles: 80 mm thermal receipt, A4 invoice, lab report, prescription, discharge summary, referral letter, claim form. Black on white, facility header, page numbers, no navigation. |

## 8. Keyboard

| Keys | Action |
|---|---|
| `/` | Focus patient search |
| `Alt+N` | New visit (reception) |
| `Alt+C` | Call next ticket |
| `Alt+V` | Record vitals |
| `Alt+O` | New order |
| `Alt+P` | New prescription |
| `Alt+S` | Save / sign current form |
| `Alt+L` | Lock workstation |
| `?` | Shortcut help |

Shortcuts are listed in the help dialog and never override browser/system essentials.

## 9. Writing

- Name things the way staff do: "Visit", "Ticket", "Bill", "Receipt", "Claim", "Ward", "Bed", "Prescription".
- Buttons say exactly what happens; the same verb carries through the flow (button "Release result" → toast "Result released").
- Errors say what happened and what to do: "This ID is already on Wanjiru Kamau's record. Open that record, or request a merge." Errors don't apologise and are never vague.
- Empty states invite the next action: "No patients waiting. New arrivals appear here when reception opens a visit."
- No clinical abbreviations that the Kenyan MOH or ISMP lists as error-prone in dose fields (e.g. write "units", not "U"; "daily", not "QD").

## 10. Implementation

`web/src/styles/tokens.css` (Tailwind v4 `@theme`):

```css
@import "tailwindcss";

@theme {
  --color-canvas: #F4F6F8;
  --color-surface: #FFFFFF;
  --color-surface-sunken: #E6EAEF;
  --color-surface-hover: #EEF2F6;
  --color-selected: #DCE9F8;
  --color-ink: #0B1220;
  --color-ink-muted: #3A4556;
  --color-ink-disabled: #5B6575;
  --color-border-strong: #6B7685;
  --color-border-subtle: #C9CFD8;
  --color-primary: #0B4F9C;
  --color-primary-hover: #083D7A;
  --color-primary-tint: #E8F1FB;
  --color-danger: #A3121A;
  --color-danger-tint: #FDECEC;
  --color-danger-ink: #9B1111;
  --color-success: #086129;
  --color-success-tint: #E7F4EC;
  --color-success-ink: #0A5C2B;
  --color-warning: #FFC20E;
  --color-warning-tint: #FFF4D6;
  --color-warning-ink: #6B4500;
  --color-focus-inner: #0B1220;
  --color-focus-outer: #FFD400;
  --color-triage-red: #B00020;
  --color-triage-orange: #F28C28;
  --color-triage-yellow: #FFD100;
  --color-triage-green: #3FB86B;
  --color-triage-blue: #0050B5;
  --radius-control: 4px;
  --radius-overlay: 8px;
  --font-sans: "Atkinson Hyperlegible Next", system-ui, sans-serif;
}

:root { color-scheme: light; background: var(--color-canvas); color: var(--color-ink); }
:focus-visible { outline: 2px solid var(--color-focus-inner); box-shadow: 0 0 0 4px var(--color-focus-outer); }
@media (prefers-reduced-motion: reduce) { * { transition-duration: 0ms !important; animation-duration: 0ms !important; } }
```

Verify Tailwind v4 `@theme` syntax and `next/font` usage against the installed versions' docs before writing them.
