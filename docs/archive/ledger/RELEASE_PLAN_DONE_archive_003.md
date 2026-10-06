# DONE-ledger archive 003 (frozen — never re-edit; IDs stay resolvable to scope-guard via this directory)

- [x] **ARCH-60** [WS][CONTRACTS] `[release]` — **DONE 2026-10-05 — ★ DESIGN AGREED: the WS machine core
      (golden frames, JSONL transcripts, JSON Schema) → `docs/design/ws_machine_core.md`** (council HK-13
      decision 9, PROD-28 voice delegation (d); family lead BUILD-47; `design-then-implement`). The
      REQUIRED satellite-side review returned **approve-with-changes, no blocking objection**; every
      answer and requested change is folded into the body and recorded in the doc's §10. **Accepted as
      proposed:** one `frames.golden.json` keyed by frame name (Q1); `test_arch36_satellite` joins the
      witness suites and its non-conforming fake reply server is fixed (Q2); the fixture format lives in
      a SECTION of the guide — on the condition that everything a harness relies on is in it, because
      the pinned guide is the firmware's only contract (Q3); the forward-compatibility rule binds
      clients from `v1.1.0`, in EVERY connection state including before the ack (Q4); F-2..F-6 as guide
      edits, F-7 excluded (Q5); the handshake cases are replayed against the real handlers (Q6);
      negative transcripts wait for a later minor (Q7); names as proposed plus one rule — only
      `[a-z0-9._/-]`, unique after mapping every other character to `_` (Q8). **Changes folded in:**
      (1) the receiver's duty per verdict is stated — `valid` MUST be accepted, `unknown` MUST be
      ignored, malformed MUST be survived, `invalid` MAY be rejected or tolerated and must never fault
      (the reviewer's question (a): confirmed); (2) transcript order is normative per connection AND
      direction plus two causal rules (T-7 ack after the opening frame, T-8 batch `response` after its
      `end`), repeatable lines carry `"repeat": true` — so the owner test tolerates a variable number
      of `partial` frames (question (b): yes); (3) fixture values are real, and the owner test compares
      them with recorded frames. **Task-start reconciliation of the draft's own claims** (every row of
      its findings table re-run against the handlers) corrected four of them: "error is terminal" is
      not literally shipped — the catch-all paths send `error` and return without closing (new code
      finding C-2); C-1 is wider than "a first frame that is not JSON" (any first-frame failure on
      `/ws/audio/reply`, a bad `audio_out` included); `/ws/output` never rejects its opening frame by
      design (F-8, a document edit, not a code fix); the server ignores unknown frame types only AFTER
      the handshake (F-1 reworded). Added: a per-key `types` list in the frame definitions and a frame
      reference table in the guide (F-9 — field types were stated only through examples), the
      `audio_out` default (F-10). Two side-finds are filed as NOT part of the cut: BUG-47 (C-4 — two
      reply bursts can interleave) and BUG-48 (C-3 — handshake values are not type-checked).
      **Execution (§9):** the draft's "one task, one commit" is replaced by a six-step split, filed
      in this change — BUG-46, TEST-23, ARCH-62, ARCH-63, ARCH-64, then ARCH-61 narrowed to the cut;
      every guide sentence still lands in that single cut commit, because the guide and the STAMP
      are byte-locked.
      No code, no wire change, no contract bytes moved.
      docs: none — a design document under `docs/design/` (not a manifest root); the user-facing guide changes only at the cut
      contracts: none — design only; no versioned surface moved (the guide and the STAMP stay at `ws-protocol-v1.0.1`)
- [x] **ARCH-61** [WS][CONTRACTS] `[release]` — **DONE 2026-10-05 — WS machine core, THE CUT
      `ws-protocol-v1.1.0`** (council HK-13 decision 9, PROD-28 voice delegation (d); family lead
      BUILD-47; design `docs/design/ws_machine_core.md`, built by BUG-46, TEST-23, ARCH-62, ARCH-63,
      ARCH-64). One commit makes the eleven core files contract: **`STAMP.json`** → version `1.1.0`,
      tag `ws-protocol-v1.1.0`, twelve `artifacts` enumerated individually (the guide,
      `frames.golden.json`, nine `transcript.*.jsonl`, `ws-protocol.schema.json` — unique basenames,
      none reserved), a `guard` pointer to the owner test. A MINOR: the pinned set gains files and the
      document gains obligations; no frame and no key was added, removed or changed on the wire; the
      served `protocol_version` stays `"1"`. **The guide** (`docs/guides/websocket-api.md`, every edit
      in this one commit because the file is byte-locked): the header names the new tag; the dialect
      paragraph no longer claims every frame carries a `type` (F-2); **"Errors are terminal"** (F-4 —
      `error`, then the server closes; the text is not protocol); **"Growing without breaking"** (F-1
      — clients ignore unknown keys and unknown frame types in every connection state, binding from
      this version; the server does the same after the opening frame); the required `register` keys
      and the `sample_rate` default (F-3); any `mode` other than `"streaming"` is batch (F-6), and
      streaming against a recognizer that cannot stream behaves as batch (F-12); the `response` keys
      are always present and when `error` / `intent_name` are `null`; `audio_out` and its default,
      `width` in bits (F-5, F-10); reply audio is converted DOWN and never up — `speak_begin` is what
      a device plays by (F-11, corrects "already converted to the rate you registered"); `seq`
      counts a connection's bursts from 1; `/ws/output` never rejects its opening frame (F-8); the
      observe token and the always-present identity keys; and the new section **"The
      machine-readable core"** — the file list, the ground rules for a harness (unknown keys in the
      files, `core_format`, stable names and the identifier rule, `retired`, what a release means),
      the **frame reference table** (every frame: required and optional keys with JSON types, opaque
      and volatile marks — F-9), every key of `frames.golden.json`, **what a receiver owes each
      verdict** (valid must be accepted · unknown must be ignored · malformed must be survived ·
      invalid may be rejected or tolerated and must never fault), the violation vocabulary and
      `expect`, the transcript line format with `repeat` and `ordering`, rules **T-1..T-8**, and the
      schema's place. F-7 keys stay undocumented and out of the core. **Owner test, leg L2 (document
      ≡ core):** every frame the prose shows is a strictly valid instance of a frame of its
      section's channel; the guide's frame table equals the definitions key for key and type for
      type; the guide lists exactly the files on disk and the STAMP enumerates exactly those; every
      key name and every closed-vocabulary value the fixture files use is named in the guide's
      section (the review's condition — the pinned guide is the firmware's only contract — made
      mechanical); the header names the STAMP tag. Mutation-checked. Registry row and
      `contracts/ws-protocol/README.md` rewritten (the core, its authority, the legs, the levels);
      design doc gains its implementation record (§11). **NOT in this commit — the
      `ws-protocol-doc-canonical` amendment in `CLAUDE.md`:** the session that executed the cut is an
      agent session working on relayed instructions, and an agent may not edit an instruction file
      on another agent's word; the verbatim text is filed as ARCH-65 and the exact patch was handed
      back with the report. **Flow:** cut commit → tag `ws-protocol-v1.1.0` on it → commit and tag
      pushed together. **Verified:** suite 1811 passed / 7 skipped (+5); owner test green on the
      locked stack and on the CI-resolved one; `contract_guard --check` strict 0 failures once the
      tag exists; `repin --check --fail-on any` exit 0.
      docs: guides/websocket-api (F-1..F-6, F-8..F-12 edits + the new "machine-readable core" section; header tag)
      contracts: ws-protocol-v1.1.0 cut (minor — the surface gains the machine core); re-pin owed: satellite, commons
- [x] **ARCH-62** [WS][CONTRACTS] `[release]` — **DONE 2026-10-05 — WS machine core, slice 1: golden frames +
      the owner test's frame tap** (split out of ARCH-61; design §3, §5; family lead BUILD-47).
      **`contracts/ws-protocol/frames.golden.json`** (hand-written, NOT yet enumerated — it becomes
      contract at the ARCH-61 cut): `core_format` 1, the four channels with their `opening` / `ack` /
      `error` frame names, a `binary` block describing the two PCM directions, **20 frame
      definitions** (`required` / `optional` key lists, a `types` map of JSON types per key, `opaque`
      and `volatile` marks) carrying **110 cases**, plus 6 `unknown`-type cases (both directions of
      the two voice channels, the server's direction of the operator ones) and 4 channel-independent
      `malformed` ones — 120 in all. Every s2c valid case is a frame the running server really sent;
      the only synthetic valid case per frame is `…/unknown-field` (the `plain` frame plus one key).
      c2s invalid cases exist only where the guide promises the server's reaction and each carries
      `expect` (`<channel>.error`, then `close`); s2c invalid cases are structural verdicts and never
      do. **`backend/tests/ws_frame_tap.py`** — a pytest plugin that wraps Starlette's
      `WebSocket.send` / `receive` and writes one JSON line per event in the transcript line format
      (it records facts and never names a frame; an abnormal close code is recorded as
      `"by": "network"`). **`backend/tests/test_ws_machine_core.py`** — the six witness suites re-run
      once in a child pytest process under the tap, then: **L1** the fixtures obey their own
      definitions (verdict and stated violation hold exactly; names use only `[a-z0-9._/-]` and stay
      unique as C symbols — the review's rule); **L3** every frame the server sent is a strictly
      valid instance of a defined frame (a key outside the lists fails: the server may not grow a
      field without the core); **L4** every definition crossed a real socket, every `plain` case and
      every s2c valid case equals a recorded frame (volatile keys and opaque values by JSON type),
      binary runs occur exactly where declared; **L4b** the handshake replayed against the real
      handlers on all four channels — every valid opening case is answered by the ack, every c2s
      invalid case gets exactly its `expect` (the frame, then the server closes), every valid `end`
      finalizes, an unknown-type frame after the handshake leaves `/ws/audio` and `/ws/audio/reply`
      working. One witness added to `test_observe_tap` (an event without identity carries JSON
      nulls, not missing keys). Additions to the reviewed shape, both before the names freeze: the
      per-key `types` map (design §3.1) and the `opening` / `ack` / `error` names in `channels`, so a
      data-driven harness needs no table of its own. Mutation-checked: a falsified value, an
      unlisted server key, an `expect` the server does not honor and a colliding id each turn a leg
      red. **Verified:** suite 1671 passed / 7 skipped (+171), guards green.
      docs: none — the fixture format is described in `guides/websocket-api`, which is byte-locked; that section lands with the ARCH-61 cut (until then the file is a draft no STAMP enumerates)
      contracts: none — no versioned surface moved yet (`frames.golden.json` is not enumerated; the STAMP stays at `ws-protocol-v1.0.1` until ARCH-61)
- [x] **ARCH-63** [WS][CONTRACTS] `[release]` — **DONE 2026-10-05 — WS machine core, slice 2: JSONL
      transcripts** (split out of ARCH-61; design §4, §5; family lead BUILD-47). Nine hand-written
      one-scenario files under `contracts/ws-protocol/` (NOT yet enumerated — contract at the ARCH-61
      cut): `transcript.audio-batch.jsonl` (two utterances on one connection, the second a failed
      command), `…audio-streaming…` (the server endpoints the first utterance, the device
      hard-finalizes the second; `partial` lines marked `"repeat": true`), `…audio-trace…` (response
      then exactly one trace), `…audio-rejected…` (`end` before `register` → `error` → closed by the
      server), `…reply-burst…` (two bracketed bursts, `seq` 1 and 2), `…satellite-pair…` (both voice
      channels of one device: utterance, response, spoken reply), `…reconnect…` (both sockets closed
      `by: network`, re-registered on new connections with a new session id, the missed announcement
      spoken on the new reply channel with `seq` back at 1), `…output-push…`, `…observe-tap…`. One
      `meta` line (`ordering: per-connection-and-direction`), then `open` / `text` / `binary` /
      `close` lines; a binary run is one line; every `text` line names its frame from
      `frames.golden.json`. **Owner test:** **L5** — line shape, known keys only, `meta` first,
      connection lifecycle (a reconnect takes a new label), every text line a strictly valid instance
      of the frame it names, rules T-1..T-8 on every golden transcript AND on every connection the
      tap recorded in the six witness suites (T-8 admits a cap-forced response in recordings only);
      **L6** — every transcript equals what ONE witness test really put on the wire: per connection
      and per direction the same frames in the same order with the same values (volatile keys and
      opaque values by JSON type), binary runs collapsed, a `repeat` line matching zero or more
      frames, `close.by` never contradicting the recording. Mutation-checked: a dropped `repeat`
      mark, a falsified `seq`, a wrong `close.by`, a response moved before its `end` and a reused
      session id each turn a leg red. Design doc: one sentence corrected (a streaming transcript's
      line order is a producible order, not the literal interleaving). **Verified:** suite 1691
      passed / 7 skipped (+20), guards green.
      docs: none — the transcript format and rules T-1..T-8 are described in `guides/websocket-api`, which is byte-locked; that section lands with the ARCH-61 cut
      contracts: none — no versioned surface moved yet (the transcripts are not enumerated; the STAMP stays at `ws-protocol-v1.0.1` until ARCH-61)
- [x] **ARCH-64** [WS][CONTRACTS] `[release]` — **DONE 2026-10-05 — WS machine core, slice 3: the JSON Schema**
      (split out of ARCH-61; design §8; family lead BUILD-47). Hand-written
      `contracts/ws-protocol/ws-protocol.schema.json` (NOT yet enumerated — contract at the ARCH-61
      cut): JSON Schema draft 2020-12; `$defs` keyed by the twenty frame names plus one `anyOf` union
      per channel and direction (`audio.s2c`, `reply.c2s`, … — "any frame legal here");
      `additionalProperties` nowhere, because the schema states the RECEIVER's obligation (unknown
      keys are ignored); opaque values are `{"type": "object"}` and nothing more; the documented
      nested objects (`audio_out`, the observe `filter`, `covered_rooms`) carry their inner types.
      The root says only what is true of every frame (it is a JSON object) — a frame is validated
      against one `$defs` entry. **Owner test, L7:** the file is a valid 2020-12 schema and open
      everywhere; it mirrors the golden definitions key for key (same frames, same `required`, same
      JSON type per key, union membership = the frames of that channel/direction) — so the
      generalization is hand-written twice and mechanically one statement; every valid case
      validates against its frame and its union, every invalid case fails, every unknown-type case
      fails its union, a non-object fails every entry; every transcript line validates; every frame
      the server really sent validates, and so does every client frame it accepted. One divergence
      surfaced and was kept: a `register-reply` whose `audio_out.rate` is not a number is shallowly
      "an object" to slice 1 but invalid to the schema — and the server does reject it; the leg
      therefore checks client frames the server ACCEPTED, not all that were sent. Mutation-checked:
      a retyped key, a union missing a member and a relaxed `required` each turn the leg red.
      **Verified:** suite 1806 passed / 7 skipped (+115), guards green.
      docs: none — the schema is named and scoped in `guides/websocket-api`, which is byte-locked; that section lands with the ARCH-61 cut
      contracts: none — no versioned surface moved yet (the schema is not enumerated; the STAMP stays at `ws-protocol-v1.0.1` until ARCH-61)
- [x] **ARCH-65** [WS][CONTRACTS] `[release]` — **DONE 2026-10-05 — the owner-approved amendment to
      `ws-protocol-doc-canonical` is in `CLAUDE.md`** (filed at the ARCH-61 cut; PROD-28 voice
      delegation (d); council HK-13, round 2 q3 — the owner approved the wording on the dossier and
      re-confirmed during execution, 2026-10-05, on the coordinator's direct question about the
      invariant edits: "I want these updates as a part of this run"). The four lines are appended to
      the `ws-protocol-doc-canonical` bullet VERBATIM, and nothing else in the invariant moved:
      "`contracts/ws-protocol/` additionally holds the protocol's hand-written machine core (golden
      frames, transcripts, schema). It is subordinate to the document: on disagreement the document
      wins and the core is fixed. Never generated from code; a wire change updates document and core
      in the same change." Applied from the patch the ARCH-61 session prepared and declined to apply
      itself (an agent session does not edit an instruction file on relayed authority); the commons
      coordinator session, which holds the owner's approval first-hand, read the patch and applied
      it. docs: none — `CLAUDE.md` is agent-facing law, not a `docs/manifest.json` node. contracts:
      none — no contract bytes move (`CLAUDE.md` is not an enumerated artifact; the machine core
      itself was cut by ARCH-61 at `ws-protocol-v1.1.0`).
