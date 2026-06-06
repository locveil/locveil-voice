/**
 * Type-safe i18next (UI-7) — binds `t()` keys and namespaces to the English bundle, so a mistyped key or namespace
 * is a compile error and editors autocomplete keys. The RU bundle is structurally constrained to match `en`
 * (see locales/ru/index.ts), so this one source of truth governs both languages.
 */
import 'i18next';
import type { en } from './locales/en';

declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: 'common';
    resources: typeof en;
  }
}
