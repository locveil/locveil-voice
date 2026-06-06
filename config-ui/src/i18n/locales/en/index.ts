/** English resource bundle — one key per i18next namespace. UI-7. */
import { common } from './common';
import { layout } from './layout';
import { donations } from './donations';
import { configuration } from './configuration';
import { prompts } from './prompts';
import { templates } from './templates';
import { localizations } from './localizations';
import { monitoring } from './monitoring';
import { overview } from './overview';

export const en = {
  common,
  layout,
  donations,
  configuration,
  prompts,
  templates,
  localizations,
  monitoring,
  overview,
} as const;
