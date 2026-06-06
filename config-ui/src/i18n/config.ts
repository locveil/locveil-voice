/**
 * i18n config (UI-7) — the UI-language axis, orthogonal to the donation *content* language (LanguageTabs).
 *
 * Default = `ru` (the product is Russian-first), fallback = `en` (covers any not-yet-translated key). The user's
 * choice is persisted to localStorage and restored on boot; the LanguageSwitcher writes it.
 */

export const SUPPORTED_LNGS = ['ru', 'en'] as const;
export type UiLang = (typeof SUPPORTED_LNGS)[number];

export const DEFAULT_LNG: UiLang = 'ru';
export const FALLBACK_LNG: UiLang = 'en';
export const STORAGE_KEY = 'irene.ui.lang';

export const LANG_LABELS: Record<UiLang, string> = {
  ru: 'Русский',
  en: 'English',
};

export function isUiLang(v: unknown): v is UiLang {
  return typeof v === 'string' && (SUPPORTED_LNGS as readonly string[]).includes(v);
}

/** The persisted choice, or the default when nothing valid is stored. Safe under SSR / blocked storage. */
export function initialLang(): UiLang {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (isUiLang(stored)) return stored;
  } catch {
    /* localStorage unavailable — fall through to default */
  }
  return DEFAULT_LNG;
}
