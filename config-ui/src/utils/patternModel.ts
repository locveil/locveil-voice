/**
 * patternModel (UI-2) — the bidirectional translation layer between the human "word card" model and raw spaCy
 * token patterns. Pure, frontend-only, no spaCy runtime (settled in UI-1 §4).
 *
 *   decompile: spaCy token dict  ->  friendly Card   (for editing)
 *   compile:   friendly Card     ->  spaCy token dict (for saving)
 *
 * **Lossless by construction.** Every friendly card preserves enough of its source encoding to reproduce the
 * exact original dict, and anything the cards can't represent is stored verbatim in an `advanced` card. So the
 * round-trip invariant `compile(decompile(x))` deep-equals `x` for EVERY token (proven by patternModel.test.ts
 * against all 28 real phrasing files). The card vocabulary mirrors UI-1 §3.2 / §3.3; this module is what UI-3's
 * editor sits on. Persona-facing labels/help live in UI-3 — this module is logic only.
 */

export type SpacyToken = Record<string, unknown>;
export type SpacyPattern = SpacyToken[]; // one "way of saying it" (a token_patterns entry / slot pattern / etc.)

/** Which spaCy attribute a word/one-of card came from. Preserved so round-trip is exact; the UI surfaces only the
 *  LEMMA-vs-not distinction ("include its forms"), never TEXT-vs-LOWER. */
export type Attr = 'TEXT' | 'LOWER' | 'LEMMA';

export type Card =
  | { kind: 'word'; attr: Attr; word: string; optional?: boolean; repeat?: boolean }
  | { kind: 'oneOf'; attr: Attr; via: 'in' | 'regex'; words: string[]; optional?: boolean; repeat?: boolean }
  | { kind: 'number'; via: 'likeNum' | 'regex'; regex?: string; optional?: boolean; repeat?: boolean }
  | { kind: 'anyWord'; optional?: boolean; repeat?: boolean }
  | { kind: 'rest'; optional?: boolean; repeat?: boolean }
  | { kind: 'advanced'; raw: SpacyToken };

export type CardPattern = Card[];

const ATTRS: Attr[] = ['TEXT', 'LOWER', 'LEMMA'];
const DIGIT_REGEXES = new Set(['^\\d+$', '\\d+']); // §3.3: digit regexes shown as "a number"
const REST_REGEX = '.*';
// Regex metacharacters that disqualify a REGEX value from being a plain "a|b|c" alternation.
const META = /[\\^$.*+?()[\]{}]/;

// ----- small type guards (keep the strict type-checked lint happy) -----

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}
function isStringArray(v: unknown): v is string[] {
  return Array.isArray(v) && v.every((x) => typeof x === 'string');
}
/** A single-key wrapper value like `{IN:[…]}` or `{REGEX:"…"}`. */
function singleKey(v: unknown): [string, unknown] | null {
  if (!isRecord(v)) return null;
  const keys = Object.keys(v);
  return keys.length === 1 ? [keys[0], v[keys[0]]] : null;
}
function isPureAlternation(r: string): boolean {
  if (r.length === 0 || META.test(r)) return false;
  const parts = r.split('|');
  return parts.every((p) => p.length > 0) && parts.join('|') === r;
}

// ----- decompile: spaCy token -> Card -----

export function decompileToken(token: SpacyToken): Card {
  // OP only models optional(?)/repeat(+). Anything else (*, !, non-string) -> advanced (verbatim).
  let optional = false;
  let repeat = false;
  let rest: SpacyToken = token;
  if ('OP' in token) {
    const op = token.OP;
    if (op === '?') optional = true;
    else if (op === '+') repeat = true;
    else return { kind: 'advanced', raw: token };
    const clone = { ...token };
    delete clone.OP;
    rest = clone;
  }

  const mods = { optional: optional || undefined, repeat: repeat || undefined };
  const adv: Card = { kind: 'advanced', raw: token };

  // Friendly cards have EXACTLY one attribute key.
  const entries = Object.entries(rest);
  if (entries.length !== 1) return adv;
  const [key, value] = entries[0];

  if (key === 'LIKE_NUM' && value === true) return { kind: 'number', via: 'likeNum', ...mods };
  if (key === 'IS_ALPHA' && value === true) return { kind: 'anyWord', ...mods };

  if ((ATTRS as string[]).includes(key)) {
    const attr = key as Attr;
    // plain string -> a word
    if (typeof value === 'string') return { kind: 'word', attr, word: value, ...mods };
    const wrap = singleKey(value);
    if (wrap) {
      const [wk, wv] = wrap;
      if (wk === 'IN' && isStringArray(wv)) return { kind: 'oneOf', attr, via: 'in', words: wv, ...mods };
      if (wk === 'REGEX' && typeof wv === 'string') {
        if (attr === 'TEXT' && wv === REST_REGEX) return { kind: 'rest', ...mods };
        if (attr === 'TEXT' && DIGIT_REGEXES.has(wv)) return { kind: 'number', via: 'regex', regex: wv, ...mods };
        if (isPureAlternation(wv)) return { kind: 'oneOf', attr, via: 'regex', words: wv.split('|'), ...mods };
      }
    }
  }
  return adv;
}

