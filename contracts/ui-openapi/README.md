# ui-openapi — the backend REST schema config-ui is built against (owned, generated)

The artifact **lives at [`config-ui/openapi.json`](../../config-ui/openapi.json)** — a
committed GENERATED file (owned surfaces keep their home; this folder holds the version
authority, per `../locveil-commons/process/contracts.md` §2). It is a repo-internal
contract: the backend generates it, config-ui consumes it.

- **Generator:** `scripts/dump_openapi.py` — assembles the same router set the real
  runner serves and dumps `app.openapi()`. Run after any endpoint/schema change.
- **Consumer:** `config-ui` — `npm run gen:api-types` turns the committed schema into
  `src/types/openapi.gen.ts`; the editor type-checks against it
  (`config-ui-stays-functional`).
- **Drift guard (layer 2):** `backend/tests/test_openapi_drift.py` rebuilds the schema
  in-process and fails on any byte of semantic drift — a schema change that isn't
  re-dumped can no longer ship silently.
- **Declaration:** `STAMP.json` declares `artifacts: []` with `guard` →
  `backend/tests/test_openapi_drift.py`. The generated file is deliberately NOT
  byte-enumerated (`../locveil-commons/process/contracts.md` §2 — a repo-internal generated
  artifact whose regenerate-and-compare test is the stronger check): its content moves with
  the code on every endpoint change, and the drift guard, not a byte-lock, keeps the
  committed copy exact.
- **Versioning (three levels):** the STAMP versions the convention surface, not each
  regeneration. Major = a deliberate breaking reshape of the REST surface convention;
  minor = a consumer-visible reshape of the generated surface (e.g. the package rename that
  moved every generated schema name); patch = stamp metadata. Every level is a `version` +
  `date` bump and a `ui-openapi-vX.Y.Z` tag on the same commit.
