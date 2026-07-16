# Review — hardcodings & config overrides that violate dynamic build-and-loading (ARCH-50)

**Date:** 2026-07-16 · **Scope:** every namespace / provider-list / path / class hardcoded where the
entry-points-or-config contract intends dynamism, and every config field declared but ignored or
overridden — across `backend/src/locveil_voice/` (components, intents, core, workflows, inputs,
outputs, config, tools) and the deployment TOMLs.

**Trigger:** the BUILD-36/PROD-21 rename bounce exposed that `IntentHandlerManager` discovers from a
literal namespace while the config's `discovery_paths`/`auto_discover` sat stale with zero effect.
ARCH-50 is the systematic sweep for that whole failure class. Frozen evidence; this doc asserts no
task status. Verdicts were ruled by the owner in the 2026-07-16 design session (three rounds);
the governing ruling is **no config overrides** — a declared field is honored or deleted, never
silently out-voted by code.

**Ground truth used throughout:** `backend/pyproject.toml` registers 13 entry-point groups
(8 provider families incl. `vad`, plus `components` (11), `workflows` (1), `intents.handlers` (15),
`inputs` (3), `runners` (4)). There is **no** `locveil_voice.outputs` group (outputs are
composition-registered by ARCH-15 design).

---

## A — The seed: dead discovery config on the intent-handler path

### F-A1 — `discovery_paths` / `auto_discover` declared, plumbed, documented — never read
- Declared: `config/models.py:715-716` (`IntentHandlerListConfig`), defaults duplicating the literal.
- Plumbed: `components/intent_component.py:73-74` and `:2109-2110` build them into the manager's
  config dict.
- Present in **all 8** TOMLs (config-master.toml:561-562 + 7 profiles) and skip-listed in
  `tools/build_analyzer.py:770`.
- Never consumed: `intents/manager.py:97-98` discovers from the literal
  `"locveil_voice.intents.handlers"`; no code path reads `auto_discover` or `discovery_paths`.
- Same namespace literal duplicated at `config/models.py:879` (validator) and
  `core/contract_validator.py:37` (`HANDLERS_PACKAGE`).
