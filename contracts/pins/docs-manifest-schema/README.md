# docs-manifest-schema — the user-docs manifest schema pin (consumed)

A **pinned, one-way-inward copy** of the `locveil-commons`-owned JSON Schema that every
repo's `docs/manifest.json` validates against (family `docs-manifest-schema`; owner artifact
`process/user-docs/manifest.schema.json`; prose convention `process/user-docs.md` §4). Never
hand-edit any file here — the pin moves only by a re-pin task (`scripts/repin.py`).

**Why this is a pin and the manifest is not a contract:** `docs/manifest.json` is this
repo's own instance data — nodes come and go with ordinary doc work, guarded by the
coherence test. The contract is the SHAPE it must have, and that shape is owned by commons.
The repo-internal `docs-manifest` stamp that used to version the manifest itself was retired
for this pin; its `docs-manifest-v1` git tag stays as frozen history.

| File | Origin | What it is |
|---|---|---|
| `manifest.schema.json` | commons (byte-identical) | the schema — roots, the surface→glob map, node shape and classes |
| `STAMP.json` | commons (byte-identical) | the owner's version stamp |
| `PIN.json` | **voice-stamped** | which commons tag/commit this repo validates against, file hashes, when |

Conformance (layer 2): `backend/tests/test_docs_manifest.py` validates `docs/manifest.json`
against the pinned schema on every run — no sibling checkout, never skipped — and keeps the
manifest coherent with the tree (node↔file bijection under the roots, surface globs that
match real files, canonical pointers that resolve, docs-verdict node ids that exist).
