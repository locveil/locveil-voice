/**
 * Russian resource bundle (RU). UI-7.
 *
 * Typed as `typeof en` so the compiler enforces key-parity with English — a missing or extra key here is a build
 * error, which is our completeness guard (the "language files are complete" requirement, checked at compile time).
 */
import type { en } from '../en';
import type { DeepStringify } from '../../types';
import { common } from './common';
import { layout } from './layout';
import { donations } from './donations';
import { configuration } from './configuration';
import { prompts } from './prompts';
import { templates } from './templates';
import { localizations } from './localizations';
import { monitoring } from './monitoring';
import { overview } from './overview';

export const ru: DeepStringify<typeof en> = {
  common,
  layout,
  donations,
  configuration,
  prompts,
  templates,
  localizations,
  monitoring,
  overview,
};