// ----- compile: Card -> spaCy token -----

function withOp(tok: SpacyToken, card: { optional?: boolean; repeat?: boolean }): SpacyToken {
  if (card.optional) tok.OP = '?';
  else if (card.repeat) tok.OP = '+';
  return tok;
}

export function compileToken(card: Card): SpacyToken {
  switch (card.kind) {
    case 'advanced':
      return card.raw;
    case 'word':
      return withOp({ [card.attr]: card.word }, card);
    case 'oneOf':
      return withOp(
        card.via === 'in'
          ? { [card.attr]: { IN: card.words } }
          : { [card.attr]: { REGEX: card.words.join('|') } },
        card,
      );
    case 'number':
      return withOp(card.via === 'likeNum' ? { LIKE_NUM: true } : { TEXT: { REGEX: card.regex ?? '\\d+' } }, card);
    case 'anyWord':
      return withOp({ IS_ALPHA: true }, card);
    case 'rest':
      return withOp({ TEXT: { REGEX: REST_REGEX } }, card);
  }
}

// ----- pattern-level (a "way of saying it" = an ordered list of tokens) -----

export function decompilePattern(pattern: SpacyPattern): CardPattern {
  return pattern.map(decompileToken);
}
export function compilePattern(cards: CardPattern): SpacyPattern {
  return cards.map(compileToken);
}
export function decompilePatterns(patterns: SpacyPattern[]): CardPattern[] {
  return patterns.map(decompilePattern);
}
export function compilePatterns(patterns: CardPattern[]): SpacyPattern[] {
  return patterns.map(compilePattern);
}

// ----- slot_patterns: { LABEL: SpacyPattern[] } <-> { LABEL: CardPattern[] } -----

export function decompileSlots(slots: Record<string, SpacyPattern[]>): Record<string, CardPattern[]> {
  const out: Record<string, CardPattern[]> = {};
  for (const [label, patterns] of Object.entries(slots)) out[label] = decompilePatterns(patterns ?? []);
  return out;
}
export function compileSlots(slots: Record<string, CardPattern[]>): Record<string, SpacyPattern[]> {
  const out: Record<string, SpacyPattern[]> = {};
  for (const [label, patterns] of Object.entries(slots)) out[label] = compilePatterns(patterns ?? []);
  return out;
}

// ----- extraction_patterns: [{ pattern: SpacyPattern, label?, …extra }] -----
// The pattern is translated; the label and any other keys are preserved verbatim (lossless), so UI-3 can group
// fillers by parameter (UI-1 §3.4) using the contract's param<->label association.

export interface ExtractionPattern {
  pattern: SpacyPattern;
  label?: string;
  [k: string]: unknown;
}
export interface FillerPattern {
  cards: CardPattern;
  label?: string;
  extra: Record<string, unknown>; // non-pattern/label keys, preserved for round-trip
}

export function decompileExtractionPattern(ep: ExtractionPattern): FillerPattern {
  const { pattern, label, ...extra } = ep;
  return { cards: decompilePattern(pattern ?? []), label, extra };
}
export function compileExtractionPattern(fp: FillerPattern): ExtractionPattern {
  const ep: ExtractionPattern = { ...fp.extra, pattern: compilePattern(fp.cards) };
  if (fp.label !== undefined) ep.label = fp.label;
  return ep;
}
export function decompileExtractionPatterns(eps: ExtractionPattern[]): FillerPattern[] {
  return (eps ?? []).map(decompileExtractionPattern);
}
export function compileExtractionPatterns(fps: FillerPattern[]): ExtractionPattern[] {
  return (fps ?? []).map(compileExtractionPattern);
}