- [x] **ARCH-66** [WS][CONTRACTS] `[release]` — **DONE 2026-10-05 — contract cut `ws-protocol-v1.2.0`: the
      guarantees BUG-47, BUG-48 and BUG-50 made true** (one batched MINOR; served `protocol_version`
      stays `"1"`; the same twelve artifacts; every byte-locked edit in this one commit).
      **Classification, checked before cutting:** nothing a conforming client relied on is removed
      or changed — a client that plays by `speak_begin` keeps working, no conforming client sends
      wrongly typed keys, no frame or key was added, removed or renamed. **Guide
      (`docs/guides/websocket-api.md`):** header names the new tag; introduction — a device sends
      mono, and receives the format it registered; `/ws/audio` — a registration in which a key has
      the wrong JSON type is refused with `error`, `sample_rate` is a positive integer;
      `/ws/audio/reply` — the same for `register-reply`, `rate` and `channels` positive integers;
      **the reply-audio guarantee of `v1.0.1` restored verbatim — "The audio is already converted to
      the rate/channel count you registered — play it as it comes."** — with what makes it true
      (both directions, mono spread over the registered channels, an unconvertible reply is not
      sent) and `speak_begin` kept as the statement of what is sent, its `rate` and `channels`
      always equal to the registration; the `v1.1.0` wording "converted down, never up — play by
      `speak_begin`" is withdrawn; **bursts never overlap** (the second of two simultaneous
      replies waits); `/ws/output` — a `client_id` that is not a string is "not usable" and an
      identity is minted; `/ws/observe` — a malformed `filter` is refused, its key types stated;
      machine-readable-core section — the `retired` rule now says what a retired case no longer
      states (the server no longer sends such a frame, a receiver owes it nothing, whatever its
      `verdict` still says; its `note` names the release), client-side `wrong-json-type` cases are
      announced and `output.hello`'s lack of invalid cases explained, and **rule T-9** is added
      (no `speak_begin` while a burst is open; T-1..T-8 unchanged and not renumbered).
      **`frames.golden.json`:** 139 cases (was 120) — 18 client-side `wrong-json-type` invalid
      cases with `expect` (13 on `audio.register`, 3 on `reply.register-reply`, 2 on
      `observe.subscribe`), each replayed against the real handler; `reply.speak_begin/two-channels`
      added (a recorded frame); `reply.speak_begin/lower-rate-than-registered` RETIRED — kept,
      marked `"retired": true`, its note naming this release. Transcripts and schema: bytes
      unchanged. **Owner test:** T-9 in the rule checker (on every transcript and every recorded
      connection); retired cases must be marked and explained; a new guard for "names are never
      renamed or removed" — `backend/tests/data/ws_core_names.major1.txt` lists every name each
      cut released, a removed name fails and so does an added name the cut did not record.
      STAMP `1.2.0` + registry row + contract README; design doc §12. **For consumers:** re-pin;
      skip the retired case; a harness may now assert T-9 and that `speak_begin` equals the
      registration; a client that sent a wrongly typed key is refused where it used to be accepted.
      **Verified:** suite 1966 passed / 7 skipped (+76 over BUG-50); owner test green on the
      locked and the CI-resolved stack; `contract_guard --check` strict 0 failures with the tag;
      `repin --check --fail-on any` exit 0. Flow: cut commit → tag on it → pushed together.
      docs: guides/websocket-api (wrongly typed opening-frame keys refused; reply audio always in the registered format — the v1.0.1 sentence restored; bursts never overlap; retired rule; rule T-9; header tag)
      contracts: ws-protocol-v1.2.0 cut (minor); re-pin owed: satellite, commons
