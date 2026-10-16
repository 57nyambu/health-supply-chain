// WCAG 2.x relative luminance and contrast ratio (https://www.w3.org/TR/WCAG22/#dfn-contrast-ratio).

export function parseHex(hex) {
  const value = hex.trim().replace(/^#/, "");
  const full = value.length === 3 ? [...value].map((c) => c + c).join("") : value;
  if (!/^[0-9a-fA-F]{6}$/.test(full)) throw new Error(`Not a 6-digit hex colour: ${hex}`);
  return [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16));
}

export function luminance(hex) {
  const [r, g, b] = parseHex(hex).map((channel) => {
    const c = channel / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrast(foreground, background) {
  const [light, dark] = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
  return (light + 0.05) / (dark + 0.05);
}

/** `--color-name: #hex;` declarations from a CSS file. */
export function readTokens(css) {
  const tokens = {};
  for (const match of css.matchAll(/--color-([a-z0-9-]+):\s*(#[0-9a-fA-F]{3,6})\s*;/g)) {
    tokens[match[1]] = match[2];
  }
  return tokens;
}

const TEXT = 7; // WCAG 2.2 AAA 1.4.6 — every text pair (DESIGN-SYSTEM §2)
const UI = 3; // control boundaries and focus indicators

/** The pairs DESIGN-SYSTEM §2.3 requires, as [foreground, background, minimum]. */
export const PAIRS = [
  ...["surface", "canvas", "selected", "surface-sunken", "surface-hover"].map((bg) => ["ink", bg, TEXT]),
  ...["surface", "canvas", "surface-sunken"].map((bg) => ["ink-muted", bg, TEXT]),
  ["on-primary", "primary", TEXT],
  ["on-primary", "primary-hover", TEXT],
  ...["surface", "canvas", "primary-tint"].map((bg) => ["primary", bg, TEXT]),
  ["on-primary", "danger", TEXT],
  ["on-primary", "success", TEXT],
  ["danger-ink", "danger-tint", TEXT],
  ["success-ink", "success-tint", TEXT],
  ["warning-ink", "warning-tint", TEXT],
  ["ink", "warning", TEXT],
  ...["red", "orange", "yellow", "green", "blue"].map((c) => [`triage-${c}-text`, `triage-${c}`, TEXT]),
  ...["surface", "canvas", "surface-sunken"].map((bg) => ["border-strong", bg, UI]),
  ["focus-inner", "surface", UI],
  ...["primary", "danger", "ink"].map((bg) => ["focus-outer", bg, UI]),
];

export function check(tokens, pairs = PAIRS) {
  return pairs.map(([fg, bg, minimum]) => {
    if (!tokens[fg] || !tokens[bg]) return { fg, bg, minimum, ratio: 0, ok: false, missing: true };
    const ratio = contrast(tokens[fg], tokens[bg]);
    return { fg, bg, minimum, ratio, ok: ratio >= minimum };
  });
}
