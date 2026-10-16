export type Pair = [foreground: string, background: string, minimum: number];
export type Result = { fg: string; bg: string; minimum: number; ratio: number; ok: boolean; missing?: boolean };
export function parseHex(hex: string): [number, number, number];
export function luminance(hex: string): number;
export function contrast(foreground: string, background: string): number;
export function readTokens(css: string): Record<string, string>;
export const PAIRS: Pair[];
export function check(tokens: Record<string, string>, pairs?: Pair[]): Result[];
