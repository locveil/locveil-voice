# Irene — Release Plan

The single active tracker for the road to release. Supersedes the legacy `docs/TODO.md` +
`docs/TODO/TODO0x` (refactor-era, mostly complete — to be archived under DOC-2).

**Target:** _TBD_ · **Status:** reviving (paused ~Sep 2025, restarted May 2026) · **Version:** 15.0.0

## Definition of release (exit criteria) — _draft, refine_

- [ ] Clean `uv sync`; boots in CLI **and** WebAPI modes on x86_64, and as a Docker image.
- [ ] CI green (re-enabled, current action versions).
- [ ] No phantom-reference / runtime `NameError` bugs; pyright (standard) at/under an agreed threshold.
- [ ] Import layering honored: no real cycles, no backwards cross-layer imports per an agreed contract.
- [ ] Test suite runs and passes; coverage understood.
- [ ] Models point to current versions with live download URLs.
- [ ] Docs accurate at the release version; quickstart works end-to-end.

---

## How to use this file

- **Workstreams** are stable buckets. **Tasks** are the unit of work — sized to one coherent commit/PR,
  with a stable ID (referenced in commit messages, e.g. `ARCH-1: …`).
- Status: `- [ ]` open · `- [x]` done · annotate `BLOCKED`/`DEFERRED`/`DOING` + reason inline. Priority `P0–P2`.
- Individual lint findings live in the review docs (e.g. `docs/review/phase0_static_baseline.md`) and
  **roll up** into a task here — keep this file a spine, not a dumping ground.
- Record what actually happened (and decisions) in the **Action journal** at the bottom.

---

## Workstreams

### Architecture & Refactor (ARCH)
- [ ] **ARCH-0** (P1) — _NEXT_ — Architecture MAP & document. Enumerate every cross-layer/backwards import,
      misplaced foundational type, and real-vs-artifact cycle in the §F import SCC; propose a layering target.
      Done when: `docs/review/phase1_architecture_map.md` exists with the full map + target + ranked fix list.
      Refs: `docs/review/phase0_static_baseline.md` §F.
- [ ] **ARCH-1** (P0) — Relocate `AudioData` / `WakeWordResult` from `intents/models.py` to a foundational
      module; re-point ~25 importers downward; drop the `audio_helpers.py` `TYPE_CHECKING` band-aid.
      Done when: type lives in a low layer, all importers point downward, ruff/pyright clean, imports OK.
- [ ] **ARCH-2** (P0) — Break the `config → core` cycle: remove `config/validator.py:222`
      `from ..core.components import discover_providers` (invert/inject) and the import-time schema-validation
      side-effect; drop the `core/assets.py` `TYPE_CHECKING` band-aid for `AssetConfig`.
- [ ] **ARCH-3** (P2) — Further layering fixes surfaced by ARCH-0 (placeholder; split into tasks after the map).

### Code Quality & Review (QUAL)
- [x] **QUAL-1** — Phase-0 static baseline (ruff/pyright/vulture/validators/import-graph). → `docs/review/phase0_static_baseline.md` (6e39886)
- [x] **QUAL-2** — Review round 1: phantom-reference `NameError`s + method shadowing. → b6cd282
- [ ] **QUAL-3** (P1) — Category D wiring: `Monitoring`/`Configuration` define `get_python_dependencies` as an
      unbound instance method; the 4 runners miss the metadata methods. Done when: `dependency_validator --validate-all` passes 58/58.
- [ ] **QUAL-4** (P1) — Type-safety debt: re-tighten `mypy.ini`/`pyrightconfig.json` and burn down the ~1063
      standard-mode pyright errors (subdivide after ARCH lands). Refs: §E.
- [ ] **QUAL-5** (P2) — Cruft: 360 unused imports, 62 star-imports, vulture dead-code pool. Refs: §G.
- [ ] **QUAL-6** (P2) — Config schema gap: 9 `CoreConfig` fields without section models (import-time warning). Refs: §H.

