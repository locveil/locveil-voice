/** English resource bundle — one key per i18next namespace. UI-7. */
import { common } from './common';
import { donations } from './donations';
import { configuration } from './configuration';
import { prompts } from './prompts';
import { templates } from './templates';
import { localizations } from './localizations';
import { monitoring } from './monitoring';

export const en = {
  common,
  donations,
  configuration,
  prompts,
  templates,
  localizations,
  monitoring,
} as const;