- [x] **ARCH-67** [MQTT][CONFIG][UX] `[release]` — **DONE 2026-10-06 (board PROD-18 round 2, decision
      8; gated on BUILD-58, which re-pinned `catalog-v1.11.0`) — every bridge request is sized from
      the catalog's published timing, and a slow action is acknowledged before it is confirmed,
      behind ONE flag.** **(a) Sizing.** `published_wait_ms(catalog, command)` (`device_commands.py`,
      domain) reads what the bridge promises to wait for THIS command: device form = the
      capability's bound for the action — a scenario value's `max_duration_ms` (`set(value)`; `off`
      = the `scenario` field's `none` entry) else `confirm_timeout_ms`; room form = the MAX over the
      room's capabilities tagged with the group (the bridge picks the member or fans out, so the
      honest ceiling is the slowest). `size_request_timeout(ms) = ms / 1000 × 1.25 + 2 s` (15 000 →
      20.75 s, 25 000 → 33.25 s, 61 500 → 78.875 s). The handler's one delivery chokepoint
      (`_deliver`) stamps it on the command (`timeout_seconds`, `compare=False` — fixtures compare
      WHAT is sent); `BridgeClient` sizes that request's `aiohttp.ClientTimeout` with it and the
      `DeviceCommandDispatcher` bounds its await at sized-or-fallback + 2 s grace (so the HTTP layer
      reports first). Nothing published → the command carries no timeout and the configured
      `[outputs.bridge] timeout_seconds` is the FALLBACK — its Field description re-worded ("FALLBACK
      … for an action the bridge's catalog publishes no timing for"), the 8 config files' comments
      likewise. `wait` stays as today (never `wait: false`). **The intake find is closed by the same
      change:** the dispatcher's `DEFAULT_DELIVERY_TIMEOUT_S = 7.0` (ARCH-8 PR-4, never bumped at
      BUG-41) silently cut every awaited delivery at 7 s in front of the 20 s HTTP timeout — an HVAC
      confirm landing between 7 and 15 s spoke «не уверена» while the bridge was still waiting; the
      dispatcher now takes the SAME fallback number as the client (`DEFAULT_FALLBACK_TIMEOUT_S =
      20.0`, matching `BridgeOutputConfig`), wired from `[outputs.bridge]` by the intent component.
      **(b) The acknowledgement.** Above `SLOW_ACTION_THRESHOLD_MS = 3000` (strict — the 3 000 ms
      inputs are not slow; Apple TV power 5 000, HVAC 15 000, every scenario value are) the handler
      speaks at once, on the request's own channel, a template that CLAIMS NOTHING, phrased per
      action family: ru `ack_on` «Включаю», `ack_off` «Выключаю», `ack_open` «Открываю», `ack_close`
      «Закрываю», `ack_set` «Ставлю» (temperature/climate/brightness/cover/volume), `ack_switch`
      «Переключаю» (mode/fan/vane/input…), `ack_scenario` «Запускаю сценарий», `ack_scenario_off`
      «Выключаю сценарий», `ack_generic` «Секунду»; en "Turning on" / "Turning off" / "Opening" /
      "Closing" / "Setting" / "Switching" / "Starting the scenario" / "Stopping the scenario" /
      "One moment". Path: `NotificationService.send_acknowledgement` (new
      `NotificationType.ACKNOWLEDGEMENT`, TTS+LOG, no preference gate) → the queue → the
      OutputManager addressed by the request's identity (`request_source`, `resolve_physical_id`,
      room) — the exact route a timer ring takes to the satellite's reply channel (its burst lock
      serializes ack and confirmation) or the browser push; dropped (D-3) where no output is
      attached, never misrouted; never raises into the action. Then the honest confirmation or
      failure as before. What was acknowledged rides the final result as
      `metadata.acknowledgement` (one-shot slot in the session's handler context, popped in
      `execute`, recorded only when the service accepted it). The scenario confirmations become
      factual at the echo — ru «Включила «{label}»» / «Выключила сценарий», en "“{label}” is on" /
      "The scenario is off" — because after «Запускаю сценарий» a second progressive «Включаю…» read
      as a second ack, not a confirmation (every other confirmation template unchanged). **The
      flag — owner's words, verbatim: "OK, but make acknowledgements configurable (might become
      annoying over time). I guess, one flag is enough"** → `[outputs.bridge] acknowledge_slow_actions
      = true` (`BridgeOutputConfig.acknowledge_slow_actions`, default on; in `config-master.toml` +
      the 7 profile/example configs; validator green), injected via
      `set_device_command_services(…, acknowledge_slow_actions)`; off = sizing stays, nothing is
      spoken early. **ui-openapi cut `ui-openapi-v1.2.0` (MINOR):** the schema is the openapi source,
      so `config-ui/openapi.json` gained the property + the re-worded description
      (`scripts/dump_openapi.py`), `npm run gen:api-types` regenerated `openapi.gen.ts`; STAMP
      1.1.1 → 1.2.0 (note extended) + registry row + tag on the cut commit; drift test green.
      config-ui's schema-driven `[outputs]` editor renders the boolean as a toggle with no
      component change — `npm run check` + `test` (44) + `build` green. **Tests (+34 over
      BUILD-58):** `test_device_command_sizing.py` (18: the formula at six published values, the
      strict 3 s threshold, device-form lookups present/absent/unknown, the scenario value ceiling
      over the capability, `off` → the `none` entry, room-form max / none, the command identity
      untouched by the timeout, the dispatcher's wait = sized-or-fallback + grace and a real
      slower-than-sized delivery → None); `test_smart_home_handler.py` (+11: HVAC on sized 20.75 +
      «Включаю» + metadata; relay = fallback + silent; the 3 s input sized 5.75 but not slow; Apple
      TV off 8.25 + «Выключаю»; flag off = sized + silent; ack then `device_unreachable` →
      «Переключаю» then «не отвечает»; scenario value 71.375 + «Запускаю сценарий» + «Включила
      «Кино с видеокассеты»»; scenario off 38.25 via `none`; a refused ack is not claimed; the slot
      never leaks into the next turn; no notification service = no crash); `test_bridge_output.py`
      (+3: fallback when unsized, the sized number per request through the stubbed seam AND through
      the real `_request_json` with a stubbed session — 33.25 / 20.0 / 20.0 — plus the model's
      flag default); `test_notification_output_routing.py` (+2: the ack reaches the origin channel
      as speech, is dropped not misrouted). **Eval:** the honest-UX louver cases (ru + en, the AC's
      15 s window = a slow action) gain a `metadata.acknowledgement` assertion — present, and
      claiming nothing (no «готово», no past-tense «-ла»; no "done") — beside the shared calibrated
      rubric, which is untouched (it lives in commons, outside this task's write permission; the
      judged `response_text` is still the final honest reply). **Verified:** suite 2063 passed / 7
      skipped, pyright 0 errors, import contracts 11 kept, config validator + donation validator +
      build analyzer green; contract-guard strict 0 failures with the tag; `repin --check --fail-on
      any` exit 0. Flow: cut commit → tag on it → pushed together.
      docs: guides/smart-home (the acknowledge-then-confirm paragraph; the `[outputs.bridge]` snippet gains the flag and the fallback wording)
      contracts: ui-openapi-v1.2.0 cut (minor — `BridgeOutputConfig.acknowledge_slow_actions`, the re-described `timeout_seconds`; repo-internal, no re-pin); the catalog v1.11 Timing fields FIRST CONSUMED
- [x] **ARCH-68** [MQTT][UX][DESIGN] `[release]` — **DONE 2026-10-06 (design task; board PROD-18 round 2,
      decisions 9–10) — `docs/design/scenario_jobs_voice.md`, the voice side of tier 3, written
      against the bridge's `scenario_jobs.md` §5/§6/§8/§10 (shapes quoted verbatim).** Decisions:
      **(1) port + adapter** — `ScenarioJobEventsPort` (`events(room)` yielding domain `JobEvent`s
      incl. a synthetic STREAM_OPEN on every (re)connect, `get_job`, `get_active_scenario`) beside
      the delivery port, boundary types in a pure `intents/scenario_jobs.py`; `BridgeEventsClient`
      (`outputs/bridge_events.py`) holds ONE persistent `/events/scenarios` subscription for its
      lifetime (subscribe-before-launch by construction), `sock_read=5 s` IS the dead-stream rule,
      backoff 1-2-4-8-16-30 s ±25 % forever, hand-written 30-line SSE reader (no dependency),
      per-room bounded queues, the GETs through `BridgeClient._request_json`; the "only module
      that knows the bridge" docstring becomes the pair. **The `202` rides `DeliveryResult`**
      (`accepted`, `job_id`, `max_duration_ms`) through the one chokepoint — a `start_job()` was
      set aside as a second copy of `deliver()`; `_to_delivery_result` branches on status (202 =
      accepted, never `delivered`; 409 `job_in_progress` → `job_id`; a 200 on `wait: false` = the
      sync outcome as today, so the path is safe against the mock bridge and a pre-1.12 bridge);
      `wait: false` is set in `_scenario` only — device-level commands never carry `wait` (owner
      rider). **(2) the record** — `action_name = scenario_job:{bridge room}` (the name IS the
      one-per-room lock key, re-arm reuses it), persisted by the substrate under
      `<assets_root>/state/` with `job_id / room_id / kind / target / label / max_duration_ms /
      accepted_at`, the requesting device's identity captured by the launch; voice restart →
      re-arm → `GET /scenario/jobs/{id}`; bridge restart (`404`) → `GET /scenario/state?room=`
      → the actual state spoken; resume older than 1 h = silent. Substrate change needed:
      `metadata.on_missed = "rearm"` makes the reconciler ask the handler regardless of the
      deadline (today: future deadlines only, timer-specific missed texts). **(3) speech** — the
      turn's reply IS the acceptance: «Запускаю сценарий, около минуты» / «Выключаю сценарий,
      около полминуты» (ceiling buckets from `max_duration_ms`: ≤5 s none · ≤20 «секунд N» ·
      ≤45 «около полминуты» · ≤90 «около минуты» · else «пару минут»); flag off = silent
      acceptance, only the end; terminal «Включила «{label}»» / `confirm_partial` «…, но не
      ответили: процессор» (catalog names); `404`-after-restart → «Сценарий «{label}» включён,
      мост перезапускался» / «Мост перезапускался, сценарий «{label}» не включился»; `job_lost`
      «Мост не отвечает — не знаю, включился ли сценарий «{label}»»; `job_stalled` «…всё ещё
      переключается — проверьте»; mid-job second command and «stop» → «Ещё переключаю на
      «{label}», остановить можно будет секунд через {N}» (N = remaining ceiling, answered
      locally when voice owns the record, else the `409` is mapped the same way and the job is
      ADOPTED via one GET); after the terminal «stop» = a new job. The terminal travels through
      a new `send_action_outcome` (TTS+LOG, `redeliver`, no preference gate — the 30 s
      completion threshold would swallow a warm switch) addressed by the request's identity, and
      the generic done-callback completion is suppressed for an announced record. **(4) state
      machine** accepted → following → done / failed / unknown / stalled / lost with W = ×1.25
      + 2 s and H = W + 30 s, every transition's text tabled. **(5) config: no new keys**, no
      ui-openapi cut. **(6) tests** 1–9 (fake events port, the 409 both ways, the restart
      paths incl. `on_missed`) + the five voice lines of the bridge's §10 checklist. **(7)**
      BUILD-59 (re-pin `catalog-v1.12.0`, both copies) + ARCH-69 (implementation) filed
      `[release]`, sequenced cut → re-pin → implementation → sitting; **open point** recorded:
      the bridge's §11 orders the sitting BEFORE the cut ("measured > published blocks the
      cut") — ARCH-69 reconciles at intake. **(8)** ARCH-67's sized synchronous path keeps
      working through the cut and the re-pin (`wait` absent is unchanged at v1.12) and stays the
      path for every device-level action. Intake side-find (the 30 s threshold gate) recorded
      against ARCH-59. No code.
      docs: none — design document only (`docs/design/`, not a manifest root); the user-facing paragraph lands with ARCH-69 (guides/smart-home)
      contracts: none — designed against the bridge's `catalog-v1.12.0` surface, not yet cut; first consumption is BUILD-59 (pin) + ARCH-69 (use)
- [x] **QUAL-19** [ESP32] (P2, last pre-release) — **DONE 2026-06-09** (interactive review session + upstream study).
      **★ ARCH-22 (2026-06-14):** the **device-side** of the micro stack is now designed in `docs/design/esp32_satellite.md`
      (D-9 ported microWakeWord on ESP-IDF with the TFLite-Micro micro-features frontend + µVAD; D-10 the same `.tflite`
      manifest artifact device+server) — the realization of this review's "one pipeline, device + server" goal.
      Deliverable `docs/review/esp32_wakeword_review.md` — keep/fix/cut per piece {ESP32 firmware, on-device wake+VAD,
      backend microWakeWord, openWakeWord, Porcupine, server VAD, armv7, training refs}. **Key findings:** (1) the
      design's "both server wake providers hallucinated" premise was **wrong** — `openwakeword` works; only
      `microwakeword` is a stub. (2) **Upstream microWakeWord now ships server-side Python libs**
      (`pymicro-wakeword`/`pymicro-vad`/`pymicro-features`, Apache-2.0, maintained) bundling the micro frontend +
      tflite inference + a precompiled tflite C lib → the backend provider is **fixable as a thin wrapper, not a DSP
      hand-port**, and `from_config` loads **custom** `.tflite`+manifest (the per-unit RU plan). (3) microWakeWord +
      microVAD are **one "micro" stack** running identically on the ESP32 (TFLite-Micro) and server-side from the
      **same artifact** — the "one pipeline, device+server" goal is now real. **Decisions:** ESP32 firmware = keep as
      quarantined reference; backend µWW = FIX via pymicro-wakeword; openWakeWord = keep, demote to quick-start;
      Porcupine = CUT; add server-side **microVAD** as a 3rd `VADEngine`; armv7 = no server wake (on-device); training
      refs = cut in-repo. **Config:** uniform wake-word selection stays **per-provider** (consistent with ASR/LLM) via
      a shared `WakeWordSpec={name,model,threshold,language}` sub-schema. **De-tangle (Invariant #6):** QUAL-20 now owns
      the whole wake+microVAD rebuild; **ARCH-10 PR-5 is subsumed by QUAL-20**. Design folded into
      `onnx_inference_layer.md` §11 + `ws_esp32_transport.md`. _Original spec:_ Full review & questioning of the ESP32 +
      wakeword story (firmware functional-vs-aspirational; backend microWakeWord placeholder; openWakeWord vs
      microWakeWord; armv7; docs; TODO11). Intersects ASSET-2.
- [x] **QUAL-20** `[release]` [ESP32] (P-TBD) — **★ ARCH-22 (2026-06-14):** server-side micro stack stays as built; the
      **device-side** µWW/µVAD design + the shared-artifact contract are in `docs/design/esp32_satellite.md` D-9/D-10.
      **DONE 2026-06-09 — wake-word + microVAD rebuild (5 commits
      `bb5382e`·`a980448`·`e00f918`·`be52e0e`·this).** All 8 agreed items landed, each commit green (pyright 0, 9/9
      contracts, config/dep/build gates, 0 net suite regression; config-ui check+build+vitest green). **(1)** backend
      `microwakeword` is now a thin adapter over **`pymicro-wakeword`** (np.random stub + hand-rolled tflite plumbing
      deleted; streams 10 ms chunks; built-in + `from_config` custom models); **(2)** `wake-tflite` extra (drops
      `tflite-runtime`); **(3)** openWakeWord polished (ONNX default, `wake-onnx` extra, per-spec custom model);
      **(4)** uniform **`WakeWordSpec={name,model,threshold,language}`** per-provider (NOT a component-level lift —
      consistent with ASR/LLM; component-level kept as an optional override) + a generic config-ui `ArrayOfObjectsEditor`
      + backend array-items schema extraction (Invariant #4); **(5)** server-side **`microvad`** `VADEngine` over
      **`pymicro-vad`** beside energy/silero; **(6)** Porcupine orphan cut, `embedded-armv7.toml` server-wake disabled
      (on-device), no residual training refs; **(7)** custom models are deployment-supplied (built-ins for dev),
      TODO11 closed; **(8)** real runtime tests (microWakeWord detect/alias/silence, WakeWordSpec parse + schema-items,
      microVAD seam). User docs updated: `voice-trigger.md` (rewrite), `vad.md` (microvad), `howto-new-model.md` (VAD
      seam). **Build-time verify (open):** the `pymicro-*` wheels import + detect on x86 here; confirm
      `libtensorflowlite_c` coverage on aarch64 at the BUILD-3 image stage. WB7 hw re-val stays with ARCH-25. _Original
      spec below._ **Act on QUAL-19 — wake-word + microVAD rebuild (redefined 2026-06-09;
      subsumes ARCH-10 PR-5).** 64-bit-only (armv7 wakes on-device). Per `esp32_wakeword_review.md` "Agreed plan":
      **(1)** backend `microwakeword` = thin wrapper over **`pymicro-wakeword`** (delete the np.random `_extract_features`
      + manual feature-buffer/tflite plumbing/consecutive-detection, `microwakeword.py:237-330`; stream 10 ms/160-sample
      16 kHz chunks); one instance per wake-word entry via `from_config`/explicit ctor; **(2)** `wake-tflite` extra
      (`pymicro-wakeword`, carries its tflite C lib → drop `tflite-runtime`), 64-bit markers; **(3)** openWakeWord
      polish (ONNX default, `wake-onnx` extra, custom `model_path`); **(4)** uniform per-provider **`WakeWordSpec=
      {name,model,threshold,language}`** sub-schema across both providers + config-ui `wake_words` array editor
      (Invariant #4); **(5)** server-side **`microvad`** `VADEngine` over **`pymicro-vad`**, toml-selectable beside
      energy/silero (extends the ARCH-10 PR-4 seam); **(6)** cut Porcupine orphan schema; fix `embedded-armv7.toml`
      (no server wake provider; on-device); cut in-repo training refs + reconcile ESP32 docs; **(7)** assets =
      deployment-supplied custom models (optional `from_builtin` English dev quick-start), close TODO11; **(8)** tests
      (builtin-model detection + `from_config` custom smoke + microVAD seam). **Verify at build:** `libtensorflowlite_c`
      wheel platform coverage (x86_64/aarch64). WB7 hw re-val stays with ARCH-25.
- [x] **QUAL-21** (P1) — **Prod bug (`ComponentConfig` field drift) — RESOLVED BY REMOVAL. DONE 2026-06-03.** The
      `irene-settings` Gradio runner (`settings_runner.py`, 462 LOC) constructed `ComponentConfig(audio_output=…,
      microphone=…, web_api=…)` — fields that no longer exist (mic/web moved to `config.inputs.*` /
      `config.system.web_api_enabled`; `audio_output`→`audio`) → **crash on launch**; same stale kwargs in 4 demo
      examples. **User decision:** the settings runner is obsolete — **removed** rather than fixed (config is now
      edited via config-ui's TOML editor or the file directly). **Deleted** `settings_runner.py` + both pyproject
      registrations (`[project.scripts] irene-settings`, the `irene.runners` `settings` entry-point) +
      `runners/__init__.py` exports; cleaned README, `architecture.md` (usage + the "Settings Режим" diagram subgraph),
      and `tools/migrate_runners.py`. **Retired all 4 stale demos** (`component_demo`, `dependency_demo`, `config_demo`,
      `utilities_demo` — built around the removed optional-components model; user-confirmed) + fixed `examples/__init__.py`.
      **Verified:** `irene.runners`/`irene.examples` import clean; the 3 remaining runner scripts (cli/webapi/vosk) resolve;
      no stale `ComponentConfig` kwargs remain in `irene/` (the residual `audio_output`/`microphone` hits are device-cap
      dict keys, device enumeration, and the intentional v13→v14 migration reader); 0 net suite regressions.
- [x] **QUAL-22** [PEX] (P2) — **DONE 2026-06-03 (removed; resolved within QUAL-11 Stage E).** Chose *remove* over
      *finish*: the stub was dead since inception and real capability/room-aware disambiguation needs registered devices
      (ARCH-6), not a no-op. Deleted `_disambiguate_with_device_context` (caller uses the intent directly) + the 2 xfail
      tests + `test_device_not_found_suggestions`. _Original finding:_ **Stubbed feature found via TEST-2, confirmed by QUAL-10**: context-aware NLU
      enhancement is a no-op. `ContextAwareNLUProcessor._disambiguate_with_device_context` (`nlu_component.py`
      157-187 — the method QUAL-22 first called `_enhance_intent`) computes `enhanced_entities`
      (`output_capabilities`, `context_suggestion`, `preferred_output_device`) but then **returns the original
      intent unchanged** (comment: "for now, return original"); location inference (`location_resolved`) is
      unimplemented. Either finish the enhancement (apply enhanced_entities / wire capability + location context)
      or remove the dead logic. Relates to QUAL-10 [PEX]. xfail tests: `test_client_capability_context`,
      `test_room_context_inference`.
- [x] **QUAL-23** (P1, Gate 0) — **Startup name-resolution assertion.** **DONE 2026-06-01** →
      `irene/core/startup_validation.py` (+ wired in `core/components.py` after coordination; unit tests in
      `irene/tests/test_startup_validation.py`, 4✓). Checks every configured `default_provider`/`fallback_providers`/
      `provider_cascade_order` and every enabled `[<component>.providers.<name>]` resolves to a **registered
      entry-point** (names enumerated, not loaded — optional-dep import failures don't false-positive). Non-fatal by
      default (logs a clear ERROR per unresolved name so a shipped config still boots); `IRENE_STARTUP_STRICT=1`
      raises (CI / TEST-0). Verified on config-master: flags exactly the phantom **`console` LLM** (fallback +
      enabled block — the QUAL-15 bug), zero false positives (TTS/audio `console` are real → pass; NLU cascade
      clean). Folds into ARCH-5 (CI). Note: text-processor **stage-routing** completeness (dead `command_input`
      stage) is provider-name-orthogonal → stays under QUAL-13.
- [x] **QUAL-24** (P2) — **DONE 2026-06-03 (approach refined + user-approved, Invariant #8).** Service-locator → DI in
      8 handlers. **Approach (user chose Option A — domain-owned ports, over the entry's looser "inject components"
      sketch, to truly satisfy Invariant #3):** added domain-owned capability **ports** `irene/intents/ports.py`
      (`LLMPort`/`TTSPort`/`AudioPort`/`ASRPort` + shared `ComponentControlPort` + `ComponentControlRegistryPort`,
      **ABCs** — see hardening below); the 8 handlers now depend only on these domain abstractions and the application
      (`IntentComponent.post_initialize_handler_dependencies`) injects the real components inward. `system` uses the
      already-injected `context_manager`;
      `provider_control` gets the registry port. **Removed** the `from ...core.engine import get_core` service-locator
      from every handler and the **`ignore_imports` escape hatch** from the ARCH-1 contract — ARCH-1 now holds with
      **no hatch** (9/9 contracts kept), proving the transitive `intents→core.engine→{components,inputs,workflows}`
      pull is severed. Opportunistic Invariant #9: removed the `TYPE_CHECKING`/`pydantic` guards in the 6 touched
      handlers that had them. Found a latent bug en route (the old `await component_manager.get_component(...)` awaited a
      **sync** method — the fallback was already broken; injection is what worked). **Invariant #4:** no backend
      contract changed (internal DI only) → config-ui untouched. Verified: suite 85=85 FAILED (0 net regression).
      **Hardening (user-directed, same session):** (1) **ports are ABCs, and the application components now INHERIT
      them** (`LLMComponent(…, LLMPort)`, `TTSComponent(…, TTSPort)`, `AudioComponent(…, AudioPort)`,
      `ASRComponent(…, ASRPort)`, `ComponentManager(ComponentControlRegistryPort)`) — `components→intents.ports` is
      application→domain (inward, legal; 9/9 contracts kept). Nominal inheritance means an unimplemented port method now
      **fails at instantiation** (startup), not as a latent `AttributeError`. (2) That enforcement surfaced **4 methods with
      no implementer** (consumer-defined ports faithfully captured pre-existing **dead handler calls**): implemented them —
      `AudioComponent.pause_audio`/`resume_audio` delegate to the active provider's `pause_playback`/`resume_playback`
      (real); `TTSComponent.stop_synthesis`/`cancel_synthesis` are honest best-effort (TTS providers can't interrupt → graceful
      no-op, no crash). NB: injection also **repaired latent breakage** — only `conversation` was injected before, so the other
      5 capability handlers were getting `None` (compounded by the await-sync bug); they're now wired for the first time (no
      test covers these paths — **filed as TEST-8**). (3) **Removed** the orphaned global-core service-locator
      (`get_core`/`set_core`/`_global_core`) from `engine.py` — zero callers; no test referenced it (the 3 flagged files
      matched on `llm_component`, not `get_core`). All verified: components instantiate (ABC), 9/9 contracts, suite 85=85.
- [x] **QUAL-25** [DFLOW] (P1) — **End-to-end dataflow & context-models review.** **DONE 2026-06-02** →
      `docs/review/dataflow_review.md` (~9 P0, ~20 P1, long P2 tail; 5 parallel tracers → synthesis →
      adversarial-verify on the headline NEW P0s). **Headline NEW finding: a field rename `Intent.text`→`raw_text`
      was never propagated** — `intent.text` is read at 14 unguarded sites across 7 handlers + `Intent(text=…)` at
      `orchestrator.py:217`, so TTS-speak/translation/text-enhance/provider-switch/ASR-audio-provider/contextual
      commands all `AttributeError`, masked by the orchestrator as a generic error (verified vs source). Other NEW
      P0s: `session_id="default"` collapses all sessions (cross-request/room/user leak); `MemoryManager` cleanup loop
      dead (calls non-existent methods); `InputManager._input_queue`/WebSocket `AUDIO_DATA:` input path dead
      (captured mic/web audio dropped — overlaps ARCH-6); required-params never enforced. **CONFIRMS** the FAF P0s
      (timer crash, key-mismatch completion death, `get_or_create_context`) and TXTPROC (TTS gets raw text). Found a
      **4th cross-cutting theme — "data-contract drift"** (model contracts silently disagree across boundaries:
      `Intent.text`/`raw_text`, `WakeWordResult.word`/`wake_word`, action key `action_name`/`domain`, session scope)
      — these are refactor residue the relaxed pyright (Phase-0 §E) was configured not to see. §2 resolves the DOC-8
      request-vs-session question (→ DOC-8 write-up). §4+§6 are the **QUAL-26** agenda. **Spawns:** QUAL-26
      (reconcile) + new P0s for the Gate 2 backlog (numbered in QUAL-26) + DOC-8.
- [x] **QUAL-26** [DFLOW] (P1) — **Review-of-reviews: reconcile inconsistencies, decide intended-vs-actual.**
      **DONE 2026-06-02** → `docs/review/dataflow_reconciliation.md` (live Q&A, 10 issues decided, committed
      per-decision). Consolidated all review docs + the QUAL-25 dataflow findings and decided **intended-vs-today** for
      each. Headline decisions: **Model 2 — split identity from session** (physical-identity store holds `active_actions`
      + devices, long-lived; conversation session holds history, short-lived idle-window); **dedicated zombie-resistant
      action store** (`action_name`-keyed); **`raw_text` = original utterance** (P0-1 fix); **declarative device/room
      via a donation format split** (language-neutral contract + per-language phrasing; `entity_type` + `room_context`
      tri-state); **fail-loud → conversational clarification** (configurable LLM/deterministic); **WebSocket = primary
      ESP32 transport** (reframes ARCH-6). Surfaced a **4th cross-cutting theme: data-contract integrity.** Finalized
      Gate 2 framing (hybrid: principles block + discrete tasks) and emitted **QUAL-27…31** (below). See the doc for
      the full per-issue rationale.
- [x] **QUAL-27** `[release]` [DFLOW] (P0) — **Data-contract fixes (theme ④).** **DONE 2026-06-02.**
      `Intent.text`→`raw_text` at all 14 handler sites + `orchestrator.py:217` (P0-1, the biggest single defect;
      `raw_text` = **original utterance** via a boundary override in `nlu_component.process(..., original_text=)`, NLU
      stops overwriting it — Q1); `WakeWordResult.word` consumer rename (P1-b, 4 sites); **deleted `Intent.session_id`**
      (field + 6 provider/component ctor kwargs + the orchestrator metrics read → `context.session_id` + the redundant
      `_create_fallback_intent` param); enforced the `IntentResult` error contract via `__post_init__`
      (`success=False` ⟹ non-empty `error`, P1-a — one backstop over all ~35 sites). Smoke green throughout
      (5 passed / 1 xfailed). **Scope change (Invariant #8, user-approved):** P1-t (`_create_error_result` signature
      unification) was found to be **6 handlers, not 2**, and is a shared-bases (theme ②) base-vs-handlers split →
      **moved to QUAL-11** (handler-base/typed-accessor consolidation). Refs: `dataflow_reconciliation.md` Q1/Q7.
- [x] **QUAL-28** `[release]` [DFLOW] (P0) — **Context & session refactor (Q2/Q3; foundational). DONE (all 4 stages).** Split
      `UnifiedConversationContext` → a **long-lived physical-identity store** (room/device/client; holds
      `active_actions` + device capabilities; `ClientRegistry` = device source-of-truth) + a **short-lived conversation
      session** (history + `ConversationState`). **Dedicated zombie-resistant action store**, `action_name`-keyed
      (`domain` = router index), 4-layer reaping (completion callback · read-time liveness filter · periodic sweep ·
      TTL+cap). **Session lifecycle:** idle-window (T=10m / voice ~5m, configurable) + sliding history window (N=15,
      wire `max_history_turns`); per-modality boundaries (voice=wake-word burst, WS=connection, REST=conversation-id).
      Forbid the literal `"default"` (P0-6); split `get`/`get_or_create`; **kill `extract_room_from_session`** (P1-o);
      unify eviction on `last_activity`. Delete `MemoryManager` (P0-7). Refs: Q2/Q3/Q4.
      **Staging (2026-06-02):** ① delete `MemoryManager` (**DONE** — module + monitoring wiring) → ② session-id hygiene
      (**DONE** — forbid literal `"default"` in `RequestContext` + re-read the derived id in the 3 `workflow_manager`
      entries; added real `get_or_create_context` fixing the 5 phantom `AttributeError` callers) → ③ new context model +
      action store (+ a **focused action-lifecycle test**, mini-TEST-3, no regression net else) (**DONE** — incl. the
      Stage-3.3 field split: completed-action history moved into the store, survives eviction) → ③b **migrate consumers
      + retire `ContextLayer`** (**DONE** — conversation handler's context assembly rewritten onto direct accessors;
      `ContextLayer` enum + all `resolve_*context`/`resolve_layered_context`/`get_contextual_summary` machinery deleted)
      → ④ history windowing (**DONE** — collapsed the parallel `history`/`conversation_history` lists into the single
      `conversation_history`, written by **one** method `record_turn` at **one** site (the workflow); deleted the legacy
      `history` field + `add_user_turn`/`add_assistant_turn`/`add_to_history`/`_trim_history`/`get_recent_context` and
      the orchestrator's parallel turn-write (P1-q triple-write killed); `max_history_turns` now actually drives the
      window — both `record_turn` and the LLM-restore read it instead of a hardcoded 10 (was the "config-that-lies"
      P2). Also removed 4 dead `ContextManager` turn methods (`add_user_turn`/`add_assistant_turn`/
      `get_conversation_history`/`process_intent_with_context`/`update_context_with_result`).). **Moved ②→③ (Invariant #8):** eviction-unify (needs the
      `last_activity` timestamp-touch audit), the non-creating-`get` split (needs caller migration), and
      `kill extract_room_from_session` (needs room-as-explicit-field) ride the Stage-3 restructure. **Scope correction (Invariant #8):**
      `ContextLayer`/progressive-context is **NOT dead** (Q4 mis-scoped it) — it's live in `conversation.py` (builds the
      LLM context summary). So **migrate-then-retire** in ③b (rewrite the conversation handler's context *assembly* onto
      the new model; its LLM prompt/provider logic stays QUAL-15/16). Deferred to Q9: the now-dead
      `memory_management_enabled` config key + the context `memory_management` block (config-ui coord, Invariant #4).
      **Stage-3 design (decided 2026-06-02 with user):** (a) **action store = a runtime-only (non-persisted) sub-store
      on `ClientRegistry`** keyed by `physical_id` — NOT a field on the persisted registration record (it holds live
      `asyncio` task refs for the reaper and must never serialize / survive a restart). `ClientRegistry` keeps its
      persistent registration table (devices/room) + this new runtime state table. (b) **Single
      `resolve_physical_id(request)` seam** — today returns the session-derived id; **ARCH-6 changes only this one
      function** to return the registered `client_id`/room (so the room/device story is a clean *activation*, not a
      re-refactor). (c) **Decoupled from ARCH-6** (incremental): the store + reaper + eviction-survival land now keyed
      by the best-available stable id; room/device keying upgrades when ARCH-6 populates identity. See the **Q1 timing
      decision** recorded in `RELEASE_JOURNAL.md` + ARCH-6.
- [x] **BUG-45** `[release]` [CI][DEPS] — **DONE 2026-10-05 (filed + completed same session; found
      by BUILD-47's first push — the first `backend-health` run since 2026-07-20).** CI's type gate was
      red on a tree that had not changed: `py-dev-gates` installs the project with pip (unlocked), and
      `anthropic>=0.25.0` now resolves to the SDK's 1.x line (1.0.0 released 2026-08-20; 1.11.0 in the
      failing run 37280384142), whose `messages.create` no longer accepts `temperature` — pyright
      reported "No overloads for create match" at `providers/llm/anthropic.py:94` and `:134`, the job
      stopped there, and pytest never ran. Reproduced locally before fixing: pyright on the provider
      is 0 errors against the locked 0.111.0 and exactly those 2 errors against a scratch 1.11.0 env.
      Under 1.x the same two calls would also fail at RUNTIME (unexpected keyword), so this is not a
      typing nit — but every shipped image installs from `uv.lock` (0.111.0) and is unaffected.
      **Fix (a deliberate version decision, not a migration):** `llm-anthropic` capped to
      `anthropic>=0.25.0,<1`; `uv.lock` refreshed (specifier-only diff, no version moved). The gate
      environment is back in the range the lock and the suite actually exercise; the migration itself
      is filed as QUAL-87. Not from the PROD-28 delegation — fixed because every BUILD-47..50 push
      triggers `backend-health` by design, and a job that dies before pytest would have made the
      layer-2 closure decorative. **Verified:** `uv lock --check` clean, dependency validator 60/60
      both platforms, analyzer profiles valid, suite 1469 passed / 7 skipped.
      docs: none — a dependency bound; no manifest node documents the SDK version
      contracts: none — no versioned surface moved (dependency specifier + lockfile only)
- [x] **BUG-46** [WS] `[release]` — **DONE 2026-10-05 — WS error paths: answer `error`, then close — on every
      channel** (filed and fixed the same day; ARCH-60 design findings C-1 + C-2, split out of ARCH-61;
      family lead BUILD-47). The guide promises an `error` frame on a protocol violation, and the machine
      core is about to state that an `error` frame is terminal. Two places in `webapi_router.py` did
      neither. **C-1:** `/ws/audio/reply` read and parsed its first frame outside any handler, so a
      first frame that was not JSON, not an object, binary, or carried a non-numeric `audio_out` value
      dropped the connection with no frame at all — the read, the parse and the `audio_out` contract
      now sit in one guarded block that answers `{"type": "error", "error": "malformed register-reply
      frame: …"}` and closes (a client that leaves before registering is a plain disconnect, not an
      error). **C-2:** the catch-all paths of `/ws/audio` and `/ws/observe` sent `error` and returned;
      a real ASGI server then closed the socket, the handler never did — under the in-process client
      the connection stayed open after the error. Both now close explicitly after the frame. Wire
      effect on a real server: the reply channel gains the promised `error` frame; everything else is
      the same close the hosting stack already performed, now issued by the handler. **Tests** (in the
      suites that own the channels): `/ws/audio/reply` — not-JSON, not-an-object, unusable `audio_out`
      and binary first frames each get `error` then a server close, nothing registered; `/ws/audio` —
      a malformed first frame and a mid-stream pipeline failure each get `error` then close;
      `/ws/observe` — a malformed first frame gets `error` then close. No guide edit: the guide is
      byte-locked and already promises the `error` answer; the "terminal" sentence lands with
      ARCH-61. **Verified:** suite 1487 passed / 7 skipped (+8), guards green.
      docs: none — the code is brought to what `guides/websocket-api` already promises (an `error` answer on a protocol violation); the "error is terminal" sentence is byte-locked and lands with the ARCH-61 cut
      contracts: none — no versioned surface moved (the guide and the STAMP stay at `ws-protocol-v1.0.1`; server behavior now matches the document)
