# i18n retrofit spec (UI-7) — shared conventions for localizing config-ui

The i18n foundation is already built and green (`react-i18next`, `en`+`ru` bundles, a live `LanguageSwitcher`).
This doc is the contract every retrofit slice follows so the result is consistent. **Read it fully before editing.**

## What you are doing
Replace every **user-facing English string** in your assigned files with an i18n key, and add that key to **both**
`src/i18n/locales/en/<ns>.ts` and `src/i18n/locales/ru/<ns>.ts`. The English value is the *existing* text verbatim;
the Russian value is a natural, fluent translation.

## The mechanism
- Hook: `import { useTranslation } from 'react-i18next';` then inside the component
  `const { t } = useTranslation('<ns>');` — `<ns>` is your namespace (e.g. `donations`).
- Use: `t('some.key')`. For a **generic** shared string use the `common` namespace explicitly:
  `const { t } = useTranslation(['<ns>', 'common']);` and call `t('common:actions.save')`.
- Interpolation: English `` `Found ${n} issues` `` → key value `'Found {{count}} issues'`, call `t('key', { count: n })`.
- Pluralization: keep it simple — if the source did `${n} warning${n!==1?'s':''}`, use i18next plurals
  (`key_one`/`key_other`) **only if trivial**; otherwise a single neutral phrasing is fine.

## Key naming
- Group by component or concept: `t('cards.kind.word.label')`, `t('validation.title')`, `t('actions.addWord')`.
- Reuse `common` for truly generic verbs/states (see the `common` namespace: `actions.*`, `status.*`). Don't
  duplicate "Save"/"Cancel"/"Loading…" into your namespace — call `common:actions.save` etc.

## RU bundle parity (IMPORTANT)
`src/i18n/locales/ru/index.ts` is typed `DeepStringify<typeof en>`, so **every key you add to `en/<ns>.ts` must
also exist (same nesting) in `ru/<ns>.ts`** or the build fails. Add to both, together.

## Do NOT translate technical identifiers
Keep these **verbatim, in English/as-is** (they are canonical, self-matching, or code):
- model / driver / service / provider / component names; intent and method names (`timer.set`).
- slot labels (`DURATION_VALUE`), spaCy attribute names (`LEMMA`, `IS_ALPHA`), JSON/config keys, file names.
- anything rendered in `<code>` or `font-mono`, and the donation **content** values themselves.
Translate prose, labels, buttons, headings, help text, placeholders, validation/empty-state messages, tooltips
(`title=`/`aria-label=`).

## Boundaries — do not touch
- Never edit: `src/i18n/index.ts`, `src/i18n/config.ts`, `src/i18n/types.ts`, `src/i18n/i18next.d.ts`,
  `src/i18n/locales/en/index.ts`, `src/i18n/locales/ru/index.ts`, or **any namespace file that isn't yours**.
- Only edit the component/page files in **your assigned list** and your `en/<ns>.ts` + `ru/<ns>.ts`.
- The namespace key already exists in both `en/index.ts` and `ru/index.ts` — just fill the seeded `{}` object.

## Verify before you finish
Run `npm run type-check` (from `config-ui/`). It must pass with **zero errors**. The typed `t()` will flag any
mistyped key, and the RU parity type will flag any missing translation. Also glance that no obvious English remains
in your files. Do not run `npm run build` (not needed). Report what you changed.