- **Verdict (owner):** DELETE both fields end-to-end; keep ONE shared namespace constant used by all
  three sites. Entry-point groups are inherently open for third-party registration, so a configurable
  namespace list buys nothing (mirrors the PROD-8 council's rejection of config-path discovery).
  → **tracked as ARCH-52**

### F-A2 — intent-assets root is CWD-relative `Path("assets")`
- `intents/manager.py:88` (no fallback) and `components/nlu_component.py:529` (no fallback) —
  the exact QUAL-59 bug class; `runners/web_server.py:122-126` carries a package-relative fallback,
  `nlu_component.py:687` was already fixed package-relative. Containers align only by coincidence
  (WORKDIR `/app` + volume at `/app/assets` + `LOCVEIL_VOICE_ASSETS_ROOT=/app/assets`).
- **Verdict (owner):** one shared resolver helper (env override, else package-relative repo-root
  fallback); all sites adopt it; no new config field. → **tracked as ARCH-52**

### F-A3 — hardcoded fallback domain priorities mask loading failures
- `intents/manager.py:568-574`: on any donation/config priorities failure, a literal dict
  (`audio:90, timer:70, …`) is silently installed.
- **Verdict (owner):** fail hard — delete the dict; a priorities-loading failure raises at startup
  (BUG-36 fail-loud posture). → **tracked as ARCH-52**

### F-A4 — `capability_ports`: static handler-name → component wiring table
- `components/intent_component.py:259-265`: six handler entry-point names mapped to injected
  component attrs (conversation→llm, voice_synthesis_handler→tts, …); `:287` special-cases
  `provider_control_handler` for registry injection. Adding a handler that needs a component means
  editing the component.
- **Verdict (owner):** handlers declare their ports via a classmethod (the
  `requires_configuration()` / `EntryPointMetadata` pattern); the table and the special case
  disappear; the injection loop becomes generic. → **tracked as ARCH-53**

### Sanctioned exception — conversation-context special-casing
- `intents/context_models.py:163,182,684,753,778` key conversation-history restoration on the
  literal handler name `"conversation"`.
- **Verdict (owner):** KEEP as-is — domain semantics of *the* conversation domain, not a loading
  concern. No task filed; this is the one sanctioned name special-case on the intent path.

Everything else on the intent-handler path is genuinely dynamic and healthy: entry-point discovery
filtered by config `enabled`/`disabled`, config injection by declared requirement + naming patterns,
donation-driven pattern registration. No hardcoded handler class list exists.

---

## B — Declared-but-ignored config fields (the "pydantic override" smell)

Cross-reference of every `Field(...)` in `config/models.py` against runtime readers
(dynamic-access patterns — `model_dump` → dict key, `getattr` with computed names — were checked
before declaring a field dead). Owner ruling: dead fields are DELETED (`dead-code-remove-not-fix`),
not implemented. → **all tracked as QUAL-83** unless noted.

### F-B1 — `AssetConfig`: the entire download/cache-management block is dead (11 fields)
`models.py:982-998`: `cleanup_on_startup`, `auto_download`, `download_timeout_seconds`,
`max_download_retries`, `verify_downloads`, `cache_enabled`, `max_cache_size_mb`, `cache_ttl_hours`,
`preload_essential_models`, `model_compression`, `concurrent_downloads` — zero consumers in
`core/assets.py` (it reads only the computed `*_root`/`*_cache_dir` properties). Downloads are not
throttled, verified, or retried per any of these knobs.

### F-B2 — handler config models are dead: handlers take no config
- `DateTimeHandlerConfig` (`models.py:676-678`: timezone/date_format/time_format) — handler
  `intents/handlers/datetime.py:31` is `def __init__(self)`, no `requires_configuration`;
  strftime formats are hardcoded in the handler.
- `GreetingsHandlerConfig` (`models.py:683-684`: personalized/context_aware) — same
  (`greetings.py:31`).
- **Verdict (owner):** delete both models + their `intent_system` fields + TOML sections; handlers
  keep current behavior; re-add deliberately if a real need arrives.

### F-B3 — partially-dead config families
- `ContextualCommandsConfig` (`models.py:696-699`): only `latency_threshold_ms` is read
  (`core/metrics.py:1027`); `enable_pattern_caching`, `cache_ttl_seconds`,
  `max_cache_size_patterns`, `performance_monitoring` are dead.
- `MonitoringConfig`: `dashboard_enabled` (:469), `memory_management_enabled` (:472),
  `memory_cleanup_interval` (:484), `memory_aggressive_cleanup` (:485) — the memory trio are
  QUAL-28 MemoryManager-deletion leftovers — and `debug_auto_inspect_failures` (:488).
- `NLUAnalysisPerformanceConfig`: `max_analysis_time_ms` (:620), `enable_caching` (:622),
  `cache_ttl_seconds` (:623) dead; only `max_concurrent_analyses` is read.
- `NLUAnalysisLanguagesConfig` (:628-629): never accessed — and the capabilities endpoint
  **overrides** it with a literal `["ru", "en"]` (`components/nlu_analysis_component.py:990`),
  which also violates the QUAL-36 single-language-policy rule. Fix: delete the sub-config, endpoint
  reads the canonical top-level policy.

### F-B4 — scattered dead singles
`MicrophoneInputConfig.auto_resample`/`resample_quality` (:72-73),
`VoiceTriggerConfig.strict_validation` (:324), `NLUConfig.persist_language_preference` (:376),
`VADConfig.processing_timeout_ms` (:448),
`UnifiedVoiceAssistantWorkflowConfig.monitoring_enabled` (:1077) and `enable_vad_processing`
(:1080 — VAD gating actually comes from `VADConfig.enabled`; `voice_assistant.py:129` hardcodes the
log string), plus passthrough-only fields (serialized by the TOML template generator, never read):
`WebInputConfig.websocket_enabled`/`rest_api_enabled` (:115-116),
`CLIInputConfig.prompt_prefix`/`history_enabled` (:122-123),
`VoiceTriggerConfig.buffer_seconds` (:316).

---

## C — Dual enable-flag authority (silent config override, both directions)

### F-C1 — `[components].X` force-overwrites `[X].enabled`; the build analyzer reads the loser
- `config/models.py:75-82` (CoreConfig `model_validator`): `self.tts.enabled =
  self.components.tts` etc. — the user's `[tts] enabled = …` is silently overwritten at parse time,
  and only 8 of 11 components are synced.
- Runtime authority: `core/components.py:165` + `:375-377` reads `config.components.<name>`
  (derived from `model_fields` — good pattern).
- Build-time authority: `tools/build_analyzer.py:583` reads the **raw TOML** `[X].enabled` — the
  pre-sync value. The two can disagree: an image built without a component's deps that the runtime
  will then enable, or vice versa.
- **Verdict (owner):** `[components]` is the single authority. Delete the per-section `enabled`
  fields and the force-sync validator; the build analyzer reads `[components]`; 8 TOMLs and the
  config-ui `ConfigSection` editors updated in the same change. → **tracked as ARCH-54**

---

## D — Provider-name literals & force-adds in components

Owner ruling: **strict config only** — no force-adds, no name literals; `default_provider` +
`fallback_providers` from config are the entire loading set; nothing configured survives → fail
loud (BUG-36 posture). Deployment TOMLs gain explicit `console`/`energy` entries where that
resilience is wanted — the behavior becomes visible config. → **all tracked as ARCH-55**

- **tts** (`components/tts_component.py`): init defaults `"console"` (:86-87), literal fallbacks in
  config reads (:127-128), force-add of console to the enabled set (:143-144),
  `essential_providers = ["console"]` (:185), console-enabled-by-default special case (:194),
  last-resort console instantiation (:309-312), request-time/schema defaults (:776, :795).
- **audio** (`audio_component.py`): init defaults (:84-85), force-add (:151-152), last-resort
  instantiation + default pinning (:180-185), schema default (:510).
- **voice_trigger** (`voice_trigger_component.py`): init defaults `"openwakeword"` (:42-43 — note
  no `fallback_providers` field even exists on `VoiceTriggerConfig`), force-add (:162-163),
  last-resort instantiation with a **literal `hey_jarvis` wake-word** (:198-214).
- **asr** (`asr_component.py`): init default `"vosk"` (:79), literal config-read fallbacks
  (:159, :162).
- **llm** (`llm_component.py`): init default `"openai"` (:82), literal config-read fallbacks
  (:162, :166), console as hardcoded degrade target (:253), force-append of console to the fallback
  chain (:274-275), schema default (:600).
- **vad** (`workflows/audio_processor.py`): `or "energy"` duplicating the model default (:193),
  energy pinned into discovery + selection (:195-203), name-branching on `"energy"` (:225),
  hard re-instantiation of energy on init failure (:231-233). The config-model default
  `VADConfig.default_provider="energy"` (`models.py:444`) is legitimate; the component-side literals
  are the smell. Several of these are *documented resilience anchors* ("energy: always available, no
  assets") — the strict-config ruling preserves the resilience by declaring it in the TOMLs instead.

---

## E — Hand-maintained maps & lists duplicating entry-points ground truth

### F-E1 — five component→namespace maps drift independently
1. `core/assets.py:65-77` `provider_namespace_map` (+ the 8-namespace search list :87-95).
2. `core/startup_validation.py:33-39` `COMPONENT_NAMESPACES` — **missing `vad`**: VAD's
   `default_provider` (a name-ref field, `models.py:444`) is never startup-validated.
3. `components/configuration_component.py:352-360` `provider_groups` — **missing `vad`**, and it
   backs `GET /config/providers/{component}`; the config-ui `provider_select` widget
   (`ConfigWidgets.tsx:274,288`) infers the component from the config path, so
   `vad.default_provider` (declared `widget: provider_select`) calls `/config/providers/vad` →
   404 → **the VAD provider dropdown renders empty. Live user-visible bug.**
4. `config/validator.py:219` hand-list — missing `vad` AND `text_processor`.
5. `tools/build_analyzer.py:429-434` fallback list — names the **phantom `locveil_voice.outputs`**
   group (never existed).
- **Verdict (owner):** one canonical map module (component key → entry-point group) next to the
  loader; all five sites import it; "all provider groups" derives from its values.
  → **tracked as ARCH-57**

### F-E2 — build analyzer hand-lists and convention-derived paths
- `component_names` hand-lists ×2 (`build_analyzer.py:575-578`, :618-620) cover 8 of the 11
  entry-pointed components.
- Module paths derived by naming convention (`:596`): `intent_system` →
  `locveil_voice.components.intent_system_component` — a **phantom module** (the real file is
  `intent_component.py`; the entry-point value already carries the true module path).
- **Verdict (owner):** derive component sets from the canonical map / `ComponentConfig.model_fields`
  and module paths from the entry-point values themselves. → **tracked as ARCH-57**

---

## F — Decorative entry-point machinery & parallel discovery mechanisms

### F-F1 — `locveil_voice.inputs` group has zero consumers; InputManager hardcodes its classes
- `inputs/manager.py:17-19` direct-imports `CLIInput`/`MicrophoneInput`/`WebInput`; `:52-101` wires
  them in per-class if-branches. The pyproject group (3 entries) is decorative.
- **Verdict (owner):** make it real — `InputManager` discovers inputs from the group (per-class
  config wiring reworked to a generic configure path). → **tracked as ARCH-56**

### F-F2 — `locveil_voice.runners` group has zero consumers
- Runners launch via `python -m` (Dockerfile CMD, docs); nothing reads the group.
- **Verdict (owner):** delete the group from pyproject (and the analyzer fallback list, with the
  phantom `outputs`). → **tracked as ARCH-56** (analyzer list itself: ARCH-57)

### F-F3 — dead parallel discovery/loading code
- `core/intent_asset_loader.py:1627-1660` `EnhancedHandlerManager` — zero callers; embodies a
  third (file-scan) handler-discovery mechanism and reads an `assets_root` config key that exists
  nowhere.
- `config/models.py:1298-1332` `ComponentLoader` — export-only (`config/__init__.py:84,120`), zero
  functional callers; duplicates ComponentManager's discovery inside the config layer.
- `components/base.py:216` `get_provider_capabilities` — zero call sites repo-wide (verified at
  PROD-8 intake; carried here per the council delegation).
- `intents/manager.py:465-503` `add_handler`/`remove_handler` — zero callers (`reload_handlers` IS
  live: `intent_component.py:605,997,1159`); with them gone, the legacy
  `_get_handler_patterns` fallback (:403-446) loses its last reachable caller (donations are
  mandatory since Phase 6 — handlers without donations are removed at init).
- **Verdict (owner):** delete all four (`dead-code-remove-not-fix`). → **tracked as QUAL-83**

---

## G — Heuristic name literals outside loading (deferred)

- `core/entity_resolver.py:290` hardcodes the device-domain list
  `["device","smart_home","iot","home_automation"]`.
- `core/report_bundle.py:124` triages on the `"smart_home"` intent-name prefix.
- **Verdict (owner):** keep as named module-level constants with the coupling documented NOW (they
  drive classification, not loading); revisit donation-driven derivation later.
  → **tracked as QUAL-84 [deferred]**

---

## H — The guard (the failure class no test caught)

Existing partial guards: `validate_entry_point_consistency` (`models.py:90-104`), BUG-36
loadability checks, the handler contract validator. None catch: dead config fields (B), hand-map
drift vs pyproject (E), dual-flag divergence (C).
- **Verdict (owner):** full coherence guard — hermetic test(s) asserting (a) every hand map /
  analyzer list ≡ pyproject entry-point groups, (b) every declared config field has a runtime
  reader (AST/grep-based, explicit tiny allowlist), (c) config-master ≡ model schema.
  → **tracked as TEST-22**

---

## Remediation index

| Task | Scope | Findings |
|---|---|---|
| ARCH-52 | intent-handler loading: delete dead discovery fields, shared namespace constant, shared assets-root resolver, fail-hard priorities | F-A1, F-A2, F-A3 |
| ARCH-53 | capability ports become handler-declared metadata | F-A4 |
| ARCH-54 | `[components]` is the single enable authority | F-C1 |
| ARCH-55 | provider loading honors config strictly (no force-adds / name literals) | D |
| ARCH-56 | InputManager consumes its entry-point group; runners group deleted | F-F1, F-F2 |
| ARCH-57 | canonical namespace map (fixes the live config-ui VAD dropdown 404); analyzer derives from EP values | F-E1, F-E2 |
| QUAL-83 | dead config fields (~30) + dead code (4 units) + QUAL-36 language-policy fix | B, F-F3 |
| QUAL-84 | [deferred] donation-driven heuristics | G |
| TEST-22 | full coherence guard | H |
