> **📄 FROZEN EVIDENCE — not the task ledger.** Findings/rationale below are a point-in-time record. The
> authoritative **scope + status** is [`docs/RELEASE_PLAN.md`](../RELEASE_PLAN.md); chronology is
> [`docs/RELEASE_JOURNAL.md`](../RELEASE_JOURNAL.md). Inline status notes here are **historical and NOT
> authoritative** — check the ledger for live status. Edit this file only to correct a *finding*.

# Fire-and-Forget through the Durable-Execution Lens — QUAL-56

**Status:** complete (2026-07-02). **Predecessors:** `fire_and_forget_review.md` (QUAL-8, lifecycle bugs — all
fixed by QUAL-28/9/11) and `arch_memory_review_2026-07-02.md` §A5/Part 3 (QUAL-57 — confirmed the store is
in-memory; this review is the full durability critique it deferred to here).
**Method:** two parallel deep-reads — (1) the current F&F subsystem across 8 durability dimensions;
(2) **comparative:** how the sibling `../wb-mqtt-bridge` handles device-state persistence and restart recovery
(user-requested). **Scope framing from the user (2026-07-02):** *"It's only timer for now, but I plan more
intent handlers in the future, which will require durability"* and *"a fix + rules for new handlers would be
required"* — durability is therefore assessed as a **platform requirement** (the smart-home arc: ARCH-8 device
handlers, scenario-like actions), not a timer-only nicety.
**Follow-ups filed:** → tracked as **ARCH-27** (durable-action substrate design + handler-authoring rules),
**BUG-19** (store/status correctness fixes independent of the design), **QUAL-61** (dead capability removal).
Bridge-side findings → **VWB-18** (filed uncommitted in `../wb-mqtt-bridge/docs/action_plan.md` per
`cross-repo-source-of-truth`). _One-time status pointer (2026-07-02): VWB-18 was verified at intake, accepted
and **fixed** by the bridge maintainer same day — all three findings (F7) confirmed real, plus an aggravation
this review missed (boot persisted default state before the restore stub ran, clobbering last-good on every
boot). See the bridge's `action_plan_DONE.md`._

---

## TL;DR — verdict

