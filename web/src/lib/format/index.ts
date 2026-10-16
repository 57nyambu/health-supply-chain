/**
 * Display formats (web/CLAUDE.md): KES from API decimal strings without float arithmetic,
 * DD/MM/YYYY and 24-hour time in Africa/Nairobi, masked phone numbers.
 */

const TIME_ZONE = "Africa/Nairobi";
const MONEY = /^(-)?(\d+)(?:\.(\d{1,2}))?$/;

/** "1500" | "1500.5" | "-12.00" → "KES 1,500.00" (string arithmetic only). */
export function formatKES(amount: string, { currency = true }: { currency?: boolean } = {}): string {
  const match = MONEY.exec(amount.trim());
  if (!match) throw new Error("formatKES expects a decimal string with at most 2 decimals");
  const [, sign, whole = "0", fraction = ""] = match;
  const grouped = whole.replace(/^0+(?=\d)/, "").replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const text = `${grouped}.${fraction.padEnd(2, "0")}`;
  const signed = sign && /[1-9]/.test(whole + fraction) ? `-${text}` : text;
  return currency ? `KES ${signed}` : signed;
}

/** Normalise typed money ("1,500.5") to the API's decimal string ("1500.50"), or null. */
export function parseKES(input: string): string | null {
  const cleaned = input.replace(/[,\s]/g, "").replace(/^KES/i, "");
  const match = MONEY.exec(cleaned);
  if (!match || match[1]) return null;
  return `${(match[2] ?? "0").replace(/^0+(?=\d)/, "")}.${(match[3] ?? "").padEnd(2, "0")}`;
}

function parts(value: Date | string, options: Intl.DateTimeFormatOptions) {
  const date = typeof value === "string" ? new Date(value) : value;
  const formatted = new Intl.DateTimeFormat("en-GB", { timeZone: TIME_ZONE, ...options }).formatToParts(date);
  return Object.fromEntries(formatted.map((p) => [p.type, p.value]));
}

/** ISO date ("1990-04-12") or timestamp → "12/04/1990" (dates of birth have no time zone). */
export function formatDate(value: Date | string): string {
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [y, m, d] = value.split("-");
    return `${d}/${m}/${y}`;
  }
  const p = parts(value, { day: "2-digit", month: "2-digit", year: "numeric" });
  return `${p.day}/${p.month}/${p.year}`;
}

/** Timestamp → "14:05" in Africa/Nairobi. */
export function formatTime(value: Date | string): string {
  const p = parts(value, { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
  return `${p.hour}:${p.minute}`;
}

export function formatDateTime(value: Date | string): string {
  return `${formatDate(value)} ${formatTime(value)}`;
}

/** Typed "DD/MM/YYYY" → ISO "YYYY-MM-DD", or null when not a real date. */
export function parseDate(input: string): string | null {
  const match = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(input.trim());
  if (!match) return null;
  const [, d, m, y] = match.map(Number) as [number, number, number, number];
  const date = new Date(Date.UTC(y, m - 1, d));
  if (date.getUTCFullYear() !== y || date.getUTCMonth() !== m - 1 || date.getUTCDate() !== d) return null;
  return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

/** Kenyan phone → E.164 ("0712 345 678" → "+254712345678"), or null. */
export function normalisePhone(input: string): string | null {
  const digits = input.replace(/[\s()-]/g, "");
  const match = /^(?:\+?254|0)?([17]\d{8})$/.exec(digits);
  return match ? `+254${match[1]}` : null;
}

/** "+254712345678" → "+254 7•• ••• 678" (DESIGN-SYSTEM §6.3). */
export function maskPhone(e164: string): string {
  const match = /^\+254(\d)(\d{5})(\d{3})$/.exec(e164);
  return match ? `+254 ${match[1]}•• ••• ${match[3]}` : "•••";
}

/** Age text from an ISO date of birth: "34y", or months under two years ("18m"). */
export function ageText(dateOfBirth: string, today: Date = new Date()): string {
  const [y, m, d] = dateOfBirth.split("-").map(Number) as [number, number, number];
  const p = parts(today, { day: "numeric", month: "numeric", year: "numeric" });
  const ty = Number(p.year), tm = Number(p.month), td = Number(p.day);
  const months = (ty - y) * 12 + (tm - m) - (td < d ? 1 : 0);
  return months >= 24 ? `${Math.floor(months / 12)}y` : `${Math.max(months, 0)}m`;
}
