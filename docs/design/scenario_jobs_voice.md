# Scenario jobs, voice side — the durable job + the bridge SSE adapter (ARCH-68 design)

**Status: DESIGN — written 2026-10-06 against the bridge's job-API spec; implementation →
ARCH-69 (this document is its spec), re-pin → BUILD-59.** Board PROD-18 round 2, decisions 9–10
(owner paste 2026-10-06). The bridge side: [`../../../locveil-bridge/docs/design/scenarios/
scenario_jobs.md`](../../../locveil-bridge/docs/design/scenarios/scenario_jobs.md) — §5 (the
shapes), §6 (what a consumer may rely on), §8 (what voice said it will build; the two designs
meet there), §10 (the WB7 checklist). Every shape quoted below is that document's, verbatim;
on disagreement the bridge's spec wins for the wire and this one for what voice does with it.
Substrate: [`durable_actions.md`](durable_actions.md) §3 (the `durable-actions` invariant).
Predecessor: ARCH-67 (acknowledge-then-confirm, sized requests — `RELEASE_PLAN_DONE.md`).

## 1. What this adds, in one paragraph

Today a scenario switch is one synchronous request: ARCH-67 sizes it from the catalog's
`max_duration_ms` (a cold movie start = 78.875 s), speaks «Запускаю сценарий» at once and the
factual «Включила «{label}»» when the bridge's chain ends (`smart_home.py:755–817`). That
works, and keeps working (§9). What it cannot do: survive a voice restart mid-chain (the turn
dies with the process), refuse a second command honestly (today it would send a second request —
the bridge's new per-room lock answers `409`), or report a chain the bridge finished after voice
gave up. The job path fixes the three: the scenario command is sent with `wait: false`, the
bridge's `202` hands voice a `job_id` and a ceiling, voice launches a **durable action** that
follows the job over the bridge's SSE channel to its terminal event and speaks the outcome to the
device that asked — through the same route a timer ring takes, surviving restarts on either side.

## 2. The driven port and the adapter

### 2.1 `ScenarioJobEventsPort` (`intents/ports.py`, beside `DeviceCommandDeliveryPort`)

The domain's need is "follow one room's job to its end and, when the stream cannot be trusted,
read the record". That is three abstract methods — pure (the port module is pinned pure by the
*Domain ports and boundary types stay pure* contract, `pyproject.toml:582`):

```python
class ScenarioJobEventsPort(ABC):
    """Driven port for the bridge's scenario-job events (ARCH-68; the tier-3 job API)."""

    @abstractmethod
    def events(self, room_id: str) -> AsyncIterator[JobEvent]:
        """The room's job events as they arrive, plus a synthetic STREAM_OPEN on EVERY
        (re)connect of the underlying stream — the follower's cue to GET the record (§6.2/§6.4
        of the bridge spec). Never ends on its own; the consumer stops iterating."""

    @abstractmethod
    async def get_job(self, job_id: str) -> JobLookup:
        """`GET /scenario/jobs/{id}` → the record, UNKNOWN (404 job_unknown) or UNREACHABLE."""

    @abstractmethod
    async def get_active_scenario(self, room_id: str) -> Optional[str]:
        """`GET /scenario/state?room=` → the active scenario id, "none" when the room is
        idle (404), None when the bridge did not answer."""
```

The boundary types live in a new pure module `intents/scenario_jobs.py` (same regime as
`device_commands.py`): `JobEvent(kind: STREAM_OPEN | STARTED | PHASE | STEP | TERMINAL, job_id,
room_id, job_state, failures: Tuple[JobFailure, ...], result_scenario, duration_ms)` with
`JobFailure(device, command, error)` = the terminal event's `failures[]` entries verbatim
(`scenario_jobs.md` §5.4); `JobLookup = Union[JobRecord, JobLookupMiss]` where `JobRecord(job_id,
room_id, kind, target, state, max_duration_ms, failures, result_scenario, duration_ms)` is the
§3 record's domain view and `JobLookupMiss(reason: "unknown" | "unreachable")`. `PHASE` and
`STEP` carry only `job_id`/`room_id` — narration is a later cut (§8 a of the bridge spec); they
are liveness.

