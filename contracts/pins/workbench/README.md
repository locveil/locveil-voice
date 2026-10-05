# workbench — the Workbench plugin contract pin (consumed)

A **pinned, one-way-inward copy** of the `locveil-commons`-owned plugin contract (family
`workbench`; owner surface `packages/workbench/`). `config-ui` is the Voice Workbench
plugin: it compiles against this contract and its build emits the manifest fragment the
shell reads to load it. Never hand-edit any file here — the pin moves only by a re-pin task
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

What this pin does NOT yet do: the TypeScript build still resolves the contract types
through the `file:` link to the commons checkout (`locveil-workbench` in
`config-ui/package.json`), not through the pinned `contract.ts`. The pin makes a commons
contract move VISIBLE here (the staleness check names it, and the pinned bytes show the
diff at re-pin time); it does not yet isolate the type-check from the live sibling.