### Tests (TEST)
- [ ] **TEST-1** (P1) — Fix broken tests referencing removed/renamed symbols (`ConversationContext`→
      `UnifiedConversationContext`, `TTLCache`, `ContextualCommandPerformanceManager`). 16 undefined-name refs.
- [ ] **TEST-2** (P1) — Get the suite running green; assess coverage and trustworthiness.

### Build & CI (BUILD)
- [ ] **BUILD-1** (P0) — Verify clean `uv sync` + CLI and WebAPI boot at v15.
- [ ] **BUILD-2** (P1) — Re-enable CI (`config-validation.yml` is manual-only; update deprecated
      `upload-artifact@v3` / `setup-python@v4`).
- [ ] **BUILD-3** (P1) — Verify the minimal Docker build (x86_64 builder feeds analyzer package names to
      `uv sync --extra`, which expects extra *names* — confirm/fix). Refs: README-DOCKER, build audit.
- [ ] **BUILD-4** (P2) — config-ui build (`npm ci && npm run build`; `dist` is git-ignored).

### Models & Assets (ASSET)
- [x] **ASSET-1** — Refresh stale model IDs (Anthropic→Claude 4.x, Whisper large-v3, ElevenLabs multilingual_v2, spaCy 3.8, gpt-4→gpt-4o-mini). → fc85306
- [ ] **ASSET-2** (P1) — Liveness-check all model download URLs after the pause (`models.silero.ai` flaky → prefer torch.hub; openWakeWord v0.5.1; alphacephei vosk).
- [ ] **ASSET-3** (P2) — DEFERRED — Migrate `lingua-franca` off the abandoned MycroftAI git pin to the OVOS
      successors (`ovos-number-parser`/`ovos-date-parser`), or mirror/vendor. Refs: `pyproject.toml` note.

### Documentation (DOC)
- [x] **DOC-1** — Sync README/architecture to v15; archive ~28 historical docs to `docs/archive/`. → 4a55519
- [ ] **DOC-2** (P2) — Archive completed `docs/TODO/TODO0x`; mark `docs/TODO.md` superseded by this file; keep open TODO11 + partials.
- [ ] **DOC-3** (P2) — Fix cosmetic "v13" strings in `irene/core/engine.py` docstrings/logs.

### Release Readiness (REL)
- [ ] **REL-1** (P0) — Sign off the Definition-of-release checklist above (fill target + criteria).
- [ ] **REL-2** (P1) — `config-example.toml` + quickstart finalization (the release-time config story).
- [ ] **REL-3** (P1) — Version bump / changelog / tag.

---

## Action journal

### 2026-05-31
- **Revival analysis** — full doc + code + build + asset audit; established real version is 15.0.0, single
  `UnifiedVoiceAssistantWorkflow`, web API is a router (not a component), 58 entry-points (not "77").
- **DOC-1** — README/architecture synced to v15; ~28 historical docs `git mv` → `docs/archive/` (+ index);
  deprecation banners on `irene_current.md`, `configuration_guide.md`, `PIPELINE_IMPLEMENTATION.md`. → 4a55519
- **ASSET-1** — stale model IDs refreshed; `uv.lock` regenerated (spaCy 3.8.14). → fc85306
- lingua-franca abandoned-upstream tech-debt note added to `pyproject.toml`. → 3e20cd0 (see ASSET-3)
- **QUAL-1** — Phase-0 static baseline filed. → 6e39886
- **QUAL-2** — review round 1: fixed phantom-reference `NameError`s + method shadowing (16 files, +24/−206);
  verified no regressions. → b6cd282
- **Decisions:** work directly on `main`, branch only when explicitly asked · `config-master.toml` stays the
  canonical config (config-example is a release-time story) · architecture defects masked by `TYPE_CHECKING`
  (AudioData misplacement, config→core cycle) to be mapped first (ARCH-0) then fixed (ARCH-1/2), not patched piecemeal.