### 2.2 `BridgeEventsClient` (`outputs/bridge_events.py`, beside `BridgeClient`)

One class, one background task for its lifetime, started by `setup_bridge_output`
(`runners/composition.py:89–96`) right after `BridgeClient` and stopped with it:

- **One persistent subscription** to `GET {base_url}/events/scenarios` (the existing channel,
  §5.4), opened at start and kept open whether or not a job runs — so "subscribe before
  launching" (§6.3) holds by construction and the handler never waits for a connect inside a
  turn. The stream session is `aiohttp.ClientTimeout(total=None, sock_read=5.0)`: the bridge
  sends a `keepalive` after each ~1 s of silence, so **5 s without any frame is exactly the
  spec's dead stream** (§8 d) and surfaces as `asyncio.TimeoutError` → reconnect. The two
  housekeeping bodies are consumed and never forwarded:
  ```
  data: {"eventType":"connected","message":"Connected to scenarios channel","timestamp":"2026-10-06T18:31:12.418532"}
  data: {"eventType":"keepalive","timestamp":"2026-10-06T18:31:13.419104"}
  ```
- **SSE parsing** is a 30-line hand-written reader over `resp.content` (lines `id:` / `data:`,
  an empty line ends a frame; the JSON is the `data:` payload with the type in `eventType`) —
  no new dependency. `Last-Event-ID` is not sent (the channel does not honour it, §6.2).
- **Reconnect** with the §8 d backoff: 1 → 2 → 4 → 8 → 16 → 30 s cap, ±25 % jitter, forever
  (an idle box reconnecting to a bridge that is down costs one request per half-minute). A
  successful connect resets the backoff. After EVERY successful connect — the first one
  included — the client pushes `JobEvent(STREAM_OPEN)` to every subscriber; what the follower
  does with it is §5.
