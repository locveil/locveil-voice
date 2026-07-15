/**
 * i18n bootstrap (UI-7, plugin-local since UI-17) — react-i18next with `en`/`ru` bundles,
 * one namespace per app area.
 *
 * Imported for its side effect from the plugin entry. This instance is PLUGIN-LOCAL by
 * design (HK-11: i18n bundles into each plugin — react-i18next here is the plugin's own
 * module copy, so the "default instance" cannot collide with other plugins). The active
 * locale is the SHELL's signal (`PageProps.locale`, synced in `plugin.tsx`) — no
 * persistence, no `<html lang>` writes: chrome owns both. This axis stays independent of
 * the donation *content* language (LanguageTabs).
 */
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { en } from './locales/en';
import { ru } from './locales/ru';
import { DEFAULT_LNG, FALLBACK_LNG, SUPPORTED_LNGS } from './config';

export const NAMESPACES = Object.keys(en) as (keyof typeof en)[];

void i18n.use(initReactI18next).init({
  resources: { en, ru },
  lng: DEFAULT_LNG,
  fallbackLng: FALLBACK_LNG,
  supportedLngs: SUPPORTED_LNGS,
  defaultNS: 'common',
  ns: NAMESPACES,
  interpolation: { escapeValue: false }, // React already escapes
  returnNull: false,
  react: { useSuspense: false },
});

export default i18n;