Measured against the durable-execution reference model (persisted record of intent + idempotent steps +
recovery/reconciliation on restart + delivery guarantees), **the F&F subsystem scores zero on every axis by
explicit design**: the action store is deliberately runtime-only, nothing is re-armed after a restart, delivery
of completions is at-most-once with five independent silent-drop points, the retry machinery is dead config, and
two handlers report their own failures as success. Within a single process lifetime the QUAL-28 store is sound
(QUAL-8's bugs stayed fixed); across a restart the user's timer silently never rings and *"list timers"* denies
it ever existed. Today only the timer (up to 24 h horizon) truly needs durability — but the planned handler
generations do, so the remedy is a **substrate + rules**, not a timer patch.

The bridge comparison sharpens the design brief: it demonstrates the right persistence *shape* (tiny generic
SQLite key→JSON store behind a port; single `update_state` chokepoint doing dirty-write-on-change; ephemeral-field
filter; shutdown-artifact protection; reconcile-by-diff on restart; retained MQTT as external state) — and also
the two failure modes to design against: **persist-without-restore rot** (state written for months, restore still
a logging stub) and the **stale-intent key** (deactivated scenario resurrects on restart because completion never
clears the persisted record).

## Part 1 — F&F vs the durable-execution reference model

### D1. Persistence & crash survival — NONE (by design)

`ClientRegistry._actions` is documented "NEVER persisted (holds live task refs; must not survive a restart)"
(`client_registry.py:165-168`); `ActionRecord` "must never be serialized" (`:116-121`, live `asyncio.Task` at
`:126`). `_save_registrations` writes only `self.clients` (`:570-589`). Lost on restart: **in-flight timers**
(`_run_timer` = `asyncio.sleep(duration)`, `timer.py:377-386` — a 10-min timer restarted at minute 5 vanishes
with no notification and no record it existed), audio/TTS actions, the queued notification backlog
(`notifications.py:83`), per-identity history (`client_registry.py:169-173`), all metrics (`metrics.py:116,208`).
**User experience = total silent loss**: no startup code announces anything, and *"list timers"* reads the empty
store (`timer.py:284-286`) — indistinguishable from never having set one.

### D2. Scheduling durability — NONE; plus a dead scheduler

Timers are in-process `asyncio.sleep`. **`AsyncTimerManager`** (`core/timers.py:31`) — instantiated at the
composition root, injected, started and stopped (`composition.py:46`, `engine.py:53,70,107,138`) — has **zero
non-test schedule callers**: dead capability (→ QUAL-61). No cron-like component, no persisted schedule, no
re-arm logic anywhere.

### D3. Idempotency & duplicates — NONE; live-record overwrite bug

No dedup/idempotency-key machinery exists. Name generation: timers `timer_{counter}` with an instance counter
that resets per restart (`timer.py:41,162-163`); audio/TTS use **millisecond timestamps**
(`audio_playback_handler.py:67`, `voice_synthesis_handler.py:77`) — same-ms launches collide.
**Collision = silent overwrite of a live record**: `add_action` assigns with no existence check
(`client_registry.py:457-460`); the old task keeps running untracked, and its done-callback later
`remove_action`s the *new* record under the same key (`base.py:741`, removal has no record-identity check,
`client_registry.py:487-495`) — a name collision can evict a live successor. The 32/identity cap eviction
likewise drops a record **without cancelling its task** (`client_registry.py:464-468`). → **BUG-19**

### D4. Delivery guarantees — at-most-once, five silent-drop points

Completion path: done-callback → `_notify_action_result` (only if `record.session_id`, `base.py:759-762`) →
`NotificationService` → queue → consumer → OutputManager → e.g. `RemoteAudioOutput`. Drops, in order:
**(1)** preference gate suppresses completions under `long_running_threshold=30s`
(`context_models.py:451-458`) — and the gate re-mints an evicted session's context with *default* prefs
(`notifications.py:206`), so tuning doesn't survive eviction; **(2)** queue full → drop-with-warning
(`notifications.py:172-178`, QUAL-58's bound); **(3)** client offline at completion → drop
(`remote_audio.py:108-110`); **(4)** no origin match → drop-to-history (`notifications.py:375-382`,
`manager.py:112-118`) — history that is itself in-memory + 1h-TTL; **(5)** TTS/delivery failure → status False,
no requeue (`notifications.py:401-403`). `NotificationMessage.retry_count/max_retries=3` exist and are **never
read** (`notifications.py:66-67`) — dead fields (→ QUAL-61). Only the LOG sink is guaranteed.

### D5. Retry & failure handling — machinery present, dead in practice; failures masked

`_execute_with_retry` re-invokes the whole coroutine up to `max_retries+1` with fixed delay
(`base.py:815-870`; transient classification by string matching, `:872-911`) — but default `max_retries=0` and
**no call site ever passes it**: the retry branch is unreachable in production. Failure notifications default to
`critical_only=True` (`context_models.py:96-97,460-468`) → **the user is not told about ordinary failures**.
Timeout-cancelled actions are recorded as `error="cancelled"` — indistinguishable from user cancellation — and
`timeout_occurred` is never set (`metrics.py:229-231`). Worse: TTS/audio action coroutines catch their own
exceptions and `return False` (`voice_synthesis_handler.py:410-413`, `audio_playback_handler.py:279-281`) — the
store records **success**; the failure path never even starts. `retry_count` is written once as 0
(`base.py:683`) and never updated. → **BUG-19** (masking, timeout classification), **ARCH-27** (notification
policy is a design decision).

### D6. Recovery/reconciliation on restart — NONE

No startup code reconciles, restores, or announces (grep `restore|resume|reconcil` over composition/engine:
zero). The only recovery-adjacent machinery is the in-process zombie-reaper stack (4 layers,
`client_registry.py:448-455`) — it handles dead tasks, not dead processes.

### D7. Observability — aggregate-only, amnesiac

Runtime views exist in-process (context views `context_models.py:239-261`, metrics summary
`metrics.py:350-372`) and REST exposes **aggregates** (`/monitoring/*`, Prometheus counters), but an operator
**cannot enumerate named in-flight actions with owners/deadlines over REST**, and per-identity completion
history has no REST surface at all. Post-QUAL-59, `ActionDebugger.inspect_active_action`
(`debug_tools.py:90-170`) has zero callers — the deep-inspection capability is dead (→ QUAL-61). All views
reset on restart (D1). → observability requirements fold into **ARCH-27**.

### D8. Consumer inventory — what durability is actually for

All launches go through `execute_fire_and_forget_with_context` (`base.py:88-135`) — the single choke point,
which is the good news: a substrate slotted there covers every consumer. Today: **timers** (`timer.py:168-179`,
up to 24 h — the only consumer where durability matters now), audio playback ×4 and TTS ×4 (seconds-scale,
default 300 s timeout, no retries). **Per the user, future intent handlers (smart-home arc) will require
durability — the substrate must be platform-level, with authoring rules new handlers declare against.**

## Part 2 — Comparative: how `wb-mqtt-bridge` persists state (and what to take)

*(Evidence paths relative to `../wb-mqtt-bridge`; full detail in the agent read, summarized here.)*

**What it does:** a single generic **SQLite key→JSON table** (`aiosqlite`, upsert per write) behind a 5-method
`StateRepositoryPort` (`infrastructure/persistence/sqlite.py:36-217`); keys `device:{id}` (full state) and
`active_scenario` (intent). Writes are **dirty-write-on-change** from the one `update_state` chokepoint every
mutation funnels through (`devices/base.py:662-735`), full-record so idempotent, fire-and-forget tasks flushed
best-effort at shutdown; an **ephemeral-field filter** keeps churn fields (e.g. `last_command`) off disk
(`base.py:21-27`); teardown/failed-setup states are **blocked from overwriting last-good** persisted state
(`devices/service.py:170-187,326-333`). Restart recovery: **scenario intent is real** — `active_scenario` is
reloaded and re-applied via **reconcile-by-diff** (recompute the delta vs assumed state, re-issue only what
differs, `scenarios/service.py:402-439`, `reconciler.py:349-411`); WB-passthrough devices seed assumed state
from **retained MQTT payloads** with an explicit opt-in so retained *command* topics can't re-fire
(`wb_passthrough/driver.py:137-162`, `mqtt/client.py:47-54`).

**Patterns to borrow for the ARCH-27 substrate:**
1. Tiny generic key→JSON SQLite store behind a hexagonal port — no schema ceremony, `aiosqlite`, upsert.
2. One chokepoint owns persist — for Irene that's exactly `execute_fire_and_forget_with_context` + the
   done-callback: launch persists the record, completion **deletes it in the same operation** as the in-memory
   removal.
3. Persist **intent, reconcile by diff** — don't journal execution; on startup re-derive: a timer re-arms from
   its stored deadline (fire-now-with-apology if the deadline passed), a device action re-checks the device.
4. Ephemeral-field filter — keep live-task bookkeeping (task ids, monitors) out of the persisted record.
5. Shutdown discipline — flush pending writes before teardown; never let exit bookkeeping mark in-flight
   actions failed.

**Pitfalls the bridge itself demonstrates (design against them):**
- **Persist-without-restore rot** — device state has been written on every change since early phases while the
  restore side is a logging placeholder (`devices/service.py:435-455`), and the design doc claims durability
  that doesn't round-trip. *Rule: the design ships persist + restore + a restart test together, or not at all.*
- **Stale-intent resurrection** — `deactivate()` never clears the persisted `active_scenario` (no
  `state_repository.delete` call exists in the codebase) → deactivate, restart, and the scenario **re-activates
  and powers the AV gear back on**. *Rule: completion/cancellation clears the persisted record atomically with
  the in-memory clear.* → filed to the bridge as **VWB-18** (uncommitted), together with the restore-stub rot
  and the toggle-power inversion risk on restart (`reconciler.py:192-202`).
- Silent-failure store API (errors swallowed to logs), locale-ambiguous `DD-MM-YYYY` timestamp strings —
  avoid both.

## Part 3 — Findings → follow-ups

| # | Finding | Severity | → |
|---|---|---|---|
| F1 | No persistence/recovery for in-flight actions; restart = silent loss incl. 24h timers; future handlers need durability (user scope statement) | design gap (platform) | **ARCH-27** design: durable-action substrate + handler-authoring rules |
| F2 | Action-name collision silently overwrites a live store record; cap-eviction doesn't cancel the evicted task; ms-timestamp names collide | P1 correctness | **BUG-19** |
| F3 | TTS/audio coroutines mask failure as success (`return False`); timeout indistinguishable from user-cancel; `timeout_occurred`/`retry_count` never set | P1 correctness/truthfulness | **BUG-19** |
| F4 | Delivery of completions at-most-once with 5 silent-drop points; failure notifications suppressed by default; prefs don't survive eviction | design decision needed | **ARCH-27** (delivery-guarantee + notification policy section) |
| F5 | Dead capability: `AsyncTimerManager` (instantiated, never used), `ActionDebugger` inspection path (zero callers post-QUAL-59), `NotificationMessage` retry fields (never read) | hygiene | **QUAL-61** (user preference: dead code removed) |
| F6 | No REST enumeration of in-flight actions / per-identity history | observability gap | **ARCH-27** (observability requirements) |
| F7 | Bridge: `active_scenario` never cleared on deactivate → resurrection on restart; device-state restore is a stub; toggle-power inversion on restart | bridge-side | **VWB-18** (uncommitted filing in bridge ledger) |
| F8 | Retry machinery dead config (`max_retries=0` everywhere, fixed-delay, string-match transience) | keep-or-cut decision | **ARCH-27** (decide; if cut, removal folds into its implementation tasks) |