- **Fan-out:** `events(room_id)` registers a bounded `asyncio.Queue` (64; on overflow the
  oldest is dropped and a STREAM_OPEN is enqueued so the follower re-syncs by GET — the
  mirror of the bridge's slow-consumer rule, §6.7) filtered by `room_id`; a terminal event
  without `job_id` (the startup-restore notification, §5.4) is dropped at the adapter.
- **The two GETs** reuse `BridgeClient._request_json` (injected at construction: one HTTP seam,
  the tests stub one function): `get_job` maps `200` → `JobRecord`, `404` with
  `detail.code == "job_unknown"` → `JobLookupMiss("unknown")`, transport errors →
  `JobLookupMiss("unreachable")`; `get_active_scenario` maps `200` → `scenario_id`, `404` →
  `"none"`, transport error → `None`. Both use the fallback timeout (`[outputs.bridge]
  timeout_seconds`, `bridge.py:145–149`) — they are reads, nothing published sizes them.
- **"The ONLY module that knows the bridge"** (`bridge.py:3`) becomes a pair: both module
  docstrings say "one of the two modules that know the bridge — `bridge.py` (REST) and
  `bridge_events.py` (SSE); nothing else speaks to it". `core` keeps no edge to `outputs`
  (`pyproject.toml:599–612`): the handler gets the port injected like the delivery port, via
  `set_device_command_services(…, events_port=…)` (`manager.py:139`, `intent_component.py:105`),
  the composition passes the instance up through `core` typed `Any` (the OutputManager pattern).

### 2.3 How the `202` reaches the handler — `DeliveryResult` fields, not a `start_job()`

**Decision: `DeliveryResult` (`core/interfaces/output.py:40`) gains three fields —
`accepted: bool = False`, `job_id: Optional[str] = None`, `max_duration_ms: Optional[int] =
None` — and `DeviceCommand` gains `wait: Optional[bool] = None`.** A separate `start_job()` on
the delivery port was considered and set aside: it would need its own OutputManager routing,
its own timeout sizing, its own transport-error mapping and its own capture shape — a second
copy of everything `deliver()` → `_to_delivery_result` already does — for a request whose
only difference is one body field and one status code. One chokepoint keeps the dispatcher's
bounded wait, the fixtures, the ack path and the `bridge_unreachable` mapping untouched.

- `DeviceCommand.request_body()` (`device_commands.py:91–94`) adds `"wait": false` **only when
  `self.wait is False`**; `to_dict()` (the fixture/capture shape) is unchanged, so no crossover
  fixture moves. The handler sets `wait=False` in exactly one place — `_scenario`
  (`smart_home.py:755`), for `capability == "scenario"` (`set` and `off`), and only when an
  events port is wired. **Every device-level command keeps `wait` absent** — the owner's
  rider: device-level long actions stay synchronous under tier 1.
- `_to_delivery_result(command, status, payload)` (`bridge.py:212–237`) today ignores `status`.
  It branches:

  | `status` | mapping |
  |---|---|
  | `202` | `delivered=False, accepted=True, job_id=state.job_id, max_duration_ms=state.max_duration_ms, echoed_value=state` — **never `delivered`**: `success: true` on a `202` means accepted, not done (§5.1), and `_speak_outcome` must never turn it into «Включила». |
  | `409` with `error.code == "job_in_progress"` | as today (`delivered=False, error_code="job_in_progress", detail=error.message`) **plus `job_id=error.job_id`** — the running job, which the handler may adopt (§4.4). |
  | `200` on a `wait: false` request | the bridge (or the commons mock bridge, or a pre-1.12 bridge that ignores `wait`) ran the chain synchronously: mapped exactly as today → the ARCH-67 confirmation. The job path is therefore safe to ship before the re-pin and against every bridge voice may meet. |
  | everything else | unchanged. |

  The `202` body, verbatim from §5.1:
  ```json
  {"success": true, "device_id": "scenario_manager_living_room", "capability": "scenario", "action": "set",
   "state": {"scenario": "music_auralic", "job_id": "j-…", "max_duration_ms": 61500}, "error": null, "no_op": false}
  ```
  and the `409`:
  ```json
  {"success": false, "device_id": "…", "capability": "scenario", "action": "set", "state": null,
   "error": {"code": "job_in_progress", "message": "a scenario job is running in room 'living_room' (job j-…, switch → movie_zappiti)", "job_id": "j-…"}}
  ```
- The request timeout for the `wait: false` POST stays ARCH-67's sized value (the bridge
  emits `scenario_job_started` and writes the `202` inside the request, §5.4 — it answers in
  milliseconds; the sized timeout is merely never reached). `max_duration_ms` on the `202`
  equals the catalog's published number for the target (§5.4, confirmed by the bridge); voice
  takes it from the response and falls back to `published_wait_ms` if absent.

## 3. The durable record — one per room

The follower is launched through the substrate, never hand-rolled (`durable-actions`):

```python
await self.execute_fire_and_forget_with_context(
    self._follow_scenario_job,
    action_name=f"scenario_job:{room_id}",      # bridge room id — the name IS the one-per-room key
    domain="smart_home", context=context,
    timeout=hard_cap_s + 5.0,                   # §5: H + the timer's 5 s monitor grace
    durable=True, redeliver_on_reconnect=True,  # a missed outcome loses real value (§3 rule 4)
    job_id=job_id, room_id=room_id, kind=kind, target=target, label=label,
    max_duration_ms=max_duration_ms, accepted_at=time.time(), resume=False)
```

