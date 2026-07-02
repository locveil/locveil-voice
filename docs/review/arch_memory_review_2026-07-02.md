> **📄 FROZEN EVIDENCE — not the task ledger.** Findings/rationale below are a point-in-time record. The
> authoritative **scope + status** is [`docs/RELEASE_PLAN.md`](../RELEASE_PLAN.md); chronology is
> [`docs/RELEASE_JOURNAL.md`](../RELEASE_JOURNAL.md). Inline status notes here are **historical and NOT
> authoritative** — check the ledger for live status (`read-at-start-record-at-completion` / `single-task-ledger`).
> Edit this file only to correct a *finding*.

# Architecture + Memory-Overconsumption Review — QUAL-57

**Status:** complete (2026-07-02). **Scope:** (1) is the overall design a solid, state-of-the-art voice-assistant
architecture; (2) memory-overconsumption potential per request and resident, **especially multi-turn conversation
state and the fire-and-forget (F&F) path**, on the 1 GB-class ARM targets (WB7).
**Method:** three parallel deep-reads (runtime architecture map · multi-turn/conversation memory audit · F&F QUAL-8
re-verification + `create_task` census), the three headline memory findings then spot-verified directly at
`metrics.py:213/752`, `webapi_router.py:852-861`, `conversation.py:44/429/447`.
**Follow-ups filed:** → tracked as **BUG-16** (M1), **BUG-17** (M2), **BUG-18** (M3), **QUAL-58** (M4–M8 sweep),
**QUAL-59** (A6/A7 drift + dead code). Architecture-level gaps A1–A5 recorded for user decision (design-scale, not
filed unilaterally). F&F durability lens remains **QUAL-56** (this review confirms its premise: state is in-memory
only).

---

## TL;DR — verdicts

