# web/ — frontend rules

Loaded when you work under `web/`. The root `CLAUDE.md` still applies. Visual rules: `docs/agent/DESIGN-SYSTEM.md`.

## Stack
- Next.js 16 (App Router, latest 16.x patch), React 19, TypeScript strict, pnpm.
- Tailwind CSS 4 with tokens from `src/styles/tokens.css` (DESIGN-SYSTEM §10). No raw hex colours in components.
- Radix UI primitives wrapped as owned components in `src/components/ui/`; lucide icons.
- Data: Server Components for initial page data where it keeps things simple; TanStack Query in client components; typed client generated from `api/openapi.yaml` (`openapi-typescript` + `openapi-fetch`) in `src/lib/api/`.
- Forms: react-hook-form + zod (mirrors API validation; the API stays authoritative).
- Tests: Vitest + Testing Library; Playwright for scenarios; `@axe-core/playwright` for accessibility.
- Check version-specific APIs (request interception file naming, caching defaults, `next/font`, Tailwind 4 `@theme`) against the installed versions' docs before writing them.

## Structure
```
src/app/(public)/login · mfa · locked
src/app/(workspace)/layout.tsx          session + permissions gate, app shell
src/app/(workspace)/reception · triage · consult · lab · imaging · pharmacy · wards
                    cashier · billing · claims · inventory · reports · admin
src/app/design/                          token and component catalogue (dev/admin only)
src/components/ui/ · clinical/ · finance/
src/lib/api/ · auth/ · format/ (KES, dates, phones)
tests/e2e/scenarios/                     one spec per COMPLETION.md scenario
```

## Rules
- The API enforces access. The UI only hides what `/api/v1/me` says the user can't do — never rely on the UI to protect data.
- Same origin: the browser calls `/api/*` (Next rewrites in dev, nginx in prod). Session cookie is httpOnly. Never put tokens or PHI in localStorage, sessionStorage or IndexedDB.
- No PHI in URLs (use opaque UUIDs), document titles, analytics, console output or error reports.
- PHI pages are dynamic with `Cache-Control: no-store`; never statically generate them.
- Every patient-scoped screen shows `<PatientBanner>` (two identifiers, allergies state, alerts, payer) and `<JourneyRail>`.
- Money via `formatKES()` on API decimal strings; no float arithmetic on money in the browser.
- Dates DD/MM/YYYY, 24-hour time, Africa/Nairobi.
- Keyboard-first: every workflow completes without a mouse; shortcuts per DESIGN-SYSTEM §8.
- No card input fields anywhere — card payments use the provider's hosted page.
- Copy follows DESIGN-SYSTEM §9: sentence case, verbs on buttons, specific errors, no all-caps labels.
- Light mode only; support `forced-colors: active` and `prefers-reduced-motion`.

## Done means
The feature's Playwright path passes with axe clean (serious/critical = 0), `pnpm lint`, `tsc --noEmit` and Vitest pass, and the screen matches DESIGN-SYSTEM (screenshot reviewed). New screens get a screenshot link in PROGRESS.md.
