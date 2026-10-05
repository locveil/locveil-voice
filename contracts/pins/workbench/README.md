# workbench — the Workbench plugin contract pin (consumed)

A **pinned, one-way-inward copy** of the `locveil-commons`-owned plugin contract (family
`workbench`; owner surface `packages/workbench/`). `config-ui` is the Voice Workbench
plugin: it compiles against **this copy** of the contract and its build emits the manifest
fragment the shell reads to load it. Never hand-edit any file here — the pin moves only by a re-pin task
(`scripts/repin.py`); the pinned tag is recorded in `PIN.json`.

| File | Origin | What it is |
|---|---|---|
| `contract.ts` | commons (byte-identical) | the contract as code — `WorkbenchPlugin`, `ManifestFragment`, the host API a plugin receives |
| `manifest-fragment.schema.json` | commons (byte-identical) | machine form of `ManifestFragment` — what a plugin's `dist/manifest.json` must satisfy |
| `runtime-config.schema.json` | commons (byte-identical) | the shell's runtime config shape (shell-owned; held because a pin is always the owner's complete set) |
| `STAMP.json` | commons (byte-identical) | the owner's version stamp |
| `PIN.json` | **voice-stamped** | which commons tag/commit this repo builds against, file hashes, when |

Conformance (layer 2): `backend/tests/test_workbench_pin_conformance.py` — assembles the
manifest fragment exactly as `config-ui/vite.config.ts` does (from
`config-ui/manifest.fragment.json` + the `package.json` version) and validates it against
the pinned `manifest-fragment.schema.json`; checks a peer major is declared for every shell
singleton; and holds a tripwire on the vite config so the build cannot start emitting a
field the test does not see. Hermetic — no build, no Node, no sibling checkout.

**The pinned `contract.ts` is the file config-ui type-checks against.** The plugin imports
its contract types from `locveil-workbench/contract`; `config-ui/tsconfig.json` maps that
specifier (`paths`) to `contracts/pins/workbench/contract.ts`, and no `locveil-workbench`
package is installed — the import is type-only and erased at build, so the bundle needs
nothing at runtime. The pinned file imports React types and sits outside any
`node_modules`, so a companion `react` entry maps that import to config-ui's own
`@types/react`. A change to the contract in the commons checkout therefore reaches the
type-check only through a re-pin; `locveil-ui-kit` stays a linked package (the shell's
runtime singleton — a package-style surface with no pinned bytes).

Two guards keep it that way. The conformance test above fails if the mapping is missing,
points anywhere but this folder or gains a second route, if a `locveil-workbench`
dependency or lock entry reappears, if the type-check is run on another project file, or if
a source file imports the contract as anything but `import type … from
'locveil-workbench/contract'`. The `frontend-health` CI job asks the compiler itself
(`tsc --listFilesOnly`): the pinned `contract.ts` must be in the program, and nothing from
the commons checkout except `packages/ui-kit`.

A re-pin that changes `contract.ts` can therefore fail config-ui's type-check — that is the
point: fix the plugin in the same re-pin task.
