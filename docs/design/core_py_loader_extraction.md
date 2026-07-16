# Design — extracting the entry-point loader to `locveil-commons/packages/core-py` (ARCH-42)

**Date:** 2026-07-16 · **Status:** AGREED (interactive owner session, 2 rounds) · **Owner after
extraction:** locveil-commons (regime 2) · **Consumers:** voice (#1), bridge (#2 via CORE-7)

**Council scope (PROD-8, 2026-07-16, binding):** extract the entry-point-group discovery engine
ONLY — voice's `DynamicLoader`. The `EntryPointMetadata` build-time quartet
(`get_python_dependencies`/`get_platform_support`/`get_supported_architectures`/
`get_platform_dependencies`) and all its values stay voice-side; bridge's by-name config resolver
(`utils/class_loader.py`) stays bridge-side; config→entry-point unification is REJECTED (it would
break the offline `dump_catalog` golden generator). The `build_analyzer` →
`get_provider_class` → classmethod seam is preserved. Hard predecessor ARCH-50 delivered the
hardcodings inventory (`docs/review/dynamic_loading_hardcodings_review.md`); its remediation
(ARCH-52..57, QUAL-83, TEST-22) is the state this design starts from.

---

## 1. What is being extracted

`backend/src/locveil_voice/utils/loader.py::DynamicLoader` (~115 lines): entry-point-group
discovery with a `(namespace, enabled-list)`-keyed class cache and a per-namespace
**failure ledger** (BUG-36: an enabled provider that fails to import must be reportable by name,
not vanish). Consumed surface in voice today (post-ARCH-50 remediation, 20 importing files):

| Method | Call sites | Notes |
|---|---|---|
| `discover_providers(namespace, enabled=None)` | 18 | the workhorse; loads classes |
| `get_provider_class(namespace, name)` | 3 | **the analyzer seam** (council-locked) |
| `list_available_providers(namespace)` | 2 | analyzer catalog, inputs manager |
| `get_discovery_failures(namespace)` | 2 | BUG-36 reporting (`core/components.py`) |
| module singleton `dynamic_loader` | all | process-global cache + ledger |

NOT travelling (voice-side aux in the same file): `require_dependencies`, `safe_import`,
`check_optional_dependency`, `DependencyChecker`, `get_component_status`, `suggest_installation`.
Also not travelling: the py3.8/`pkg_resources` compat branches — both consumers pin Python 3.11;
the shared module is `importlib.metadata`-only.

Bridge's current consumer shape (`domain/devices/service.py::load_device_modules`): inline EP
discovery of `locveil_bridge.devices` (9 drivers), whole-group load, **base-class validation**
(`issubclass(loaded, DevicePort)`) with loud per-entry rejection. CORE-7 requires this to move out
of `domain/`.

## 2. The shared surface (commons `packages/core-py/entry_point_loader.py`)

Module name **`entry_point_loader`** (owner ruling). Ships the **class only** — no module-level
instance; each consumer owns its singleton (the shared artifact stays state-free).

```python
class DynamicLoader:
    def discover_providers(self, namespace: str, enabled: list[str] | None = None,
                           base_class: type | None = None) -> dict[str, type]
    def get_provider_class(self, namespace: str, name: str,
                           base_class: type | None = None) -> type | None
    def list_available_providers(self, namespace: str) -> list[str]
    def list_registered(self, namespace: str) -> list[str]
    def get_discovery_failures(self, namespace: str) -> dict[str, str]
    def clear_cache(self) -> None
```

Faithful semantics preserved: cache keyed `(namespace, enabled)`, failure ledger with
success-clears-entry behavior, module logger, graceful empty-dict on a broken discovery
mechanism. Three agreed deltas (owner: "faithful + both improvements", + one rule-of-two
addition surfaced in review):

1. **`base_class=` validation (new, optional).** An entry whose loaded object is not a
   `base_class` subclass is rejected into the failure ledger (`"not a <Base> subclass"`), exactly
   the check bridge hand-rolls today. Voice may adopt per provider family later; default `None`
   keeps voice byte-compatible.
2. **`get_provider_class` loads the single named entry point** instead of materializing the whole
   group (today fetching one class imports every sibling). Group-cache hits are still used when
   present; a miss loads only the named EP and records its failure individually. The analyzer seam
   is unaffected — where the analyzer wants full groups it calls `discover_providers`/
   `list_available_providers` as before.
3. **`list_registered` (new): names WITHOUT importing.** Rule-of-two on arrival: voice's
   `startup_validation` enumerates registered names import-free (it hand-rolls
   `importlib.metadata.entry_points` today) and bridge's `dump_catalog` builds the golden without
   loading a single driver. `list_available_providers` keeps its historical loading semantics.

## 3. Versioning, consumption, enforcement

- **Home:** `locveil-commons/packages/core-py/` — own `pyproject.toml`, own tests (the behavior
  suite lives with the owner), README; versioned by prefixed tags **`core-py-vN`**
  (productization D-8/D-11). The guards' precedent (`packages/scope-guard`, `packages/contract-guard`).
- **Consumption: vendored module at a pinned tag** — the estate's proven model; hermetic Docker
  builds, no git/pip install machinery, per-repo import paths.
- **Enforcement: STRICT PIN + identity test** (owner ruling — this is the estate's **first
  vendored RUNTIME code**, so convention-only discipline is not enough):
  - `contracts/pins/core-py/` in each consumer: the pinned `entry_point_loader.py` + `PIN.json`
    (sha256) + README, registry row in `contracts/README.md` — contract-guard's hash + TAG rules
    apply (the CI tag-fetch requirement is already met, BUILD-39).
  - The **importable copy** lives at `backend/src/locveil_voice/utils/entry_point_loader.py`; a
    hermetic conformance test asserts it is **byte-identical** to the pin (the catalog's
    two-copies-move-together discipline). A local edit to the runtime file breaks commit + CI.

## 4. Voice migration (implementation task, `[release]` by owner ruling)

- Vendored: `utils/entry_point_loader.py` (never edit; class only).
- New voice-owned composition module `utils/entry_points.py`: `dynamic_loader = DynamicLoader()` —
  the process-global singleton (cache + failure ledger semantics unchanged). Sits next to
  `utils/namespaces.py` (ARCH-57's group-name registry, which stays voice-local: group names are
  consumer-owned INPUTS to the shared engine).
- **Full import sweep** (owner ruling, over a loader.py shim): all 20 call sites move to
  `from ..utils.entry_points import dynamic_loader`; `utils/loader.py` shrinks to the voice aux
  helpers only.
- Pin + registry + identity test per §3. `startup_validation` may adopt `list_registered` in the
  same change (mechanical, behavior-identical).
- Acceptance: full suite green; analyzer JSON byte-identical across all 6 profiles (the engine
  change is behavior-neutral for voice — `base_class` unused, single-EP `get_provider_class`
  returns identical classes); coherence guard green; import contracts 11/11 (utils stays the
  bottom layer).

## 5. Bridge adoption contract (what CORE-7 codes against)

Binding conditions from the council + this surface:
- Bridge vendors the SAME `entry_point_loader.py` at the SAME `core-py-vN` tag (own pin folder,
  own identity test), instantiates its own singleton in `utils/` **or behind a port — never
  `domain/`** and with **zero new import-linter exceptions**.
- `load_device_modules`'s inline discovery is replaced by
  `discover_providers("locveil_bridge.devices", base_class=DevicePort)` — the hand-rolled
  issubclass check becomes the engine's native rejection path, with per-entry reasons in the
  failure ledger (a reporting improvement bridge doesn't have today).
- `dump_catalog` may use `list_registered` (names without loading) — **no catalog-golden drift**:
  adoption is an infra swap, no contract bump.
- Bridge's by-name config resolver (`utils/class_loader.py`) is untouched — different mechanism,
  no second consumer, stays local per the council.

## 6. Explicitly staying put

- `EntryPointMetadata` + the build-time quartet + all values — voice-side (`core/metadata.py`).
- `utils/namespaces.py` (voice) — consumer-local group-name registry; bridge names its own groups.
- Voice aux helpers in `utils/loader.py`; bridge's `class_loader.py`.
- The logging-scheme extraction (ARCH-43) stays PARKED per the council — loader first.

## 7. Sequencing

1. **This design** lands (voice `docs/design/`); write-back to commons board **PROD-8**: the
   surface is known — the `packages/core-py` skeleton is unblocked (council lock satisfied:
   ARCH-50 ✓ + ARCH-42 ✓).
2. **Commons**: cut `packages/core-py/` (skeleton + `entry_point_loader.py` + tests + README),
   tag **`core-py-v1`** — a commons-side task under PROD-8.
3. **Voice**: migration task (§4) executes against `core-py-v1` — filed as **ARCH-58 `[release]`**.
4. **Bridge**: CORE-7 executes against the same tag (bridge's ledger owns it; §5 is its contract).
