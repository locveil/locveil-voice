# core-py — consumed pin (owner: locveil-commons)

One-way inward copy of the shared entry-point-group discovery engine
(`packages/core-py/entry_point_loader.py` + owner STAMP verbatim) at the tag recorded in
`PIN.json` — **never hand-edit**; move it with `make repin CONTRACT=core-py` under a
deliberate re-pin ledger task (family declared in `../../../.repin.toml`).

This is the estate's **first vendored RUNTIME code** (ARCH-58, owner ruling: strict), so
the pin has a third leg beyond the usual two: the importable copy at
`backend/src/locveil_voice/utils/entry_point_loader.py` must stay **byte-identical** to the pinned
artifact here. `backend/tests/test_core_py_pin_identity.py` asserts the triangle
(pin bytes ↔ runtime copy bytes ↔ PIN.json sha256) hermetically on every push — a local
edit to the runtime file breaks commit and CI, which is the point.

Semantics/behavior questions: the design doc
`docs/design/core_py_loader_extraction.md` (§2 is the binding surface) and the owner's
behavior suite (`../locveil-commons/packages/core-py/tests/`). Voice's singleton lives in
`backend/src/locveil_voice/utils/entry_points.py` (consumer-owned composition, not part of the pin).
