/** Phase 2 lane helpers for browser scenarios (ADR-024). Synthetic data only. */
import { expect, type Page } from "@playwright/test";

import { createUser, djangoShell, signIn } from "../support";

/** Sign in a fresh user with these roles, wait until the shell has loaded, then open ``path``. */
export async function signInAs(page: Page, roles: string[], path?: string): Promise<{ email: string; id: number }> {
  const user = createUser(...roles);
  await signIn(page, user.email);
  await expect(page).not.toHaveURL(/\/login/);
  await expect(page.getByRole("navigation").first()).toBeVisible();
  if (path) await page.goto(path);
  return user;
}

/** A made-up name no one else in the seed has (consonant-vowel syllables). */
export function syntheticName(syllables = 3): string {
  const consonants = "bdfghjklmnprstw";
  const vowels = "aeiou";
  let word = "";
  for (let i = 0; i < syllables; i++) {
    word += consonants[Math.floor(Math.random() * consonants.length)]! + vowels[Math.floor(Math.random() * vowels.length)]!;
  }
  return word[0]!.toUpperCase() + word.slice(1);
}

/** A synthetic patient at the seed facility, created directly (test-only); returns its id. */
export function createPatient(options: { given?: string; family?: string; sex?: "female" | "male"; dob?: string } = {}): {
  id: string;
  given: string;
  family: string;
} {
  const given = options.given ?? syntheticName();
  const family = options.family ?? syntheticName(4);
  const sex = options.sex ?? "female";
  const dob = options.dob ?? "1990-05-01";
  const id = djangoShell(
    [
      "import uuid, datetime",
      "from apps.facilities.seed import facility",
      "from apps.patients.models import Patient",
      "site = facility()",
      `p = Patient.objects.create(facility=site, mrn='E2E-' + uuid.uuid4().hex[:10].upper(), given_name='${given}', family_name='${family}', sex='${sex}', date_of_birth=datetime.date.fromisoformat('${dob}'))`,
      "print(p.pk)",
    ].join("; "),
  );
  return { id, given, family };
}

/** A queue board at the seed facility for these service point codes; returns its device token. */
export function createBoardToken(name: string, pointCodes: string[]): string {
  return djangoShell(
    [
      "from apps.facilities.seed import facility",
      "from apps.facilities.models import ServicePoint",
      "from apps.visits import services",
      "site = facility()",
      `points = list(ServicePoint.objects.filter(facility=site, code__in=${JSON.stringify(pointCodes)}))`,
      `board, token = services.create_board(facility=site, name='${name}', service_points=points, actor=None)`,
      "print(token)",
    ].join("; "),
  );
}

/** With E2E_EVIDENCE=1, save a screenshot to docs/evidence/screens/<name>.png (synthetic data). */
export async function evidence(page: Page, name: string): Promise<void> {
  if (process.env.E2E_EVIDENCE === "1") await page.screenshot({ path: `../docs/evidence/screens/${name}.png`, fullPage: true });
}
