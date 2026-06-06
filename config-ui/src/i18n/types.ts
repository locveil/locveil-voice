/**
 * i18n bundle types (UI-7).
 *
 * `DeepStringify<T>` maps every string-literal leaf of the English bundle to `string` while preserving the object
 * shape. Typing the RU bundle as `DeepStringify<typeof en>` enforces **key-parity** (same keys, nested the same way)
 * without demanding identical text — so a missing/extra/misnested RU key is a build error, but the translations are
 * free. This is the compile-time half of the "language files are complete" guarantee.
 */
export type DeepStringify<T> = {
  [K in keyof T]: T[K] extends string ? string : DeepStringify<T[K]>;
};
