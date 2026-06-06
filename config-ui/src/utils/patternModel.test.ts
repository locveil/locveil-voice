/**
 * patternModel tests (UI-2). Two layers:
 *  1. unit cases that lock the §3.2 / §3.3 friendly mapping (a token decompiles to the EXPECTED card);
 *  2. the required round-trip guarantee — load all 28 real phrasing files and assert
 *     `compilePattern(decompilePattern(p))` deep-equals `p` for every token pattern (lossless by construction).
 */
import { readdirSync, readFileSync, existsSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, it, expect } from 'vitest';
import {
  decompileToken,
  compileToken,
  decompilePattern,
  compilePattern,
  type SpacyToken,
  type Card,
} from './patternModel';

describe('decompileToken — the friendly mapping (§3.2/§3.3)', () => {
  const cases: Array<[string, SpacyToken, Card]> = [
    ['exact word (LOWER)', { LOWER: 'set' }, { kind: 'word', attr: 'LOWER', word: 'set' }],
    ['word + forms (LEMMA)', { LEMMA: 'set' }, { kind: 'word', attr: 'LEMMA', word: 'set' }],
    ['exact word (TEXT)', { TEXT: 'timer' }, { kind: 'word', attr: 'TEXT', word: 'timer' }],
    ['one-of (IN)', { LOWER: { IN: ['timer', 'alarm'] } }, { kind: 'oneOf', attr: 'LOWER', via: 'in', words: ['timer', 'alarm'] }],
    ['empty one-of stays editable', { LEMMA: { IN: [] } }, { kind: 'oneOf', attr: 'LEMMA', via: 'in', words: [] }],
    ['one-of from alternation regex', { TEXT: { REGEX: 'set|start|begin' } }, { kind: 'oneOf', attr: 'TEXT', via: 'regex', words: ['set', 'start', 'begin'] }],
    ['a number (LIKE_NUM)', { LIKE_NUM: true }, { kind: 'number', via: 'likeNum' }],
    ['a number (anchored digits)', { TEXT: { REGEX: '^\\d+$' } }, { kind: 'number', via: 'regex', regex: '^\\d+$' }],
    ['any word', { IS_ALPHA: true }, { kind: 'anyWord' }],
    ['the rest', { TEXT: { REGEX: '.*' } }, { kind: 'rest' }],
  ];
  for (const [name, token, card] of cases) {
    it(name, () => {
      expect(decompileToken(token)).toEqual(card);
      expect(compileToken(card)).toEqual(token); // exact round-trip
    });
  }

  it('modifiers map to OP', () => {
    expect(decompileToken({ LOWER: 'minutes', OP: '+' })).toEqual({ kind: 'word', attr: 'LOWER', word: 'minutes', repeat: true });
    expect(decompileToken({ IS_ALPHA: true, OP: '?' })).toEqual({ kind: 'anyWord', optional: true });
  });

  it('falls back to advanced (verbatim) for things the cards cannot express', () => {
    const samples: SpacyToken[] = [
      { POS: 'VERB' }, // unsupported attribute
      { IS_SENT_START: false },
      { LEMMA: 'x', POS: 'NOUN' }, // multi-attribute
      { LOWER: { NOT_IN: ['a'] } }, // unsupported value op
      { TEXT: { REGEX: '\\d{1,2}[-:]\\d{2}' } }, // complex regex
      { LIKE_NUM: true, OP: '*' }, // unsupported operator
    ];
    for (const tok of samples) {
      const card = decompileToken(tok);
      expect(card.kind).toBe('advanced');
      expect(compileToken(card)).toEqual(tok); // verbatim
    }
  });
});

// ----- the 28-file round-trip guarantee -----

const DONATIONS = resolve(process.cwd(), '..', 'assets', 'donations');

/** Recursively collect every array-of-objects (a candidate token pattern) in a parsed donation file.
 *  Non-token object arrays still round-trip (they decompile to `advanced` verbatim), so this is a superset
 *  that strengthens the losslessness guarantee. */
function collectObjectArrays(node: unknown, out: SpacyToken[][]): void {
  if (Array.isArray(node)) {
    if (node.length > 0 && node.every((x) => typeof x === 'object' && x !== null && !Array.isArray(x))) {
      out.push(node as SpacyToken[]);
    }
    for (const x of node) collectObjectArrays(x, out);
  } else if (node && typeof node === 'object') {
    for (const v of Object.values(node)) collectObjectArrays(v, out);
  }
}

function loadPhrasingFiles(): Array<{ file: string; doc: unknown }> {
  if (!existsSync(DONATIONS)) return [];
  const out: Array<{ file: string; doc: unknown }> = [];
  for (const dir of readdirSync(DONATIONS, { withFileTypes: true })) {
    if (!dir.isDirectory() || dir.name === 'backups') continue;
    for (const lang of ['en', 'ru']) {
      const p = join(DONATIONS, dir.name, `${lang}.json`);
      if (existsSync(p)) out.push({ file: `${dir.name}/${lang}.json`, doc: JSON.parse(readFileSync(p, 'utf8')) });
    }
  }
  return out;
}

describe('round-trip on the real phrasing files', () => {
  const files = loadPhrasingFiles();

  it('finds the phrasing files (sanity)', () => {
    expect(files.length).toBeGreaterThan(0);
  });

  let totalPatterns = 0;
  let totalTokens = 0;
  let friendlyTokens = 0;

  for (const { file, doc } of files) {
    it(`${file} round-trips losslessly`, () => {
      const patterns: SpacyToken[][] = [];
      collectObjectArrays(doc, patterns);
      for (const p of patterns) {
        expect(compilePattern(decompilePattern(p))).toEqual(p); // the invariant
        totalPatterns += 1;
        for (const tok of p) {
          totalTokens += 1;
          if (decompileToken(tok).kind !== 'advanced') friendlyTokens += 1;
        }
      }
    });
  }

  it('the friendly mapping actually covers most real tokens (not all advanced)', () => {
    expect(totalPatterns).toBeGreaterThan(0);
    // Guards against a trivial pass where everything decompiles to `advanced`.
    expect(friendlyTokens / Math.max(totalTokens, 1)).toBeGreaterThan(0.5);
  });
});