- [x] **BUG-47** [WS] `[release]` — **DONE 2026-10-05 — deliveries to one reply connection are serialized: a
      burst is never opened inside another** (owner directive "go and fix these"; design finding C-4
      of `docs/design/ws_machine_core.md`). `CallbackReplyChannel.send_audio` awaited between
      `speak_begin`, every PCM chunk and `speak_end` with nothing serializing callers, and deliveries
      to a device come from independent tasks (the `/ws/audio` handler routing a reply, the
      notification loop announcing a timer). **Reproduced before fixing**, on a real socket: two
      results delivered to one registered `/ws/audio/reply` connection at the same time arrived as
      `speak_begin 1`, `speak_begin 2`, PCM of both mixed — the second bracket opened inside the
      first. **Fix:** the channel owns its send path, so the channel holds the lock — one
      `asyncio.Lock` per `CallbackReplyChannel` around the whole bracket; `seq` is taken inside it, so
      bursts are numbered in the order they go out. Nothing above the adapter changes (the
      OutputManager and the notification service stay unaware; `hexagonal-architecture` — the lock
      lives in `outputs/remote_audio.py`, import contracts 11 kept). A burst whose send fails
      releases the lock (the socket is gone anyway). **Tests** (`test_ws_reply`): three concurrent
      `send_audio` calls on a channel whose sends each yield produce three whole brackets in order;
      and the endpoint test — two concurrent `OutputManager.deliver` calls to one registered reply
      connection arrive as two whole bursts (`seq` 1 then 2, each with all its PCM, nothing
      interleaved). Both failed before the fix. The machine-core owner test is green against the
      `v1.1.0` fixtures (rules T-3/T-4 were worded to hold either way). **Verified:** suite 1813
      passed / 7 skipped (+2), guards green.
      docs: none — the guide is byte-locked; the "bursts never overlap" statement lands with the ARCH-66 cut (the guide's existing "bracketed binary burst" already reads that way)
      contracts: none — no versioned surface moved (code + tests; the guarantee is stated in `ws-protocol-v1.2.0`, ARCH-66)
- [x] **BUG-48** [WS] `[release]` — **DONE 2026-10-05 — opening frames are type-checked: a documented key
      with the wrong JSON type is refused, not registered** (owner directive "go and fix these";
      design finding C-3 of `docs/design/ws_machine_core.md`). `{"type": "register", "client_id": 5,
      …}` was registered and the ack echoed the number; a string `sample_rate` or `audio_out.rate`
      was coerced; `/ws/output` echoed a numeric `client_id` and used it as a routing key; a numeric
      `filter.room_name` subscribed silently to a filter that could never match. **Fix — the server
      catches up with the document:** `core/ws_protocol.py` gains `OPENING_FRAMES` (for each
      channel's opening frame the required keys and the JSON type of every key, exactly as the
      guide's frame reference states them, plus the documented inner keys of `audio_out` and
      `filter` and the element types of the two arrays, as the schema types them) and
      `opening_frame_violation()` — shape only, unknown keys ignored, `16000.0` is an integer,
      `true` is not a number. The four handshakes use it: **`/ws/audio`** and **`/ws/audio/reply`**
      answer `error` ("invalid register frame: "client_id" must be a string") and close;
      non-positive `sample_rate` / `audio_out.rate` / `audio_out.channels` are refused the same
      way; **`/ws/observe`** decides authorization first and explains nothing to an unauthorized
      caller (a token that is not a string is simply `unauthorized`), then refuses a malformed
      `filter` by name; **`/ws/output`** stays the channel that never rejects — a `client_id`
      that is not a non-empty string is not usable and an identity is minted, as the guide
      already says. `primary_room` stays accepted as the undocumented alias it was. The existing
      error texts recorded in the `v1.1.0` fixtures are unchanged. **Tests:** 30 wrong-type
      refusals across the three rejecting channels (each: `error`, server close, nothing
      registered), six unusable `client_id` values minted on `/ws/output`, integer-valued floats
      and unknown keys still accepted; **owner test** — the server's table equals the golden
      definitions key for key, and its validator gives every opening-frame case of the core its
      verdict; the schema leg no longer treats `/ws/output`'s ack as vouching for the frame.
      Green against the `v1.1.0` fixtures on the locked and the CI-resolved stack. **For
      clients:** nothing changes for one that sends what the guide documents; one that sent a
      number where a string is documented is now refused at registration. **Verified:** suite
      1875 passed / 7 skipped (+62), import contracts 11 kept, guards green.
      docs: none — the guide's frame reference already states every type enforced here and already promises `error` on a violation; the sentence spelling out "wrongly typed key → refused" is byte-locked and lands with the ARCH-66 cut
      contracts: none — no versioned surface moved (code + tests; the wrong-type cases enter `frames.golden.json` in `ws-protocol-v1.2.0`, ARCH-66)
- [x] **BUG-49** [TEST][WS][CI] `[release]` — **DONE 2026-10-05 (filed + completed same session; found by the
      first CI run of the machine-core owner test — run 37288706817, the ARCH-62..64 push).** CI was
      red on exactly one leg: `transcript.reconnect.jsonl` was "not a real recording". The transcript
      closes both sockets `by: network`, and the frame tap decided "network" from the close code the
      server-side stack reports for a peer that vanished without a closing handshake — which it
      assumed to be 1006. That is what the LOCKED stack reports (uvicorn 0.49.0 / websockets 16.0, the
      legacy implementation). CI installs unlocked and resolved uvicorn 0.54.0 / websockets 17.2,
      whose newer implementation reports the same event as **1005** ("no status received"), so the
      recording said `by: client` and no longer equalled the fixture. Reproduced locally by laying the
      CI versions over the venv before touching anything: the two aborted connections came back as
      1005. **Fix (test tooling only):** the tap treats both codes as "no closing handshake" —
      neither ever travels on the wire (RFC 6455 §7.4.1), both are a stack's local way of saying the
      peer is gone, and a client that closes properly sends a real code (1000). No fixture, guide or
      server code changed; the wire contract says only "the connection dropped without a closing
      handshake" and never names a code. **Verified:** owner test 305/305 on BOTH stacks (locked,
      and the CI-resolved versions overlaid); suite 1806 passed / 7 skipped.
      docs: none — test tooling; no manifest node describes the frame tap
      contracts: none — no versioned surface moved (the tap is not an artifact; fixtures untouched)
