# TEST-7 Phase B — triage worklist + risk-ranked coverage

Working doc for the TEST-7 suite rewrite. Produced 2026-06-15 from the failure signatures (one-line
tracebacks of all 82 failures) + the Phase-A coverage baseline (45.6%). Decisions locked with the
user: **same contract-level method as the release-plan new code · 100% green · delete stale outright ·
all clusters in one sweep · pytest-cov mandatory**. Triage rule per failing test: *behavior gone →
delete · behavior live but asserts a drifted internal → rewrite to the port/public contract · test
right, code wrong → fix the code.*

This is the input the Phase C/D multi-agent workflow executes against.

---

## 1. Failure triage — 82 failures, by cluster → verdict

| Cluster (files) | # | Root-cause signature | Verdict | Notes |
|---|---|---|---|---|
| **phase4 contextual** (`test_phase4_contextual_commands`, `_integration`, `_performance`) | 21 | `'NoneType' has no attribute 'active_actions'` (16) + `ContextualCommandPerformanceManager is not defined` (2) | **DELETE** | Built around the **deleted** perf-manager + None-context fixtures (pre-refactor org). The contextual-command *behavior* (stop/resume, disambiguation) survives — **re-cover it fresh** in the rewrite, don't patch these. |
| **cascading NLU** (`test_cascading_nlu`) | 9 | `KeyError 'provider'` — `entities['provider']` vs `_recognition_provider` | **REWRITE** | Assert on the current recognition-provider contract (public), not the old entities key. |
| **NLU / params** (`test_context_aware_nlu`, `test_no_intent_clarification`, `test_parameter_schema_unification`) | 10 | `Intent.__init__() got unexpected 'session_id'` / `missing 'entities'`; `Empty parameter schema for llm.console` | **REWRITE** (+1 FIX, see §3) | Update `Intent(...)` construction to the current signature. `context_aware_nlu` is the **reference fixture pattern** to emulate elsewhere. |
| **VAD** (`test_vad_phase2/3/4`) | 13 | metrics `'dict' has no attribute average_processing_time_ms/timeout_events/...` (4); `VADConfig has no 'energy_threshold'` (2); `Configuration not available in workflow` (4); `'error' == 'asr_result'`; `Error should mention VAD requirement` | **REWRITE** (+1 FIX, see §3) | Metrics are dicts now; `energy_threshold` moved under `[vad.providers.energy]`; inject a config component in the fixture. |
| **spaCy assets** (`test_spacy_asset_integration`) | 6 | `'function' has no attribute call_count/assert_called`; `'ru_core_news_sm' in {}` | **REWRITE** | Mock-vs-MagicMock; fix the asset-loader fixture (the `test_context_aware_nlu` loader pattern). |
| **phase1/6 integration** (`test_phase1_integration`, `test_phase6_integration`) | 6 | assorted pre-refactor integration scaffolding | **DELETE** | Superseded by `test_smoke_e2e` (TEST-0) + the new seam tests. Verify none asserts unique live behavior before deleting. |
| **misc drift** (`test_qual34_param_wiring`, `test_language_source_of_truth`, `test_component_trace_integration`, `test_intent_enable_disable`, `test_llm_fallback`, `test_phase7_performance`) | 14 | result-dict keys (`generation_success`/`enhancement_success`); attr renames (`IntentRegistry._handlers`, `IntentComponent.get_system_status`); `'fallback'=='fast_provider'`; missing `create_test_audio`; trace stages | **REWRITE** | Case-by-case to current contracts. `component_trace_integration` (3) drifted on ARCH-19 trace internals — re-assert on the envelope/handler-events API. |
| **smart-home resolution** (cases within `cascading`/`context_aware`) | ~3 | `assert 'device_resolved' in {...device_resolution_failed:True}`; `'location_resolved' in {...location_resolution_failed}` | **DELETE** | Tests the **unbuilt** MQTT/bridge device resolution (ARCH-8, "not in this build"). Delete these cases until ARCH-8 lands. |
| **removed module** (`test_phase7_*`) | 1 | `No module named 'irene.providers.text_processor.general_text_processor'` | **DELETE** | Module removed in the text-processor refactor. |