- **Identity.** `action_name = "scenario_job:{room_id}"` with the **bridge's** room id (the
  scenario device's `room`, `CatalogDevice.room`). The timer mints unique names (§3 rule 6);
  here the name is deliberately the lock key: one record per room mirrors the bridge's one job
  per room (decision 10), re-arm reuses it (D-8), and a colliding launch is impossible because
  `_scenario` consults the handler's room index (§4.4) before sending. The requesting device's
  identity (`physical_id`, `session_id`, `room_id` = voice's room, `source`, `language`) is
  captured by the launch as for every F&F action (`base.py:147–161`) — that is what routes the
  outcome back to the satellite reply socket, the web push or the desktop output, and what
  `redeliver_on_reconnect` queues for an offline satellite (`notifications.py:426–443`).
- **Persisted** (`<assets_root>/state/durable_actions.json`, the timer's store, D-2 — never
  `cache/`): the `DurableActionRecord` the launch writes (`base.py:751–765`) with
  `rearm.params` = the JSON kwargs above: `job_id`, bridge `room_id`, `kind` (`switch` |
  `stop`), `target` (scenario id or `none`), `label` (the spoken name resolved from the
  catalog's value labels at launch, in the request language — so re-arm needs no catalog),
  `max_duration_ms`, `accepted_at`. `metadata.language` rides as today; `completion_message`
  is `None` — the outcome is not known at launch (§4.5 says how the terminal text travels).
- **In memory** the handler keeps `self._jobs: Dict[str, RunningJob]` (bridge room → the
  launch's params + the `ActionRecord`), filled at launch and at re-arm, cleared when the
  follower returns. It is the §4.4 "voice owns the room's record" check.
- **Re-arm after a voice restart** — `rearm_durable_action(record)` relaunches
  `_follow_scenario_job` with the persisted params and `resume=True`; the follower's first act
  on resume is `get_job(job_id)` (§5, the STREAM_OPEN rule — the persistent stream's first
  connect delivers one anyway). A record older than `GRACE_WINDOW_SECONDS` (1 h,
  `durable_actions.py:41`) at resume is dropped silently with a log line — the house has moved
  on; speaking a yesterday's outcome is noise. **Substrate change this needs** (found at
  intake): `reconcile_durable_actions` re-arms only records whose deadline is in the future
  (`durable_actions.py:238–244`) and announces the rest with timer texts (`:48–55`). A follower
  whose hard cap passed while voice was down must still be ASKED, not announced as «истёк
  таймер». Additive rule: a record with `metadata["on_missed"] == "rearm"` goes to
  `rearm_durable_action` regardless of its deadline, and the handler decides (GET → speak, or
  the 1 h silence). Records without the key behave exactly as today; the restart test covers
  both branches. (The alternative — a 24 h F&F `timeout` so the deadline is always in the
  future — was set aside: it lies on the `/actions` listing and the hard cap would then be
  unmonitored.)
- **After a bridge restart** — every job id is unknown (`scenario_jobs.md` §3): `get_job` →
  `JobLookupMiss("unknown")` → `get_active_scenario(room_id)` → speak the room's actual state
  (§4.3), never a bare failure.

## 4. Speech

All texts are `assets/templates/smart_home_handler/{ru,en}.yaml` entries (nouns from the
catalog, never from an event — the language-data convention). The scenario `label` is the
catalog value's label in the request language; device names in `failures[]` go through
`_device_name` (`smart_home.py:142`) from the catalog by `device` id, falling back to the id.

### 4.1 Acceptance (the `202`)

The turn's own reply IS the acknowledgement — no mid-turn notification, no second utterance:
`IntentResult(text=…, should_speak=True, metadata={"acknowledgement": text, "scenario_job":
{job_id, room_id, max_duration_ms}})`. The text is ARCH-67's `ack_scenario` / `ack_scenario_off`
extended with the ceiling, a new template pair `ack_scenario_job` / `ack_scenario_off_job`:

| `max_duration_ms` (s = ceil(ms / 1000)) | suffix ru | suffix en |
|---|---|---|
| s ≤ 5 | (none — «Запускаю сценарий») | (none) |
| 5 < s ≤ 20 | «, секунд {N}» — N = s rounded UP to a multiple of 5, spoken as a numeral word («секунд пятнадцать») | ", about {N} seconds" |
| 20 < s ≤ 45 | «, около полминуты» | ", about half a minute" |
| 45 < s ≤ 90 | «, около минуты» | ", about a minute" |
| s > 90 | «, пару минут» | ", a couple of minutes" |

So today's values speak: a stop (`none`, 29 000) → **«Выключаю сценарий, около полминуты»**;
every movie/music start (54 500–61 500) → **«Запускаю сценарий, около минуты»**; the
`music_reel`/`tape`/`turntable` starts (29 500) → «Запускаю сценарий, около полминуты». The
numbers are ceilings (tier 2); the WB7 sitting measures the real ones, and the phrase stays
a ceiling statement either way.

**Flag off (`acknowledge_slow_actions = false`): acceptance is silent** — the turn returns
`IntentResult(text="", should_speak=False, metadata={"scenario_job": …})` and the terminal
event is the only thing spoken. This is the owner's line in the bridge's §10 checklist ("with
the flag off, only the end") and keeps the ONE flag meaning one thing: whether voice speaks
before it knows.

### 4.2 Terminal event (success / failure)

The terminal is `scenario_switched` (switch) or `scenario_shutdown` (stop) with `job_id`,
`job_state`, `failures[]` (§5.4):

```
data: {"eventType":"scenario_switched","scenario_id":"movie_zappiti","room_id":"living_room","timestamp":"…","state":{…},"job_id":"j-…","job_state":"failed","duration_ms":41377,"failures":[{"device":"processor","command":"set_input","error":"gate timeout: …"}],"powered_off":["streamer"]}
```

- `job_state: succeeded` → ARCH-67's factual template: **«Включила «{label}»»** /
  **«Выключила сценарий»** (en "“{label}” is on" / "The scenario is off").
- `job_state: failed` → the existing `confirm_partial` over the same ok text, `{failed}` =
  the failing devices' catalog names, deduplicated, in event order:
  **«Включила «Кино с Zappiti», но не ответили: процессор»** (en "“…” is on, but no response
  from: processor"). The bridge's rule is that `failed` means "done, with these devices not
  where the plan wanted them" (§3), so the ok verb is honest and the clause names the gaps.
- The same texts are produced from a `JobRecord` when the outcome is learned by `get_job`
  instead of the event (`state`, `failures`).

### 4.3 The other endings

| ending | ru | en |
|---|---|---|
| bridge restarted (`404 job_unknown`), room now at the target | `job_bridge_restarted_ok`: **«Сценарий «{label}» включён, мост перезапускался»** (stop: «Сценарий выключен, мост перезапускался») | "“{label}” is on — the bridge restarted" |
| bridge restarted, room NOT at the target | `job_bridge_restarted_failed`: **«Мост перезапускался, сценарий «{label}» не включился»** (stop: «…, сценарий не выключился») | "The bridge restarted — “{label}” did not come on" |
| bridge restarted, `GET /scenario/state` also unanswered | `job_lost`: **«Мост не отвечает — не знаю, включился ли сценарий «{label}»»** | "The bridge isn't responding — I don't know whether “{label}” came on" |
| bridge unreachable through the backoff until the hard cap | `job_lost` (same) | (same) |
| hard cap passed, record still `running` | `job_stalled`: **«Сценарий «{label}» всё ещё переключается — проверьте»** | "“{label}” is still switching — please check" |
| resume > 1 h after acceptance | (silent; log) | |

### 4.4 A second command mid-job, and «stop»

`_scenario` checks the room index first. **Voice owns the room's running record** → answered
locally, no request (§8 c), with N = the record's remaining ceiling, `ceil((accepted_at +
max_duration_ms/1000 − now))` rounded UP to a multiple of 5, floor 5:

- a second start, or «stop», while a **switch** runs → `busy_scenario`:
  **«Ещё переключаю на «{label}», остановить можно будет секунд через {N}»**
  (en "Still switching to “{label}” — you can stop it in about {N} seconds");
- any scenario command while a **stop** runs → `busy_scenario_off`:
  **«Ещё выключаю сценарий, секунд через {N} можно будет продолжить»**
  (en "Still shutting the scenario down — about {N} seconds more").

**Voice does not own a record** (another client started the job, or voice just restarted
without one) → the request is sent; a `409 job_in_progress` comes back with `error.job_id`
(`error.message` is prose, never parsed) → voice **adopts the job**: one `get_job(job_id)`
gives `kind`, `target`, `max_duration_ms`, `started_at` (§3 record), the label comes from the
catalog's value labels for `target`, the follower is launched for it exactly as for a job
voice started, and the turn answers the same `busy_scenario` / `busy_scenario_off` phrase
with N from those numbers. If that GET misses (`unknown` — the job ended between the `409`
and the GET; or `unreachable`), the turn answers `busy_scenario` with N from the catalog's
`max_duration_ms` of the command voice just sent and no follower is launched. After the
running job's terminal, «stop» is a plain new job (`scenario.off`, `wait: false`, `none`'s
ceiling — 29 000 today → «Выключаю сценарий, около полминуты»).

### 4.5 How the terminal text travels

The follower renders the phrase and announces it itself through a new
`NotificationService.send_action_outcome(session_id, domain, action_name, message, source,
physical_id, room_name, language, redeliver=True)` — `ACTION_COMPLETION` type, `TTS + LOG`,
`redeliver` honoured, **no preference gate** (modelled on `send_acknowledgement`,
`notifications.py:268–303`). Then it marks the in-memory `ActionRecord.metadata["announced"]
= True` and returns `True`; `_notify_action_result` (`base.py:862`) returns early for an
announced record. Why not the done-callback's generic completion: (a) the text is not known at
launch, and (b) `send_action_completion_notification` gates on the session's
`long_running_threshold` of 30 s (`context_models.py:460–467`) once the monitoring component
has wired the context manager — a warm switch finishing in 25 s would be swallowed. The user
asked; the answer is never below a threshold (the ARCH-28 D-5 argument). Delivery itself is
the existing route: `_deliver_via_output_manager` addressed by `source` + `physical_id`
(`notifications.py:526–539`) — the satellite's reply socket, the web push, the console — and
the undelivered queue drained at the satellite's next registration (`webapi_router.py:1165`).

## 5. Watchdog and liveness — the follower's state machine

Timers from acceptance: **W = `max_duration_ms` × 1.25 + 2 s** (the §6.5 watchdog; 61 500 →
78.875 s), **H = W + 30 s** (the hard cap: one more backoff cycle and a GET). Both are
constants of the follower, not config (§6).

| state | on | → state | says |
|---|---|---|---|
| **accepted** | the `202` landed, record persisted, index set | following | the §4.1 acceptance (or silence) — the turn's reply |
| **following** | `TERMINAL` for `job_id` | done / failed | §4.2 |
| following | `PHASE` / `STEP` for `job_id` | following | nothing — liveness only (resets nothing: W and H are absolute) |
| following | `STREAM_OPEN` (every reconnect; the first connect on resume) | per the GET: `running` → following; terminal → done / failed; `unknown` → **unknown**; `unreachable` → following (the adapter keeps reconnecting) | nothing, or §4.2 / §4.3 |
| following | W fires, stream alive | GET as above; `running` → following (until H) | nothing |
| following | H fires | one last GET: `running` → **stalled**; terminal → done / failed; `unknown` → unknown; `unreachable` → **lost** | §4.3 |
| **unknown** | `get_active_scenario(room)` → target (`result == target`, or `none` for a stop) | done | `job_bridge_restarted_ok` |
| unknown | → something else | failed | `job_bridge_restarted_failed` |
| unknown | → `None` (bridge silent) | lost | `job_lost` |
| **stalled** / **lost** / done / failed | — | the follower returns; the record is deleted with the in-memory one (`base.py:833–835`); the room index is cleared | — |

Keepalives are not progress (§6.6) and never reach the follower. Events for another `job_id`
in the same room (a job voice did not start, racing a stale index) are ignored except one
case: a `TERMINAL` for a different job while voice's own job is still `running` by the last
GET means the bridge forgot voice's job → treated as `STREAM_OPEN` (GET → likely `unknown`).
A stalled job is released, not killed (there is no cancel in the minimum); if the bridge does
finish it later, a next command meets the lock's `409` and §4.4 adopts it, or finds the room
free. Teardown: the follower is cancelled by process shutdown like every durable task — the
done-callback keeps the record for reconciliation (`base.py:815–831`), and the next start
re-arms it (§3).

## 6. Config

**No new keys.** The backoff, the 5 s dead-stream window, the queue bound, W and H are
recovery policy, not user tunables (BUG-17 / `GRACE_WINDOW_SECONDS` precedent). The job path
is enabled by the bridge output being enabled (`[outputs.bridge] enabled`); the one flag
`acknowledge_slow_actions` keeps its ARCH-67 meaning (§4.1). `config-ui-stays-functional`:
nothing changes in `CoreConfig`, no `ui-openapi` cut, config-ui untouched.

## 7. Tests (ARCH-69) and the WB7 sitting

**Unit, all hermetic.** A `FakeScenarioJobEvents` implementing the port from a scripted list
(`events(room)` yields what the test pushes; `get_job` / `get_active_scenario` answer from a
dict) and the stubbed `_request_json` seam (`test_bridge_output.py` pattern):

1. `_to_delivery_result`: `202` → `accepted`, `job_id`, `max_duration_ms`, not `delivered`;
   `409 job_in_progress` → `error_code` + `job_id`; `200` on a `wait: false` command → today's
   mapping; `request_body` carries `wait` only when `False`; `to_dict` unchanged.
2. The SSE reader: the two housekeeping frames dropped; a job frame parsed; a frame split
   across chunks; `sock_read` timeout → reconnect with the backoff sequence (1-2-4-8-16-30,
   jitter bounded) and a `STREAM_OPEN` per connect; queue overflow → `STREAM_OPEN`.
3. The handler: scenario start with the port wired → `wait: false` sent, the record persisted
   (store contents: `action_name`, `rearm.params`, `on_missed`), the acceptance text per the
   §4.1 table at 29 000 / 29 500 / 61 500 / 15 000 / 4 000, flag off → silent; a device-level
   command never carries `wait`.
4. The follower: terminal `succeeded` → «Включила …» via `send_action_outcome` with
   `redeliver=True`, record deleted, index cleared, no second generic completion; terminal
   `failed` → the `confirm_partial` clause with catalog names; STREAM_OPEN → GET running / GET
   terminal / GET unknown → each §5 row; W then H with the record `running` → `job_stalled`;
   unreachable through H → `job_lost`.
5. The 409 both ways: voice owns the record → no request, `busy_scenario` with N from the
   record; voice does not → request sent, `409` mapped to `busy_scenario` and the job adopted
   (a follower for `error.job_id` exists, its terminal spoken).
6. «stop» mid-job → `busy_scenario`; after the terminal → a new job with `none`'s ceiling.
7. Restart paths (the ARCH-28 restart test shape): launch → new store instance + reconcile →
   `rearm_durable_action` relaunches with `resume=True` and GETs; `404` → `get_active_scenario`
   → `job_bridge_restarted_ok` / `_failed`; a record older than 1 h → silent; a record past
   its deadline with `on_missed: rearm` is re-armed, a timer record past its deadline keeps
   today's apology path.
8. Routing: the outcome reaches the originating channel as speech
   (`test_notification_output_routing.py` pattern), is queued for redelivery when the
   satellite is offline, drained at registration.
9. The import contracts stay at 11 kept (ports pure, core → no outputs edge).

**The WB7 sitting — voice's lines of the bridge's §10 checklist, verbatim:**

```
[ ] voice acknowledges at once («включаю …»), confirms at the end; with the flag off, only the end
[ ] a second command mid-switch → "still working" (and the bridge logged a 409)
[ ] «stop» mid-switch → refused as "still working"; after the end → a new job that powers down
[ ] voice restart mid-switch → it re-subscribes and still confirms the end (or reports the job)
[ ] bridge restart mid-switch → voice reports a failure; `GET /scenario/jobs/<id>` → 404 job_unknown
```

plus the measured lines (cold starts, warm switches, stops) driven by voice — the
`duration_ms` is read off the SSE terminal in the owner's `curl -N` terminal. For the
bridge-restart line the expected voice text is §4.3's `job_bridge_restarted_ok` or `_failed`
(a state-based report, not a bare failure — the bridge's §8 row agrees).

## 8. Sequencing and the tasks this design files

Per the owner's execution order (board PROD-18, decision 9) and the instruction this design
ran under:

1. **ARCH-68** — this design (closed as a design task).
2. The bridge cuts **`catalog-v1.12.0`** (SCN-19; additive minor — the golden is
   byte-identical, the openapi gains the job schemas and event payloads, the guide gains
   "Jobs").
3. **BUILD-59** `[release]` — re-pin both catalog copies at `catalog-v1.12.0`
   (`python3 scripts/repin.py catalog`; the fixtures' `catalog_version` does not move — the
   golden's hash is unchanged); the conformance test asserts the openapi carries
   `ScenarioJobAccepted` / `CanonicalError.job_id` / `JOB_IN_PROGRESS`.
4. **ARCH-69** `[release]` — the implementation, this document as its spec (§2–§7), gated
   on BUILD-59 so the generated types and the conformance test see the real schema.
5. **The WB7 sitting** (§7) with both builds deployed; results into the bridge's SCN-19 table
   and a journal line here.

**Open point for the bridge / the owner:** the bridge's §11 orders voice's implementation
and the sitting BEFORE the cut ("any measured > published blocks the cut"), while the order
above puts the cut first so voice implements against the pinned schema. Both work for the
wire (§2.3 makes voice safe against a bridge that ignores `wait`); which one the owner wants
decides whether a sitting finding can still move a ceiling before `1.12.0` is tagged. ARCH-69
reconciles this at intake.

## 9. What ARCH-67's synchronous path keeps doing

Until ARCH-69 lands — and afterwards whenever no events port is wired, or the bridge answers
a `wait: false` request with `200` — a scenario command is what it is today: one sized
request (`max_duration_ms` × 1.25 + 2 s, `smart_home.py:244–265`), «Запускаю сценарий» at
once behind the flag, the factual «Включила «{label}»» or the honest failure when the bridge's
chain ends. It keeps working through the cut and the re-pin: `wait` absent is unchanged on
the wire at v1.12 (§5.1 — the default stays `true`). The job path replaces it for scenario
commands only; every device-level action stays on it by decision.

## 10. Considered and set aside

- **`start_job()` on the delivery port** — §2.3: a second chokepoint for one field.
- **Speaking the acceptance through `send_acknowledgement`** as ARCH-67 does — the turn ends
  at the `202`, so the turn's reply is the natural carrier; one utterance, not two.
- **Letting the done-callback speak the outcome** by writing `completion_message` into the
  record — defeated by the 30 s threshold gate (§4.5).
- **A per-launch minted name** (`scenario_job:{room}:{job_id}`) plus an index for the lock —
  the name as the key is simpler and matches the bridge's unit of concurrency.
- **Subscribing per job** (open the stream at launch, close at terminal) — loses "subscribe
  before launching" by construction and adds a connect to every turn.
- **Narrating steps** («процессор включается…») — later cut, per §8 a; the `PHASE`/`STEP`
  events are consumed as liveness so the adapter already carries them.
- **Cancel** — none in the minimum (decision 10); a «stop» is refused mid-job and is a new
  job after.