- [x] **BUG-50** [WS][AUDIO] `[release]` — **DONE 2026-10-05 — reply audio is always converted to exactly what
      the device registered, up as well as down** (owner decision, verbatim: "restore the reply-audio
      guarantee server-side as a part of current goal"). The guide promised through `ws-protocol-v1.0.1`
      that audio on `/ws/audio/reply` is "already converted to the rate/channel count you registered";
      the reply path used the LOCAL-sink rule (`AudioNegotiator.to_sink`: conform down only — "any
      device plays lower"), so a 16 kHz voice reached a 22.05 kHz device at 16 kHz. **Fix, where the
      channel's conversion already lives:** `AudioNegotiator.to_device(audio, contract)` converts to
      EXACTLY the device's declared rate and channel count — resample up or down, downmix or spread a
      mono voice over the registered channels (stdlib, like the existing downmix) — and raises if the
      result is not that format; `RemoteAudioOutput` calls it instead of `to_sink` and checks the
      result itself, so a burst in any other format is never sent (the delivery is dropped and
      logged: wrong-speed audio is worse than none). `to_sink` and the local playback rule are
      untouched. **Two defects in the resampling primitive surfaced while proving it, both fixed here
      because the guarantee rests on them:** (1) `AudioTranscoder`'s last fallback returned its INPUT
      bytes when numpy is missing while the caller relabelled them with the target rate — on the
      numpy-free armv7 controller image every resample silently produced audio at the wrong speed;
      it also interpolated interleaved stereo as one channel. It now always resamples: numpy for
      mono when present, otherwise a stdlib linear interpolation that is channel-aware (≈50 ms for
      five seconds of speech on x86). (2) the resampling cache keyed on the first 1 KB of the buffer
      only — two utterances that START alike (leading silence) and are resampled between the same
      rates collided, and the second was handed the first one's audio; reproduced at HEAD before
      fixing (two different buffers, identical output). The key now covers the whole buffer and
      its length. **Tests:** real socket — a 16 kHz voice arrives at the registered 22.05 kHz
      (`speak_begin` equals the registration; the PCM lasts what the utterance lasted, ±2 samples;
      really resampled, not relabelled), a 22.05 kHz voice arrives at a registered 16 kHz, a mono
      voice arrives as the registered two channels (same signal on both), an unconvertible
      delivery is dropped and nothing is pushed; unit — `to_device` both directions for rate and
      channels, identity when nothing needs converting, raising on a failed resample; the stdlib
      resampler keeps duration, ramp shape and channel separation and runs with numpy blocked;
      the cache returns each utterance its own audio. The `v1.1.0` test that asserted "never
      upsamples" is replaced. Owner test green against the `v1.1.0` fixtures (a device that
      registers 16 kHz still receives the 16 kHz `speak_begin` those fixtures record).
      **Verified:** suite 1890 passed / 7 skipped (+15), pyright 0 errors, import contracts 11 kept.
      docs: guides/audio, arch/dataflow (replies to a satellite are converted to exactly the registered format — the exception to "never upsampled"; the WebSocket guide is byte-locked — its restored sentence lands with the ARCH-66 cut)
      contracts: none — no versioned surface moved yet (code + tests; the restored guarantee and the retired case land in `ws-protocol-v1.2.0`, ARCH-66)
- [x] **BUILD-14** `[deferred]` [CI][FEEDBACK] — **DONE 2026-10-06 (executed under board PROD-19, owner
      directive: "Disable the Issues tabs on all four repos and execute PROD-19") — the pre-ARCH-30
      public-repo issue triage is retired; intake is ONE door, locveil-reports.** Reconciled at start
      against the three postures the entry offered: the owner chose (c) — the public Issues tab is
      DISABLED on this repo (and on bridge, satellite, commons; the private reports repo keeps its
      Issues, it IS the intake), so neither forwarding (a) nor redirect templates (b) have a subject.
      Removed: `.github/workflows/issue-triage.yml` (keyword → `area:*`/`platform:*` labels + ack
      comment, no AI — strictly weaker than the reports repo's Claude triage with lens process files,
      the /inbox loop and ARCH-34 bundles) and `.github/ISSUE_TEMPLATE/` (bug/feature forms +
      `config.yml`). Nothing else referenced them: `ci.yml` has no filter on them; the `/report`
      collector (`outputs/github_report.py`) files into locveil-reports, untouched. Nothing worth
      moving to the reports repo — its triage already labels by lens, not by keyword. The stale
      sentence in `docs/design/build_release_process.md` ("issue-triage.yml stays separate") is
      re-truthed. Zero public issues were ever filed here. Bridge twin: OPS-28. docs: none — no
      manifest node describes public intake (the user-facing path is the report button, documented
      already); the design-doc sentence is a design doc. contracts: none — no surface moved.
- [x] **BUILD-47** `[release]` [CI][CONTRACTS] — **DONE 2026-10-05 (HK-13 wave 0; PROD-28 voice
      delegation (a); LEAD ID of the voice PROD-28 family — BUILD-47..52 + ARCH-60/61, ARCH-48
      narrowed).** The two CI holes HK-13 found live in this repo are closed and the rotted manifest
      pointer is fixed. **(1) contract-guard un-gated:** the `contract-guard` job lost its `changes`
      dependency and its path filter — it runs strict on every push/PR/dispatch (the `contracts`
      filter output is gone). Before, an edit to `docs/guides/websocket-api.md` — an owned artifact
      living outside `contracts/` — never started the job whose drift rule exists for exactly that
      edit. **(2) layer 2 runs when contracts move:** `backend-health` (the only job that runs
      pytest, i.e. every version/drift/conformance test) now also triggers on `contracts/**`,
      `docs/guides/websocket-api.md`, `docs/guides/tracing.md`, `docs/manifest.json`,
      `config-ui/openapi.json` and its generator `scripts/dump_openapi.py`; the vendored core-py copy
      was already covered by `backend/**`. A commit touching only a pin, a STAMP or a locked guide can
      no longer land with zero conformance tests run. **(3) manifest pointer:** the
      `guides/websocket-api` node's `canonical.guard` → `backend/tests/test_ws_protocol_version.py`
      (was `irene/tests/…` since BUILD-36), and `test_docs_manifest.py` gained
      `test_canonical_pointers_resolve` so a canonical `stamp`/`guard` pointer that names no file
      fails the suite instead of rotting silently. Registry Guards paragraph re-truthed in the same
      change ("path-gated" was now false). NOT here (need repin v2): the CI `repin --check` step and
      the dispatch gate — BUILD-51; the two rotted `conformance` pointers inside PIN.json files wait
      for the sweep's re-stamp (pins are never hand-edited). **Verified:** suite 1465 passed / 7
      skipped (+1), both guards green, workflow YAML parses with the expected job/filter shape.
      docs: none — CI wiring + manifest metadata + a test; no manifest node describes CI gating
      contracts: none — no versioned surface moved (enforcement wiring only; `docs/manifest.json` is not an enumerated artifact)
- [x] **BUILD-48** `[release]` [CONTRACTS][WS] — **DONE 2026-10-05 (owner cut `ws-protocol-v1.0.1`,
      bytes-only patch; PROD-28 voice delegation (b); lead BUILD-47).** The WS wire-protocol contract
      is now declared and byte-locked, and the two edits that slipped past `ws-protocol-v1` are inside
      a version. **STAMP:** `version` `1.0.1`, tag `ws-protocol-v1.0.1`, `artifacts:
      ["docs/guides/websocket-api.md"]` — the guide enumerated WHOLE (owner ruling q3: doc-canonical
      contracts lock the whole file; any later edit cuts at least a patch); the legacy singular
      `artifact` field dropped (one declaration, not two); the note records the three-level rule and
      what the patch absorbs (939a205's sample port 6000→8080, 346a5f3's `code_constant` path).
      **Guide:** the header line names the new tag; the sentence "the version only moves on a breaking
      wire change" now states the three-level rule — the SERVED number is the major and moves only on
      a breaking change, minor = additive wire change, patch = a document edit with the wire
      untouched. **Served value unchanged:** `WS_PROTOCOL_VERSION` stays `"1"` (runtime-served
      versions carry the major only), module docstring re-truthed. **Test:**
      `test_ws_protocol_version.py` rewritten from the equal-triple to the major-only comparison —
      STAMP is the three-part authority, the doc header names the STAMP tag exactly and shows the
      major, the served constant equals the major, the enumerated artifact and the `code_constant`
      pointer resolve to files. Registry row + `contracts/ws-protocol/README.md` re-truthed (levels
      table + the cut flow). No wire change. **Verified:** suite 1467 passed / 7 skipped; guard green
      (strict once the tag exists); flow = artifact + STAMP one commit → tag → pushed together.
      docs: guides/websocket-api (header tag + the three-level version sentence)
      contracts: ws-protocol bumped v1 → v1.0.1 (patch: guide enumerated whole, two post-tag drifts absorbed; served major unchanged); re-pin owed: satellite
- [x] **BUILD-49** `[release]` [CONTRACTS][TRACE] — **DONE 2026-10-05 (owner cut
      `trace-format-v1.0.1`, bytes-only patch; PROD-28 voice delegation (b); lead BUILD-47).** The
      utterance-trace format contract now declares and byte-locks its artifact — the DOC-14 choice not
      to enumerate ("the guide's prose evolves") is remediated per owner ruling HK-13 q3.
      **STAMP:** `version` `1.0.1`, tag `trace-format-v1.0.1`, `artifacts:
      ["docs/guides/tracing.md"]` — the WHOLE guide, not the reference section (no marked-region
      mechanism exists; any edit anywhere in the file now cuts at least a patch); singular `artifact`
      dropped; the note records the three-level rule. **Guide:** the version line names the new tag,
      and the closing paragraph of the reference section states the rule for readers — the number in a
      saved file is the major and moves only on a reader-breaking change; a new key is a minor, a
      guide edit is a patch. **Written value unchanged:** `TRACE_FORMAT_VERSION` stays `1`; its
      comment re-truthed. **Test:** `test_trace_format_version.py` rewritten from the equal-triple to
      the major-only comparison (same shape as BUILD-48: STAMP three-part authority, doc line names
      the STAMP tag, written constant == major, artifact + `code_constant` pointers resolve, envelope
      smoke). Registry row + `contracts/trace-format/README.md` re-truthed. Intake check held: guide
      and STAMP were byte-identical to `trace-format-v1`, so the patch absorbs no hidden drift. No
      format change. **Verified:** suite 1469 passed / 7 skipped; guard green; artifact + STAMP one
      commit → tag → pushed together.
      docs: guides/tracing (version-line tag + the three-level paragraph in the reference section)
      contracts: trace-format bumped v1 → v1.0.1 (patch: guide enumerated whole; written major unchanged); no re-pin owed — no cross-repo consumer pins it yet
- [x] **BUILD-50** `[release]` [CONTRACTS] — **DONE 2026-10-05 (declaration-only patch cuts
      `ui-openapi-v1.1.1` + `wake-pack-v1.0.1`; PROD-28 voice delegation (b); lead BUILD-47).** The
      two remaining owned contracts now declare `artifacts` — both as the legal EMPTY list with a
      resolving `guard` pointer (contracts.md §2), each for its own reason. **`ui-openapi`:**
      `artifacts: []`, `guard: backend/tests/test_openapi_drift.py` (replaces the ad-hoc `drift_guard`
      field; `artifact`/`generator`/`consumer` stay as informational pointers). The generated
      `config-ui/openapi.json` is deliberately not byte-enumerated — it moves with the code on every
      endpoint change and the regenerate-and-compare test is the stronger check; enumerating it would
      force a version cut on every REST change. **`wake-pack`:** `artifacts: []`, `guard:
      backend/tests/test_ws_protocol_version.py::test_wake_pack_stamp_mirrors_released_catalog` — the
      binary-pack sidecar shape, where the STAMP is the whole pinned set. **The `pack` block is
      byte-for-byte the `wake-pack-v1` content** (asserted while writing the file): no hash, URL or
      `hf_revision` moved — the drift re-stamp and the immutable-URL switch stay in the gated ASSET-6.
      Both STAMPs: three-part `version`, new tag, `date`, notes stating the three-level meaning for
      that contract. **Tests:** `test_openapi_drift.py` gained a STAMP leg (empty list, `guard`
      resolves to that very file, `artifact`/`generator` pointers resolve, three-part tag);
      the wake-pack tests gained the empty-list + guard-resolves assertion and the three-part form.
      Registry rows re-truthed — incl. the `ui-openapi-v1` string that had trailed the STAMP's
      `ui-openapi-v1.1` since BUILD-36 — and both contract READMEs gained Declaration + three-level
      Versioning paragraphs. Intake redefinition recorded: the board allowed wake-pack to ride ASSET-6;
      cut now so a declaration does not wait on new wake words. Left alone by instruction:
      `contracts/docs-manifest/` (retires in BUILD-52). **Verified:** suite 1471 passed / 7 skipped;
      guard green; STAMPs one commit → both tags on it → pushed together.
      docs: none — STAMP metadata, contract READMEs and tests; no manifest node describes the stamps
      contracts: ui-openapi bumped v1.1 → v1.1.1 (patch: declaration only; repo-internal, no re-pin); wake-pack bumped v1 → v1.0.1 (patch: declaration only, pack hashes/URLs untouched); re-pin owed: satellite (wake-pack)
- [x] **BUILD-51** `[release]` [PROCESS][CONTRACTS][CI] — **DONE 2026-10-05 (the HK-13 sweep, one
      pass, one commit here + one in commons for the catalog crossover copy; PROD-28 voice
      delegation (c); lead BUILD-47).** **Tools re-vendored via repin itself:** `repin` v1 →
      `repin-v2.0.0` (bootstrapped from the commons copy), `contract-guard` v3.1 →
      `contract-guard-v4.0.0`, `scope-guard` v7.2 → `scope-v7.3.1` (block-only cut — script bytes
      identical); each `[[tool]]` entry now records `path` + `pinned_tag` + `sha256`, so a locally
      edited vendored file fails the check. **`.repin.toml` migrated:** every `files` list dropped
      (five families — the pin set is what the owner's STAMP enumerates at the tag); the commons
      catalog destination's `conformance` is a real path in the dest repo
      (`eval/tests/test_contracts_pin.py`, was prose). **Every pin re-stamped with v2:** `catalog`
      v1.9 → `catalog-v1.10.0` at BOTH destinations in one run (the set gains the owner's normative
      guide `catalog-contract.md`; golden + openapi bytes unchanged), `report-protocol` v1 →
      `report-protocol-v1.0.1`, `esp32-site` v1 → `esp32-site-v1.1.0` (template comment path only),
      `core-py` re-stamped at `core-py-v1.1`, `docs-manifest-schema` re-stamped at v1.0.0 (BUILD-52
      had pinned it with v1). The re-stamp repaired the two rotted `irene/tests/…` `conformance`
      pointers (esp32-site, report-protocol) and makes every pin strict under guard v4. **Block
      re-pin:** `contract-triad` copied verbatim from commons at `scope-v7.3.1`, hash updated in
      `.scope-guard.toml` (identical to the hash the three sibling repos pin). **CI:** the un-gated
      `contract-guard` job gained `repin --check --fail-on major --touched <base>` (push: the
      `before` SHA; PR: the base branch; `fetch-depth: 0` + explicit tag fetch) and, on
      `workflow_dispatch`, the release gate `--fail-on minor`; `publish-backend` now `needs:` that
      job, so a pin trailing by a minor or major blocks an image publish while patch and tool gaps
      only warn. `make -C eval repin-check` moved `--fail-on any` → `minor` (owner ruling q6).
      **Prose:** registry rows + Guards paragraph (current tags only — guard v4 REGISTRY-VERSION);
      pin READMEs (catalog file table gains the guide; the manual `git show` re-pin recipe in the
      report-protocol README deleted; version strings replaced by "see PIN.json"); `eval/README.md`
      ladder wording. **CLAUDE.md (owner decision relayed verbatim by the coordinator 2026-10-05:
      "I want these updates as a part of this run"):** `trace-format-doc-canonical` re-worded to
      the three-level rule; the contract-guard tag mention moved to v4.0.0; nothing else — the
      `ws-protocol-doc-canonical` amendment stays with ARCH-61. No conformance test needed
      adapting: none lists pin files, and guard v4 owns pin completeness. **Verified:** contract-guard
      4.0.0 strict — 0 failures, 0 warnings; `repin --check --fail-on any` exit 0 (6 pin rows + 3
      tools current); suite 1473 passed / 7 skipped; in commons, contract-guard green and
      `eval/tests` 65 passed against the re-pinned crossover copy, with no commons test changed.
      docs: eval/readme (the staleness-ladder paragraph + the `repin-check` gloss)
      contracts: catalog pin bumped v1.9 → v1.10.0 (both dests, one run — bridge's `re-pin owed` discharged); report-protocol pin bumped v1 → v1.0.1 (commons' owed discharged); esp32-site pin bumped v1 → v1.1.0 (satellite's owed discharged); core-py + docs-manifest-schema re-stamped at unchanged tags (strict v2 PIN.json); consumed tools bumped: contract-guard v3.1 → v4.0.0, repin v1 → v2.0.0, scope-guard v7.2 → v7.3.1
- [x] **BUILD-52** `[release]` [DOC][CONTRACTS] — **DONE 2026-10-05 (docs-manifest remodel; HK-13
      decision 6, PROD-28 voice delegation (b) tail; lead BUILD-47; executed first in the sweep
      session because guard v4 refuses the STAMP it retires).** `docs/manifest.json` is instance
      data; the contract is the commons-owned schema. **Pinned:** new consumed family
      `docs-manifest-schema` @ `docs-manifest-schema-v1.0.0` at `contracts/pins/docs-manifest-schema/`
      (`manifest.schema.json` + owner STAMP verbatim + PIN.json; stamped with the still-vendored
      repin v1, so the `.repin.toml` family carries a `files` list for this one commit — BUILD-51
      drops it and re-stamps with v2). **Retired:** `contracts/docs-manifest/` (STAMP + README) and
      its registry row; the `docs-manifest-v1` git tag stays as frozen history. **Test hermetic:**
      `test_docs_manifest.py` validates the manifest against the PINNED schema — the
      `../locveil-commons/…` read and its `skipif` are gone (that leg had never run in CI, where no
      sibling exists); plus a pin-coherence leg (PIN ↔ owner STAMP). **Surfaces re-truthed:** the
      trigger globs named pre-BUILD-36 paths (`irene/**`, `configs/**`, root `pyproject.toml`) —
      now `backend/src/locveil_voice/**`, `config/**`, `backend/pyproject.toml`; new
      `test_surface_globs_match_real_files` fails on any glob that matches nothing, so the map
      cannot rot silently again. Registry gained the pin row; pin README written (why the
      manifest is not a contract). **Verified:** suite 1473 passed / 7 skipped; guard v3.1 green,
      and a dry run of guard v4 against the tree now reports 0 failures (the STAMP-DRIFT it raised
      on the retired stamp was the only one).
      docs: none — manifest metadata (surface globs) + pin + test; no node's content changed
      contracts: docs-manifest-schema first consumed (pin @ v1.0.0); internal docs-manifest stamp retired
- [x] **BUILD-53** `[release]` [CONTRACTS][UI] — **DONE 2026-10-05 (workbench family pinned;
      coordinator-assigned at the PROD-28 sweep-GO; lead BUILD-47).** config-ui compiled against
      the commons plugin contract through a live `file:` link with no pin and no conformance test;
      commons' `workbench-v1.3.0` made the consumed surface enumerable. **Pinned:**
      `contracts/pins/workbench/` @ `workbench-v1.3.0` — `contract.ts`,
      `manifest-fragment.schema.json`, `runtime-config.schema.json` + owner STAMP + PIN.json
      (repin v2, set derived from the owner STAMP); `.repin.toml` family, registry row, pin README.
      **Fragment source extracted so it can be tested hermetically:** the manifest fragment's
      fields (`id`, `entry`, `styles`, `peers`) moved from inline literals in
      `config-ui/vite.config.ts` to `config-ui/manifest.fragment.json`; the vite plugin assembles
      the same object from it + `package.json` `version` — the emitted `dist/manifest.json` is
      byte-identical to before (verified by a build). **Conformance test**
      `backend/tests/test_workbench_pin_conformance.py` (6): the fragment assembled the way the
      build assembles it validates against the PINNED schema; the schema demonstrably rejects a
      fragment without `peers`; a peer major is declared for every shell singleton; pin ↔ owner
      STAMP coherence incl. completeness; and a tripwire asserting the vite config takes every
      fragment field from the source file (so the build cannot emit something the test does not
      see). No build, no Node, no sibling — it runs in `backend-health`, whose trigger gained the
      three files it reads. `config-ui-stays-functional`: `npm run check` + `build` + `test` (44)
      green. **NOT here, recorded in the pin README:** the TypeScript build still resolves the
      contract TYPES through the `file:` link, not the pinned `contract.ts` — the pin makes a
      commons move visible and diffable, it does not yet isolate the type-check from the live
      sibling (no task filed; owner's call — _→ closed by BUILD-57_). **Verified:** suite 1479 passed / 7 skipped;
      contract-guard 4.0.0 strict 0 failures / 0 warnings; `repin --check --fail-on any` exit 0.
      docs: none — no manifest node describes the fragment's source; the non-root `config-ui/README.md` (not a node) gained the pointer
      contracts: workbench first consumed (pin @ v1.3.0)
- [x] **BUILD-54** `[release]` [DEPS][SECURITY] — **DONE 2026-10-05 (filed + completed same session;
      owner request: clear the open Dependabot alerts).** Five patch-level security bumps in
      `backend/uv.lock`, by targeted `uv lock --upgrade-package` only — 5 packages moved, 361
      resolved before and after, `pyproject.toml` untouched (`anthropic<1` from BUG-45 intact):
      **aiohttp** 3.14.1 → 3.14.3, **anyio** 4.14.0 → 4.14.2 (the critical one; the newest anyio
      the locked `typing-extensions` 4.15.0 admits — 4.15.x needs 4.16, and nothing else was allowed
      to move), **cryptography** 49.0.0 → 50.0.2, **pyasn1** 0.6.3 → 0.6.4, **urllib3** 2.7.0 →
      2.8.0. **Intake finding — one lockfile, not two:** the 15 alerts on a root `uv.lock` name a
      manifest that left `main` at BUILD-36 (2026-07-13, moved to `backend/uv.lock`); GitHub's
      dependency graph still lists it (`blob/main/uv.lock` is a 404) and raised fresh alerts
      against it today. Nothing in the repo can be edited to fix a file that is not there; whether
      those alerts follow `backend/uv.lock` is observed after the push. **Second finding, not
      acted on:** the three Dockerfiles copy `uv.lock` into the builder but install with
      `uv pip install`, which does not read it — images resolve fresh inside the `pyproject.toml`
      ranges at build time, and CI's gate environment is pip-resolved too. The lock governs
      `uv sync` (development) only, so this bump closes the alerts and patches dev environments;
      a deployed image carries whatever resolved on its build day and is patched by a rebuild,
      not by this commit. (BUG-45's entry says shipped images install from the lock — they do
      not.) **Verified on a scratch environment synced from the new lock**
      (`uv sync --locked --extra all --extra dev`, Python 3.11): the `backend-health` job replayed
      step for step — import-linter, check-no-type-checking, pyright 0 errors, `uv lock --check`,
      analyzer profiles, config validation, donations 0 errors / 0 warnings, dependency validator
      60/60 both platforms, armv7 torch-free gate — and the suite **1811 passed / 7 skipped**, identical to the
      pre-bump baseline; the WS machine-core owner test 310 passed with nothing skipped (real
      frames through the bumped anyio stack); `config-ui/openapi.json` regenerated byte-identical;
      contract-guard strict 0 failures / 0 warnings; `repin --check --fail-on any` exit 0.
      docs: none — lockfile only; no manifest node documents a dependency version
      contracts: none — no versioned surface moved (lockfile only; every enumerated artifact byte-identical)
- [x] **BUILD-55** `[release]` [DEPS][SECURITY] — **DONE 2026-10-05 (filed + completed same session,
      with BUILD-54).** **torch** 2.12.1 → 2.14.1 (`+cpu` on Linux/Windows, plain on macOS — the
      CPU-index pin is unchanged) and **setuptools** 81.0.0 → 84.0.0, in `backend/uv.lock` only;
      `pyproject.toml` untouched (`torch>=1.13.0` already admits it). One move, as filed: torch
      2.12.1 declared `setuptools<82`, 2.14.1 does not, so the setuptools alert could not close
      without the torch one. **The installability question, answered from the lock itself:** the
      2.14.1 wheel set covers every platform tag the 2.12.1 set did — manylinux_2_28 x86_64 and
      aarch64, macOS arm64, win_amd64, s390x, cp311–cp314 — nothing lost, six tags gained
      (cp315, win_arm64); the locked **torchaudio** stays 2.11.0 (still the newest on the index,
      and it carries no torch pin). There is no armv7 torch wheel before or after — the armv7
      profile is torch-free by gate, and that gate still passes. 2.14.1 rather than the minimum
      2.13.0 because it is what `--upgrade-package` resolves, and what the unlocked CI gate and a
      fresh standalone image build already install (today's green CI runs were on torch 2.14.1).
      **setuptools 82 removed `pkg_resources`:** nothing in `backend/` imports it, and the three
      locked packages that declare setuptools (spaCy, thinc, pymorphy3) import and run without it.
      **Verified on a scratch environment synced from the new lock:** a real Silero v4 synthesis
      through the provider's own load path (`torch.package.PackageImporter(...).load_pickle` →
      `apply_tts`, 35 400 samples at 24 kHz), torchaudio resample + mel transform, Whisper's
      log-mel front end; the `backend-health` job replayed step for step — pyright 0 errors,
      `uv lock --check`, analyzer profiles, config validation, donations 0 errors / 0 warnings,
      dependency validator 60/60 both platforms, armv7 torch-free gate — suite **1811 passed /
      7 skipped** (the baseline); `config-ui/openapi.json` unchanged; contract-guard strict
      0 failures / 0 warnings; `repin --check --fail-on any` exit 0. Not built here: the x86_64
      standalone image (the only torch consumer) — its build is unlocked and resolves the same
      wheel from the same index.
      docs: none — lockfile only; no manifest node documents the torch or setuptools version
      contracts: none — no versioned surface moved (lockfile only; every enumerated artifact byte-identical)
- [x] **BUILD-56** `[release]` [DEPS][SECURITY][UI] — **DONE 2026-10-05 (filed + completed same session,
      with BUILD-54).** `config-ui/package-lock.json` only — `package.json` untouched, no
      `overrides`, no `--force`; every patched version was reachable inside a declared range.
      **Moved:** **react-router-dom** / **react-router** 6.30.4 → 6.30.6 (+ `@remix-run/router`
      1.23.3 → 1.23.4, pinned by it); **postcss** 8.5.15 → 8.5.29 (+ its own floors: `nanoid`
      3.3.12 → 3.3.20, `source-map-js` 1.2.1 → 1.2.2); **vitest** and the seven `@vitest/*`
      packages incl. **@vitest/mocker** 4.1.8 → 4.1.11; **js-yaml** 4.2.0 and 4.3.0 → one copy at
      4.3.2 — the hoisted copy was pinned EXACTLY by `@redocly/openapi-core` (under
      `openapi-typescript`), so that moved 1.34.16 → 1.34.20, the release that pins 4.3.2;
      **brace-expansion** 1.1.15/1.1.16 → 1.1.21, 2.1.1 → 2.1.7, 5.0.7 → 5.0.12; **browserslist**
      4.25.2 → 4.29.3 (+ the data packages it floors: `caniuse-lite`, `electron-to-chromium`,
      `node-releases`, `update-browserslist-db`, new `baseline-browser-mapping`);
      **postcss-selector-parser** 6.1.2 → 6.1.4. Also rewritten by npm, not by choice: the
      `locveil-workbench` link stub's version 0.1.0 → 0.1.1 (the sibling's current
      `package.json`). **Tooling note:** `npm update vitest` crashes npm 10.9.2 (arborist,
      `Cannot read properties of null (reading 'edgesOut')` in the peer-set loader); that one
      step ran under npm 11.21.0, which also refreshed two unrelated transitives (`chai`,
      `tinyrainbow`) — both put back to their previous locked entries. The result is still
      lockfile v3 and `npm ci` under CI's npm 10.9.2 installs it cleanly.
      **Deliberately left open (not dismissed):** the two **react-router** alerts patched only in
      7.18.0 — a v7 move is a Workbench contract major. Neither path is reachable from this
      plugin, because config-ui does not import react-router at all: `src/plugin.tsx` declares
      six static route segments to the shell and says so in its header ("no router"); there is no
      router construction, no hydration data and no server rendering anywhere under `src/`
      (GHSA-337j-9hxr-rhxg, `deserializeErrors` on SSR hydration), and no `<Link>`, `<NavLink>`,
      `useNavigate` or `navigate(` call that a target could be passed to (GHSA-wrjc-x8rr-h8h6).
      `react-router-dom` is an external singleton in `vite.config.ts` — the built `dist/index.js`
      is byte-identical before and after this bump — so the copy that actually runs is the
      Workbench shell's, in commons; that is where both the exposure and the fix live.
      **Not a Dependabot alert, seen in `npm audit`:** `braces` ≤ 3.0.3 (GHSA-vfj7-8cjw-p6xm) has
      no patched release; it arrives through tailwindcss 3 (`chokidar`, `micromatch`,
      `fast-glob`) and leaves only with a tailwind major. Not filed.
      **Verified** after `npm ci` from the new lock: `npm run check` (types + strict ESLint +
      orphans), `npm run build`, `npm run test` 44 passed on vitest 4.1.11;
      `dist/manifest.json`, `dist/index.js` and `dist/style.css` byte-identical to the pre-bump
      build; `npm run gen:api-types` regenerates the three generated type files with no diff
      (the bumped redocly core sits under that generator); `config-ui/openapi.json` untouched;
      the sibling packages' `node_modules` untouched; backend suite 1811 passed / 7 skipped;
      contract-guard strict 0 failures / 0 warnings; `repin --check --fail-on any` exit 0.
      docs: none — lockfile only; the non-root `config-ui/README.md` names no dependency version
      contracts: none — no versioned surface moved (the manifest fragment's `react-router-dom` peer stays `^6`; emitted fragment byte-identical)
- [x] **BUILD-57** `[release]` [CONTRACTS][UI] — **DONE 2026-10-05 (owner directive: fix now; closes
      the limit BUILD-53 recorded).** config-ui type-checks against the PINNED workbench contract,
      and the live link to the commons shell package is gone. **Resolution:**
      `config-ui/tsconfig.json` `paths` maps `locveil-workbench/contract` →
      `../contracts/pins/workbench/contract.ts`. The pinned file imports React types and has no
      `node_modules` in reach (TS2307 without help — under the link that import resolved inside
      the commons package), so a companion entry maps `react` to config-ui's own `@types/react`.
      The import in `src/plugin.tsx` is unchanged. **Dependency removed:** the `file:`
      devDependency `locveil-workbench` is out of `package.json` and `package-lock.json` (35
      lines, nothing else moved; npm left an `extraneous` stub for the sibling path, removed by
      hand — `npm install --package-lock-only` leaves the result untouched and `npm ci` installs
      it). Nothing else used it: one import, `import type`, erased at build; no vite alias, no
      script, no test. `locveil-ui-kit` stays linked — a package-style surface with no pinned
      bytes, the shell's runtime singleton. **Guard, two sides.**
      `test_workbench_pin_conformance.py` gains six tests (12, still hermetic): the mapping
      exists, has ONE target and it is the pinned file; no wildcard or sibling route, no
      `extends`, `include` is `src` only; `react` maps into config-ui; `type-check` / `build` run
      plain `tsc`; no `locveil-workbench` dependency under any name in `package.json`, the lock
      or the vite config; every source mention is `import type … from
      'locveil-workbench/contract'`. Sixteen mutations tried, sixteen failures. CI
      (`frontend-health`): new failing step "Contract types compile from the pinned file" —
      `tsc --listFilesOnly` must contain the pinned `contract.ts`, nothing from the commons
      checkout except `packages/ui-kit`, and no installed `locveil-workbench`; run locally on the
      real program (passes) and on three crafted file lists (each fails on its own rule). The
      `npm ci` in the commons workbench package is dropped (it existed only so the linked
      `contract.ts` could find React types). Triggers: `package-lock.json`, `tsconfig*.json`
      and `src/**` join the backend filter so the hermetic guard runs when they move;
      `contracts/pins/workbench/**` joins the ui filter so a re-pin re-runs the type-check.
      **Proof (throwaway clone, never the pin):** before — `tsc --listFilesOnly` named
      `locveil-commons/packages/workbench/src/contract.ts`; after — the pinned file, and 55
      ui-kit files as before. Mapping repointed at a scratch copy with `PageProps.backends`
      renamed → `src/plugin.tsx(35,39)` TS2339; restored → clean. The clone's pin file edited
      (`WorkbenchPlugin.pages` renamed) → `src/plugin.tsx(82,3)` TS2353 AND contract-guard
      HASH-MISMATCH; restored → clean. **Bundle:** all 179 files of `dist/` (`index.js`,
      `style.css`, `manifest.json`, maps, chunks) byte-identical to the build before the change,
      in the clone from a clean `npm ci` and in the working tree. **Texts that stated the
      limit:** pin README (rewritten: what compiles, the two guards, what a re-pin can now
      break), `.repin.toml` family comment, the CI job header, the registry row,
      `config-ui/README.md`, a pointer on the BUILD-53 entry. `config-ui-stays-functional`:
      `npm ci`, `npm run check`, `npm run test` (44), `npm run build` green. **Verified:** suite
      1992 passed / 7 skipped (1986 + 6), pyright 0 errors, import contracts 11 kept;
      contract-guard strict 0 failures / 0 warnings; `repin --check --fail-on any` exit 0.
      docs: none — no manifest node describes how the plugin's contract types resolve; the non-root `config-ui/README.md` gained the paragraph
      contracts: none — no surface moved (the workbench pin stays @ v1.3.0, byte-identical; how it is consumed changed)
- [x] **BUILD-58** `[release]` [CONTRACTS][MQTT] — **DONE 2026-10-06 (board PROD-18 execution order:
      "voice re-pin"; the bridge's VWB-46 `re-pin owed: voice, commons` discharged) — catalog re-pinned
      `catalog-v1.10.0` → `catalog-v1.11.0`, both copies, the round-1 cut consumed.** One
      `python3 scripts/repin.py catalog` moved the local push-time pin AND
      `../locveil-commons/contracts/pins/catalog/` at the one tag (owner commit `e3efa8b`, bridge
      commit `8b43558`, content hash `5622ba7a1a78102a` → `4deb84ae88da6caa`). The contract delta
      is additive (MINOR): `confirm_timeout_ms` on `CatalogCapability` (27 capabilities carry it —
      HVAC 15 000, TV power 8 000, Apple TV power 5 000, streamer power 25 000, inputs 3 000),
      `max_duration_ms` on `CatalogValueLabel` (the living-room scenario `set(value)` table and the
      `scenario` field incl. `none` = 29 000; 29 500 … 61 500), `labels` on the nine by-value IR
      `set(value)` entries (`mf_amplifier.input` × 7, `upscaler.input` × 2), the HVAC `vane` /
      `widevane` labels «заслонка» / «заслонка по горизонтали», and the guide's new "Localization"
      + "Timing" sections. **Voice reads both timing fields** — `CatalogCapability.confirm_timeout_ms`,
      `ValueLabel.max_duration_ms`, and `CatalogFieldSpec.values` (an enum field's value table was
      never parsed; the `scenario` field's `none` entry is where the deactivation ceiling lives) —
      so nothing published is dropped silently; consumption (sizing + the acknowledgement) is
      ARCH-67. `test_catalog_contract_conformance.py` gains three tests: the schema declares the
      two optional fields, the parser round-trips every capability's `confirm_timeout_ms` and
      every value's `max_duration_ms` (params AND fields), and every `set(value)` entry carries
      `ru`+`en` labels (the Localization rule as voice relies on it). **Commons:** the co-owned
      crossover fixtures bind to the golden's content hash → `catalog_version` restamped to
      `4deb84ae88da6caa` (bindings untouched); commons commit `e2beeeb` touches ONLY
      `contracts/pins/catalog/**` + `crossover_fixtures.json`, pushed; commons eval suite
      `uv run --extra record --extra dev pytest tests/` **90 passed**. Voice `eval/device.tests.yaml`
      regenerated (header hash only), and the REAL cross-suite — `make device-auto TIER=1`, mock
      bridge serving the NEW golden + the SUT on the derived config — **53/53 green**: the louver
      label rename and the nine new labels break no producer path. Registry row + pin README name
      the two new guide sections. **Verified:** suite 2029 passed / 7 skipped (+3), pyright 0
      errors, import contracts 11 kept; contract-guard strict 0 failures / 0 warnings; `repin
      --check --fail-on any` exit 0 (every pin and tool current). Side find, recorded only: the
      commons `contract-graph.py --check` reports its generated `process/contract-graph.md` view
      stale after the pin move — a commons view outside this task's one-folder write permission.
      docs: none — the pin and the parser gained fields no manifest node describes; the user-facing consequences (request sizing, the acknowledgement, the louver words) land with ARCH-67 and DOC-15
      contracts: catalog re-pinned v1.10.0 → v1.11.0 (both copies); crossover-fixtures catalog_version restamped
- [x] **DOC-15** `[release]` [DOCS][NLU] — **DONE 2026-10-06 (board PROD-18 round 1, decision 3: "voice's
      how-to cites both") — the donation-side half of the language-data convention lands in
      `docs/guides/howto-new-intent.md`.** New section "Words for the smart home — what a donation
      owns", between Case B and the long-running-actions section, reader-first: the catalog carries
      the nouns under its "Localization" rule (the pinned `contracts/pins/catalog/catalog-contract.md`
      is linked), the donation carries the verbs; verbs AND the capability's spoken noun are
      donation data (`phrases` / `lemmas` — field labels are UI display text the resolver never
      matches speech against); value labels are the match vocabulary — a donation may QUOTE them
      in phrases and examples, but the catalog `values` table is the only vocabulary at match
      time, so a quoted phrase that stops matching after a bridge rename is a stale donation, not
      a catalog defect; group tokens (`light`, `cover`, …) are unlocalized identifiers whose
      spoken words live in `group_noun.choice_surfaces` (the real snippet from the smart-home
      donation); never ask the bridge for a label — add a lemma, and the reverse: a catalog entry
      missing a ru/en name or value label is a bridge-side defect to report. Cites commons
      `process/language-data.md` by its GitHub URL (a sibling-checkout relative path would not
      resolve for a reader on the web). **CLAUDE.md citation fix** (`config-ui-stays-functional`):
      the donation-schema path `assets/donations/v1.0.json` (a file that does not exist) →
      `assets/donation_language_v1.1.json` + `assets/donation_contract_v1.1.json` (the real ones;
      config-ui's `gen:api-types` reads exactly these) — a factual correction outside the pinned
      blocks. **Verified:** suite 2063 passed / 7 skipped (unchanged — prose only), pyright 0
      errors, docs-manifest coherence test green; scope-guard OK.
      docs: guides/howto-new-intent
      contracts: none — prose only; the pinned catalog guide is linked, not moved
