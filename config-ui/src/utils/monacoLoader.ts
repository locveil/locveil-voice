/**
 * Monaco bundled locally (UI-20) — no CDN at runtime.
 *
 * `@monaco-editor/react`'s default loader fetches monaco from the jsdelivr CDN —
 * a silent external dependency in a privacy-first, LAN-deployable product (and a
 * hard failure offline). This module points the loader at the monaco instance
 * bundled INTO the plugin, and inlines the editor worker (a blob worker keeps the
 * plugin a single-file ESM bundle under the Workbench import-map load — no
 * relative worker-asset resolution to break).
 *
 * Import this module before any <DiffEditor>/<Editor> renders (both consumers,
 * TomlPreview and DiffViewer, import it at module top).
 */
import * as monaco from 'monaco-editor';
import { loader } from '@monaco-editor/react';
import EditorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker&inline';

(self as typeof self & { MonacoEnvironment?: monaco.Environment }).MonacoEnvironment = {
  // One worker class for every label: the plugin only renders read-only diff
  // views (TOML/plain text), so the language-specific workers are never needed.
  getWorker: () => new EditorWorker(),
};

loader.config({ monaco });
