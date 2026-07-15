/**
 * i18n config (UI-7) — the UI-language axis, orthogonal to the donation *content* language (LanguageTabs).
 *
 * Default = `ru` (the product is Russian-first), fallback = `en` (covers any not-yet-translated key).
 * Since UI-17 the active locale comes from the Workbench shell (chrome owns the switch and its
 * persistence) — the plugin only mirrors the signal.
 */

export const SUPPORTED_LNGS = ['ru', 'en'] as const;
export type UiLang = (typeof SUPPORTED_LNGS)[number];

export const DEFAULT_LNG: UiLang = 'ru';
export const FALLBACK_LNG: UiLang = 'en';

export function isUiLang(v: unknown): v is UiLang {
  return typeof v === 'string' && (SUPPORTED_LNGS as readonly string[]).includes(v);
}
