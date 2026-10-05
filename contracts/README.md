# locveil-voice — contract registry

The direction-labeled index required by `../locveil-commons/process/contracts.md` §2.
Every contract this repo OWNS and every pin it CONSUMES, one line each; details live in
the per-contract READMEs. Layout is the uniform org shape: `contracts/<name>/` owned,
`contracts/pins/<name>/` consumed. Pins are one-way-inward, version-stamped copies per
the `cross-repo-source-of-truth` invariant — owned elsewhere, **never hand-edited**;
re-pin from the owner when it moves.

## Owned

| Contract | Where | Version authority |
|---|---|---|
| [`ws-protocol`](ws-protocol/README.md) | the normative text stays `docs/guides/websocket-api.md` (`ws-protocol-doc-canonical`); `ws-protocol/` holds the STAMP, the README and the hand-written machine core subordinate to the guide (`frames.golden.json`, nine `transcript.*.jsonl`, `ws-protocol.schema.json`); the major is served as `protocol_version` in every `registered` ack | `ws-protocol/STAMP.json` + tag `ws-protocol-v1.2.0`; the guide and the eleven core files are enumerated individually (byte-locked); the served value is the major only (`backend/tests/test_ws_protocol_version.py`); document ≡ core ≡ real frames is checked by `backend/tests/test_ws_machine_core.py` |
| [`wake-pack`](wake-pack/README.md) | sidecar stamp over the unmodified ASSET-5 HF pack (third-party manifest, never forked); in-code catalog is the release list | `wake-pack/STAMP.json` + tag `wake-pack-v1.0.1`; `artifacts` empty + `guard` (the STAMP is the whole pinned set; catalog coherence asserted in `backend/tests/test_ws_protocol_version.py`) |
| [`ui-openapi`](ui-openapi/README.md) | repo-internal GENERATED contract — artifact stays `config-ui/openapi.json` (generator `scripts/dump_openapi.py`, consumer `npm run gen:api-types`) | `ui-openapi/STAMP.json` + tag `ui-openapi-v1.1.1`; `artifacts` empty + `guard` → the drift test `backend/tests/test_openapi_drift.py` |
| [`trace-format`](trace-format/README.md) | artifact stays `docs/guides/tracing.md` → "The trace file format (reference)" (`trace-format-doc-canonical`); `trace-format/` holds the STAMP + pointer README; the major is written as `trace_version` in every saved trace | `trace-format/STAMP.json` + tag `trace-format-v1.0.1`; the guide is enumerated whole (byte-locked); the written value is the major only (agreement checked by `backend/tests/test_trace_format_version.py`) |

## Consumed (pins)

| Pin | Owner | Notes |
|---|---|---|
| [`catalog`](pins/catalog/README.md) | locveil-bridge (pinned tag: see `pins/catalog/PIN.json`) | LOCAL complete copy (golden + openapi + the owner's normative guide `catalog-contract.md`) for the push-time schema check (`backend/tests/test_catalog_contract_conformance.py`); one `make repin` updates it and the commons crossover copy at the same tag |
| [`report-protocol`](pins/report-protocol/README.md) | locveil-commons (tag `report-protocol-v1.0.1`) | problem-report machine core; conformance: `backend/tests/test_report_protocol_conformance.py` |
| [`esp32-site`](pins/esp32-site/README.md) | locveil-satellite (tag `esp32-site-v1.1.0`) | Plane-B nginx site template; conformance: `backend/tests/test_arch36_tls_e2e.py` |
| [`docs-manifest-schema`](pins/docs-manifest-schema/README.md) | locveil-commons (tag `docs-manifest-schema-v1.0.0`) | the JSON Schema `docs/manifest.json` validates against — the manifest itself is instance data, not a contract; conformance: `backend/tests/test_docs_manifest.py` (hermetic, reads the pinned copy) |
| [`workbench`](pins/workbench/README.md) | locveil-commons (tag `workbench-v1.3.0`) | the Workbench plugin contract config-ui builds against — `contract.ts` + the manifest-fragment and runtime-config schemas; the pinned `contract.ts` is the file config-ui type-checks against (tsconfig `paths`, no live `locveil-workbench` package); conformance: `backend/tests/test_workbench_pin_conformance.py` (the manifest fragment this repo's build emits validates against the pinned schema, tested at its source; the type mapping and the absence of the dependency are held in place) |
| [`core-py`](pins/core-py/README.md) | locveil-commons (pinned tag: see `pins/core-py/PIN.json`) | the shared entry-point discovery engine — the estate's FIRST vendored RUNTIME code (ARCH-58, strict): the importable copy `utils/entry_point_loader.py` must stay byte-identical to the pin; conformance: `backend/tests/test_core_py_pin_identity.py` |

_The shared crossover instruments stay in `../locveil-commons/contracts/pins/`:
`crossover-fixtures/` (co-owned, both product repos' cross-suites assert against it) and
the commons `catalog/` copy the eval framework's mock bridge serves (voice stamps both
catalog PIN.jsons via `scripts/repin.py` — the two copies move together or not at all)._

Guards: layer 1 is the vendored `scripts/contract_guard.py` (commons
`packages/contract-guard/`, pinned at tag **`contract-guard-v4.0.0`** — never edit the
vendored file, `scripts/repin.py tool contract-guard` to move; runs in `hooks/pre-commit`
with `--relax-tags` (mid-bump tolerance) and strict in the `contract-guard` CI job on every
push — no path gate — `--check` only); layer 2 is the per-contract version/drift tests and
per-pin conformance tests listed above, which CI runs whenever `contracts/**` or an owned
artifact path moves. Staleness (a pin or vendored tool trailing its owner) is the vendored
repin tool's job — `.repin.toml` + the `process/contracts.md` §5 severity ladder: the hook
warns, push CI fails on a major gap or on touch-the-family, the image-dispatch gate and
`make -C eval repin-check` fail on a minor-or-major gap. A pin's file set is whatever the
owner's STAMP enumerates at the tag; this repo's `.repin.toml` names only the family, the
destination and the conformance test.