**Rough split:** ~28 delete · ~50 rewrite · ~3 fix-code (below). Net suite move: 82 red → 0 (100% green), with the deleted clusters' *behavior* re-covered fresh in §2.

---

## 2. Risk-ranked coverage fill (Tier 1 first)

Risk = coverage-gap × churn × hot-path × defect-history. Baseline 45.6%. Churn = commits since 2026-06-01.

| Module | Cov | Stmts | Churn | Hot-path / history | Tier |
|---|---|---|---|---|---|
| `core/workflow_manager.py` | **20%** | 492 | 15 | request routing spine; QUAL-28 F&F | **1** |
| `core/components.py` | **20%** | 244 | 7 | component manager (everything loads through it) | **1** |
| `components/nlu_component.py` | **38%** | 603 | 16 | recognition (silent-failure critical); QUAL-11 | **1** |
| `intents/context.py` | **25%** | 362 | 10 | identity/eviction; QUAL-24/28 | **1** |
| `workflows/voice_assistant.py` | **48%** | 372 | **18** | most-churned spine; the unified pipeline | **1** |
| `components/asr_component.py` | **25%** | 343 | 14 | ASR provider/fallback | **1** |
| the **5 capability handlers** (voice_synthesis, audio_playback, speech_recognition, translation, text_enhancement) | low | — | — | **TEST-8**: newly port-wired by QUAL-24, a real bug just fixed there, **unverified** | **1** |
| `intents/orchestrator.py` | 41% | 212 | 8 | handler dispatch | **2** |
| `tools/replay_trace.py` | 34% | 211 | new | new-code wiring (build/run/seed/reinject) | **2** |
| `runners/voice_runner.py` | 34% | 159 | new | new-code wiring (workflow start) | **2** |
| `workflows/audio_processor.py` | 65% | 378 | 12 | VAD segmenter (already half-covered) | **2** |
| leaf utils, format helpers, model/hardware providers | varies | — | — | low marginal risk; cover via smoke/integration not unit | **3** |

**Method per Tier-1/2 item (the locked recipe):** `object.__new__`/`SimpleNamespace` to bypass heavy
construction; assert on the **port/public** behavior; test the off-paths; model/hardware paths go to
the smoke harness (`test_smoke_e2e`), NOT heavy unit tests. **TEST-4** = the NLU/params Tier-1 work;
**TEST-8** = the 5 handlers; **TEST-3** = F&F lifecycle (context/workflow_manager); **TEST-6** = ASR
fallback/resampling; **TEST-5** = text-processor.

---

## 3. Fix-code candidates (test may be right — verify before rewriting/deleting)

These are the high-value "real bug" suspects — the same way TEST-1/2 banked QUAL-21/22.

1. **`device_id = 7` in `configs/config-master.toml:69`** (`test_master_config_field_alignment`) — the
   **canonical reference config** hardcodes a *machine-specific* audio device id (a named ThinkPad dock).
   The test flags `device_id` as a deprecated field. Almost certainly **FIX**: it shouldn't pin a real
   device in the master reference (Invariant #2). Confirm the intended default (auto / `null` / `-1`).
2. **`Empty parameter schema for llm.console`** (`test_parameter_schema_unification`) — the console LLM
   stub declares no parameter schema. **Verify:** declare a minimal schema (fix) vs the test over-asserting
   on an intentional stub (rewrite the assertion).
3. **`Error should mention VAD requirement`** (`test_vad_phase3`) — touches the VAD-required workflow-init
   path **just reworked in QUAL-46**. Verify the current error-message contract; rewrite the assertion to it
   (or fix the message if it regressed).

---

## 4. Phase C/D workflow shape (for reference)

- **C (green the suite):** fan out per-cluster — delete the DELETE files, rewrite the REWRITE clusters
  to port-level assertions, verify+resolve the 3 FIX candidates. Barrier: full suite green.
- **D (coverage fill):** fan out per Tier-1 module — characterization tests at the seams, re-measure with
  pytest-cov each round until the Tier-1/2 list is covered. `test_smoke_e2e` stays the green anchor throughout.