**Architecture: solid and unusually well-disciplined for its class — but not fully state-of-the-art at the
interaction layer.** The bones are genuinely good: one unified workflow with conditional stage-skipping (the
docs' old dual-workflow model is historical), entry-point provider discovery across 8 families, donation-driven
3-tier NLU cascade (keyword→spaCy→LLM), true streaming ASR with partials where the provider supports it,
device-negotiated audio contracts for ESP32 satellites, and **enforced** hexagonal layering (import-linter
contracts, zero live violations found). What's missing vs. the current reference shape: **barge-in**, **incremental
TTS**, and **per-client concurrency isolation** (shared singleton workflow + shared ASR decoder state, lock-free
session dict).

**Memory: the F&F path — historically the worst offender — is now clean** (all 10 QUAL-8 findings resolved by the
QUAL-28 store redesign; re-verified). **The live risk moved to the request path:** a per-session **metrics leak**
that grows on *every* REST call and WS connection (M1), an **uncapped PCM accumulator** on the `/ws/audio` batch
floor that lets one misbehaving client OOM the box (M2), and an **untrimmed LLM conversation store** whose
configured bound is dead code (M3).

---

## Part 1 — Architecture assessment

### What's right (measured against wake→VAD→streaming-ASR→NLU→action→TTS reference shape)

- **Single unified pipeline, stage-skipping per entry point** (`irene/workflows/voice_assistant.py:35-52`); all
  entry points (REST text/audio, `/ws/audio`, CLI, mic runner, trace variants) funnel through `WorkflowManager` —
  one orchestration spine, not N parallel pipelines.
- **Hexagonal layering is enforced, not aspirational**: 7 import-linter contract groups
  (`pyproject.toml:436-566`) + a test; grep confirmed zero live violations; the old `get_core()` service-locator
  escape hatch is gone (`engine.py:27-30`); composition root injection (`runners/composition.py:27-51`).
- **Provider/component model**: 8 provider families + 11 components discovered via entry points, config-gated,
  availability-checked (`asr_component.py:129-156`); runtime default-provider switching.
- **Streaming where it counts**: sherpa `OnlineRecognizer` path emits true partials with endpoint detection,
  decode off-loop via `to_thread` (`providers/asr/sherpa_onnx.py:218-260`); `/ws/audio` gates on
  `supports_streaming()` and falls back to a batch floor (`webapi_router.py:824-874`); ESP32 does on-device wake
  word, server-authoritative endpointing, reply audio conformed to a per-device `AudioContract`
  (`webapi_router.py:988-1030`).
- **Edge-first NLU tiering**: donation-driven cascade keyword→spaCy→LLM with per-provider confidence thresholds
  (`nlu_component.py:271-333, 785-881`) — the right cost/latency shape for an embedded box.
- **Async hygiene**: blocking inference consistently `asyncio.to_thread`-offloaded (~25 sites verified); the one
  `time.sleep` found lives inside a `to_thread`-executed blocking body (`providers/audio/miniaudio.py:203`).
- **Observability**: trace/replay infrastructure (used by the eval harness), event-bus tap (`/ws/observe`),
  metrics with bounded ring buffers.

### Gaps vs. state of the art (A-findings)

- **A1 — no barge-in / interruption.** No mechanism ducks or cancels in-progress TTS on new speech;
  `stop_current_workflow` kills the whole workflow task, not the utterance (`workflow_manager.py:772-785`).
  Modern assistants treat interruption as a first-class interaction primitive.
- **A2 — TTS is whole-utterance.** "Streaming" = PCM playout of a fully synthesized result
  (`tts_component.py:440-489`); no incremental synthesis → reply latency scales with response length.
  (`docs/design/streaming_tts.md` exists as design only.)
- **A3 — no per-client concurrency isolation.** One process-wide workflow singleton with instance-level buffers
  (`workflow_manager.py:56,439-448`; `voice_assistant.py:77-79`); shared ASR provider instance whose decoder state
  is reset *between* utterances only (`asr_component.py:400-454`) — concurrent batch-path clients can contaminate
  each other (streaming path is safe: per-call `create_stream()`, `sherpa_onnx.py:240`); `ContextManager.sessions`
  mutated lock-free (`context.py:68-101`). Single-household load makes this latent, not broken — but it's the
  main scalability wall.
- **A4 — weak session continuity.** Contexts keyed by `session_id` only (`context.py:75`); REST mints a fresh
  session per request absent `room_alias` (`webapi_router.py:223`); `resolve_physical_id` usually falls back to
  session-derived ids (`client_registry.py:586-604`) — room/device continuity works only when callers cooperate.
- **A5 — no durability for in-flight actions.** Action store is in-memory (`ClientRegistry._actions`); a restart
  loses timers/deferred completions. **This is exactly QUAL-56's lens — premise confirmed, task stands.**
- **A6 — API/doc drift.** `/system/capabilities` hardcodes provider/workflow lists that diverge from reality
  (`webapi_router.py:716-719` advertises `continuous_listening`; only `unified_voice_assistant` exists,
  `workflow_manager.py:29-31`); docs' dual-workflow narrative is historical.
- **A7 — dead/latent code with wrong assumptions.** Phase-3.5 action-management methods still assume domain-keyed
  `active_actions` (`handlers/base.py:1114-1115, 1228-1252` — would mis-cancel/double-record if ever wired; REST
  endpoints are stubs, `intent_component.py:532-559`); `get_context_for_intent_processing` machinery has zero
  callers (`context.py:274-343`); cwd-dependent hardcoded paths in NLU donation conversion
  (`nlu_component.py:641, 661-671`); god-objects (`intent_component.py` 2276 lines, `api/schemas.py` 2259).

**Verdict:** architecture ≈ **top-quartile for embedded/self-hosted voice assistants** (layering discipline,
provider model, streaming seam, eval harness are all above the norm — many production systems ship worse), but
**not SOTA at the interaction layer** until A1/A2 land, and **single-household-scoped** until A3/A4 are addressed.

## Part 2 — Memory-overconsumption findings (M-findings, ranked)

- **M1 [HIGH] — Metrics session leak: permanent per-session growth in a process-lifetime singleton.**
  Every new session calls `record_session_start` (`context.py:101`) → stores
  `_active_actions[f"session_{sid}:session"]` (key format `metrics.py:213`) + a `_domain_metrics[f"session_{sid}"]`
  entry (~1-1.5 KB combined). `record_session_end` checks `if domain in self._active_actions`
  (`metrics.py:752`) — but keys are `"{domain}:{action_name}"`, so the check is **always false**: the completion
  never fires and nothing ever deletes `_domain_metrics["session_*"]`. Session eviction paths don't even call
  `record_session_end` (`context.py:241-242, 877-878`). Amplifier: REST mints a fresh session **per request**
  (`webapi_router.py:223, 283`), `/ws/audio` per connection (`:779`) → the leak grows with *every* API call.
  Side effects: `current_concurrent_actions` permanently inflated; dashboard/summary endpoints iterate
  ever-growing dicts (`metrics.py:349, 845`). *(spot-verified)* → **tracked as BUG-16**
- **M2 [HIGH] — `/ws/audio` batch floor accumulates PCM without any cap.**
  `frames = bytearray()` grows per binary frame until an `{"type":"end"}` text frame or disconnect
  (`webapi_router.py:852-861`) — no max-bytes/max-duration bound, no backpressure; ~32 KB/s ≈ **115 MB/h per
  connection** for a client that never sends "end" (buggy satellite firmware), plus a 2× peak at `bytes(frames)`
  (`:864`). The mic/VAD path *is* bounded (`audio_processor.py:331-340`) — only this floor is not.
  *(spot-verified)* → **tracked as BUG-17**
- **M3 [MED-HIGH] — LLM conversation store unbounded; `max_context_length` is dead config.**
  `handler_contexts["conversation"]["messages"]` appends system/user/assistant entries per turn
  (`conversation.py:423-426, 429, 447`) and domain threads likewise (`context_models.py:664-679`);
  `max_context_length` is read from config (`conversation.py:44,51,54,85`; `config/models.py:574`;
  `config-master.toml:508`) and **never used** — no trim exists. Each turn also ships the **full** history to the
  LLM (`conversation.py:596`) → unbounded prompt growth (latency + token cost). Room-scoped sessions have stable
  ids (`session_manager.py:37-39`), so the primary household use-case keeps one context alive for days.
  General `conversation_history` is fine (capped 10, `context_models.py:348-356`) — the leak is specifically the
  LLM-handler store. *(spot-verified)* → **tracked as BUG-18**
- **M4 [MED] — `AudioTranscoder._resampling_cache`: 100-entry FIFO retaining full audio blobs at ~0% hit rate.**
  Class-level, keyed md5(first 1 KB)+rates (`audio_helpers.py:546-549, 625-631, 670-676`) — live audio is unique
  per utterance, so it's a dead store; the reply-conform path caches full synthesized TTS replies
  (`audio_negotiator.py:182-184`) → up to ~20-30 MB retained in rate-mismatch deployments. → **QUAL-58**
- **M5 [LOW-MED] — Per-identity action-history keysets never pruned.** `_recent_actions`/`_failed_actions`/
  `_action_error_count` capped per identity but identity keys never deleted (`client_registry.py:171-173,
  513-530`); with session-id fallback physical ids, every F&F-launching ephemeral session adds a permanent key.
  → **QUAL-58**
- **M6 [LOW] — Maintenance functions exist but are never wired.** `ClientRegistry.cleanup_expired_clients()`
  (`client_registry.py:393-413`) and `reap_dead_actions()` (`:502-509`, the advertised "layer-3 periodic sweep")
  have **zero runtime callers** (only tests). Bounded in practice by layers 1/2/4, but the documented 4-layer
  reaping model is really 3-layer; random per-connection `client_id`s would also grow `self.clients` + rewrite
  `cache/client_registry.json` per registration (`:203-204, 541-559`). → **QUAL-58**
- **M7 [LOW] — Unbounded queues + orphaned warm-up tasks.** `NotificationService` queue has no maxsize
  (`notifications.py:81`; consumer normally running, but `get_notification_service()` can mint a consumer-less
  instance, `:531-536`); input queues unbounded (`inputs/web.py:99`, `inputs/manager.py:43`, `inputs/cli.py:31`
  — human-rate, INFO); six provider `warm_up` preloads are unreferenced `create_task` orphans (GC-cancellable
  mid-model-load): `asr/whisper.py:58`, `asr/vosk.py:52`, `asr/sherpa_onnx.py:70`, `tts/piper.py:68`,
  `tts/silero_base.py:98`, `tts/vosk.py:78`. → **QUAL-58**
- **M8 [LOW, disk] — Trace files unbounded on disk.** Per-utterance trace JSON embeds full base64 audio
  (`trace_context.py:633-652`, deliberate) and is dropped from RAM after save — no RAM accumulation — but
  `traces_dir` has no rotation/cap. → **QUAL-58**

### Per-request transients (bounded — no action)

Voice-segment peak ≈ 4-5× utterance size (chunks + combined copy + float32 normalize, `audio_processor.py:79-96,
495`) — transient, bounded by `max_segment_duration_s`. Trace objects are per-utterance and dropped after save.

## Part 3 — F&F re-verification (QUAL-8 → 2026-07-02)

All **10** QUAL-8 findings resolved (9 FIXED, 1 CHANGED-by-redesign) by the QUAL-28 store-centric rewrite +
QUAL-9/11: launch/removal keys symmetric on `(physical_id, action_name)` (`handlers/base.py:697, 750`;
`client_registry.py:450-488`); `get_or_create_context` exists (`context.py:84-102`); task refs held in
`ActionRecord.task` (`client_registry.py:126`) — no GC-cancellable orphans; timeout monitor awaits the shielded
task instead of flat-sleeping (`base.py:812-822`); pruning is layered (done-callback + read-time liveness reap +
32/identity cap; `MemoryManager` deleted); metrics keyed `domain:action_name` (QUAL-9, `metrics.py:211-234`); the
timer duplicate-`session_id` TypeError, divergent write-back processors, unreferenced completion task, and
cancelled-timer TODO are all gone (write-backs deleted outright; `timer.py` rewritten, 389 lines).
Residuals — all folded into **QUAL-58** except the latent-correctness item (**QUAL-59**): the never-scheduled
layer-3 reaper (harmless today: `add_active_action`'s task-less records are its only true exposure and it has
zero callers), per-identity keyset growth (M5), notification-queue path (M7), and the domain-keyed dead
Phase-3.5 methods (A7). Full `create_task` census: every site except the six warm-up preloads (M7) is
referenced + lifecycle-managed.

## Part 4 — Verified FINE (checked, bounded, no action)

`conversation_history` capped 10 with single writer; session eviction wired and running (30-min idle, lazy sweep
+ background task from `engine.py:106`); F&F action store capped/reaped (above); metrics ring buffers all maxlen'd
(`metrics.py:116, 135, 663, 695, 1023-1025`); VAD/mic path fully bounded incl. drop-oldest mic queue
(`microphone.py:199-214`); NLU recognition cache OFF by default, capped+TTL when on (`nlu_component.py:841-849`);
fuzzy cache capped FIFO (`hybrid_keyword_matcher.py:765-769`); history→NLU injection = last-3 intent names only;
event-bus/observe/WS-output registries deregister in `finally`; observe queue bounded drop-oldest
(`observe.py:33-45`); timers self-delete; TTS temp files cleaned in `finally`; no audio/results retained on
contexts after completion.
