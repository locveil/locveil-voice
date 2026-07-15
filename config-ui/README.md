# config-ui — the Voice Workbench plugin

The configuration and donation editor for the Irene voice assistant. Since UI-17 it is
not a standalone app: it builds as a **plugin bundle for the Locveil Workbench** (the
shared browser workbench in the sibling `locveil-commons` checkout) and appears there
as the **Voice** tab — six pages: Donations, Templates, Prompts, Localizations,
Monitoring, Configuration.

## Build & run

```bash
npm ci
npm run build     # dist/: index.js (ESM) + style.css + manifest.json
npm run dev       # same build, rebuilds on change (reload the Workbench tab)
```

Then run the Workbench and open the Voice tab:

```bash
cd ../../locveil-commons/packages/workbench
npm install && npm run build && npm run serve   # http://localhost:6107
```

The plugin talks to the Irene backend on the same host the Workbench is served from,
port 8080 (override by setting `window.__IRENE_API_BASE__` before the plugin loads).

## How the bundle fits the Workbench

- `dist/manifest.json` is the build-emitted manifest fragment: entry, styles, and the
  peer majors the shell verifies before loading.
- React, react-dom, react-router-dom and `locveil-ui-kit` are **not bundled** — the
  shell serves them through its import map, so every plugin shares one copy.
- Everything else (i18next, the editors, Monaco wrapper) bundles into `dist/index.js`;
  the locale follows the shell's RU/EN switch.
- Design tokens and the CSS reset come from the shell; the bundle carries only its own
  component styles.

## Gates

```bash
npm run check     # type-check + strict ESLint + orphan-module guard
npm run test      # vitest
```

Both must stay green together with `npm run build` — config-ui is a first-class
consumer of the backend contracts (donation schema, config schema, REST API), and its
generated types (`npm run gen:api-types`) must match the backend it edits.
