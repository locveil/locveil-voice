# Irene — Completed Release Tasks (frozen archive)

Frozen, append-only record of **completed** (`[x]`) release tasks, split out of
[`RELEASE_PLAN.md`](./RELEASE_PLAN.md) to keep the active ledger readable (Invariant #6 still
owns scope+status; this is its done-history). Organized by workstream, IDs preserved so open
tasks and the journal resolve their references here. **Do not re-edit** — closed work only;
rationale/chronology lives in [`RELEASE_JOURNAL.md`](./RELEASE_JOURNAL.md).

---

### Architecture & Refactor (ARCH)
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
### Code Quality & Review (QUAL)
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
- [x] **QUAL-29** [DFLOW] (P1) — **Donation format split (Q6; precedes declarative device-resolution). DONE (backend) —
      config-ui editor rebuild carved to UI-5 (user-approved Invariant #4 deferral 2026-06-03).** Split
      donations into a **language-neutral contract** (method list + invariant `ParameterSpec` core: name/type/required/
      choices/min-max + **`entity_type`** {device/location/room/person/generic} + per-method **`room_context`**
      {required/none/conditional}) + **per-language files** (phrases/lemmas/token/slot patterns + language-specific
      `extraction_patterns`/`aliases`/`default_value`/`description`). Schema `v1.0`→`v1.1`; update the loader
      (`core/donations.py`, `core/intent_asset_loader.py`); shrink `cross_language_validator` to phrasing-completeness.
      Intersects DOC-5b, DOC-7, UI-1/2/3.
      **Decisions (2026-06-02, user):** (1) **Layout** = `assets/donations/<handler>/contract.json` (neutral core) +
      `<handler>/{en,ru}.json` (phrasing only, joined by `method_name#intent_suffix` + param `name`). (2) **Migration
      tie-break:** where en/ru diverge on a neutral field, **Russian wins** (it's the primary language; also fixes the
      latent loader bug where `_merge_language_donations` silently took params/patterns from whichever language iterated
      first). (3) **`default_value` lives in the per-language files** (handles language-specific default text like the
      timer completion message, which already diverges en/ru today; canonical defaults like `unit="minutes"` just
      repeat harmlessly). (4) **SCOPE CHANGE — heuristic deletion MOVED to QUAL-11.** `entity_resolver._is_device_entity`
      /`_is_location_entity` are **live** (`nlu_component.py:38/62` call them every request), and the entity_type-driven
      *replacement* is the Q7b typed accessor (QUAL-11). So QUAL-29 only ADDS the `entity_type`/`room_context`
      declarations (defaulted conservatively: `entity_type="generic"`, `room_context="none"` — humans refine); the
      heuristics stay live until QUAL-11 swaps in the declarative resolver atomically (no broken window). QUAL-29 stays
      **first** — it provides the contract QUAL-11 consumes.
- [x] **QUAL-30** [DFLOW] (P1) — **Clarification UX — Grade 1. DONE 2026-06-03 (deterministic responder; carve-outs
      tracked).** Built the **single fail-loud boundary → explain-and-ask** mechanism: `get_param` now raises a structured
      **`MissingRequiredParameter`** (param_name/description/intent_name); the handler base's `execute_with_donation_
      routing` catches the `ParameterExtractionError` family **before** the generic error and calls a new base
      **`_clarify()`** responder → a single-turn, **localized, speak-able** `IntentResult` (`success=True`,
      `metadata.clarification=True`). Responder is **deterministic + localized** via a new system template set
      `assets/templates/clarification/{ru,en}.yaml` (loaded unconditionally, not per-handler; `get_template` handles the
      language→default fallback so no language is hardcoded). Fixed the fake **`confidence=1.0`** NLU fallback → `0.0`
      (honest no-match; routing keys on `_recognition_provider`, so safe). Tests: `test_clarification.py` (3, green).
      **Carve-outs (not blockers — gated elsewhere):** **LLM phrasing** ("use an LLM if present") deferred to the
      **QUAL-15** LLM foundation (deterministic is the offline guarantee — the must-have; LLM is the review's opt-in
      enhancement); **device/room clarification** → **ARCH-6** (no registered devices yet); **per-handler activation** →
      **QUAL-34** (handlers adopt `get_param` for required params — only timer uses the accessor today, with a caller
      default, so nothing triggers it in production yet); **no-intent** clarification already exists via the conversation
      fallback (now with honest confidence). Grade 2 (multi-turn slot-filling) is **QUAL-31**.
      **Residuals — extend the fail-loud family (slotted, not forgotten):** (a) **`InvalidParameter`** (out-of-range /
      bad-choice, distinct from missing) → **QUAL-34** (per-handler, build the exception + decide clarify-vs-default);
      (b) **`UnresolvedDevice`** raise→clarify when `room_context=required` can't resolve → **ARCH-6** (it owns the
      resolve-or-clarify policy; today resolvers degrade with a `_resolution_failed` marker, don't raise); (c) **targeted
      no-intent clarification** — today no-intent gives a *generic* "didn't understand, try X" (offline) or LLM chat
      (online); the NLU already computes `_fallback_context.likely_domain` ("probably timer") but **nothing uses it** for
      a "did you mean to set a timer?" prompt — **enhancement beyond Grade-1 scope → QUAL-37** (keeps QUAL-30 a clean `[x]`; 7d's "explain-and-ask" is met generically). **System** errors (component down) correctly
      stay graceful errors (not clarifications); their hardcoded English message → QUAL-36. Refs: Q7. _Original spec:_
      At the fail-loud boundary, convert structured failures into explain-and-ask; configurable responder; fix
      `confidence=1.0`.
- [x] **QUAL-31** [DFLOW] (P2, feature) — **Clarification UX — Grade 2 (multi-turn slot-filling). DONE 2026-06-09.**
      A clarifying ask is now a real dialogue turn: the QUAL-30 `_clarify` boundary arms a one-shot
      **`pending_clarification`** on the session (`UnifiedConversationContext.set_pending_clarification` — original
      intent name + asked-for slot + the triggering utterance), and a **pipeline pre-check** at the head of
      `BaseWorkflow._process_pipeline` reads the NEXT turn as the answer: it **prepends the original utterance** and
      re-runs the FULL understanding pipeline (text-processing → NLU → extraction → coercion) on the combined text —
      so *no separate slot-extractor* is needed and CHOICE/range/typed coercion all apply for free. Covers **text
      and voice** (both `process_text_input` and the audio paths converge on `_process_pipeline`). **Design choices
      vs. the original sketch (Invariant #8(d), narrowed):** (1) used a **dedicated `pending_clarification` field**, NOT
      the `ConversationState` enum — its `CLARIFYING` value already carries the unrelated *no-intent fallback* meaning
      (conversation handler) and `CLARIFYING→CLARIFYING` is an invalid transition that would have broken re-asks; the
      field's presence is the trigger, fully decoupled from the existing state machine. (2) **Expiry rides session
      eviction** — pending lives on the per-session context, which `ContextManager` drops after `session_timeout`
      (the Q2 idle window), and it's consumed by exactly the next turn, so no separate timer is needed. (3) **Re-asks
      append** — a resumed turn calls NLU with the combined text as `original_text`, so if the handler clarifies again
      `_clarify` re-arms with it (multi-slot via successive rounds). Tests: `test_qual31_slot_filling.py` (4 — arming,
      one-shot consumption, combined-utterance resume, normal-turn untouched); QUAL-30's 3 still green. No donation/
      config/REST contract touched → config-ui N/A. Verified: pyright 0, 9/9 import contracts, no-TYPE_CHECKING clean,
      suite 83=83 FAILED (0 net regression; +4 new passing). **Known limitation → QUAL-44:** the resume pre-check
      assumes the next turn IS the answer; if the user instead barks a new command it gets combined into a garbled
      utterance (bounded only by one-shot consumption + idle expiry). _Original spec:_ `pending_clarification`
      on the conversation session + `ConversationState = awaiting-clarification` + a pipeline pre-check that fills the
      slot from the next turn and completes the original intent (symmetric to the F&F `contextual` check, but transient).
      Expires with the Q2 idle window. Follow-up to QUAL-30.
- [x] **QUAL-32** `[release]` [QUAL] (P2) — **DONE 2026-06-08** (outcome at end of item). **Purge `TYPE_CHECKING` import guards repo-wide (Invariant #9).** _ARCH-15
      PR-9.2 note: the new I/O modules (`core/interfaces/output.py`, `core/event_bus.py`, `core/observe.py`,
      `outputs/*`) were authored TYPE_CHECKING-free (direct imports, per the PR-3 user directive), so they add **nothing**
      to this purge surface._ ~13 files
      still carry an `if TYPE_CHECKING:` block (`core/metadata.py`, `core/interfaces/webapi.py`, several
      `intents/handlers/*.py`, `utils/audio_helpers.py`, …). For each: if there's no real import cycle, hoist the import
      to module top and de-stringize the annotation; if there **is** a cycle, fix it at the architecture level (break
      the upward edge — move the shared type down / route via a port, per Invariant #3) rather than re-guard. Done when
      `grep -rn TYPE_CHECKING irene/ --include=*.py` returns nothing (outside prose/docstrings) and imports/smoke stay
      green. _Two files already cleared opportunistically (2026-06-02): `intents/handlers/conversation.py` + `timer.py`
      (the QUAL-28 touch surface)._
      **— OUTCOME (2026-06-08):** Reconciliation (Invariant #8) — only **4** real guards remained, not ~13 (prior
      refactors cleared the rest; the `utils/audio_helpers.py` + `intents/context_models.py` hits are *comments*, not
      guards). Purged all 4: `core/interfaces/webapi.py` + `intents/handlers/system_service_handler.py` (empty `pass`
      blocks removed) and `core/metadata.py` + `intents/handlers/random_handler.py` (hoisted `from pydantic import
      BaseModel` — a hard dep, no cycle — and de-stringized the `Type[BaseModel]` annotations). **Added a build-time
      gate** mirroring the hexagon `lint-imports` story: `scripts/check_no_type_checking.py` (AST-based, so it ignores
      comments/strings) + a wrapping test `irene/tests/test_no_type_checking.py` + a hard-failing CI step in
      `config-validation.yml` — CI breaks if a guard reappears (negative-tested). 9/9 import contracts kept; suite 83
      failed = baseline (no net regression).
- [x] **QUAL-33** `[release]` [DFLOW] (P2) — **Handlers ignore declared CHOICE params (surfaced by QUAL-29). DONE.**
      Two handlers DECLARED a CHOICE parameter their code never read — a genuine bug the format split exposed.
      **(a) `datetime.format` — DONE:** all three handlers (`current_time`/`current_date`/`current_datetime`) now branch
      on the canonical `format` (time: 12hour/24hour/verbose · date: short/iso/full=verbose · datetime: iso/unix/
      readable/verbose), rendering via `strftime` with the natural template as the verbose default. **(b) `system.info_
      type` — DONE (user-reduced scope):** `_handle_info_request` branches on `info_type`; the canonical set was
      **reduced to `[system, performance]`** — `configuration`/`logs` REMOVED from the donation entirely (user 2026-06-03:
      "no handlers, no donations" — not declaring options we don't implement is the *fix* for this bug class, not a
      regression). `performance` renders real metrics (`get_metrics_collector().get_performance_summary()` + uptime) via
      a new bilingual `performance` template; `system` keeps the existing info. **Authored bilingual `choice_surfaces`**
      for both (`datetime.format` en+ru; `system.info_type` en+ru), making the values reachable (QUAL-29's matcher
      extracts CHOICE via surfaces). Validator now reports `datetime`/`system` surface-complete. _ru surfaces are a
      proposal pending native-speaker review._ Refs: `qual29_choices_decisions.md` Cases 1–2.
- [x] **QUAL-34** `[release]` [DFLOW] (P2) — **Triage declared-but-unconsumed donation params. DONE 2026-06-03 (per-
      handler triage with user input).** All 19 resolved: **removed 9** (`audio_playback.file_path`;
      `conversation.{topic,query_topic,context_reference}` — query_topic was wrongly `required`, a latent clarification
      bug; `datetime.{location,timezone}`; `greetings.return_time`; `timer.retain`); **removed the whole `train_schedule`
      handler** (bogus external-API handler — code/donation/templates/demo/doc/config/registration); **wired 10 via the
      typed `get_param` accessor + bilingual choice_surfaces** (`voice_synthesis.voice` Bucket-B migration off raw_text;
      `datetime.relative` real date-offset; `greetings.time_of_day` explicit greeting; `text_enhancement.{improvement_type,
      correction_type}` LLM focus directive; `system_service.{component,metric_type,detailed}` + `system.{topic,component}`
      — `detailed` a real verbosity toggle, rest consumed-as-scope where handlers are generic). Fixed wrong-English ru
      surfaces + missing en surfaces on several CHOICE params. New `test_qual34_param_wiring.py` (3) + audit doc marked
      resolved; 0 net suite regressions; donations load 0 warnings. **Original triage detail follows.** The QUAL-33 bug class
      is **not** limited to datetime/system: **19 of ~56 declared
      params across 11 of 14 handlers are never read as `intent.entities[...]`** (7 are CHOICE params). Two buckets:
      **A — genuinely dead** (feature not built; e.g. `greetings.time_of_day`, `text_enhancement.improvement_type`,
      `system_service.metric_type`, `datetime.relative/location/timezone`, `conversation.topic/query_topic/context_
      reference`) → per-param **wire-or-remove** (the QUAL-33 precedent: build the feature, or stop declaring it; for
      CHOICE params kept, author bilingual `choice_surfaces`). **B — bypassed** (feature works but re-parses
      `intent.raw_text` instead of the NLU entity; e.g. `voice_synthesis.voice` → `voice_name`) → **fold into QUAL-11**
      (typed `ParameterSpec` accessor; same as QUAL-25 P1-r/P1-s). Also decide the `language`-as-pseudo-param pattern
      (declared CHOICE in most handlers but satisfied by `context.language`). Done when every declared param is either
      consumed or removed, and the audit re-runs clean. **Per-handler adoption of `IntentHandler.get_param` (QUAL-11
      Stage D) folds in here** — migrating each handler off ad-hoc `intent.entities.get(...)` to the typed accessor IS
      "consume the declared param" (and resolves Bucket B's raw_text bypass at the same site). The timer handler is the
      done reference (Stage D). **Also (extends QUAL-30's fail-loud family):** per handler, decide **invalid-value**
      behavior — build/raise **`InvalidParameter`** (review Q7b: out-of-range / not-in-choices, *distinct* from
      missing-required) → flows through the existing `_clarify` boundary; vs clamp to the declared `default_value`.
      Today `get_param` either clamps-to-default (silent) or raises `MissingRequiredParameter` (mislabeling an invalid
      required value as "missing") — fix the distinction here. Refs: `declared_param_audit.md`, QUAL-11, QUAL-30, QUAL-33, Q6/Q7.
- [x] **QUAL-35** `[release]` [PEX][MQTT] — **DONE 2026-07-06 (Slice 3 closed it — evidence-first, interactive).**
      **Slice 3 record:** authored the tier-2 hard-phrasing fixtures (F90–F98 measurable + F100–F102 relative
      adjustments) and ran the two-leg measurement (baseline vs the QUAL-50 LLM tier). The scoreboard said the wins
      were NOT in a new NLU tier; what got built instead: **(a)** group-noun routing for RAW NLU entities
      (`_group_for_surface` — LLM puts «свет»/«шторы» in `target`, never the CHOICE param; F92/F95),
      **(b)** power-verb → playback play/stop fallback (tape-deck class; F93), **(c)** resolver `scan_utterance`
      (stem-grade catalog spotting when word order defeats the post-verb extraction regex; F94),
      **(d)** donation pattern fixes — mode-worded hvac phrases (the greedy «кондиционер на» routed a setpoint
      sentence to hvac_mode at conf 1.00 where NO fallback tier can ever help; F96) + «звук на» volume_set pattern
      with mute out-specified (threshold coin-flip actuated volume up/down; F97). **Final: tier-1 gate 47/47
      (F94/F96/F97/F98 graduated in); tier-2 `NLU=llm` 5/8 — red = F100–F102 only (→ QUAL-68).** Colloquial lexicon
      («вруби»/«глуши») deliberately NOT added to donations — the LLM tier covers it (already enabled in ALL 6
      deployment configs since QUAL-50/51 — the 'disabled in deployments' note was stale) and the smart-home guide
      now documents the teach-a-word-via-donations recipe instead (user decision). **spaCy T2 leg DROPPED on
      evidence** (zero smart-home patterns exist; `spacy_provider` never consumes `token_patterns` at recognition;
      no fixture uniquely needed it) → revival, if ever, lives in QUAL-53. **Excluded by design** (recorded in the
      fixture-file header): anaphora, multi-command/negation, source→dest, free-text spans. 10 new unit tests;
      suite 1299; pyright 0. _Restructure + historical spine below (kept as the record):_
      landed): what remains runs in THREE SLICES; the historical prose below is the record, the slices are
      the plan.** **Already satisfied elsewhere** (task-start reconciliation): (a) typed `entity_type`
      donations ✓ ARCH-8 PR-4; (b) the Q7b declarative swap ✓ PR-3; (c) D-15 room policy + missing-room
      clarify ✓ PR-3/PR-4; resolver note (1) `options_from` dance ✓ QUAL-65; note (3) input fence lifted ✓;
      the units *requirement* (catalog `unit` + range pre-validation) ✓ PR-4; **"compound numerals need T2"
      is a dead theory** — F05/F06/F07 pass at T1 (the failures were BUG-23/24 pipeline corruption).
      **The slices:**
      • **Slice 1 — transliteration-tolerant matching (note 2) — DONE 2026-07-05.**
        `utils/text_normalizers.latin_to_cyrillic_hint` (cached): Latin words through the in-house TTS
        transcription engine ("YouTube"→«ютуб» exactly), ALL-CAPS acronyms spelled with English letter
        names (TV→«ти ви» — the engine would expand «тэлевижен»); consumed by the handler's
        `_match_option` (options with Latin also match their pronunciation hint) and the scenario label
        scorer, with «э»→«е» folding so transcription variants don't lose points. **Acceptance met:
        F41 + F53 green live, `make device-auto` → 25/27** — the only red left is F40/F42 (QUAL-64,
        user-parked). F41/F42/F53 retiered to 1 (eval-commons `30e174c`); tier 2 now means exactly the
        Slice-3 set. 3 handler tests + hint unit coverage; suite 1269 green.
      • **Slice 2 — capability breadth — SCOPE DECIDED 2026-07-05 (interactive, item-by-item), DOING.**
        **WIRE:** `volume` all four (up/down/set/mute_toggle); `playback` everything (play/stop/next/
        previous/ff/rewind; `play_pause` as the fallback where a device lacks the split actions — the
        `video` device has only the toggle); `cover.set_position` in BOTH address forms (device +
        room-group with `params{pct}`; «наполовину»→50); `climate` on/off via power-verb fallback
        («включи обогрев» fails today — power verbs only see `power` caps); kitchen-hood `fan` (power
        verbs → `set(2)`/`off`; explicit levels; «на полную»→catalog max 4); `tracks` audio/subtitles
        (no eject); `screen` aspect ratios; `menu` nav subset up/down/left/right/ok/back/home (user:
        needed for track dialogs on some devices — exit/menu/settings excluded); `presence` home/away
        («мы дома»/«мы уходим»); `cleaning` start + set_delay(minutes); **`water_supply` alarm on/off
        only** (not heating_control's). **SKIP (recorded exclusions):** `pointer`, `power.toggle`,
        `seasonal_mode` (twice-a-year deliberate act vs ASR misfire), heating_control `alarm`, **all
        four valves — PERMANENT voice fence** (consequence-heavy plumbing, like the power-fan-out
        fence). **CONTRACT-BLOCKED:** HVAC `set_mode`/`set_fan` — bare string params, no triplets/
        options_from (the G5 disease, third instance) → **bridge VWB-24 filed (uncommitted)**; wire
        after the re-pin that types them. Vanes never. Each wired item = donation method + handler
        method + crossover fixtures (PR-4 pattern). Adjudications ride along: `set_position`'s `%`
        settles units-generalization; `room_context` enforcement gets a keep-or-close call.
        **Part A DONE 2026-07-05** (`bedc867`): volume all-four (dB ranges honest via shared range
        pre-validation), playback play/stop/next/previous + seek-CHOICE with `play_pause` fallback,
        `cover.set_position` both forms («наполовину»→50), power-verb fallback → climate.on/off +
        hood fan set(2)/off. Fixtures F60–F67 ALL GREEN live first run — **33/35** (red = F40/F42 =
        QUAL-64 only). 5 handler tests; suite 1274, pyright 0. **Part B DONE 2026-07-05:** tracks audio/subtitles («смени» verbs — «переключи» is
        input_select's in the matcher's scoring, QUAL-64 family), screen aspects (CHOICE + target),
        menu nav CHOICE (7 directions), presence home/away, cleaning start + set_delay, water alarm
        (device narrowed by the alarm+leaks capability PAIR — never an id literal). Fixtures
        F70–F75; live **39/41** — only F40/F42 (QUAL-64) red. **Slice 2 COMPLETE.** Adjudications:
        units-generalization SETTLED (dB volume, % position/brightness, °C setpoint all ride the one
        catalog-range pre-validation path — no further abstraction); `room_context` declarative
        enforcement CLOSED as satisfied-by-implementation.
      • **Slice 2a — HVAC mode/fan (VWB-24 consumed) — DOING 2026-07-05.** The bridge accepted +
        implemented VWB-24 (set_mode/set_fan params typed). Scope: re-pin the contract into
        eval-commons (guards will flag stale fixtures), wire `_handle_hvac_mode` (+fan if triplets
        landed for it) via the CHOICE path against the typed values, fixtures («кондиционер на
        охлаждение»), vanes stay unwired. **DONE 2026-07-05:** re-pinned @ `a17a63b0` (VWB-24 v1.3 —
        full ru/en/de triplets, e.g. cool→«охлаждение»; wire≠canonical now: "COOL"/"cool" — the
        fixture guard learned to validate CANONICAL, which is what Irene sends per §5a);
        `_hvac_choice` matches spoken vs the device's OWN triplets (labels+canonicals through
        `_match_option`), device picked ACTION-aware (only HVACs carry set_mode — heaters must not
        clarify into it); set_fan's param is named `fan`. Fixtures F80/F81 green live — **41/43**,
        red = F40/F42 (QUAL-64) only. Gotcha hardened: a STALE mock bridge squatting on the port
        served an old golden silently (empty mode values) — `device-auto` now clears the port first.
      • **Slice 3 — hard-phrasing tier, evidence-first (absorbs old T2 AND T3).** Author the fixtures for
        the genuinely hard phrasings (multi-param «яркость 30 и температуру 22», role/preposition
        «со спальни на кухню», free-text spans, negation «все кроме торшера», anaphora «сделай его поярче»),
        then measure BOTH existing mechanisms against them: the parked spaCy patterns activated as the
        cascade fallback, and the **QUAL-50 LLM NLU tier enabled in config** (built, donation-grounded,
        DeepSeek-through-LLMPort, abstains offline — currently NOT enabled in any deployment config). Build
        only what the scoreboard says is missing. Sequencing: AFTER the QUAL-64 matcher tune, so the
        fallback tiers are built against a tuned first tier. **The old T3 bullet's "local-LLM / local-only"
        framing is OBSOLETE** (pre-dates QUAL-50/QUAL-14): the universal fallback is the configured LLM
        provider (DeepSeek with an API key), offline = graceful degradation — no separate T3 task exists.
      QUAL-35 CLOSES at Slice 3. _Historical spine below (kept as the record):_
      **★ ARCH-22 (2026-06-14) supplies the multi-room resolution SPEC
      (D-15, `docs/design/esp32_satellite.md`):** no room → primary; a covered room in the utterance → that room; a known
      (catalog) room NOT covered → spoken error "this room is not managed by this device". Needs the bridge catalog
      (ARCH-8) for the global room set + RU-morphology room matching. ARCH-22 already **carries** `primary_room`/
      `covered_rooms` on `ClientRegistration` (D-14); this task implements the resolver that consumes them. _Orig:_
      **Declarative NLU tiers T2 + T3 — MUST-HAVE for smart-home/MQTT
      (gated on ARCH-7/8). Split out of QUAL-11 (2026-06-03, user).** _ARCH-15 PR-9.2 note: the device handlers QUAL-35
      authors **emit a `device_command`-modality result delivered via the OutputManager to the designated bridge
      `OutputPort`** and await its rich `DeliveryResult` (echo/error → spoken confirm; `param_invalid` → clarify) — per
      `mqtt_integration.md` §13 (ARCH-8). No bespoke ActuationPort._ QUAL-11 deliberately shipped the **lightweight (T1)**
      extraction contract — keyword/NER + regex + CHOICE surfaces + lemmas, which is what the `hybrid_keyword_matcher`
      (the hot path) actually runs. T1 covers the easy ~80% of commands but **fails on the complex commands smart-home
      control needs.** This task builds the two heavier tiers when MQTT/smart-home lands:
      • **T2 — spaCy `Matcher`/`EntityRuler` slot-filling** (the currently-**parked** `token_patterns`/`slot_patterns`/
        `extraction_patterns`, authored across all 14 handlers but validated-then-discarded today). Implement in the
        **spaCy provider as the cascade fallback** (lemma/POS-aware recognition + span→`ParameterSpec` slot extraction).
        Wins where T1 provably fails: **compound values** ("таймер на 2 часа 30 минут" → 150 min, not 2), **two
        same-type entities by role/preposition** ("со спальни **на** кухню" → source vs dest), **multiple param=value
        pairs in any order** ("яркость 30 и температуру 22"), **free-text spans into a slot** ("напомни выключить
        плиту"), and **morphology/name-collisions at real-home scale** (`{LEMMA: лампа}` vs `{LEMMA: лампочка}`,
        deterministic vs fuzzy). _Stop the silent validate-then-discard now (QUAL-11 Stage C documents the patterns as
        parked here)._
      • **T3 — dependency-parse / local-LLM NLU** for what T2 **also** can't do (linear Matcher has no scope):
        **negation/exceptions** ("все лампы **кроме** торшера"), **anaphora** ("сделай **его** поярче"), **conditionals**
        ("**если** темно, включи свет"). Ties to the local-LLM-assist lane (QUAL-15) + ARCH-9/10 [INFER]; opt-in,
        local-only.
      **Sequencing:** design with **ARCH-7** (MQTT/output-port + room/device model) and land before/with **ARCH-8**
      (smart-home actuation) — complex device commands are unusable on T1 alone. **OWNS the device-half relocated
      from ARCH-6 (2026-06-03):** ARCH-6 deferred the `entity_type`/`room_context` *consumption* because at its build
      time NO device/room handlers existed (all decls `generic`) — that work lives HERE, where the device handlers do.
      So this task: **(a)** authors the non-generic `entity_type`/`room_context` (device/location/room/person) on the
      smart-home handlers it builds; **(b)** replaces the brittle `_is_device_entity`/`_is_location_entity` name-heuristics
      (`entity_resolver.py`) with declarative `entity_type`-driven resolver selection (the Q7b "typed accessor IS the
      replacement" atomic swap); **(c)** implements the `room_context` resolve-or-clarify policy (with QUAL-30). ARCH-6
      left the seam ready (`resolve_physical_id` returns the registered physical id; `ClientRegistry` populated by the WS
      handshake). Gated by `config-ui-stays-functional` (any donation-schema change → config-ui;
      note the parked T2 pattern fields already exist, so no new schema surface unless extended). Refs:
      `parameter_extraction_review.md` (T2 = the "dead best mechanisms" themes 1+3), QUAL-11 (T1 baseline), Q6/Q7.
      • **★ Units-of-measurement layer (design WITH this task — user, 2026-06-28).** Smart-home commands carry units
        (dimming **%**, climate **°C**, …), the same value+unit shape time already needs. BUG-6 consolidated the **time**
        family into `irene/utils/units.py` (`TIME_UNITS` table + `parse_duration`) and **removed the dead `DURATION`
        param-type stub** (it never had a `coerce()` branch). Do NOT build a general units abstraction speculatively —
        design it HERE, against the real device-unit requirements: generalize `units.py` to a value+unit type with
        **canonical normalization + externalized (donation/catalog) unit surfaces** so timer + dimming + temperature
        share ONE path. The bridge catalog (ARCH-8) declares each device's unit — that's the requirement source.
        **★ Satisfied bridge-side 2026-07-05 (VWB-20 v1.1): 27 action params carry `unit` (°C on `set_setpoint`,
        % on brightness/position) in the typed `CatalogParam`.**
        `QuantityEntityResolver` (`entity_resolver.py`) already holds the non-time nucleus (percent/degrees). _(The ru
        oblique-case numeral gap noted here was resolved separately as BUG-7.)_
      • **★ Resolver-design notes from the contract analysis (2026-07-04/05, chat → recorded here):**
        **(1) CHOICE resolution gains a SECOND surface source** — a `CatalogParam` with `options_from` (e.g.
        `apps.launch app`) enumerates its surfaces at RESOLUTION time via `GET /devices/{id}/options/<kind>`,
        not from the catalog; generalize the ARCH-26 lazy-miss pattern (resolve → miss → re-fetch → retry once)
        plus a short-TTL per-device cache — this round-trip sits inside a voice command's latency budget.
        **(2) Dynamic-set surfaces need transliteration-tolerant matching:** the options endpoint returns
        device-reported proper nouns ("YouTube", "Netflix") while RU ASR yields «ютуб»/«нетфликс» — the
        resolver must match Cyrillic↔Latin phonetically/transliterated, NOT by exact equality (per
        `donation-choice-surfaces-rule` the contract stays canonical; matching is Irene's job).
        **(3) ~~The v1 command set EXCLUDES input switching~~ FENCE LIFTED 2026-07-05 (bridge VWB-19 +
        voice QUAL-65):** `input.set {value}` + `apps.launch {app}` implemented — by_value sets validate
        offline against catalog `values`; parametric/app sets enumerate at resolution time via the
        note-(1) `options_from` dance (now BUILT: `read_options` on the port + 30s TTL cache). Only
        Cyrillic-spoken-Latin matching («ютуб») remains T2 — note (2).
        **(4) The depth doctrine (VWB-23, 2026-07-05):** resolve only as deep as the utterance specifies —
        a named device → device-canonical; a bare capability noun («включи свет», «закрой шторы») → a
        room-group command (`{room, group, action, scope}`); the noun lexicon binds group nouns to catalog
        `CatalogCapability.group` values, NOT to convention; singular → `scope: auto` (the bridge's
        `group_defaults` picks the device), «весь»/plural → `scope: all`.
        **(5) No power-group fan-out promises** in donations — the bridge allow-lists fan-out to
        `light`+`cover` only and 409s the rest by design («выключи все розетки» must not work).
        **(6) Same-room capability ambiguity: v1 CLARIFIES** (user decision 2026-07-05; TEST-18 fixtures
        F20/F21 are the spec) — don't build priority config into the v1 resolver; priority rules are
        **QUAL-63** (later release).
- [x] **QUAL-36** `[release]` [DFLOW][I18N] (P1) — **Single language source-of-truth; purge hardcoded language codes
      (theme ④; user observation 2026-06-03). DONE 2026-06-03.** **Consolidation decision (user, mid-task):** found FOUR
      competing declarations (`CoreConfig.language="en-US"` locale-form, `nlu.default_language`/`supported_languages`,
      `nlu_analysis.languages.*`, `IntentAssetLoader`'s own); user chose **promote to top-level `CoreConfig.default_language`
      + `supported_languages` (2-letter)** as the one canonical source — read at the composition root, injected inward.
      **Delivered:** (1) canonical top-level config fields; removed the `nlu.*` duplicates; deprecated the `en-US` field;
      config-master.toml updated. (2) `ContextManager` injected `default_language`+`supported_languages` (mirrors
      `max_history_turns`); `engine.py` wires them; seed fixed. (3) NLU detection reads canonical + clamps; `_analyze_text_
      language` returns `None` (no signal) → caller applies default; providers receive canonical via config injection. (4)
      invariant established. (5) **deleted all 67 `or "ru"` fallbacks** → bare `context.language`; ripped out the timer/audio/
      voice-synthesis `_get_language` re-detection heuristics; **fixed the `hybrid_keyword_matcher` `'en'`-vs-`'ru'` divergence
      bug**; made handler `language="ru"` default params required (T4). (6) language-switch validation (`system.py`) now reads
      the new **`context.supported_languages`** (seeded from canonical) — no baked `["ru","en"]`. (7) **localized the LLM
      context-injection labels** → `assets/localization/conversation/{ru,en}.yaml` (`_context_label`, by user language).
      **Verified:** new `test_language_source_of_truth.py` (6) proves en-primary + arbitrary-language seeding/clamp/labels/
      no-stomp; suite at baseline parity (0 regressions). **Carve-out → QUAL-38:** processing-language defaults (number-spelling
      utils / silero TTS / ASR / text-processor) + inline bilingual handler messages (`== 'ru'` branches) are a distinct
      concern, filed separately. Refs: `RELEASE_JOURNAL.md` 2026-06-03, QUAL-16.
- [x] **QUAL-37** `[deferred]` [DFLOW] (P2) — **Targeted no-intent clarification (enhancement; split from QUAL-30).
      DONE 2026-06-03.** The online (LLM) path already consumed `_fallback_context.likely_domain` (via
      `_build_fallback_context_prompt`, QUAL-16); the gap was the **offline** path. **Delivered:** `_handle_fallback_
      without_llm` now reads `likely_domain` and, when it matches a known domain, emits a **deterministic, localized,
      offline** targeted clarification ("Возможно, вы хотели поставить таймер?" / "Did you want to set a timer?") via a
      new `fallback_targeted` template + a `fallback_domain_labels` map (domain→friendly action phrase) in
      `assets/localization/conversation/{ru,en}.yaml`; falls through to the generic responder when there's no guess /
      unknown domain. Metadata now carries `targeted`/`likely_domain`. **Verified:** new `test_no_intent_clarification.py`
      (5) covers targeted ru/en, generic fall-through, unknown-domain fall-through, determinism + offline; 0 net suite
      regressions. **Ledger fix:** removed a corrupted duplicate QUAL-37 header that had orphaned QUAL-36's old body
      (collateral from the QUAL-36 done-edit). Refs: QUAL-30, QUAL-16, Q7.
- [x] **QUAL-38** `[deferred]` [DFLOW][I18N] (P2) — **Processing-language threading + inline-bilingual purge (carved from
      QUAL-36). DONE 2026-06-03.** **Key correction:** the processing language is the **audio-MODEL/deployment** language
      (which number-spelling/transcription rules to apply), NOT the session language — spelling numbers in the session
      language but synthesizing with a different-language voice would mismatch. So the fix is **config/model-derive**, not
      request-threading (which would introduce that bug; the QUAL-13 "request-scoped" comment was the gap). **(a) delivered:**
      `convert_numbers_to_words` made language-required (caller threads `request.language`); `PrepareNormalizer` gets a config
      `language` (was falling back to inline `"ru"`); `unified.py` threads the per-normalizer deployment language to both
      number normalizers; `silero_v3|v4` derive `self.language` from model config (default model is `*_ru.pt` → `"ru"`);
      `asr_component` transcribe endpoint resolves to `self.default_language` not a literal. (Library `utils/text_processing.py`
      defaults + the Pydantic request-schema `"ru"` defaults left as documented API/library defaults.) **(b) delivered:**
      externalized the genuine inline RU/EN strings — **voice_synthesis (6)** → `voice_synthesis_handler` templates,
      **system (3)** → `system_handler` templates, **provider_control (5)** → NEW `provider_control_handler` templates + a
      `_get_template` method; unified **random_handler (3)** error templates (added `{error}` to the ru side, dropped the
      `== 'ru'` branch). **Kept (legitimate, per done-criteria):** `system_service_handler` Russian pluralization grammar
      (strings already templated), and Russian command-keyword *parsing*. **Verified:** templates load + resolve ru/en; 0 net
      suite regressions. Done: processing language derives from model/config; handler user-facing strings externalized.
- [x] **QUAL-39** [API] (P2) — **DONE 2026-06-04 (Option 2, user-approved).** Audited the **19** routes lacking a
      `response_model` (104/123 already typed). **Key finding (the reason this task existed):** the **donations contract
      pair** `GET/PUT /donations/{handler}/contract` — UI-5's primary target — were the only **UI-5-consumed** untyped
      endpoints; reconciliation showed config-ui's other status/config/NLU reads already hit typed endpoints
      (`/intents/status`, `/configuration/config/status`, …), **not** the untyped system ones. **Done:** typed the contract
      pair's **envelopes** — `DonationContractResponse` / `DonationContractUpdateResponse` (`api/schemas.py`) — and `/health`
      (`HealthResponse`). **Contract/phrasing BODY stays `Dict[str, Any]` passthrough on purpose:** both have a **canonical
      JSON Schema** (`assets/donation_contract_v1.1.json` + `assets/donation_language_v1.1.json`, both
      `additionalProperties: true`); a strict Pydantic body would **drift from the schema AND drop fields on the editor's
      GET→PUT round-trip**. **Symmetry analysis (the donation_language question):** the language/phrasing side already does
      exactly this — `LanguageDonationContentResponse` with `donation_data: Dict[str, Any]` passthrough — so typing the
      contract envelope brings it to **parity** with the phrasing endpoints; the strong **body types** for config-ui are
      generated from the two JSON Schemas, the **envelopes** from OpenAPI (see UI-5). **Classified (b) legitimately
      dynamic / non-JSON — documented, not typed:** `/dashboard/html`, `/`, `/asyncapi`(+`.yaml`) (HTML/YAML),
      `/prometheus` (text exposition), `/asyncapi.json` + `/debug/asyncapi` (generated spec/debug docs), `/components`
      (conditional keys). **Deferred general hygiene (non-UI-5, type later if wanted):** asr `/providers`/`/reset`/
      `/transcribe`, monitoring `/contextual-commands`(+`/performance`), nlu_analysis `/capabilities`/`/statistics`,
      `/system/status` (config-ui doesn't consume it — Overview uses `/intents/status`). Verified: models accept the real
      GET/PUT shapes incl. passthrough extras, suite 85=85 (0 net regression). (Found 2026-06-04.)
- [x] **QUAL-40** `[release]` (P2) — **DONE 2026-06-07.** Generated-TOML section headers no longer dropped. **Was:**
      `ConfigManager._generate_provider_sections` / `_generate_normalizer_sections` (`config/manager.py`) built a
      per-iteration `section = "[base_path.<name>]"` header but **never appended it to `sections`**; the closing
      `"\n".join([section] + sections)` kept only the **last** header (and mis-placed it at the very top), so every
      provider/normalizer header except the last was dropped → the generated TOML collapsed all entries' keys under one
      section. **Fix:** `sections.append(...)` the header at the start of each iteration and join plainly (dropped the
      `[section] +` prepend + the dead `section = ""` init). **Verified round-trip:** new
      `test_config_section_generation.py` (3) asserts every header survives and the output re-parses via `tomllib` back to
      the original `{provider/normalizer: {...}}` nesting (the round-trip assertion fails on the old code — keys would
      collapse under the single surviving header). Backend-only (generated-TOML *content* fix; no contract/shape change),
      so config-ui's TOML-editor surface just receives correct TOML — no config-ui code change. Gates: pyright 0,
      import-contracts 9/9, dep-validator 55/55, check_scope clean, suite 84=baseline (+3).
- [x] **QUAL-41** `[release]` (P2) — **DONE 2026-06-07.** `IntentAssetLoader` validator output now matches
      `api.schemas.ValidationError`. **Was:** `validate_template_data` / `validate_prompt_data` /
      `validate_localization_data` (`core/intent_asset_loader.py`) emitted error/warning dicts keyed `{field, message,
      severity}`, but `api.schemas.ValidationError` requires `{type, message}` (+ optional `path`/`line`), so
      `ValidationError(**err)` in `intent_component.py`'s template/prompt/localization editing endpoints raised a pydantic
      error (missing required `type`) → **HTTP 500 whenever those endpoints hit a real validation error**. **Fix (chose
      "align validator output to schema" over a boundary mapper):** rewrote all three validators (incl.
      `_validate_domain_specific_localization`) to emit canonical `{type, message, path}` — the **same shape the sibling
      `validate_phrasing_data`/`validate_contract_data` already produce** (`field`→`path`; `severity` dropped, already
      encoded by the errors-vs-warnings list; `type` carries a category: `structure`/`missing_field`/`value`/`validation`).
      No consumer read `field`/`severity` (all 9 endpoint sites only `ValidationError(**err)`). **Invariant #4:** config-ui's
      template/prompt editors already read `.message` (via `any` casts: TemplatesPage/PromptsPage) → render correctly now;
      `npm run check` + `build` stay clean (no config-ui change needed). **Regression test:** `test_asset_validation_schema.py`
      (3) constructs the schema models from each validator's failing-input output — the exact path that used to 500. Gates:
      pyright 0, import-contracts 9/9, dep-validator 55/55, check_scope clean, suite 84=baseline (+3). **Also fixed
      (user-directed, same change):** `DonationsPage.tsx:859` read `err.msg` on the **phrasing** validation response while
      `validate_phrasing_data` emits `message` (canonical) — a pre-existing latent display bug on the UI-5/QUAL-29 surface
      (the adjacent warnings map already read `.message`); `err.msg`→`err.message`, config-ui check + build green.
- [x] **QUAL-42** `[release]` [DVALIDATE] (P1) — **Donation contract↔code validator + LLM translation services.
      DONE 2026-06-06 (user-directed: "do this validator right away").** Closed the real gap the donation-validation
      investigation found: nothing reconciled a **contract** against the **handler code** it drives (only contract→method
      existence; never params, never reverse coverage). **Delivered (backend):**
      **(1)** `core/contract_validator.py` — `ContractWiringValidator` introspects each handler class + AST-scans the
      module for parameter reads (`get_param`/`get_typed_param`/`intent.entities`). **Severity split (deliberate, to
      avoid false-positive boot failures):** an **unwired contract method (no callable on the class) is FATAL** — raises
      `DonationDiscoveryError`; **soft warnings** = a declared parameter never read (legitimately context-sourced, e.g.
      `language`), or a `_handle_*` method no contract declares (reverse coverage). A `strict_parameters` flag promotes
      param warnings to fatal (ratchet). **(2) Startup integration** — `IntentAssetLoader.load_all_assets` runs the
      validator over all loaded donations, **fail-fast on unwired methods**, and caches the report. Verified: the 14
      shipped handlers validate **0 fatal / 13 useful warnings** (boot stays green). **(3) Endpoints (intent_component,
      via injected `LLMPort`):** `GET /donations/validation` (the startup wiring report → UI); `POST
      /donations/{h}/validate-translation` (**LLM** meaning/consistency QA — deepseek default, else any supported
      provider with a key; **no LLM → `llm_available:false` + "validate manually" message**); `POST /donations/{h}/translate`
      (**LLM** translation *service*, content-aware replacement for the dead phrase-count `suggest-translations`; same
      graceful no-LLM path). **(4)** 8 schemas in `api/schemas.py`; design doc `donation_editor_ux.md` §9 updated for the
      UI. **Tests:** `test_contract_validator.py` (7, incl. an all-real-handlers 0-fatal guard). Gates: pyright 0,
      import-contracts 9/9, dep-validator 55/55, suite 84=baseline (+7 passing). _Decision logged:_ LLM translation
      validation is **on-demand (endpoint), not per-boot** — avoids per-startup token cost/fragility; structural wiring
      validation is the always-on startup part. Refs: `parameter_extraction_review.md`, donation-validation investigation.
- [x] **QUAL-43** [DVALIDATE] (P2) — **DONE 2026-06-06.** Removed the donation v1.0 dead validation code and
      **repointed the build analyzer at the v1.1 schemas** (user-directed mid-task). **Removed:** the dead v1.0
      schema-validation chain in `IntentAssetLoader` (`load_donation_on_demand` / `_load_and_validate_donation` /
      `_validate_json_schema` / `validate_donation_data` — 0 callers; the *v1.1* `_validate_donation_schema` stays);
      `irene/tools/intent_validator.py` + its `irene-intent-validate` script + `assets/v1.0.json`; the orphaned
      `CrossLanguageValidator.sync_parameters_across_languages` (+ its dead confidence/lang-detect helpers and the
      `TranslationSuggestions` dataclass); the rule-based `suggest_translations` method + the
      `POST /donations/{h}/suggest-translations` endpoint; the dead schemas `SyncParameters{Request,Response}`,
      `SuggestTranslations{Request,Response}`, `TranslationSuggestionsSchema`, `MissingPhraseInfo`. **Build analyzer
      rewritten:** `_validate_intent_json_files` now validates each enabled handler's `assets/donations/<h>/contract.json`
      (against `donation_contract_v1.1.json`) + its `<lang>.json` phrasing (against `donation_language_v1.1.json`) via
      `jsonschema` — the old path pointed at the non-existent v1.0 monolithic `<h>.json`, so it would have emitted false
      "file not found" build errors. Verified the real handlers validate clean + a missing contract is flagged.
      **Regenerated** the committed `openapi.json` (109→108 paths; suggest-translations gone) + the frontend types.
      Gates: pyright 0, import-contracts 9/9, dep-validator 55/55, backend suite 84=baseline, `cd config-ui && npm run
      check && npm run build` pass. _Original scope:_
      **Remove donation v1.0 dead validation code (split from UI-5 scope decision, 2026-06-06).**
      The v1.1 split (QUAL-29) + the new wiring validator (QUAL-42) left v1.0-era validation as dead weight: **(1)**
      `IntentAssetLoader._validate_json_schema()` validating against `assets/v1.0.json` (reachable only via the legacy
      `_load_and_validate_donation` / unused `validate_donation_data` paths); **(2)** `irene/tools/intent_validator.py`
      (standalone CLI validating v1.0.json, not wired into the loader/API); **(3)** `assets/v1.0.json` itself; **(4)** the
      orphaned `CrossLanguageValidator.sync_parameters_across_languages()` no-op + its now-unused
      `POST /donations/{h}/sync-parameters`-era plumbing; **(5)** the rule-based `suggest_translations()` + its
      `POST /donations/{h}/suggest-translations` endpoint, **once UI-5 stops calling it** (superseded by QUAL-42's LLM
      `translate`). **Sequencing:** do AFTER UI-5 lands (so removing the suggest-translations endpoint doesn't break the
      old UI mid-flight). Verify no remaining importers; gates: pyright 0, import-contracts 9/9, dep-validator 55/55,
      suite ≤baseline. Found during the donation-validation investigation + UI-5 scoping.
- [x] **QUAL-44** `[release]` — **DONE 2026-07-05** _(un-deferred same day, user — the TEST-18 device suite
      made the defect reproducible: an armed clarification consumed the next same-room command as its
      answer, poisoning F51–F53 in cascade)_. **Implemented exactly as scoped:** the resume pre-check
      (`voice_assistant.py`) now runs NLU on the BARE new utterance first; a confident (≥ the NLU
      component's threshold), non-fallback recognition is a fresh command — the pending clarification is
      dropped (logged) and the utterance processes clean; anything else (bare fragment / low-confidence /
      fallback) combines as before. Trade-off settled per the entry's own lean: one extra NLU pass on
      clarifying turns only; abandonment is silent (no spoken acknowledgment — the fresh command's own
      reply is the acknowledgment). Regression tests: new-command abandons, low-confidence still combines,
      bare-answer path stays green (the fakes became text-aware — an everything-recognizes-at-0.9 fake
      would have defeated the arbitration silently). Live proof: F52 flipped green; F42 stopped producing
      combine-garbage. [DFLOW] (P2, enhancement; split from QUAL-31) — _Orig:_ **Answer-vs-new-command arbitration on a
      clarifying turn.** QUAL-31's resume pre-check (`workflows/voice_assistant.py` `_process_pipeline`, the
      `take_pending_clarification` branch) **unconditionally** treats the turn that follows a clarification as the answer:
      it prepends the original utterance and re-runs NLU on the combined text. That is the intended flow ("answer with
      just the missing value"), but if the user instead **abandons the clarification and barks a new command** ("какая
      погода?" after being asked a timer duration), the combine yields a garbled utterance ("поставь таймер какая
      погода?") that can misroute or no-op. Today this is bounded only by one-shot consumption (the bad turn clears the
      marker) + idle-window expiry — acceptable for the P2 feature, but not robust. **Scope:** add deterministic
      arbitration before combining — e.g. run NLU on the **bare answer first**; if it independently recognizes as a
      **confident, non-fallback** intent (a real, different command), drop the pending clarification and process the
      answer **fresh**; otherwise (bare fragment / low-confidence / fallback) treat it as the slot answer and combine as
      today. **Trade-off to settle:** an extra NLU pass on clarifying turns only (cheap, rare) vs. a lighter
      confidence/phrase heuristic; also decide whether a brand-new command should *cancel* the pending intent silently or
      acknowledge the abandonment. Pairs with QUAL-31 (this is its known limitation) and the F&F `contextual` resolution
      (same "is this turn about the prior context or a fresh request?" question). Done when a new-command answer routes
      to the new command (not the garbled combine) with a regression test, and the legitimate slot-answer path stays
      green. Refs: QUAL-31, QUAL-30, Q7.
- [x] **QUAL-45** [WS][ESP32] (P2) `[deferred]` — **DONE (design) 2026-06-14 — SUBSUMED BY ARCH-22.** The ESP32
      audio-streaming protocol (end-of-utterance + on-device VAD/wake contract) is now fully specified in
      **`docs/design/esp32_satellite.md`** — wire protocol §4 (`{"type":"end"}` device hint + server-authoritative ASR
      endpointing, D-5/D-6), the on-device microWakeWord+microVAD contract (D-9/D-10), and the single-mic/no-server-VAD
      split (D-11). The *firmware* implementation of the end-of-utterance signaling rides the **tracked firmware rewrite**
      (esp32_satellite.md §14), not this task. _Original below._ **ESP32 audio-streaming protocol: end-of-utterance signal
      + on-device VAD/wake contract.** Filed from the ARCH-18 endpoint reconciliation (2026-06-10). The **server already** consumes a
      `{"type":"end"}` control frame on `/ws/audio` to bound an utterance (one session = one utterance = one ASR;
      `webapi_router.py:824-835`) and ARCH-18 makes that path skip server VAD+wake (they run on-device). **Device-side TODO
      (ESP32 review):** define + implement the firmware's end-of-utterance signaling (emit `{"type":"end"}` at on-device
      VAD silence; **default = end of WS session** if a firmware doesn't send it), plus the on-device VAD/wake contract the
      server now assumes. Doc: `docs/review/esp32_wakeword_review.md` + `docs/design/ws_esp32_transport.md`.
- [x] **QUAL-46** [IO] (P2) `[deferred]` — **DONE 2026-06-15.** Generalize the vosk runner into a config-driven
      **voice runner** (follows ARCH-15's "runners-as-presets — config, not code"). The old `VoskRunner` was a full
      end-to-end mic pipeline (mic → VAD → [wake] → ASR → NLU → intent → TTS) but **artificially gated to vosk** by
      two checks — an `import vosk` dependency probe and a validation rule forcing `asr.default_provider == "vosk"` —
      while the actual processing path was already provider-agnostic (delegates to the ASR component). **Removed both
      gates:** the runner now requires only `sounddevice` (its real dep — mic capture) and validates *any* configured
      + enabled ASR provider (vosk/whisper/sherpa_onnx/google_cloud); ASR-provider deps are the component system's
      concern (`irene-dependency-validate`). **Renamed** `vosk_runner.py`→`voice_runner.py`, `VoskRunner`→`VoiceRunner`,
      `run_vosk`→`run_voice`, entry points `irene-vosk`→`irene-voice` + the `irene.runners` discovery entry + the
      `runners/__init__` exports (clean rename, no alias — pre-release). **Fixed the latent VAD inconsistency:** the mic
      pipeline structurally requires VAD (the workflow raises if it's off) yet the runner forced asr/audio/nlu/etc but
      not vad — now it forces `vad.enabled=True` too, so a VAD-off config fails clearly in the runner, not deep in
      workflow init. (`voice_trigger` stays config-driven — the runner auto-skips the wake word when it's absent.)
      Docs: new "Voice (microphone)" section in `QUICKSTART.md` (config-driven ASR, both invocation forms, `--trace`).
      New `test_voice_runner.py` (8 tests: provider-agnostic validation + the force-rules incl. VAD). 9/9 import
      contracts; runner/vad suites net-zero (4 pre-existing TEST-2 failures). Invariant #4 N/A (no config schema/endpoint
      change — purely a runner gate + rename). _Note: the v13-era `tools/migrate_runners.py` still maps the old name as
      a v13→v14 migration target; left untouched (obsolete, like `config_migrator` — flagged separately → QUAL-47)._
- [x] **QUAL-47** [WS] (P2) `[deferred]` — **DONE 2026-06-15.** Retire the obsolete one-time migration tools (the
      QUAL-46 follow-up). On v15.0.0, both target long-past versions and neither is imported by runtime code:
      **`irene/tools/config_migrator.py`** (v13→v14 config migration; entry point `irene-config-migrate`) and
      **`tools/migrate_runners.py`** (legacy `runva_*.py`→v13 runners — already broken by the QUAL-46 rename, since it
      referenced `vosk_runner`/`VoskRunner`/`run_vosk`). Deleted both + removed the `irene-config-migrate`
      `[project.scripts]` entry. No tests/code referenced them (only two `docs/archive/*` historical mentions, left as
      record). Package re-syncs clean; 9/9 import contracts. **Sweep extended 2026-06-15** — retired two more
      standalone (un-imported, non-entry-point) migrators verified spent/obsolete: **`tools/migrate_to_universal_plugins.py`**
      (old plugin→provider config migration; only refs were two `docs/archive/*` guides) and
      **`scripts/migrate_donations_v11.py`** (QUAL-29 donation v1.0→v1.1 — **QUAL-29 is `[x]` and the assets are already
      v1.1**: 13 `contract.json` + per-lang files, so the one-time migration is applied/spent). Surfaced a related
      finding kept OUT of scope → **QUAL-48**: `irene/config/migration.py` is *live* v13→v14 runtime auto-migration.
      **Also retired 2026-06-15** the dead one-off VAD debug script **`tools/test_vad_sibilant_fix.py`** (already broken —
      it imported `UniversalAudioProcessor`, renamed to `VoiceSegmenter` in ARCH-18, so it `ImportError`ed; not an entry
      point, not imported) + its orphaned companion **`configs/vad-sibilant-fix.toml`** (referenced only by that script).
      The sibilant fix itself is long shipped (`docs/archive/VAD_SIBILANT_FIX.md`, left as record).
- [x] **QUAL-48** [DFLOW] (P2) `[deferred]` — **DONE 2026-06-15 (decision: remove).** Removed the v13→v14 runtime
      config-migration path — the last v13/v14 relic after QUAL-47 retired the standalone migrators. `irene/config/migration.py`
      (637 lines: `V13ToV14Migrator`/`migrate_config`/`ConfigurationCompatibilityChecker`/`create_migration_backup`) was
      wired into `config/manager.py:_dict_to_config`, guarded by `requires_migration(data)` so it only fired for a
      **v13-format** config — which never occurs on v15.0.0. Deleted the module; dropped the import + the guard block in
      `manager.py` (the normal env-resolve → `model_validate` path is unchanged); removed the import + 5 `__all__` entries
      from `config/__init__.py`. A v13 config now fails plainly at pydantic validation instead of silently morphing —
      correct for v15 (v13 is unsupported). No test depended on auto-migration (verified net-zero vs baseline); all shipped
      configs (config-master/minimal/api-only) load clean; re-exports intact; 9/9 import contracts. Invariant #4 N/A.
- [x] **QUAL-49** [INFER] (P2) `[deferred]` — **DONE 2026-06-15.** Silero TTS model-id routing fix (surfaced from the
      ARCH-24 asset-routing analysis; relates to **ARCH-24 T5** — done early). `silero_v3`/`silero_v4` were the **only**
      providers that bypassed the AssetManager model-id router: they placed the model at `<dir>/<config:model_file>` with a
      **shared default** (`v3_ru.pt`/`v4_ru.pt`), so two v3 languages — v3_ru/en/de/es all share the `silero/` dir — that
      both left `model_file` at the default resolved to the **same file** (latent collision), inconsistent with the
      sherpa/whisper/vosk `get_model_path(provider, model_id)` convention. **Fix:** route the path via
      `get_model_path("silero_v{3,4}", model_id)` (→ `silero/<id>.pt` / `silero_v4/<id>.pt`, distinct per model_id); derive
      `model_url` from the selected model_id's descriptor (legacy torch.hub-fallback safety); route the download through the
      real provider name (`download_model("silero_v4", model_id)`, not the non-existent `"silero"` fallback that silently
      failed into the legacy path + a copy hack). Explicit `model_file` still honored as an override (back-compat). New
      `test_silero_routing.py` (4 tests incl. the anti-collision property). **Invariant #4 N/A** (TTS provider config is
      free-form `Dict[str,Any]`, `models.py:191` — not schema/config-ui-typed). Gates: suite 935 green, pyright 0, contracts 9/9.
- [x] **QUAL-50** [NLU][LLM] (P2) — **LLM NLU classifier as a cascade fallback provider** (decided 2026-06-15 in the
      ARCH-24 T4 armv7 config session). New `LLMNLUProvider(NLUProvider)`: when the deterministic providers (keyword +
      spaCy-on-64-bit) don't recognize an utterance, ask the **LLM to classify** it into a known intent **and extract its
      parameters** (intent taxonomy sourced from the donation/bridge catalog) — recovering fuzzy *commands* the keyword
      matcher misses. Slots into `provider_cascade_order` **after** keyword/spaCy (last NLU resort, before the
      `conversation.general` fallback). **Deliberately revises the QUAL-15/16 "NLU is LLM-free" stance — but only as a
      last-resort fallback**: the deterministic path stays primary and offline still works (keyword → conversation
      templates). Needs `[llm]` enabled with a provider (cloud = HTTP, so armv7-viable, but adds online dependency + latency
      for fuzzy commands). Full provider integration (the PR2 lesson): `LLMNLUProviderSchema` registered +
      `[nlu.providers.llm]` config-master block + `get_supported_architectures()`. **Gates the ARCH-24 T4 armv7 config**
      (which wants keyword→llm NLU — providers-before-configs). When low-confidence/missing-param: hand to the conversation
      handler's CLARIFYING multi-turn (already in place — `conversation.py` `ConversationState.CLARIFYING` + QUAL-37
      targeted clarification; verify it elicits a **missing required parameter**, not just domain-level specificity).
      **Design (confirmed 2026-06-15; corrected 2026-06-16):** the provider returns a **plain `Intent`**
      {name, entities, confidence, raw_text} via `recognize_with_parameters` — **identical to keyword/spaCy, no special
      output** (the earlier "rich structured JSON object" plan was wrong; see QUAL-52 below). It does what every NLU provider
      does: **classify** (LLM picks one intent name from the donation taxonomy, or abstain → `None`) + **extract params**
      (`extract_parameters`), then returns the Intent. **Catalog grounding is NOT the LLM's job** — the shared
      `ContextualEntityResolver` (run by `ContextAwareNLUProcessor` downstream, for *every* provider) canonicalizes entities
      against the live catalog/context. So the LLM emits **raw entity spans** ("kitchen", "lamp"), not canonical IDs — the
      shared resolver grounds them. The classification call is a **plain text** `chat_completion` (no
      `LLMPort.generate_structured`, no structured-output capability). **Confidence is DERIVED, written to the standard
      `Intent.confidence`:** (i) intent ∈ donation set [hard gate], (ii) fraction of **required params that resolve** against
      catalog/context [the real signal], (iii) an **evidence span** the LLM must quote [anti-hallucination]; LLM
      self-report/logprobs are a weak prior only. **Commands** accept only if intent-valid + evidence + ALL required params
      resolved (missing → CLARIFYING; unresolvable / no-evidence → abstain); **queries** accept on intent-valid + evidence.
      **DEPENDS ON QUAL-52** (the reworked, budget-aware LLM component — *not* its structured output, which was reverted).
      **Built 2026-06-16:** `irene/providers/nlu/llm.py` `LLMNLUProvider` — `_initialize_from_donations` builds the
      taxonomy + `parameter_specs` from the same donations; `recognize_with_parameters` makes one deterministic
      `LLMPort.generate_response` call, parses locally, and returns a plain `Intent` or `None`. Abstains on
      no-LLM / offline / unparseable / intent∉donations / evidence-not-in-text; else confidence = `0.7 + 0.25 × required-coverage`
      (a missing required param still clears the threshold → the handler's QUAL-30 `_clarify` asks — verified at
      `handlers/base.py:285,302`). Injection mirrors the conversation handler: `set_llm_component(LLMPort)`, soft-injected by
      `NLUComponent.post_initialize_coordination` via `core.component_manager.get_component('llm')` (no hard dep → no-LLM
      builds still start). `LLMNLUProviderSchema` registered + `[nlu.providers.llm]` (enabled=false, opt-in) + pyproject
      entry-point; default cascade unchanged. Arch = all (cloud HTTP is armv7-safe). Tests `test_llm_nlu.py` (13). Gates:
      suite 995 green, pyright 0, contracts 9/9 (provider→`intents.ports` is ARCH-4-legal), config-ui type-checks (Inv #4).
      **Unblocks ARCH-24 T4** (armv7 config can now use `keyword→llm`). Prompt wording is a first cut → **QUAL-51**.
- [x] **QUAL-51** [NLU][LLM] (P2) — **Prompt-tightening session for QUAL-50** (DONE 2026-06-16; interactive scope agreed
      with the user). Tightened the inline classifier system prompt: conservative "abstain when unsure" framing, an explicit
      JSON output contract + anti-hallucination (verbatim evidence), and the taxonomy + few-shot **filtered to the utterance
      language** (by script). Few-shot = hand-written **abstain** exemplars per language (the key last-resort lesson) +
      **auto-sourced positives** from each intent's donation `examples`. Kept the prompt **inline** (per the user's call) —
      it's *dynamically assembled* from donations (taxonomy + examples), so it isn't a static authored asset like the
      `assets/prompts/*` task prompts; `docs/guides/prompting.md` updated to document this one generated exception (Inv #10).
      Decisions: instructions **English-only** (LLMs follow them cross-lingually; taxonomy/utterance carry the language),
      classifier keys off the **input** language (`context.language`), not the system default. Tuned the
      `missing_parameter` clarification template (en+ru) — warmer, invites the answer. **Validation:** new live harness
      `scripts/eval_llm_nlu.py` + bilingual fixture `scripts/eval_llm_nlu_cases.yaml` (24 cases, real 54-intent taxonomy,
      DeepSeek via `.env`) — **24/24** after two fixture corrections (clear/fuzzy/missing-param/abstain/ambiguous all clean).
      Offline prompt-logic tests in `test_llm_nlu.py` (now 18). Gates: suite green, pyright 0, contracts 9/9. The
      keyword-matcher-feedback half is **not** automatable here → split out as **QUAL-53**.
- [x] **QUAL-52** [LLM] (P2) — **LLM component rework: real token budgets + budget-aware prompting** (surfaced 2026-06-15;
      **prerequisite for QUAL-50**; DONE 2026-06-16). Today's LLM handling used arbitrary/meaningless config knobs and was
      **token-budget-blind**. Reworked `llm_component` + providers (deepseek/openai/anthropic) + the LLM config schema:
      **(1) PR1 ✓** real **per-model token budgets** (`llm_capabilities` registry: context window + max output from actual
      model capabilities, dropping the arbitrary 150). **(2) PR2 ✓** **budget-aware prompting** — `estimate_tokens`
      (utf-8 bytes/4, dependency-free), `fit_messages` trims oldest/keeps system+final to fit the input budget;
      `context_window` exposed in config. **(3) PR3 ✗ REVERTED (2026-06-16):** first-class structured/JSON output
      (`generate_structured` + `response_format`) was built on a **wrong premise** — that the QUAL-50 NLU classifier returns
      a bespoke structured object. It does not: an NLU provider returns a **plain `Intent`**, param extraction is the
      provider's `extract_parameters` step, and catalog grounding is the **shared** `ContextualEntityResolver` downstream. So
      the classifier needs only a plain text call — no generic JSON-dict capability on the component (commit `beb08e3`).
      **(4) PR4 ✓** **dropped the unneeded fine-tuning** — `temperature` removed from schemas/config/providers (+ dead
      `top_p`/`frequency_penalty`/`presence_penalty`); providers now use a fixed deterministic `0.0`. **Invariant #4:**
      config-ui has no typed temperature field (free-form params dict) → nothing to sync, openapi unchanged. (QUAL-15/16
      console-LLM fallback / `fallback_providers` — left as-is; not in scope here.)
- [x] **QUAL-54** [APICONTRACT] (P2) `[release]` — **DONE 2026-06-27.** Targeted fix of the live-bug subset from
      `docs/review/api_result_contract_review.md` (F2 WS half + F5): the `/ws/audio` response now surfaces intent under
      `intent_name` (remapped from the orchestrator's `original_intent`, keeping the raw metadata) at both send sites
      (`webapi_router.py` streaming + batch), and the two `workflow_manager.py` pipeline-event emitters (`:482`,`:637`)
      now read `original_intent` instead of the never-populated `intent_name` (the field was always `None` in prod).
      Root masking cause fixed too: `test_pipeline_events.py`'s fake returned `metadata={"intent_name":…}` (wrong key) —
      now mirrors the real `original_intent` contract, so it's a faithful regression test. Unblocks the `eval/` WS
      intent case (provider reads `metadata.intent_name`). Gates: full suite 1066 passed / 9 skipped, pyright 0,
      import-linter 9/9. `config-ui-stays-functional` N/A (additive WS metadata + internal logging; config-ui doesn't
      consume `/ws/audio`). Full 5-way unification → QUAL-55.
- [x] **QUAL-55** [APICONTRACT] (P2) `[release]` — **DONE 2026-07-04. One canonical `IntentResult → API`
      serializer across the five execution surfaces** (retires F1/F3/F4 + the rest of F2,
      `docs/review/api_result_contract_review.md`). New `irene/api/serializers.py` →
      `serialize_intent_result(result, extra_metadata=None)`: canonical keys `text` (F1 — `/execute/*` renamed
      from `response`), `success`/`error`, `confidence` top-level (F4), `intent_name` lifted from the
      orchestrator's `original_intent` (F2), `timestamp`, raw `metadata` with endpoint extras merged IN, never
      replacing (F3). All five surfaces route through it: REST `/execute/command|audio` (`CommandResponse`
      reshaped: `text`/`confidence`/`intent_name` fields; the invented "executed successfully" fallback prose
      dropped — fail-loud ①), `/trace/command|audio` `final_result`, both WS `/ws/audio` response frames
      (supersedes QUAL-54's metadata-injection). Co-changes: **config-ui** `openapi.json` re-dumped +
      `openapi.gen.ts` regenerated, `npm run check` + `build` green (no runtime component consumed the old
      field); **eval-commons** `ws_audio_provider` reads top-level `intent_name` with metadata fallback (spans
      SUT versions). WS test fakes replaced with the real `IntentResult` (a wrong-shaped fake is how F5 hid a
      live None — same lesson). Tests: `test_api_result_serializer.py` (7); smoke e2e asserts the canonical
      keys against a live server. Suite 1180 green; 10 import contracts kept.
- [x] **QUAL-56** [QUAL][REVIEW][ARCH] (P3) `[deferred]` — **DONE 2026-07-02.** F&F design critiqued through the
      durable-execution lens + (user-requested) comparative analysis of `wb-mqtt-bridge` device-state persistence.
      Deliverable: `docs/review/faf_durable_execution_review.md`. Verdict: **zero on every durability axis by
      explicit design** — in-memory store ("NEVER persisted"), restart = silent total loss (a 24h timer vanishes;
      "list timers" denies it existed), no scheduler durability (`AsyncTimerManager` = dead capability), no
      idempotency (+ live-record overwrite on name collision), delivery at-most-once with 5 silent-drop points
      (failure notifications suppressed by default), retry machinery dead config, no recovery, aggregate-only
      amnesiac observability. Bridge comparison: right persistence shape to borrow (generic key→JSON SQLite behind a
      port, chokepoint dirty-write, ephemeral filter, reconcile-by-diff restore, shutdown-artifact protection) + two
      cautionary failure modes (persist-without-restore rot; stale `active_scenario` resurrecting on restart — filed
      to the bridge as **VWB-18**, uncommitted). User scope statements recorded: future handlers will require
      durability → platform substrate; "a fix + rules for new handlers would be required". Follow-ups filed:
      **ARCH-27** (substrate design + handler rules), **BUG-19** (store/status correctness), **QUAL-61** (dead
      capability removal, gated on ARCH-27's keep-or-cut).
- [x] **QUAL-57** [QUAL][REVIEW][ARCH] (P2) `[release]` — **DONE 2026-07-02.** **General architecture review +
      memory-overconsumption analysis** (user-requested). Deliverable: `docs/review/arch_memory_review_2026-07-02.md`.
      Method: 3 parallel deep-reads (architecture map / multi-turn memory audit / F&F QUAL-8 re-verification +
      `create_task` census); the 3 headline memory findings spot-verified directly. **Verdicts:** architecture =
      top-quartile for its class (enforced hexagonal layering — zero live violations, entry-point provider model,
      donation-driven NLU cascade, true streaming-ASR seam) but not SOTA at the interaction layer (no barge-in,
      whole-utterance TTS, no per-client concurrency isolation, weak session continuity — A1–A4 recorded for user
      decision, not filed). **F&F path now clean:** all 10 QUAL-8 findings resolved by the QUAL-28 store redesign
      (re-verified). **Live memory risk moved to the request path:** metrics session leak growing on every REST
      call/WS connection (→ BUG-16), uncapped `/ws/audio` batch PCM accumulator ≈115 MB/h per bad client (→ BUG-17),
      untrimmed LLM conversation store with dead `max_context_length` config (→ BUG-18); small-item sweep → QUAL-58;
      capability drift + dead code → QUAL-59. A5 (no action durability) confirms QUAL-56's premise — that task stands.
- [x] **QUAL-58** [MEM][QUAL] (P3) `[deferred]` — **DONE 2026-07-02.** Memory-hygiene sweep (QUAL-57 M4–M8), all five
      items: **(M4)** `AudioTranscoder._resampling_cache` now bounded by BYTES too — 4 MB total budget + 1 MB
      per-entry bypass (full TTS replies / long utterances are never cached; they were the tens-of-MB retention),
      FIFO eviction on either bound, `cache_bytes` in stats; **(M5)** `ClientRegistry.prune_stale_history(3600s)` —
      per-identity completed-action history keys (`_recent_actions`/`_failed_actions`/`_action_error_count`) are
      dropped once their newest entry is an hour stale (keysets grew monotonically with session-derived ids);
      **(M6)** the ContextManager cleanup loop (every `cleanup_interval`) now drives `reap_dead_actions()` (the
      advertised layer-3 sweep finally has a runtime caller — docstring corrected) + the M5 prune;
      `cleanup_expired_clients` deliberately stays manual — nothing refreshes `last_seen` on a live WS connection,
      so auto-expiry would unregister a live-but-quiet satellite (documented in its docstring); **(M7)**
      `NotificationService` queue bounded (maxsize 1000, `put_nowait` + drop-with-warning on overflow — never blocks
      the F&F completion path) and `send_notification` lazily starts the processing loop, killing the consumer-less
      getter-minted-instance path; the six provider `warm_up` preloads hold their task refs
      (`self._warmup_task` — were GC-cancellable mid-model-load); **(M8)** trace dir rotated to the newest
      `MAX_TRACE_FILES = 500` on every save (each file embeds full base64 audio; constant not config — same
      safety-net reasoning as BUG-17). Regression: `test_memory_hygiene.py` (7 tests across M4/M5/M7/M8);
      cache-stats shape test extended. Full suite 1139 passed / 7 skipped; pyright clean on all 11 touched files.
      Evidence: `docs/review/arch_memory_review_2026-07-02.md` §M4–M8.
- [x] **QUAL-59** [API][QUAL] (P3) `[deferred]` — **DONE 2026-07-02.** Capability drift + dead code (QUAL-57 A6/A7);
      user directive: dead code **removed**, not repaired. **(A6)** `/system/capabilities` now derives
      `nlu/voice_trigger/text_processing` provider lists from the loaded components' `providers` dicts and
      `workflows` from `workflow_manager.workflows` (the hardcoded lists advertised the long-gone
      `continuous_listening` workflow and missed the `llm` NLU provider); regression
      `test_capabilities_endpoint.py`. **(A7) deleted outright:** the domain-keyed dead Phase-3.5 action-management
      interface in `handlers/base.py` (`cancel_action`, `get_active_actions`, `get_action_status`,
      `list_all_actions`, `cancel_all_actions`, `inspect_action`, `get_action_management_capabilities` — would
      mis-cancel/double-record if ever wired; −300 LOC) plus the handler-side action-debugger wiring
      (`set_action_debugger`, attr, import; monitoring keeps its own debugger endpoints); the two `/intents/actions/*`
      REST stubs ("Full implementation requires session context") + their 3 orphaned schema classes; the zero-caller
      ContextManager introspection machinery (`get_context_for_intent_processing`, `get_recent_intent_patterns`,
      `get_dominant_domain`, `get_session_statistics`, `cleanup_session` — which also bypassed the BUG-16 metrics
      seam — `get_active_session_count`); the 2 tests that only exercised deleted methods. **Fixed (live code):**
      cwd-dependent paths in `nlu_component` now package-relative (handler dir from `handlers_pkg.__file__`, assets
      root from module parents). Stale `metrics.py` key comment was already fixed in BUG-16. **Contract artifacts
      regenerated** (endpoints removed → `scripts/dump_openapi.py` + config-ui `npm run gen:api-types`; apiClient
      never used the stubs). Gates: 1138 passed / 7 skipped; pyright clean on all 7 touched files; import-linter
      9/9 kept; config-ui `check` + `build` pass. Evidence: `docs/review/arch_memory_review_2026-07-02.md` §A6/A7.
- [x] **QUAL-60** [INTENTS][LLM] (P3) `[deferred]` — **✓ DONE 2026-07-19. Summarize-then-truncate for the LLM
      conversation window** (BUG-18 follow-up; the analysis session first established the two-layer budget
      reality: the turn window is the binding constraint, tokens never are — so the trigger stays at window
      overflow). Design executed: turns the BUG-18 window drops accumulate in a bounded pending buffer on the
      handler context (`trim_handler_messages` now RETURNS what it dropped; mid-list system machinery
      excluded); every `_SUMMARIZE_EVERY_MESSAGES` (=10, i.e. 5 turns) ONE LLM call folds them into a rolling
      summary — never a call per turn; the summary lives on the handler context, NOT in the message list, so
      neither the BUG-18 trim nor the QUAL-52 `fit_messages` layer can evict it, and it is injected at
      prompt-build time as the first context message via a new localized `earlier_summary` context label.
      Prompt: new `context_summary` asset in both languages (facts/names/decisions/open-threads brief, merge
      with prior summary, ≤5 sentences); the call is capped at `_SUMMARY_MAX_TOKENS=600` and sent role=user
      (the anthropic provider strips system messages). **Failure posture — degrade to BUG-18, never worse:**
      unavailable LLM / raised call → buffer kept (bounded at 40 messages, oldest fall back to plain
      windowing); and because the QUAL-15 chain never raises but returns the console floor's canned
      "unavailable" text on total failure, that exact text (compared against the same
      `assets/localization/llm` source the component seeds the floor from) is explicitly rejected as a
      summary. Cadence decision recorded: every-K (constant, no new config surface). Tests: new
      `test_conversation_summary.py` (6: trim-returns-dropped, one-call-per-K cadence, prompt injection with
      localized label, failure-keeps-buffer, console-floor rejection, buffer bound); `test_conversation_window`
      stub taught `is_available` (False — stays the pure BUG-18 test). Suite 1459 green; pyright 0 on both
      touched files. docs: none — no manifest node describes conversation-memory behavior. contracts: none —
      handler-internal; no wire surface moved.
- [x] **QUAL-61** [QUAL][FAF] (P3) `[deferred]` — **DONE 2026-07-02.** Dead-capability removal, all three cuts per
      ARCH-27 D-7 (user preference: dead code removed). **(1)** Retry machinery: `_execute_with_retry` +
      `_is_transient_failure` deleted (−98 LOC), `max_retries`/`retry_delay` launch params removed from both F&F
      launch methods, retry metadata keys dropped from the action record; **(2)** `AsyncTimerManager`: `core/timers.py`
      deleted + all wiring (engine ctor/attr/start/stop, composition root, `core/__init__` export, the
      `service_mapping['timer_manager']` entry) — the durable store + reconciler IS the scheduler (ARCH-28);
      **(3)** dead inspection path: `inspect_active_action` + `InspectionLevel`/`ActionInspectionResult`/
      `TestActionConfig` + vestigial history/test-action state removed from `debug_tools.py` (67 lines remain:
      `get_debugging_status` for the live `/debug` endpoint), `monitoring_component.get_action_debugger()` accessor
      removed; `NotificationMessage.retry_count`/`max_retries` fields removed (written, never read). Gates: 1156
      passed / 7 skipped; pyright clean (8 files); lint-imports 10/10.
- [x] **QUAL-62** [ARCH][QUAL] (P2) `[release]` — **DONE 2026-07-02 (filed + completed same day, user-requested
      ARCH-28 follow-up).** The new `DurableActionStorePort` seam is now reflected in the hexagon gate: 10th
      import-linter contract **"Durable-action store is reached only through its seam (ARCH-28)"** — no
      application/delivery/adapter layer (`components/workflows/providers/web_api/runners/inputs/outputs`) may
      import `irene.core.durable_actions`; the three sanctioned gateways (`intents.handlers.base` choke point,
      `core.engine` reconciler, `core.notifications` redelivery) are `ignore_imports` edges so chains THROUGH the
      seam pass while new direct imports fail. The contract proved itself during introduction: it flagged the
      transitive `webapi_router → notifications → durable_actions` chain until the gateway edges were sanctioned.
      Design doc D-2 annotated. Gates: lint-imports 10/10 kept; `test_import_contracts.py` green.
- [x] **QUAL-64** `[deferred]` [NLU] (P2) — **DONE 2026-07-05 (interactive). Keyword-matcher scoring tune** (filed from the first TEST-18
      device-suite run, 2026-07-05 — the matcher was NEVER tuned; user decision: leave the affected fixtures
      red and tune deliberately). **Evidence:** short verb phrases beat longer specific ones — «включи кино с
      видеокассеты» → `smart_home.power_on` 0.70 (should be `scenario_start`, phrase «включи кино»); «выключи
      кино» → `power_off` 0.72 despite `scenario_stop` carrying that EXACT phrase with boost 1.3 (boost does
      not overcome the short-phrase preference); both then dip under the 0.7 confidence threshold in the live
      cascade → `conversation.general`/LLM. **Scope:** phrase-length/specificity weighting + boost semantics in
      `hybrid_keyword_matcher` scoring; acceptance = TEST-18 fixtures F40/F42 green (`make device-auto`) with
      NO regression across the other handlers' routing (the suite + the WS suite are the safety net).
      Pairs with QUAL-53 (trace-driven improvement process — this is its first concrete, pre-collected case).
      **RESOLUTION (user chose specificity+boost):** the disease was a TIE, not weighting — every
      pattern hit in a method tier scored an identical constant, the stable sort broke ties by
      donation LOAD ORDER («выключи кино»: bare «выключи» beat the exact «выключи кино» by loading
      first), and the donation `boost` was never consulted in the pattern stage. New score:
      `pattern_conf × method_boost × (1+0.1×(tokens−1), cap 1.3) × donation_boost`; `intent_boosts`
      stored at load. F70's phrase workaround retired (fixture restored to «переключи субтитры» as a
      permanent regression). 15-case routing test over the full 14-donation set. **Acceptance
      exceeded: `make device-auto` 43/43 (100%)**; suite 1329, pyright 0. Bonus fence: the
      device-auto pkill needed the `[e]` bracket trick (it was killing its own recipe shell).
- [x] **QUAL-65** [PEX][MQTT] (P2) `[release]` — **DONE 2026-07-05 (filed + completed same day; user-requested
      intake: bridge VWB-19 landed input/app canonical routing — consume it before QUAL-35).**
      **Input switching + app launch by voice**, against the re-pinned contract @ bridge `3bed556` /
      catalog `dbfd2855` (`canonical_first.md` §11: `set` is the reserved canonical action for select-form
      capabilities). **eval-commons (`cc1cba9`):** re-pin (ru-labels guard refined — `labels: null` legal on
      by_value technical identifiers, non-null still requires ru); fixtures re-authored + **F50–F53**
      (by_value input / parametric input / app launch / «ютуб» transliteration-t2); the input-switching
      exclusion lifted; mock bridge serves `GET /devices/{id}/options/{kind}` (by_value → catalog keys,
      parametric → deterministic stand-ins). **Voice:** `read_options(device_id, kind)` joined
      `DeviceCatalogPort` — the QUAL-35 resolver-note-(1) `options_from` dance PULLED FORWARD
      (`CatalogService` 30s-TTL cache; `BridgeClient.get_device_options` fail-soft; composition-wired);
      handler `_handle_input_select` + `_handle_app_launch` share one option matcher built on the
      resolver's OWN normalization (`_norm`/`_stem_match` — one surface-matching truth); miss → clarify
      naming what IS available; donation methods + templates ru/en. 10 new tests (suite 1262, pyright 0,
      11 contracts; eval-commons 40). **Live: F50 green end-to-end** (by_value, zero round-trips); suite
      20/27 — F51–F53 red are NOT routing: the run exposed **QUAL-44 session-bleed** (an armed
      clarification consumes the next same-room case as its answer; matcher probe routes all three
      correctly at 0.75–0.79) → QUAL-44 un-deferred (user) + `make device` runs `-j 1` (shared per-room
      sessions make parallel cases inherent cross-talk). Guide updated (inputs/apps section + limits).
- [x] **QUAL-66** [QUAL][DONATION] (P3) `[release]` — **DONE 2026-07-05 (filed + completed same day,
      user-requested after asking what the "Contract wiring" warnings were).** **Contract-wiring
      warnings swept 21 → 0**, turning the loader's validator from ambient noise into a meaningful
      tripwire. Three families: **(1)** dead `language` globals removed from 9 donations (handlers read
      `context.language` since QUAL-36; the param was never consumed) + `conversation.session_id`
      (lives on the context per QUAL-27) — NOT touched: `system`/`speech_recognition`, whose `language`
      param is the TARGET language for switching, genuinely read (the validator's silence there proved
      the point; an over-eager first sweep removed them and the warning list itself caught the error);
      **(2)** `voice_synthesis_handler`'s declared-but-unread `provider` param removed (the handler
      parses it from raw text); **(3)** two internal helpers renamed off the `_handle_` prefix
      (`_do_language_switch`, `_fallback_without_llm`) — the prefix promises a donation entry, these
      are dispatched internally. Two tests updated (one had RELIED on the drift existing as its live
      example — now exercises the check with declare-nothing). Suite 1289 green; device suite 43/43.
- [x] **QUAL-67** [QUAL][CI][DONATION] (P3) `[release]` — **DONE 2026-07-05 (filed + completed same
      day, user-requested — the payoff of QUAL-66's zero baseline).** **Donation validation is now a
      build + CI gate:** new `irene-donation-validate` (`irene/tools/donation_validator_cli.py`) runs
      the exact runtime validation (schema strict + `validate_contracts`) over EVERY donation
      directory under `assets/donations/` (module-aware discovery — handler modules are inconsistent
      about the `_handler` suffix) with **warnings-as-errors**: a declared-but-unread param or an
      undeclared `_handle_*` method now FAILS the build instead of scrolling past in a boot log.
      Wired into `ci.yml` backend-health beside the config/dependency/build-analyzer gates (gates
      every image publish = the build gate). Verified both ways: green on the clean tree
      (14 handlers, 86 methods, 0/0), red on an injected canary param. Suite 1289 green.
- [x] **QUAL-69** `[release]` [MQTT] — **DONE 2026-07-06 (filed + completed same day). Consume the bridge's
      open-questions catalog patch: wardrobe_spots ru alias «свет» (catalog `a17a63b0` → `acc1e18b`,
      bridge commit `aa031d2`).** Inward re-pin of all three artifacts (catalog + STAMP + openapi — the
      openapi also picked up the committed canonicalAction/Capability/Param schema rename we hadn't synced);
      PIN.json stamped. Voice-side analysis: NO code change — the depth doctrine is ordering-protected (the
      group-noun check precedes device resolution on every path, incl. the Slice-3 `_group_for_surface` and
      `scan_utterance` legs), so a device carrying the group noun as an ALIAS cannot demote «свет» to
      device-form. **New fixture F17** («включи свет в гардеробе» → room-group wardrobe/light/auto) pins
      that interaction; guard 8/8, device tier-1 gate **48/48**.
- [x] **QUAL-70** `[release]` [UX][CLI] — **DONE 2026-07-06 (filed + completed same day, user request).
      Clean REPL: interactive runners log to file + trace only.** Two console-noise sources silenced for
      the CLI: (1) the root console handler — `_setup_logging` now keys `enable_console` off
      `supports_interactive` (CLI off, WebAPI/voice unchanged); `--debug` deliberately brings console
      logs back; (2) the embedded background uvicorn — `_serve_in_background` builds it with
      `log_config=None` + `access_log=False`, so its loggers propagate to the root handlers (file)
      instead of scribbling over the prompt; the FOREGROUND webapi server is untouched (docker logs
      depend on it). Verified live: `irene-cli -c configs/config-example.toml` shows banners + replies
      only; `logs/irene.log` carries the full log; `--debug` restores 500+ console lines. Suite 1300,
      pyright 0.
- [x] **QUAL-71** `[release]` [I18N] — **DONE 2026-07-06 (filed + completed same day). Hardcoded Russian
      reply strings swept out of handlers → templates.** Seven literals found (5 in conversation.py — incl.
      the «справочный режим недоступен» the user hit — plus datetime + greetings error fallbacks); all now
      resolve through the template system (ru + en authored; new `assets/templates/datetime_handler/`).
      Error-path nuance: a template call inside an `except` must never mask the ORIGINAL failure — new
      `_template_or(name, lang, fallback)` base helper: localized when assets are healthy, last-resort
      literal when the template system itself is broken (a unit test caught exactly this).
- [x] **QUAL-72** `[release]` [PROCESS] — **DONE 2026-07-06 (filed + completed same day; user caught the
      drift). `check_scope.py` now flags STRANDED completions** — a `- [x] **ID**` task entry still in the
      ACTIVE plan is a `single-task-ledger` violation (completion must MOVE the entry to the done-archive in
      the same change), and the gate silently accepted it: three same-day completions (BUILD-12, ARCH-33,
      REL-3) were flipped in place instead of moved, and every gate run since passed. Entries moved; the
      guard now fails on the class (canary-verified both directions). The gate that exists to catch drift
      must catch the maintainer's own drift first.
- [x] **QUAL-73** `[release]` [PROCESS] — **DONE 2026-07-06 (filed + completed same day; user caught it,
      second guard-hardening of the evening). Tasks filed into WRONG workstream sections** — BUILD-13 landed
      under ARCH (filed in-place at ARCH-35's completion) and BUG-29 at the tail of QUAL in the done file
      (the insert-before-next-header pattern drops entries into the PRECEDING section). Both moved.
      `check_scope.py` now fails on any ID-prefix / enclosing-section mismatch in EITHER ledger file
      (canary-verified), and CLAUDE.md's `single-task-ledger` states the section rule explicitly. Same
      lesson as QUAL-72: conventions the maintainer can violate under tempo must be machine-checked.
- [x] **QUAL-74** `[release]` [PROCESS] — **DONE 2026-07-06 (filed + completed same day; the user's THIRD
      ledger-discipline catch of the evening). Sections now sort ascending by ID, gate-enforced.** The
      done-archive had grown in completion order (56 ordering violations, most historical) and the day's
      in-place filings added more in the active file. Convention SET (user): entries ascend by ID within
      each workstream section, both files; a completion is INSERTED at its sorted position, not appended.
      Both files mechanically resorted (205 entries, zero loss — asserted), `check_scope.py` fails on
      out-of-order IDs (canary-verified), CLAUDE.md `single-task-ledger` states it. Completes the evening's
      guard triad with QUAL-72 (stranded [x]) + QUAL-73 (misfiled sections).
- [x] **QUAL-75** `[release]` [MQTT] — **DONE 2026-07-06 (filed + completed same day). Consume the bridge's
      contract v1.4 (VWB-28): re-pin @ `fc8eb31`** — openapi gains `POST /reports` + `GET /reports/evidence`
      with the **`EvidenceEnvelope`** schema (the B-11 read seam our ARCH-34 amendment asked for, delivered
      same-day); catalog golden byte-unchanged (`acc1e18b`) so all 48 device fixtures stand untouched;
      eval-commons guard 8/8. **ARCH-34's dependency gate is now LIFTED** — the endpoint exists and its
      envelope is pinned; ARCH-34 stays `[deferred]` by the v1.1 scope decision, but activation is now
      pure voice-side work (bounded call + `bridge/` bundle subtree + envelope-pin expectation).
- [x] **QUAL-76** `[release]` [MQTT] — **DONE 2026-07-07 (filed + completed same day). Consume the bridge's
      rack-verified catalog: re-pin @ `8159b4b0` (bridge `40f0452`)** — auralic gains a `previous` action,
      zappiti power becomes a **toggle** (was on/off); openapi unchanged, contract stays v1.4. Zero crossover
      fixtures bind the changed devices, so only the fixtures doc's `catalog_version` stamp moved. **Bonus
      catch:** QUAL-75's PIN.json had recorded the bridge repo HEAD in `bridge_commit` instead of mirroring
      `STAMP.bridge_commit` (the generator's commit), leaving eval-commons' `test_pin_matches_stamp` guard
      red unnoticed — convention restored, eval-commons suite 40/40 (eval-commons `14ac383`).
- [x] **QUAL-77** `[release]` [MQTT] — **DONE 2026-07-08 (filed + completed same day). Consume the bridge's
      DRV-5/SCN-11 desync-repair contract surface: openapi re-pin @ bridge `c32068e`** — `CanonicalActionResponse`
      gains `skipped_reason` (idempotence-skip marker: nothing transmitted, belief may be wrong), `force` becomes
      a reserved param bypassing idempotence guards, and two scenario endpoints land (`reconcile_preview` /
      `force_reconcile`). Pure additions (+317 lines); catalog + STAMP byte-unchanged so `PIN.bridge_commit`
      stays per the guard convention; eval-commons 40/40 (`7cfd5a7`). Voice-side adoption analyzed with the user
      (bridge maintainer's handoff note) and filed as **ARCH-39** (device-level 2-turn force-confirm) +
      **ARCH-40** (scenario force-reconcile via voice), both `[deferred]` post-release design tasks.

- [x] **QUAL-78** [OPS] `[deferred]` — **DONE 2026-07-14. The container healthcheck spams the log with one
      access line per probe.** Since the honest `HEALTHCHECK` landed (ARCH-25, 2026-07-09) uvicorn
      access-logged every probe: `INFO: 127.0.0.1:… - "GET /health HTTP/1.1" 200 OK` every 30 s, forever —
      ~2.9k lines/day drowning real events and burning the BUG-30 rotation budget. Fix as prescribed: a
      `logging.Filter` on `uvicorn.access` (`_HealthProbeAccessFilter`, `runners/web_server.py`) dropping
      2xx `/health` **and** `/ready` (covered ahead of ARCH-45), installed in `_build_uvicorn_server` — the
      single choke point both serve paths share. Non-2xx probes stay visible (a failing probe is exactly the
      event worth seeing); query strings don't unhide a probe; exact paths only (`/healthz` etc. unaffected).
      One subtlety the live verification caught: the filter must attach AFTER `uvicorn.Config(...)` — its
      `__init__` applies uvicorn's dictConfig, which resets the `uvicorn.access` logger's filters (attached
      before, the filter is silently wiped). Verified against a real uvicorn server driven through
      `_build_uvicorn_server`: two 200-probes dropped, a normal 200 request and a 503 probe both logged.
      6 new tests (`test_web_server_logging.py`, incl. no-duplicate-on-rebuild); suite 1415 pass / 7 skip;
      pyright clean on the changed files.
      docs: none — removes internal log noise; no manifest doc describes access-log contents.
- [x] **QUAL-80** [MQTT][TEST] `[release]` — **DONE 2026-07-09.** Golden catalog re-pinned
      `8159b4b0068d1c63` → **`16eee0f2f7832995`** (bridge commit `9714c3c3…`), at the bridge's request. Both
      driving fixes came out of the WB7 bring-up: **DRV-23** — WB-passthrough devices now expose feedback at
      top-level `state.<field>`, the read path voice depends on (`mqtt_integration.md` §5c), with the internal
      `mirrored` bucket retired; and **DRV-25** — `power` becomes a *readable* field on the 39 relay-switch
      devices, canonical `on`/`off`. Verified before pinning rather than trusting the request: golden's own
      `version` is `16eee0f2f7832995`; **39 of 79** devices changed, each gaining a `fields` entry on the `power`
      capability (enum, wire `"1"/"0"` → canonical `"on"/"off"`, ru/en labels); no devices added or removed;
      zero `mirrored` occurrences remain; `openapi.json` byte-identical, so it was not re-copied and config-ui's
      generated types are untouched (`config-ui-stays-functional` needs nothing). One-way inward sync per
      `cross-repo-source-of-truth`; `PIN.bridge_commit` mirrors `STAMP.bridge_commit`, never the repo HEAD
      (`cc5d4b4`) — the convention `test_pin_matches_stamp` guards, and which QUAL-75 once broke. Fixture stamp
      bumped; no fixture binds capability `fields`. eval-commons `5427063`: suite 40/40, pin guards 10/10.
      Voice side: `parse_catalog` reads the new shape (`cabinet_spots` `power` → `enum` field), unit suite 1358
      pass, and the change is purely additive — `_QUANTITY_FIELDS` still searches only `temperature`/`humidity`.
      **Not yet live:** the WB7 serves the old catalog until the bridge image is rebuilt and redeployed; a sensor
      read and a switch read want re-verifying against the controller afterwards.

- [x] **QUAL-81** [MQTT][TEST] `[release]` — **DONE 2026-07-10.** DRV-28 HVAC contract consumed: golden
      re-pinned `16eee0f2…` → **`5622ba7a1a78102a`** (bridge `eef4e8cc…`; one pin covers their DRV-25/26/28 arc),
      and the HVAC intent mapping moved off hardcoded `climate.*`. The three ACs are `MitsubishiHvac` with six
      capabilities (`power`, `mode`/`fan`/`vane`/`widevane` `.set{value}`, `temperature.set{value}` 16–31 °C);
      floors keep `climate`. Verified against their committed artifacts before pinning: exactly the 3 `*_hvac`
      devices changed, openapi +1 schema (`MitsubishiHvacState`).
      Voice: a per-device **binding table** (`_SETPOINT_BINDINGS`/`_CHOICE_BINDINGS`, new dialect first, old as
      fallback) drives `_handle_set_setpoint` and `_hvac_choice`, so the handler is correct against EITHER live
      catalog — the bridge's WB7 redeploy is still owed, and deploy order must not matter.
      `_single_capable_or_clarify`/`_capable_devices` accept an any-of capability tuple (set-temperature is
      `climate` on a floor, `temperature` on an AC — exactly fixture F21's clarify). `_QUANTITY_FIELDS`
      unchanged: `shower_sauna_sensors` still carries a `temperature` field that IS the measurement; the AC's
      old `temperature` field was its SETPOINT, so «какая температура» in an AC room had been answering the set
      target — a latent wrong answer the DRV-28 rename itself retired (comment records it).
      eval-commons (`ee66fd8`): fixtures migrated with the contract (F80→`mode.set{value:cool}`,
      F81→`fan.set{value:speed_2}`, F96→`temperature.set{value:22}`, F32's hvac read target →`temperature`);
      **F21 exposed a fixture-schema gap** — its two clarify candidates now bind different capabilities, so the
      clarify expect's `capability` accepts a list ("every candidate carries at least one of these") with the
      guard test updated; suite 40/40. Voice tests: the harness stub migrated to the DRV-28 shape (all 47
      existing tests pass against it — F21's clarify spans both dialects through the any-of picker), plus 7 new
      (new-dialect setpoint/mode/fan incl. the ru-label match, range check on the `value` spec, and a
      `children_split_legacy` old-dialect device proving the fallback). **Notable: no mode/fan handler tests
      existed at all** — the same blind spot that let the firmware drop every mode command (their DRV-26).
      pyright 0, import-linter 11/11, suite 1373. Heads-ups logged, no voice action: bridge VWB-32 (retained
      catalog-version topic wiped by the reboot), VWB-33 (language-data ownership design — half ours, they
      coordinate). **Hardware smoke owed AFTER the bridge's WB7 redeploy:** «включи кондиционер в детской» →
      `power.on`; a mode change → `mode.set` (dead firmware-side until DRV-26); «какая температура в детской» →
      `room_temperature`.

- [x] **QUAL-83** [QUAL][CONFIG] `[release]` — **✓ DONE 2026-07-16. Dead config-field + dead-code sweep**
      (ARCH-50 §B/F-F3; every deletion re-verified by grep before removal). **Config fields deleted (~30):**
      the whole `AssetConfig` download/cache block (11); `DateTimeHandlerConfig` + `GreetingsHandlerConfig`
      whole (+ their `IntentSystemConfig` fields + validator-map entries); 4 of 5 `ContextualCommandsConfig`
      (`latency_threshold_ms` stays — the one read); 5 `MonitoringConfig` (`debug_tools_enabled` +
      `notifications_default_channel` verified LIVE and kept); 3 `NLUAnalysisPerformanceConfig`;
      `NLUAnalysisLanguagesConfig` whole — and the capabilities endpoint now reports the CANONICAL
      top-level language policy set at initialize (QUAL-36) instead of a `["ru","en"]` literal; singles:
      mic `auto_resample`/`resample_quality` (+ dead validator), `VoiceTriggerConfig.buffer_seconds`/
      `strict_validation`, `NLUConfig.persist_language_preference`, `VADConfig.processing_timeout_ms`,
      workflow `monitoring_enabled`/`enable_vad_processing`, web `websocket_enabled`/`rest_api_enabled`,
      CLI `prompt_prefix`/`history_enabled`. **Dead code deleted:** `get_provider_capabilities` (PROD-8
      delegation discharged), `EnhancedHandlerManager` (63 lines incl. the third file-scan discovery
      mechanism), `ComponentRegistry`+`ComponentLoader` (+ config exports), `add_handler`/`remove_handler`
      + the legacy `_get_handler_patterns` (donation-less registration now raises explicitly;
      `reload_handlers` stays). **Orphan TOMLs deleted:** vad-development/vad-production/vad-testing/
      vosk-test; `full.toml` deleted too — `test_audio_negotiator.py` repointed to
      `standalone-x86_64.toml` (same mic-16k role; 22/22 green). TOML template generator + all live TOMLs
      stripped (one over-strip — `[asr]`/`[voice_trigger]` `resample_quality`, still model-live — caught
      by the master-completeness gate and restored); `config-ui/openapi.json` re-dumped, types
      regenerated, `api.ts` trimmed; check + build green. Verified: full suite 1411 passed / 7 skipped,
      config-validator CI-mode all valid, master-completeness valid, import contracts 11/11.
      **Discovered en route → filed QUAL-85 [deferred]:** `config/schemas.py` parallel schema tree;
      ASR/VT resampling fields whose only reader (`resolve_audio_config`) is itself caller-less; api.ts
      hand-interface drift. docs: guides/vad — the `processing_timeout_ms` row removed from the [vad]
      field table (the field is gone); no other manifest node describes deleted fields.
- [x] **QUAL-85** [QUAL][CONFIG] `[deferred]` — **✓ DONE 2026-07-19. The parallel schema tree derived away,
      the dead resampling chain deleted whole, api.ts config types now generated-only** (filed at QUAL-83;
      owner intake rulings 2026-07-19: delete the chain / derive api.ts from `openapi.gen.ts`).
      **(a) component schemas are now DERIVED, not maintained:** the hand-written
      `<Name>ComponentSchema` tree in `config/schemas.py` (drifted: QUAL-83-deleted `dashboard_enabled`
      still declared, `wake_words` as bare strings predating `WakeWordSpec`) is deleted;
      `AutoSchemaRegistry._find_component_schema` now returns the component's REAL CoreConfig section
      model (components and sections share names), so models.py-drift in component schemas is
      structurally impossible. `configuration` is the one flag with no section — declared in an explicit
      `_SECTIONLESS_COMPONENTS` allowlist. `SchemaValidator` + the `SchemaVersion` machinery (major=14
      relic) deleted with it — zero runtime callers; `config/__init__` exports trimmed;
      `test_config_schemas.py` rewritten to assert the derivation (schema IS the section model;
      bare-string wake words now correctly REJECTED). Provider schemas stay hand-written by design —
      they are the authority behind the parameter forms, with no models.py counterpart to drift from.
      **(b) the dead chain — BIGGER than filed:** not just `resolve_audio_config` — the ENTIRE
      `config/validator.py` (956 lines: ArchitectureValidator + AudioConfigurationValidator +
      ConfigurationError/FatalConfigurationError) had zero importers, zero dynamic references, no entry
      point; deleted whole per the standing dead-code rule (the live validation paths are
      `core/startup_validation.py` + the coherence/schema gates). With it: the 4
      `allow_resampling`/`resample_quality` fields on ASRConfig/VoiceTriggerConfig (+ validators),
      `audio_helpers.validate_cross_component_compatibility` + `validate_startup_audio_configuration`
      (only called from the dead class), 5 config-master.toml lines + 2 stale guidance comments.
      Knock-on caught by the coherence guard: `AssetConfig.auto_create_dirs`'s only *visible* reader was
      the dead validator — it is honored by AssetConfig's own `model_post_init` (models.py is outside
      the guard's corpus), allowlisted with that reason.
      **(c) api.ts config interfaces derive from the generated types:** the 30 hand-written config
      interfaces (`CoreConfig`…`UnifiedVoiceAssistantWorkflowConfig` + `WakeWordSpec`) replaced with
      `export type X = components['schemas']['X']` aliases over `openapi.gen.ts` — the phantom `vad`
      flag and missing `configuration`/`nlu_analysis` drift class is gone for good; `openapi.json`
      re-dumped + types regenerated (the diff = exactly the 4 deleted resampling fields); `npm run
      check` (type-check + strict lint + orphans) and `npm run build` green on first pass — proof the
      derived types are drop-in. Verified: full suite 1452 passed / 7 skipped, config-validator CI-mode,
      import contracts 11/11, pyright 0 on touched files. docs: guides/audio (stale `resample_quality`
      sentence — the knob no longer exists anywhere — replaced with "resampling is automatic").
      contracts: none — repo-internal config/schema surfaces; no stamped family moved (openapi.json is
      generated, not a contract pin).
- [x] **QUAL-86** [NLU][TRACE] `[deferred]` — **✓ DONE 2026-07-20 (filed + completed same session; the
      QUAL-53 prerequisite split out as its own task — owner ask).** **The NLU cascade trace now records
      per-provider attempts, not just the final result.** The gap QUAL-53 named: `nlu_cascade`'s
      `cascade_attempts` was a fake — one final-result entry appended around a black-box
      `recognize_with_context` call, so a recorded trace could not explain WHY an utterance fell through
      to the LLM tier. Now `_try_provider_recognition` returns `(intent, attempt_record)` — provider,
      `outcome` (recognized / low_confidence / no_intent / unavailable / error), the confidence + the
      per-provider threshold it was judged by, `duration_ms`, the error string, and — the QUAL-53 gold —
      for low-confidence abstentions the `intent_name` the tier WOULD have guessed. `recognize()`
      collects the records and ships them on the `entities["_cascade_trace"]` transport key (set on both
      the winning intent and the fallback intent — the fall-through story is the whole point);
      `process()` pops the key into the stage metadata (its real home; also `final_provider` added) on
      the traced path and strips it on the fast path, so the message surface is unchanged either way.
      Trace-format impact: additive metadata inside an existing stage — `trace-format-doc-canonical`'s
      own rule (additive keys keep the version; the reference describes stage payloads generically) means
      no doc edit, no version bump. QUAL-53's entry annotated: prerequisite discharged, the analyzer
      remains data-gated. Tests: new `test_nlu_cascade_trace.py` (5: low-confidence guess recorded,
      fall-through story on the fallback intent, unavailable-not-silent, traced-path pop, fast-path
      strip; `test_cascading_nlu` harness reused). Suite 1464 green; pyright 0.
      docs: none — tracing.md describes stage payloads generically and its additive-keys contract covers
      this. contracts: none — trace-format additive, version stays 1 per the STAMP rule.
### Bugs (BUG)
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
### Tests (TEST)
- [x] **TEST-0** (P0) — Minimal end-to-end smoke/integration harness (refactor safety net, Gate 0). **DONE
      2026-06-01** → `irene/tests/test_smoke_e2e.py` (**5 passed / 1 xfailed**, ~21s; boots the WebAPI runner once
      as a subprocess + a CLI headless check). Green flows: WebAPI boots, `привет`→`greeting.hello`, `/nlu/recognize`
      responds, LLM-offline conversation degrades gracefully (200, no crash — guards QUAL-14/15), CLI headless
      executes. ~~**xfail:** `test_set_timer_end_to_end`~~ — **now a real PASS** (the timer breakage closed: QUAL-9
      F&F via QUAL-28 + QUAL-11 Stage A recognition fix, 2026-06-03); the smoke suite guards it green. **New finding via TEST-0:** `поставь таймер на 5 минут` is **not recognized** (falls to
      `conversation.general`) *despite the timer donation being loaded* — a recognition/matching gap → logged under
      QUAL-11. So timers are **doubly broken** (recognition AND the F&F launch crash). Still TODO: wire into CI (BUILD-2).
- [x] **TEST-1** (P1) — Fix broken tests referencing removed/renamed symbols. **DONE 2026-06-01**:
      `ConversationContext`→`UnifiedConversationContext` (rename); `TTLCache`/`ContextualCommandPerformanceManager`/
      `initialize_performance_manager` were **deleted** (v13→v15 contextual-command unification) → those tests
      skipped-with-reason; `Intent.text`→`raw_text`, `ComponentConfig.audio_output`→`audio` renamed in tests.
- [x] **TEST-2** (P1) — **DONE 2026-06-15 — SUBSUMED BY TEST-7.** The deliberately-paused suite-stabilization is
      complete: TEST-7 rewrote/deleted the drifted clusters and greened the suite (the `56→82 failed` drift this task
      tracked is now `0 failed`). Closed as subsumed. _Original paused note below._ **PAUSED 2026-06-01 (deliberate — see strategy note).** Suite now **runs** and is a
      partial safety net: 136/100/0 → **166 passed / 56 failed / 13 skipped / 2 xfailed** (committed). Cleared:
      async config, symbol renames, obsolete skips, hardcoded-path bug, and the fixture-wiring cluster. The
      remaining 56 drift failures are **left unfixed on purpose** (will be obsoleted by ARCH/review then rewritten,
      TEST-7). Diagnosed-but-not-fixed clusters (for whoever does the rewrite): `test_cascading_nlu`
      provider-metadata (`entities["provider"]` vs `_recognition_provider`, ~7 — design-intent question),
      VAD/ASR metrics dict-vs-object (~8), `spacy_asset_integration` mock-vs-MagicMock (2), attr renames
      (`IntentResult.error_type`, `SpaCyNLUProvider.model_name`, `IntentRegistry._handlers`,
      `IntentComponent.get_system_status`), phase4 contextual-command + assertions. Value already banked:
      **QUAL-21**, **QUAL-22**, text_processor trace fix.
- [x] **TEST-3** [FAF] (P2) — **DONE 2026-06-15.** Fire-and-forget lifecycle coverage. The store + happy launch→complete
      path were already covered (`test_action_store.py`, `client_registry` 76%); added `test_fire_and_forget_coverage.py`
      (11 tests) for the previously-uncovered `IntentHandler` F&F machinery: launch-registers, completion-reaps-and-records-
      success, **error** → failure history, **cancel** → "cancelled", **launch-failure** → failed metadata, timeout-monitor
      register+reap, `cleanup_timeout_tasks`, metrics start/completion, notification scheduling (owned vs no-session), and
      the handler `cancel_action`/`get_active_actions`. **`handlers/base.py` 45%→52%** (and the whole F&F lifecycle
      launch→complete→error→cancel→cleanup is now exercised). Hermetic (object.__new__ handler, fresh patched
      ClientRegistry, asyncio.run). No product bugs surfaced. The deferred-result *delivery routing* through the
      OutputManager (ARCH-15) stays integration/smoke-level. Suite green (901 passed, plain pytest).
- [x] **TEST-4** [PEX] (P1) — **DONE 2026-06-15.** Parameter-extraction coverage. Its named scope is now covered:
      **the 8 ParameterTypes** via `HybridKeywordMatcher._extract_by_type` (INTEGER/FLOAT/BOOLEAN/CHOICE/DURATION/STRING
      branches + DATETIME/ENTITY fallthrough) + `_convert_and_validate_parameter`/`validate_config`
      (`test_param_extraction_coverage.py`), and **the 4 entity resolvers** Temporal/Quantity (pure parsers, full) +
      Device/Location (graceful degradation with no asset loader — verifies the QUAL-11 P0 #4 fix; the review's old
      fatal-crash is gone) (`test_entity_resolver_coverage.py`). 18 tests; `hybrid_keyword_matcher` 0%→19%,
      `entity_resolver` 62%→79%, `donations` 87%→89%. No product bugs surfaced. The remaining ~80% of
      `hybrid_keyword_matcher` (the donation-driven keyword/fuzzy `recognize()` pipeline) needs loaded donations + spaCy
      and is integration/smoke-level — out of TEST-4's "8 ParameterTypes / 4 resolvers / pattern-matching" unit scope;
      `spacy_provider` (21%) is mostly the review-confirmed dead Matcher/EntityRuler code (not worth chasing).
- [x] **TEST-5** [TXTPROC] (P2) — **DONE 2026-06-15.** Text-processor / normalizer coverage. The provider
      (`UnifiedTextProcessor`) was already covered by `test_text_processing.py`; added `test_text_normalizers_coverage.py`
      (11 tests) for the actual normalizers + the component's live methods: **NumberNormalizer** (ru digit→words,
      no-number passthrough, empty), **PrepareNormalizer** (pure-Cyrillic fast passthrough / Latin→Cyrillic transcription /
      inline number processing / `changeLatin=skip`), **RunormNormalizer** missing-dependency degradation (no model
      download), and `TextProcessorComponent.process` no-provider passthrough + `convert_numbers_to_words`. **`text_normalizers.py`
      25%→58%**; `text_processor_component` 29%→30%. Reconciliation (Invariant #8): the `text_processing_review.md`
      "process() hardcodes the general stage" finding was fixed by **QUAL-13** (`process(..., stage="asr_output")` routes
      by stage now). No product bugs surfaced. The remaining component % is the review-confirmed **dead** stage routing +
      the broken text-processing WebAPI (a known QUAL-12 finding) + `RunormNormalizer`'s model path (offline hazard) —
      deliberately not chased.
- [x] **TEST-6** (P2) — **DONE 2026-06-15 (TEST-7 Phase C/D).** ASR provider-fallback + resampling coverage restored:
      the `test_phase7_performance` resampling-latency tests were rewritten to `AudioProcessor.resample_audio_data`
      (`audio_processor.py` 71%), and the ASR provider-selection/fallback surface is covered by `test_asr_component_coverage`
      (`asr_component.py` 46%; the new test file 98%). Individual ASR providers' model-loading internals stay uncovered
      (smoke/model territory) — out of TEST-6's fallback+resampling scope. _Original:_ Restore ASR provider-fallback +
      resampling coverage (the 7 phase7 tests skipped in TEST-1 called the removed `_handle_sample_rate_mismatch`).
- [x] **TEST-7** (P1) — **DONE 2026-06-15 — suite rewritten + 100% green; coverage 45.6%→52.3%; full-suite pytest is
      now a hard CI gate (`backend-health.yml`).** Residual deep-pipeline coverage (`workflow_manager` 29%, `context`
      31%) accepted as integration/smoke-level (user-approved). Phases A–D below. Gate lifted** (ARCH-1..5 ✓ + QUAL-8/10/12/14 ✓ all `[x]`). Rewrite the
      test suite against the stabilized architecture; absorbs TEST-2 (the paused suite) + the coverage goals
      TEST-3/4/5/6/8. **Approach LOCKED with user 2026-06-15 (6 decisions):** (1) **same method as the release-plan
      new-code** — contract-level unit tests at the ports/seams (`object.__new__`/`SimpleNamespace`, test the
      off-paths, co-located), smoke (`test_smoke_e2e`) as the e2e backstop; (2) **100% green** (no xfail tail);
      (3) **delete** stale tests outright; (4) **all clusters in one sweep** (incl. the new-code wiring gaps —
      `replay_trace`/`voice_runner`/trace wiring); (5) **Phases A+B solo, then a multi-agent workflow** for the bulk
      rewrite/coverage (C/D); (6) **`pytest-cov` + closing the coverage gap is MANDATORY** (measurement is part of DoD).
      Triage rule per failing test: behavior gone → delete; behavior live but asserts a drifted internal → rewrite to
      the port/public contract; test right, code wrong → fix the code (TEST-1/2 banked QUAL-21/22 this way). **Phase A
      DONE 2026-06-15:** added `pytest-cov` + `pysqlite3-binary` (the runtime CPython 3.11.4 is built without stdlib
      `_sqlite3`, which coverage needs — mirrored wb-mqtt-bridge's pysqlite3 alias via a committed `sitecustomize.py`
      + `scripts/install_sqlite_shim.sh`; pinned `.python-version` 3.11.4 locally to stop a 3.12 drift). **Baseline
      coverage = 45.6% lines (17,546/38,488), 265 modules.** Confirmed the thesis: the request hot-path is the cold
      zone (`workflow_manager` 20%, `core/components` 20%, `context` 25%, `asr_component` 25%, `nlu_component` 38%,
      `orchestrator` 41%, `voice_assistant` 48%), while new pure-logic is well-covered (`trace_context` 76%,
      `trace_input` 89%) but new wiring is thin (`replay_trace` 34%, `voice_runner` 34%). Suite baseline restored at
      82 failed / 472 passed / 15 skipped (the ±1 is a coverage-perturbed timing benchmark). **Phase B DONE
      2026-06-15 → `docs/review/test7_triage.md`:** triaged all 82 failures into ~28 delete / ~50 rewrite / 3 fix-code,
      and risk-ranked the cold spine into Tiers (Tier-1 = `workflow_manager` 20%, `core/components` 20%, `nlu_component`
      38%, `context` 25%, `voice_assistant` 48%, `asr_component` 25%, + the 5 capability handlers/TEST-8). Biggest
      cluster (phase4 contextual, 21) = DELETE (built on the deleted perf-manager; behavior re-covered fresh). 3
      real-bug suspects surfaced: a machine-specific `device_id = 7` hardcoded in `config-master.toml` (Invariant #2),
      `llm.console` empty param schema, and a VAD-requirement error-message contract (touches QUAL-46). **NEXT: Phase
      C/D = the multi-agent workflow** (green the suite per-cluster, then coverage-fill per Tier-1 module). Done when:
      100% green + Tier-1 cold subsystems covered (confirmed by pytest-cov). **Phase C (green the suite) — bulk DONE
      2026-06-15 via a 19-agent workflow + verifier:** deleted 4 stale files (phase4 ×3 + phase6) and rewrote 13 drifted
      clusters to current port/public contracts (net −3,555 test lines; spot-checked genuine, not gamed). Fixed an
      order-dependent event-loop failure in `test_no_intent_clarification` (`asyncio.get_event_loop().run_until_complete`
      → `asyncio.run`; passed alone, failed in-suite). **Suite 82→3 failed / 555 passed.** The remaining **3 reds are
      the 2 fix-code decisions surfaced to the user** (per the rule: never fix product code autonomously): (a) `device_id`
      in `config-master` — the alignment test wants `device_id`→`device` but the model still uses `device_id`; +
      machine-specific `= 7` value; (b) `llm.console` empty parameter schema (offline-floor stub) flagged by 2 tests.
      **Phase C COMPLETE 2026-06-15 — suite 100% GREEN (558 passed / 0 failed / 7 skipped, from 82 failed).** User
      decided both fix-code questions as test/config fixes (no product-schema change): (a) `device_id` is the live
      `MicrophoneInputConfig` field (the `→device` rename was never done) → dropped from the alignment test's
      deprecated-names list + cleaned the machine-specific `device_id = 7` to the `None` default in `config-master`;
      (b) `llm.console` is a *registered* offline-floor stub (entry-point exists) with no runtime params by design →
      exempted declared stubs in the schema test (like text-processors) + rewrote the stale phantom test (console is no
      longer unregistered; uses a genuinely-unregistered name to keep phantom-detection covered). **Phase D
      (coverage fill) DONE 2026-06-15 via a 13-agent workflow:** new characterization tests at the seams for the Tier-1
      spine + 5 capability handlers + new-code wiring (~329 tests, 13 `test_*_coverage.py` files). **Overall coverage
      45.6% → 52.3%.** Big gains: `voice_runner` 34→85%, `replay_trace` 34→82%, `voice_assistant` 48→72%,
      `core/components` 20→56%, `nlu_component` 38→59%, `asr_component` 25→46%. Residual-cold (deep pipeline paths that
      need a booted core — smoke territory, not unit): `workflow_manager` 20→29%, `context` 25→31%. **No product bugs
      surfaced** (agents covered clearly-correct behavior; nothing to decide). The workflow run crashed mid-flight (lost
      its verifier/result), recovered by hand: all 13 files were written + genuine (spot-checked, not gamed); fixed one
      latent `asyncio.get_event_loop()` anti-pattern the new tests EXPOSED in `test_clarification.py` (same class as the
      Phase-C `no_intent_clarification` fix). **Suite 100% green (888 passed / 0 failed / 7 skipped); 9/9 contracts; no
      product code changed.** Optional follow-up: a deep-path round for `workflow_manager`/`context` (or accept as
      integration-level).
- [x] **TEST-8** [PORTS] (P1) — **DONE 2026-06-15 (TEST-7 Phase D).** All 5 capability handlers now covered through
      their injected ports + the graceful-degradation-when-absent path (the QUAL-24 bug class): `text_enhancement` 99%,
      `speech_recognition` 97%, `translation` 97%, `audio_playback` 80%, `voice_synthesis` 65% (the residual is the
      model-dependent TTS execution → smoke). The QUAL-24 repair is now verified. _Original scope below._
      **Capability-port handler coverage (surfaced by QUAL-24).**
      QUAL-24 found that only `conversation` was ever injected — the **5 other capability handlers**
      (`voice_synthesis`, `audio_playback`, `speech_recognition`, `translation`, `text_enhancement`) were silently
      getting `None` for their component (compounded by an await-sync bug) and are now **wired for the first time**
      via domain-owned ports (`irene/intents/ports.py`). **No test exercises these handler→port paths** — so the repair
      is unverified. Cover: (1) the injection wiring itself — `IntentComponent.post_initialize_handler_dependencies`
      sets each handler's port (and `provider_control`'s registry) and handlers degrade gracefully when a component is
      absent; (2) each handler's actions through its injected port — LLM `generate_response`/`enhance_text`/`extract_*`,
      TTS `speak` + the **best-effort `stop_synthesis`/`cancel_synthesis`** (graceful no-op, no crash), Audio `play_file`
      + the **provider-delegated `pause_audio`/`resume_audio`/`stop_playback`**, ASR `switch_language`; (3) ABC
      enforcement — a component missing a port method fails at instantiation (regression guard for the ports↔components
      contract). Fixtures: the localization-asset-loader pattern + fake port impls. Relates to QUAL-24, ARCH-1.
- [x] **TEST-9** [EVAL] (P2) `[release]` — **DONE 2026-06-27.** Wired the eval-commons voice-fixture recorder (W6 of
      `../eval-commons/docs/design/fixture_recorder.md`) into this repo's `eval/`: `make record` / `record-list` /
      `record-devices` / `setup-record` targets (recorder invoked as `python -m eval_commons.record.cli`);
      committed `profiles/recording.env.example` (machine-local `recording.env` git-ignored); **added `reference` to
      the `light_unreachable` judge case** so the recorder has a line to read (§5 decision — inert to the test, it's
      judge-only) — TODO in the YAML to confirm the target stays unreachable on a live run; repointed
      `fixtures/README.md` + `eval/README.md` at `make record` (kept the ffmpeg/TTS recipe as the alternative). Verified:
      `make record-list` derives both fixtures, `eval-fixture-record` console script resolves, `make record-devices`
      lists inputs, `make cli` still 5/5. Recording the WAVs themselves is the remaining manual (human-at-mic) step,
      which this unblocks. `config-ui-stays-functional` N/A. The recorder code + its design live in eval-commons (its
      own repo/process).
- [x] **TEST-10** [EVAL] (P2) `[release]` — **DONE 2026-06-27.** Version the WS audio fixtures: carved
      `!eval/fixtures/*.wav` out of the repo's blanket `*.wav` ignore (`.gitignore`). The blanket rule had swept the
      fixtures in by accident (generic "don't commit audio"), which made the WS suite **un-runnable in CI** (no mic)
      and **non-reproducible** (re-recording → different waveform → different WER). Fixtures are versioned test inputs,
      not stray audio. Verified the carve-out (eval/fixtures wav committable; other `*.wav` still ignored) and updated
      `fixtures/README.md`. Small files; git-lfs only if they grow. _(Strategic follow-up — golden traces as the
      reviewable regression inputs — is covered by the trace-system-testing design.)_
- [x] **TEST-11** [EVAL] (P2) `[deferred]` — **DONE 2026-06-27 (design).** Design for trace-driven system testing →
      `docs/design/trace_system_testing.md`. Uses the shipped ARCH-19 trace record/replay as (1) an **offline,
      deterministic, CI-able regression surface** — committed golden traces under `eval/traces/`, replayed via
      `irene-replay-trace --local` through the existing `cli_provider` (assert `exit_code === 0`), tiered
      `trace-system` (exit-code) vs `trace-ux` (DeepSeek judge) — and (2) **failure-trace capture**: always-trace +
      keep-on-failure for the live WS suite (with a small SUT enabler — `request_id` in `/ws/audio` metadata) and
      `--record-out`-on-mismatch offline, so a failed case ships a replayable trace (`--listen`/`--step`). Folds in
      the fixture-versioning fix (TEST-10) and a trace↔WAV unification idea. **Completing the design ≠ shipped:** filed
      implementation slices **TEST-12/13/14**.
- [x] **TEST-12** [EVAL] (P2) `[deferred]` — **DONE 2026-06-28.** Offline golden-trace replay surface (S1 of
      `trace_system_testing.md`) **+ the config-override enabler the user asked for.** (1) **`--set DOTTED.KEY=VALUE`**
      config overrides — `apply_dotted_overrides` in `config/manager.py` (JSON-typed coercion, applied pre-validation so
      Pydantic coerces+validates, strict: an explicit `--set` never silently falls back to defaults), wired into the
      base runner (all `irene-*` runners); 8 unit tests. No more hand-editing temp config files to tweak a setting.
      (2) **Replay surface:** `eval/trace.promptfooconfig.yaml` drives `irene-replay-trace -t … --config … --local`
      through the existing `cli_provider` (assert `exit_code === 0`) — no new `eval-commons` code; `make replay` /
      `replay-judge`; committed seed golden `eval/traces/timer_set_10min.json` (text trace, ~12 KB, portable) that
      replays **green** under the pure WB7 config; `eval/traces/README.md` + the 4th surface in `howto-new-test.md`.
      (3) **`diff_output` now normalizes volatile timestamps** (`_strip_volatile`) so a fire-and-forget action's
      `started_at` doesn't break an otherwise-deterministic golden (+ tests). Recording surfaced **BUG-1** (spelled-ru
      numerals; golden uses the digit form) and **BUG-2** (stale TTS↔Audio check — fixed here). The natural-speech timer
      golden + the `trace-ux` LLM tier await BUG-1.
- [x] **TEST-13** [EVAL] (P2) `[deferred]` — **DONE 2026-06-28.** Failure-trace capture for the live WS suite (S2,
      design `trace_system_testing.md`). **D-6 SUT enabler:** when tracing is on, `WorkflowManager.process_text_input`/
      `process_audio_input` stamp the trace `request_id` onto `result.metadata` (the `/ws/audio` response already
      spreads `result.metadata`, so it surfaces with no handler change); additive, gated on tracing; config-ui N/A.
      **D-13 keep-on-failure helper:** new project-agnostic `eval_commons.failures` (eval-commons `e740c80`) — reads the
      promptfoo results JSON and copies each FAILING case's `<traces_dir>/<request_id>.json` into `traces/failures/`
      (prunes the rest); robust to promptfoo nesting/version drift; reusable by wb-mqtt-bridge unchanged. Wired into the
      thin `eval/Makefile` `ws` target behind `TRACE=1` (preserves promptfoo's exit code) + documented in `eval/README`.
      **D-7 offline tier:** already satisfied — `irene-replay-trace --record-out` keeps the replayed trace on a mismatch
      (the replay diffs `{text,success,actions}`); documented in the README. Reconciliation: `--record-out` pre-existed
      (TEST-12); `/ws/audio` already had `intent_name` (QUAL-54) but not `request_id`. Gates: suite 1106 passed (+ 2
      workflow_manager tests for the stamp; eval-commons +6), pyright 0, import-linter 9/9. Remaining: **TEST-14**
      (trace↔WAV).
- [x] **TEST-14** [EVAL] (P3) `[deferred]` — **DONE 2026-06-28.** Trace↔WAV unification (S3 / D-9): a golden audio
      trace already carries its captured audio (base64 PCM16, the same bytes `--listen` plays), so a new
      `irene-replay-trace --extract-wav <file.wav>` decodes it to a standard WAV — **record once, test twice** (one
      golden trace serves both the offline replay tier *and* the live WS suite, no re-recording with a mic). It's a pure
      trace→WAV transform: a standalone CLI mode that builds no core and runs no replay; writes at the captured
      rate/channels (Irene's 16 kHz mono PCM16 → directly usable as a WS fixture; eval-commons `conform` aligns target
      format if ever needed). Module fn `write_trace_audio_to_wav` (rejects text traces / non-PCM16). Documented in
      `eval/README` (record-once-test-twice). Gates: suite 1109 passed (+3 extract-wav tests), pyright 0, import-linter
      9/9. **This closes the trace-driven system-testing series** (TEST-11 design → TEST-12 offline replay → TEST-13
      live-WS failure capture → TEST-14 trace↔WAV); no TEST- trace-playback tasks remain open.
- [x] **TEST-15** [EVAL][WS] (P3) `[deferred]` — **DONE 2026-07-01.** The WS system suite now asserts ASR/WER for
      offline ASR. **task-start-reconciliation flipped the premise:** the ledger assumed the SUT had to be changed to
      surface the recognized transcript, but a live probe showed the SUT **already** exposes it at
      `metadata.audio_processing.transcribed_text` on the batch path (`_process_single_audio_pipeline` writes it; the
      `/ws/audio` handler forwards it in `_meta`). So the fix is **eval-side only** (user-confirmed approach): the shared
      `ws_audio_provider` (in `../eval-commons`) now resolves the transcript in priority order —
      `metadata.audio_processing.transcribed_text` → last streaming `partial` → reply text — so WER scores the
      *recognized speech*, not the assistant's reply. **No SUT change.** Verified live against `configs/embedded-armv7`:
      `make ws TARGET=local` = **4/4 pass** (WER 0 on `«поставь таймер на десять минут»`; intent `timer.set`; both
      DeepSeek-judged UX cases pass with `DEEPSEEK_API_KEY` set), `make cli` still 5/5. Cleared the now-confirmed
      intent-name + unreachable-device TODOs in `ws.promptfooconfig.yaml`; refreshed `eval/README` (WER tier works, UX
      runs live). **This closes the trace-driven system-testing implementation slices** (TEST-12/13/14/15); the WS
      suite is fully green where a local SUT can assert it. (DeepSeek Russian judge *calibration* remains advisory, not
      a blocker — a standing UX-tier note, not a TEST- task.)
- [x] **TEST-16** [EVAL][UX] (P3) `[deferred]` — **DONE 2026-07-02 (user suspected obsolete; reconciliation
      showed it was blocked on the user's own gold labels — completed interactively in-session).** The DeepSeek
      Russian UX judge is now **calibrated against native-Russian-speaker gold labels**: a regenerated 20-case set
      (the 2026-07-01 probe lived in a session scratchpad and was gone), user-labeled live (16 confident + 4
      borderline, excluded from κ), graded through the same llm-rubric→DeepSeek path against the SHIPPED rubrics.
      Iterations with re-measure-all discipline: shipped rubric 81%/κ0.625 (judge too strict on terse replies,
      lenient on bureaucratese — the OPPOSITE bias profile of the Claude-labeled probe, vindicating the human
      gate) → terse-passes/bureaucratese-fails/next-step-optional 94%/κ0.875 → in-condition mixed-language example
      **16/16, κ=1.0 in-sample, verdicts stable across repeat runs**. All four borderlines got defensible verdicts.
      **Housed** in eval-commons `examples/ru-ux-calibration/` (set + gold + scorer + README, commit `4dd73d7`).
      **Rubric infrastructure fixed en route:** the documented `file://…yaml#anchor` pattern NEVER worked in
      promptfoo (fragment treated as filename — why the live suite had inline copies); shared rubrics split into
      per-rubric `{ru,en}/*.txt` files, the yaml files retired, ARCHITECTURE §7.1 flipped to CALIBRATED, and the
      live `ws.promptfooconfig.yaml` UX cases (RU+EN ×4) now reference the shared files directly (path proven live
      from `eval/`). EN rubrics carry the same structural improvements, marked uncalibrated. **Gate met: Russian
      UX pass/fail is CI-trustworthy** — standing caveats: κ is in-sample (add fresh negatives as suites grow) and
      the calibration set must be re-run after ANY rubric edit.
- [x] **TEST-17** [EVAL][MQTT] (P2) `[release]` — **DONE 2026-07-05. The Irene↔bridge contract pinned into
      `eval-commons/contracts/`** (ARCH-26 §14 one-way inward sync; eval-commons `e571241`). Pinned byte-identical
      from `wb-mqtt-bridge/contracts/` @ bridge `59f4f46` / catalog `7a1149c7` (contract patch **v1.1** + alias
      vocabulary — pinning deliberately waited for VWB-20 so the first pin is the only pin): (a)
      `openapi.json` (CatalogResponse + typed `CatalogParam` + canonical action shapes); (b) `catalog.golden.json`
      (11 rooms + `global` aggregates + scenario managers, aliases, ru/en enum labels, units); plus the bridge
      `STAMP.json`, a voice-side `PIN.json` (commit/version/date of the pin), and a consumer-story
      `contracts/README.md` (re-pin procedure). (e) **The pin is load-bearing**: `tests/test_contracts_pin.py`
      (8) validates the golden against the pinned `CatalogResponse` JSON Schema (the two halves can't disagree),
      checks STAMP↔PIN↔golden version agreement, and asserts the v1.1 shape guarantees (aliases authored, ru
      enum labels, °C/% units, `values`-XOR-`options_from`, no empty husks) — re-pinning a pre-patch artifact
      fails loudly. **Carve-outs:** (c) the real WB7 dump joins when the bridge's `ops/` cutover happens (its
      own README tracks it); (d) the `{utterance → canonical command}` crossover fixtures co-develop with
      ARCH-8 PR-1 / TEST-18 (recorded there). `jsonschema` added to eval-commons dev extra.
- [x] **TEST-18** [EVAL][MQTT] (P3) `[deferred]` — **DONE 2026-07-05. The `device_command` capture provider + Irene
      producer contract tests (ARCH-26 §14) — the suite EXISTS and RUNS: first scoreboard 16/23** (all tier-1
      actuation + clarify green; red = 3 reads → ARCH-8 PR-5, F40/F42 scenario routing → QUAL-64 matcher
      tuning [user decision: leave red, tune later], F41 transliteration + F06 compound numeral → QUAL-35
      T2 evidence). Two slices (fixtures-first fold, user 2026-07-05):
      • **Slice A — crossover fixtures — DONE 2026-07-05** (interactive; eval-commons `941e245`; step 0
        re-pin @ bridge `ee0a71d` / catalog `91909b54` was `e0d6b45`). Deliverable:
        **`eval-commons/contracts/crossover_fixtures.json` — 23 fixtures** against the pinned catalog, all
        four expect kinds `actuate | room-group | read | clarify`, tiered 1/2 (green-able with the QUAL-35
        T1 donation baseline vs needs T2 units/transliteration), **guarded by
        `tests/test_crossover_fixtures.py`** (8 tests: every binding verified against the golden — device
        ids/capabilities/actions/param ranges/enums/rooms/groups/fields + fixtures↔pin version agreement;
        16/16 green together with the pin guards — a re-pin flags stale fixtures loudly). Coverage: aliases
        («телек»/«эппл»/«радиаторы»/«пол»), typed params with °C/% ranges, scenario enum via ru label
        («кино с видеокассеты» → `movie_vhs`) + a transliteration case («эппл ти ви» → `movie_appletv`),
        room-group scope `auto` vs «весь»→`all`, room aliases «зал»/«квартира», the depth-doctrine
        named-device case («закрой тюль слева» stays device-form), the power-fence cases («печь»/«розетки»
        reachable by NAME only). **The 3 open decisions resolved (user 2026-07-05):** light-subset pair
        nouns («ночники»/«тумбочки»/«полки») **DROPPED from v1** — user will add bridge-side compound
        devices later (those fixtures return with that re-pin); same-room capability ambiguity → **CLARIFY
        in v1** (F20 playback, F21 climate), priority rules = later release → **QUAL-63**; sensor reads
        **INCLUDED** (F30–F32, incl. `any_of` for the physically-equivalent bedroom room-temperature
        sources). Immediately consumable by bridge VWB-16; voice-side this is the acceptance spec ARCH-8
        PR-3/PR-4 build toward (test-first).
        _Orig:_ **(UNGATED — startable now, pure data against the TEST-17 pin).** Author the
        `{utterance → expected canonical command}` set into `eval-commons/contracts/` next to the pinned golden:
        every parse+resolution path the golden exercises — power on/off via alias («включи свет в детской»),
        ranged setters with units («поставь 22 градуса в спальне» → `climate.set_setpoint {temp: 22}`), percent
        («яркость на 30»), cover, aggregates («выключи свет везде» → `all_lights`), scenario enums by ru label
        («кино с видеокассеты» → `scenario.set {value: movie_vhs}`), room-alias forms («в зале»), sensor read.
        Immediately consumable by the bridge's VWB-16 consumer half; voice-side they are the **acceptance spec
        PR-3/PR-4 build toward** (test-first — the resolver meets a pre-existing failing suite, not post-hoc
        assertions). NO input-switching fixtures (bridge VWB-19 gate, per QUAL-35 note).
      • **Slice B — DONE 2026-07-05** (eval-commons `1bc7b03` + voice eval wiring): built as a **mock-bridge
        capture** (refines §14.3's in-process capture — operationally superior: `eval_commons/mock_bridge.py`
        serves the PINNED golden at `/system/catalog` and records every canonical POST fixture-shaped, so the
        run also exercises the real `BridgeClient` wire serialization + the real startup catalog pull);
        `device_command_provider` drives `/execute/command`, `device_command_assert` compares against the
        fixture `expect`, `fixtures_to_tests` GENERATES the promptfoo cases (fixtures stay the single source
        of truth). Voice side: `eval/device.promptfooconfig.yaml` + `make device / device-auto` (derives the
        SUT config — env cannot override nested TOML) + EXECUTE_URL/BRIDGE_CAPTURE_URL in the target profiles.
        _Orig:_ **(~~gated on ARCH-8 PR-1~~ UNGATED 2026-07-05).** A new eval-commons
        promptfoo provider drives Irene with an utterance and returns the emitted canonical `DeviceCommand`
        (captured by the PR-1 capturing bridge `OutputPort`, not POSTed) for assertion against the Slice-A
        fixtures + the pinned openapi schema — the **producer** half of the bidirectional contract (the bridge's
        consumer half = VWB-16). **Text-input first** (isolates NLU→resolver→handler, deterministic, no
        audio/bridge); audio→canonical later (recorded RU fixtures, WS-suite pattern). The full suite turns
        EXECUTABLE at ARCH-8 PR-4 + the QUAL-35 T1 donation baseline. ~~Gated on TEST-17~~ (pinned 2026-07-05).
        Design §14.

- [x] **TEST-20** [TEST] `[deferred]` — **DONE 2026-07-14.**
      **`test_arch36_satellite.py::test_recorder_declined_and_next_utterance_finalizes` is flaky (~3/8).**
      Failed intermittently in isolation on a clean tree (measured 2026-07-09, 3/8; confirmed not caused by
      the BUG-35 change — reproduced with that diff stashed). The task-start decision ("test bug or product
      race?") came down firmly on **test bug**: the recorder itself is deterministic (T-5 finalization, uuid
      filenames — no overwrite possible). Root cause: the test ordered the two written trace files by
      `st_mtime`, and back-to-back writes tie on the kernel's coarse file-timestamp clock almost always
      (measured 196/200 ties), leaving "order" = filesystem hash order of two random uuid names — a coin
      flip. Fix: identify the finalized first utterance by CONTENT (its dropped-uplink payload; both
      envelopes carry `declined` since both decline tracing) instead of on-disk order. Evidence: pre-fix
      8/20 red in isolation; post-fix 0/40 in isolation, file 14/14, full suite 1409 passed / 7 skipped.
      **BUG-42 folded in** — same test, same root cause seen from the full-suite vantage; its "cross-file
      state leakage, passes in isolation" diagnosis is falsified by the isolation reproductions (one
      load-sensitive cause, not two defects).
      docs: none — test-internal fix; no user-facing surface changed.
- [x] **TEST-21** [EVAL][MQTT] `[release]` — **DONE 2026-07-10. Re-pin @ bridge v0.6.0 release cut** (the
      TEST-17 inward sync, filed-and-done same day off the bridge's release tag). Bridge commit `e965385`
      (HEAD at pin `46584f0`), bridge version **0.6.0**. The delta was version-only: `openapi.json` changed in
      exactly two places (`0.5.0` → `0.6.0`), `catalog.golden.json` **byte-identical**, catalog version
      unchanged (`5622ba7a1a78102a`) — so no fixture or code impact. PIN.json updated (bridge_commit mirrors
      STAMP.bridge_commit per the TEST-17 rule); eval-commons suite 40/40; eval-commons `3fd9091` pushed.
      This pin records the release pairing: **voice v0.5.2 ↔ bridge v0.6.0**.
- [x] **TEST-22** [TEST][CONFIG] `[release]` — **✓ DONE 2026-07-16. The code↔config↔entry-points
      coherence guard** (ARCH-50 §H; full-scope ruling). `backend/tests/test_coherence_guard.py`, three
      directions, hermetic: **(a)** `utils/namespaces.py` ≡ pyproject's entry-point groups (registry
      mirror + provider-family mapping + a NO-STRAY-LITERALS sweep — no runtime module may restate a
      group as a string; the sweep's first run found 29 restatements across 11 files, all replaced with
      registry imports); **(b)** every declared config field has a runtime reader (textual, corpus
      excludes the declaration site + the pure-serialization template; allowlist = exactly the three
      `*_config` fields ARCH-56 reads dynamically, each with its reason); **(c)** the reverse of
      master-completeness — no live TOML carries a key the models don't declare (nested models silently
      ignore extras, so deletions used to leave lying lines forever). **First-run catches — all real:**
      two stray `cache_ttl_seconds` lines QUAL-83's strip missed; stale `system.metrics_enabled/
      metrics_port`; nine dead `workflows.unified_voice_assistant.*` keys + two dead sub-tables
      (audio_validation, resampling); the analyzer's unreachable "Method 2" (boolean handler keys — a
      shape no TOML has and the model forbids) deleted; **handler-config sections MISPLACED in all 7
      full profiles** (`[intent_system.handlers.conversation]` etc. vs the model's
      `[intent_system.conversation]`) — every such setting had been silently dropped since inception
      (all values happen to repeat model defaults, so zero behavior change) — relocated, and the dead
      datetime/greetings tables deleted; and **BUG-43 filed**: `[asr] default_language` was never a
      declared field, so the EN profiles' `"en"` decode hint never reached whisper (guard allowlists the
      key naming BUG-43 until wired per QUAL-36). Verified: guard 14/14, full suite 1425 passed / 7
      skipped, analyzer parity vs the ARCH-55 state (only the declared VAD fallback's deps join —
      correct), all profiles valid, armv7l gate green, config-validator valid, contracts 11/11.
      docs: none — a test + config-file corrections; no manifest node documents the relocated sections.

- [x] **TEST-23** `[release]` [TEST][WS] — **DONE 2026-10-05 — real-socket witness tests for the WS frames and
      flows no suite drove through an endpoint** (split out of ARCH-61; design
      `docs/design/ws_machine_core.md` §5, review answer Q2; family lead BUILD-47). Thirteen ordinary
      endpoint tests, each in the suite that owns its channel, every one asserting on what actually
      crosses the socket. **`test_ws_reply`:** two bracketed bursts through `/ws/audio/reply`
      (`speak_begin` / chunked PCM / `speak_end`, `seq` 1 then 2) with the production conform-down
      negotiator in the app; a 16 kHz voice reaching a device registered at 22.05 kHz AS PRODUCED
      (the server never upsamples — `speak_begin` states the real format); `register-reply` without
      `audio_out` assuming 22.05 kHz mono. **`test_web_push_output`:** a deferred result arriving as a
      `message` frame; `error` + close when web push is unavailable; the opening frame is never
      rejected (a non-JSON one gets a minted identity). **`test_observe_tap`:** `subscribed`, then
      only the filter-matching bus event as an `event` frame. **`test_ws_driving_input`:** two
      utterances on one batch connection (one session id; a failed command is still a `response`);
      `end` before `register` → `error` + close. **`test_ws_streaming_asr`:** one streaming
      connection where the server endpoints the first utterance (partials, then the response, no
      `end` from the device) and the device hard-finalizes the second. **`test_arch36_satellite`:**
      the granted-trace flow with explicit device frames; the satellite pair over a real loopback
      server (utterance up `/ws/audio`, `response` back there, the spoken reply as a burst on
      `/ws/audio/reply`); a power-loss reconnect — both sockets aborted without a closing handshake,
      an announcement fired while offline goes through the real notification → durable-store path,
      both channels re-register (new session id) and the missed announcement is spoken on the new
      reply channel with `seq` restarting at 1. The suite's fake reply server now speaks the
      protocol it stands in for (`protocol_version` in the ack, `width` in `speak_begin` — both read
      by firmware). `_build_app` in `test_ws_reply` takes the voice format and negotiator as
      parameters; nothing else in the existing tests changed. **Finding (document, lands with
      ARCH-61):** the guide says the reply audio is "already converted to the rate/channel count you
      registered" — the code conforms DOWN only, so a lower-rate voice arrives at its own rate.
      **Verified:** suite 1500 passed / 7 skipped (+13); the three loopback tests stable over
      repeated runs.
      docs: none — tests only; the guide inaccuracy the tests exposed (reply audio is conformed down, never up) is a byte-locked guide edit and lands with the ARCH-61 cut
      contracts: none — no versioned surface moved (tests only)
### Internationalization (I18N)
### Build & CI (BUILD)
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
      sibling (no task filed; owner's call). **Verified:** suite 1479 passed / 7 skipped;
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
### Models & Assets (ASSET)
### Documentation (DOC)
- [x] **DOC-5b** (P2) — DONE 2026-06-08: regenerated `guides/DONATION_FILE_SPECIFICATION.md` for the v1.1
      two-part model (language-neutral `contract.json` + per-language `<lang>.json`), with full field reference
      from `donation_contract_v1.1.json` (method/param schema, type + entity_type enums) and the cross-language
      validation rule. Old single-file/v1.0 body + drift banner replaced.
### UI / config-ui (UI)
- [x] **UI-1** [DEDITOR] (P2) — **DONE 2026-06-06.** Designed the human-friendly donation/pattern authoring model →
      `config-ui/docs/donation_editor_ux.md`. **Persona-driven** (author knows handlers, **zero spaCy/NLU**): the model
      is **five everyday cards + an Advanced escape hatch** (a word [+"include its forms"] / one-of-several-words /
      a number / any word / the rest), all in example-sentence language — "token/lemma/regex/pattern" never surface.
      Organizing principle: **the v1.1 split IS the clean/spaCy line** → two editors, a clean **Contract Editor** (no
      spaCy; the good half of `ParameterSpecEditor`) and a **Phrasing Editor** that quarantines all raw spaCy. The
      three pattern locations (`token_patterns`/`slot_patterns`/`extraction_patterns`) collapse to two questions
      ("what might the user say?" / "how to find each value?"). Grounded in a 28-file survey (real spaCy vocabulary is
      small; regex mostly reduces to friendly cards). **Decisions settled here (user-approved):** translation layer is
      **frontend-only** (`patternModel.ts`, lossless-by-construction round-trip, backend keeps validate + test-match);
      raw spaCy survives as an **advanced escape hatch behind a button**, never default; **structural-first phasing**
      (UI-5 ships the functional editor + all scaffolding with the existing raw editors as interim, UI-3 swaps the
      cards into the one widget — no double build). **Scope correction (supersedes prior note):** `ParameterSpecEditor`
      is NOT "already fine" — it embeds raw `extraction_patterns` + a regex `pattern` that move to the phrasing side, so
      all three editors are in scope. **Surfaced UI-7** (config-ui-wide i18n). **Depended on QUAL-10 [PEX] ✓.**
- [x] **UI-2** [DEDITOR] (P2) — **DONE 2026-06-06.** Built the bidirectional translation layer as the
      **frontend-only** pure module `config-ui/src/utils/patternModel.ts` (decision settled in UI-1 §4 — no backend
      compile/decompile endpoint). `decompileToken`/`compileToken` (+ pattern/slot/extraction-pattern wrappers) map
      raw spaCy token dicts ↔ the human **card** model (word [TEXT/LOWER/LEMMA] / one-of [IN or alternation-regex] /
      number [LIKE_NUM or digit-regex] / any-word / the-rest / **advanced**), with the §3.3 regex reductions and
      optional/repeat ↔ `OP:"?"`/`"+"`. **Lossless by construction:** each friendly card preserves its source encoding
      and anything else is stored **verbatim** in an `advanced` card, so `compile(decompile(x))` deep-equals `x` for
      every token. **Proven** by `patternModel.test.ts` (40 tests): unit cases that lock the §3.2/§3.3 mapping + the
      **required round-trip across all 28 real phrasing files** + a guard that >50% of real tokens map to friendly
      cards (no trivial all-advanced pass). Added **vitest** + a `test` script; updated the UI-8 orphan guard to treat
      test files as entry points (a module covered by a test is intentional). The §3.4 per-parameter merge/split is
      provided at the label level (extraction/slot helpers preserve labels verbatim); the param↔label association is
      applied by **UI-3** using the contract. DoD met: `npm test` (40/40), `npm run check` (type-check + lint + orphan
      guard) + `npm run build` pass. This is the engine **UI-3** sits on.
- [x] **UI-3** [DEDITOR] (P2) — **DONE 2026-06-06.** Reimplemented the pattern editors on the UI-2 card model and
      added test-against-text. **`CardEditor`** (one word card: the 5 friendly kinds + per-card **"Advanced"** escape
      hatch → `SpacyAttributeEditor`, with "Back to cards" via `decompileToken`; "include its forms" toggle +
      optional/can-repeat). **`CardPatternsEditor`** (replaces `TokenPatternsEditor` — a list of "ways of saying it";
      controlled over `SpacyPattern[]` but keeps decompiled cards in local state and only compiles on edits, so the
      raw editor stays stable and Cancel/revert re-syncs). **`SlotCardPatternsEditor`** (replaces `SlotPatternsEditor`).
      **`PatternTester`** (UI-1 §6): a sample-sentence box → the **real recognizer** `POST /nlu/recognize`
      (`apiClient.recognizeText`) showing the recognized intent + filled values + a match/no-match badge vs the
      method's intent. Rewired the phrasing method editor to the card editors ("What might the user say?" / "How to
      find each value" / "Does this work?"); **deleted** the raw `TokenPatternsEditor`/`SlotPatternsEditor` and the
      v1.0 lemma↔token-pattern auto-sync (the per-card "forms" toggle replaces it). **§3.4 polish folded in:**
      **`ExtractionFillersEditor`** (on the UI-2 `FillerPattern` helpers) edits each contract parameter's
      `extraction_patterns` as labelled card rows, **grouped under the parameter** (with `choice_surfaces` for
      choice/entity params) — closing the per-param extraction surface that had been un-editable since UI-5 removed
      `ParameterSpecEditor`; method-level `slot_patterns` stay as "Shared value slots" referenced by label. DoD met:
      `npm test` 40/40, `npm run check` (type-check + lint + orphan guard) + `npm run build` pass. **Sits on UI-2.**
- [x] **UI-5** `[release]` [DEDITOR] (P1) — **DONE 2026-06-06.** Rebuilt the donations editor on the v1.1 split model
      (config-ui), with the QUAL-42 validations wired in and the v1.0 cruft removed. **Delivered (6 green slices):**
      **(0)** type-gen toolchain — backend `scripts/dump_openapi.py` → committed `config-ui/openapi.json` (109 paths,
      built from the runner's router factory + component routers with `core=None`, since routes build independently of
      request state); `gen:api-types` generates `src/types/openapi.gen.ts` (envelopes, via openapi-typescript) +
      `donation-{contract,language}.gen.ts` (bodies, via json-schema-to-typescript from the two v1.1 JSON Schemas).
      **(1)** `apiClient` → v1.1: `getDonationContract`/`updateDonationContract` + the QUAL-42 `getContractValidation`/
      `validateTranslation`/`translateDonation`; **removed the dead `syncParameters` (404) and rule-based
      `suggestTranslations`** (superseded by the LLM service). **(2)** `src/types/donations.ts` — generated contract/
      phrasing + envelope types (no hand-maintained drift). **(3)** new **ContractEditor** (structural: per-method
      room_context + param specs name/type/required/canonical-choices/min-max/entity_type/pattern; method names
      read-only) and **DonationValidationPanel** (QUAL-42 wiring report + LLM validate/draft, with the graceful no-LLM
      message). **(4)** new **ChoiceSurfacesEditor** (canonical → per-language spoken forms) wired into the phrasing
      method editor. **(5)** reworked the cross-language panel + LanguageTabs — **dropped the sync button/handler/prop**
      end-to-end (params are single-source under v1.1). **Drive-by:** fixed a stale `configureIntentSystem` path
      (`/intent_system/configure` → `/intents/configure`, a 404 the codegen coverage-check surfaced). **Interim/deferred
      (by design):** the raw spaCy pattern editors remain (human-card model = UI-3); editor chrome i18n = UI-7; backend
      v1.0 dead-validation removal = QUAL-43. **DoD met:** `cd config-ui && npm run check && npm run build` pass; the
      page round-trips contract + phrasing + choice_surfaces. Design: `donation_editor_ux.md` §9. **This clears the
      Invariant #4 debt deferred from QUAL-29.** _Original scope below:_
      **Rebuild the donations editor on the v1.1 split model (config-ui;
      Invariant #4 debt from QUAL-29).** QUAL-29 retired the v1.0 per-language-with-params concept on the **backend**
      (contract.json = neutral core; `<lang>.json` = phrasing) and the REST API now reflects it (`GET/PUT
      /donations/{handler}/contract`; the per-`{language}` endpoints serve phrasing; `/donations/schema` → both v1.1
      schemas; `sync-parameters` removed). **The config-ui frontend still targets the old endpoints/shape and its
      donations-editing page is therefore non-functional at runtime** (it still *builds* — TS compiles against its own
      `api.ts`). Rebuild it: **(1)** `apiClient.ts` → the v1.1 endpoints (contract get/put; phrasing get/put/validate/
      create/delete; drop `syncParameters`); **(2)** `src/types/*` → split `DonationData` into a **contract** type
      (params: name/type/required/**canonical** choices/min-max/**entity_type**, per-method **room_context**) + a
      **phrasing** type (phrases/lemmas/patterns/examples + per-param description/extraction_patterns/aliases/
      default_value/**choice_surfaces**); **(3)** a **contract editor** (one per handler) + a per-language **phrasing
      editor**; `ParameterSpecEditor` → canonical choices + `entity_type`/`room_context`, and a **`choice_surfaces`
      editor** (canonical → per-language spoken forms); **(4)** rework the cross-language panel (param parity is
      structural now — surface-completeness + method-phrasing only; drop the sync button). **Coordinate with UI-1/2/3**
      (same files: `DonationsPage`, the editors, `LanguageTabs`) — do it as ONE donations-editor redesign, not twice.
      **★ TYPE GENERATION — folded in (user-approved 2026-06-04, "stop fighting type drift"):** step (2) is done by
      **generating** `src/types/*` from the backend OpenAPI schema (`openapi-typescript`), **not** by hand-authoring them
      — hand-maintained types are the drift source this task exists to fix (Invariant #4). The backend is ~80% typed
      (104/123 routes carry a Pydantic `response_model`), so generation yields real types. **Prerequisite (backend side):**
      add a small script that dumps `app.openapi()` (static, no running server) to a **committed** `openapi.json`,
      regenerated on contract change — mirrors the bridge's committed-schema model; then a frontend `gen:api-types` script
      (`openapi-typescript <schema> -o src/types/openapi.gen.ts`) like `../wb-mqtt-bridge/ui`. **Transport stays the
      existing `fetch`-based `apiClient.ts`** (typed against the generated `paths`; optionally the tiny `openapi-fetch`).
      **OUT OF SCOPE (user, 2026-06-04): axios and react-query** — config-ui's job is load-edit-save, not server-cache;
      we adopt generation only, not the bridge's full data-layer pattern. **Two-source generation (settled by QUAL-39):**
      the donation **contract/phrasing BODY** types generate from their **canonical JSON Schemas**
      (`assets/donation_contract_v1.1.json` + `assets/donation_language_v1.1.json`, via `json-schema-to-typescript`) — the
      body stays a `Dict[str,Any]` passthrough in the API (the schemas allow `additionalProperties`; strict modeling would
      drop fields on GET→PUT). The **envelopes** (and everything else) generate from **OpenAPI** (`openapi-typescript`);
      QUAL-39 typed the previously-untyped contract envelopes so they're now strong too. DoD: `cd config-ui && npm run check` (type-check + the harmonized strict lint) **&&
      npm run build** passes + the editing page round-trips contract + phrasing.
      **This is the remaining Invariant #4 obligation deferred from QUAL-29 (user-approved 2026-06-03).**
- [x] **UI-6** `[release]` (P1) — **DONE 2026-06-04. config-ui stack harmonization with `../wb-mqtt-bridge/ui` (precedes UI-1/2/3/5).**
      **strict linting (user-insisted, same level as the bridge)** — added a bridge-identical
      `.eslintrc.cjs` (type-aware `@typescript-eslint/recommended-type-checked`; `no-floating-promises`/`no-misused-promises`
      as errors; the `any`-noise rules off), the `eslint`/`@typescript-eslint/*` + react-hooks/react-refresh devDeps, and
      `lint`/`lint:fix`/`check` scripts at `--max-warnings 0`; **fixed the runtime↔types version skew** (`@types/react`
      19→18, `@types/react-dom` 19→18, `@types/node` 24→20 to match `react@18`); added `engines: node>=18`.
      **Cleanup DONE (user: "clean up all 71 now"):** resolved all **71** the strict gate surfaced across 19 files so
      `npm run lint` (`--max-warnings 0`) + `npm run check` pass — incl. a **real latent bug fixed** (`PromptEditor.tsx`
      variable `description:` lines were shadowed by the prompt-`description:` branch and never parsed; added a
      `currentSection !== 'variables'` guard). Approach: **51 async** → `void`/arg-aware-wrap (preserves today's
      non-awaiting behavior); **14 `exhaustive-deps`** → `eslint-disable` + reason (mount/scoped loads; load fns aren't
      memoized, so adding deps would loop); **5** redundant type-assertions auto-fixed. No test net → verified by
      type-check + build (both green; `--report-unused-disable-directives` confirms every disable is needed). **ON GREEN
      (done):** folded the strict lint into the Invariant-#4 config-ui DoD + **BUILD-4** (now `npm run check && npm run build`).
      **OUT OF SCOPE (user, 2026-06-04):** axios, react-query (config-ui is load-edit-save, not a server-cache dashboard);
      OpenAPI **type generation** was folded into **UI-5** (generation-only), not here. Refs: stack comparison
      (journal 2026-06-04), `../wb-mqtt-bridge/ui/.eslintrc.cjs`.
- [x] **UI-7** [DEDITOR/I18N] (P2) — **DONE 2026-06-07.** config-ui is now fully bilingual (**ru + en**), adding more
      languages cheap. Adopted **`react-i18next`** (`i18next ^23` / `react-i18next ^13`, the bridge's declared versions —
      which only *declared* them, never wired them, so the setup is from scratch) under `src/i18n/`: namespaced TS
      bundles (`locales/{en,ru}/{common,layout,donations,configuration,prompts,templates,localizations,monitoring,overview}.ts`),
      a typed `t()` (CustomTypeOptions off the `en` bundle → mistyped keys are build errors + autocomplete), and a global
      **`LanguageSwitcher`** in the Header (persisted to localStorage, default `ru` / fallback `en`, `<html lang>` synced).
      **Completeness is compiler-enforced:** the RU bundle is typed `DeepStringify<typeof en>`, so any missing/extra/misnested
      RU key fails the build — the "language files are complete" guarantee, statically. **The two language axes stay
      orthogonal:** the UI-chrome language (switcher) is independent of the donation *content* language (`LanguageTabs`).
      Retrofitted **every** config-ui page + component (chrome, donation editor track incl. the §3.2 card vocabulary, and
      all 6 admin pages) via partitioned slices; the §3.2 card labels/help read naturally in both languages.
      Orphan guard hardened in passing (side-effect imports `import './i18n'` + `*.d.ts` exemption). DoD met:
      `npm run check` (type-check + lint 0-warn + orphan guard) + `npm run build` + `npm test` 40/40 all green. Conventions:
      `config-ui/docs/i18n_retrofit_spec.md`. Design: `config-ui/docs/donation_editor_ux.md` §7. Refs: UI-1/2/3/5.
- [x] **UI-8** (P3) — **DONE 2026-06-06.** Swept the config-ui orphans + added a guard so they can't reaccumulate.
      A reachability sweep from `src/main.tsx`/`App.tsx` (now following dynamic `import()` too) confirmed **5** modules
      unreachable with **zero** references anywhere (no dynamic/string/registry use): deleted
      `src/components/editors/{AudioOutputConfigSection,KeyValueOfStringArray,ObjectArrayEditor}.tsx`,
      `src/utils/testWorkflow.ts`, and — **decision on the borderline `src/utils/spacyAttributes.ts`** — removed it too:
      it's a 392-line spaCy attribute catalog that nothing imports; the live advanced editor uses a *different* helper
      (`spacyAttributeHelpers.ts`, kept) and UI-3's card vocabulary is survey-grounded, so UI-3 doesn't need it (git
      history preserves it if a richer attribute picker is ever wanted). **Guard added:** `scripts/find-orphans.mjs`
      (reachability check) + `check:orphans` script, **wired into `npm run check`** — the root cause was that
      `--max-warnings 0` can't see unused *exports*. DoD met: `npm run check` (type-check + lint + orphan guard) +
      `npm run build` pass; no unreachable non-`*.gen.*` modules remain. Refs: UI-5.
      A reachability analysis from the app entry (`src/main.tsx`/`App.tsx`) flagged modules unreachable yet present —
      the strict ESLint gate can't catch unused *exports* (`--max-warnings 0` only sees unused locals/imports). UI-5
      removed the v1.0 *donation* orphans; these remaining ones are **pre-existing and non-donation**, so they were left
      out of UI-5 scope: `src/components/editors/{AudioOutputConfigSection,KeyValueOfStringArray,ObjectArrayEditor}.tsx`
      + `src/utils/testWorkflow.ts`. **Verify each is genuinely dead** (no dynamic/lazy import, not referenced by a
      route/registry the static sweep can't see) before deleting. **Borderline — decide, don't auto-delete:**
      `src/utils/spacyAttributes.ts` (a spaCy attribute catalog) is currently unreferenced but may be reused by **UI-3**'s
      human-card pattern model — keep if UI-3 will consume it, else remove. Consider adding the reachability check as a
      lint/CI guard so orphans don't reaccumulate. DoD: `cd config-ui && npm run check && npm run build` pass; no
      unreachable non-`*.gen.*` modules remain (or each remaining one has a documented reason). Refs: UI-5.
- [x] **UI-9** [DEDITOR] (P2) — **DONE 2026-06-07.** Free-form dict (map) config fields now render an editable
      key/value table instead of a dead-end warning. **Root cause (verified end-to-end):** the backend schema
      generator maps any `Dict[str, X]` field to `type: "object"` (`config/auto_registry.py:329`) but only attaches
      `properties` for nested *Pydantic models* (`_extract_nested_object_schema`), so free-form maps like
      `domain_priorities` (`Dict[str, int]`) arrive with `type: "object"` and **no `properties`**. config-ui's
      `ConfigSection` only promotes object fields to a collapsible subsection when `type==='object' && properties`
      (`ConfigSection.tsx:262`); without `properties` the field fell through to `ConfigWidget`'s `case 'object'`, whose
      sole job was the yellow `objectFieldWarning` placeholder ("should be a collapsible section") — so **every**
      free-form map field showed the warning, not just `domain_priorities`. **Fix (config-ui only, no backend/contract
      change):** `ConfigWidget`'s `case 'object'` now branches on `schema.properties` — absent → render the existing
      `KeyValueEditor` (add/rename/delete entries with value coercion); present → keep the warning, since a *fixed-shape*
      object reaching the factory is a genuine routing bug worth surfacing. Single touch point because both render paths
      (simple-field `renderField` and direct widget calls) funnel through `ConfigWidget`. Reused the already-present
      `KeyValueEditor` (the deleted `KeyValueOfStringArray` from UI-8 was a different, string-array variant). DoD met:
      `cd config-ui && npm run check` (type-check + lint 0-warn + orphan guard) + `npm run build` green. Refs: UI-5/UI-8.
- [x] **UI-10** [DEPS] (P2) `[release]` — **DONE 2026-06-27.** config-ui major dependency upgrades clearing the 6
      Dependabot alerts the lockfile-only housekeeping couldn't (all needed breaking majors outside the declared
      ranges): `vite ^5`→`^8.1.0` + `@vitejs/plugin-react ^4`→`^6.0.3` (3 vite advisories + esbuild dev-server; vite 8
      uses the rolldown bundler), `react-syntax-highlighter ^15`→`^16.1.1` (prismjs DOM-clobbering — the only runtime
      one; `Prism` + prism style imports unchanged), `@typescript-eslint ^6`→`^8.62.0` + `eslint ^8.45`→`^8.57.1`
      (minimatch ReDoS in lint tooling — stayed on eslintrc, **no eslint-9 flat-config migration**). ts-eslint 8's
      stricter `recommended-type-checked` surfaced 6 lint errors: 5 unnecessary-type-assertions auto-fixed, 1 unused
      catch binding → optional-catch (`apiClient.ts`). Gate green: `npm run check` (type-check + lint + orphans) +
      `npm run build` + vitest 40/40; `npm audit` → **0 vulnerabilities**. `package.json` intent changed (deliberate
      version decision, per the `every-task-in-the-ledger` carve-out — vs. the 2 lockfile-only bumps done as housekeeping).
- [x] **UI-11** [UI] (P3) `[deferred]` — **DONE 2026-06-28.** config-ui type-contract drift in `src/types/api.ts`
      (review `config_ui_review.md` §B) — restores the type-check half of `config-ui-stays-functional`. Realigned the 4
      drifted types to the backend `CoreConfig` (verified against the generated `openapi.gen.ts` + `irene/config/
      models.py`): **(B1)** added `outputs: OutputConfig` + `trace: TraceConfig` to `CoreConfig` and defined those
      interfaces; **(B2)** added canonical `default_language`/`supported_languages` (QUAL-36), kept `language` as the
      deprecated legacy field; **(B3)** removed the phantom `default_language`/`supported_languages` from `NLUConfig`
      (they live on `CoreConfig`); **(B4)** rewrote `VADConfig` to the ARCH-18 shape (dropped ~10 phantom flat per-engine
      fields, added `default_provider` + `providers`). **Zero consumer churn** — grep confirmed no component read any
      drifted field (the editor renders from the backend schema), so the realign is pure type-accuracy. Gate
      (`config-ui-stays-functional`): `npm run check` + `npm run build` green. _Durable follow-up considered: the
      generated `openapi.gen.ts` is current but unused while hand-written `api.ts` is consumed — making `api.ts` derive
      from the generated schema would prevent recurrence, but that's a larger structural refactor (sub-interface
      consumers) left for a future call. `ajv`/`ajv-formats` remain unused deps (client validation is backend-delegated)._
- [x] **UI-12** [UI] (P3) `[deferred]` — **DONE 2026-06-28.** config-ui duplication consolidation (review §C). **The two
      genuinely-clean dedups done; C2–C5 assessed and declined as over-credited.** **C1** — the `apiClient` per-language
      CRUD quintet (donations/templates/prompts/localizations, ~250 dup lines) → 6 shared private helpers + thin typed
      wrappers; call sites/signatures/requests unchanged; 12 now-unused `*Request` imports removed (`123ce3b`). **C6** —
      the `CardPatternsEditor`/`ExtractionFillersEditor` controlled decompile→compile scaffold → `useDecompiledPatterns`
      hook (`99c1432`). Both type-proven & behavior-preserving; gate green. **C2–C5 assessed-divergent** (annotated in
      the review doc): the pages/editors are *same-concept, divergent-presentation*, not clones — C2's two pages diverge
      in ~10 (often intentional) behaviors; C3's list editors carry per-row conflict badges (Lemmas) / index+styling
      (Spacy) so they aren't faithful `ArrayOfStringsEditor` swaps; C4/C5's `TemplateKeyEditor` already uses
      `ArrayOfStringsEditor` and has read-only keys while `LocalizationKeyEditor` adds a type-switch + domain hints —
      merging would **change UX**, not dedup. Net: ~280 lines genuinely removed (C1+C6); the §C over-credit recorded so
      it isn't re-litigated. Two optional micro-consistency wins (Localization array → `ArrayOfStringsEditor`; object
      branches → `KeyValueEditor`) noted, not pursued (UX-touching, no meaningful dup). Decisions: C2 skip + C2–C5 close
      both user calls (2026-06-28). Gate (`config-ui-stays-functional`): `npm run check` + `npm run build` green.
- [x] **UI-13** [UI] (P3) `[deferred]` — **DONE 2026-06-28.** config-ui dead-code removal (review §D — unused *exports*,
      which ESLint's unused-locals rule can't see). Each verified 0 external refs before deleting; the gate (type-check)
      would catch a mis-call. Removed: `types/index.ts` 8 never-imported utility aliases (Maybe/Optional/RequiredKeys/
      ChangeHandler/ClickHandler/AsyncClickHandler/ApiMethod/LoadingState; kept `ConnectionStatus`); `types/components.ts`
      8 dead interfaces (TokenPatternsEditorProps, SlotPatternsEditorProps, HandlerListProps, ConfigSection+ConfigField,
      SearchFilters, BulkOperationResult, MonitoringData; 239→174 lines); `spacyAttributeHelpers.ts` `validateSpacyAttribute`;
      `safeStringify.ts` `wouldShowObjectObject`. **Plus folded in:** the 12 hand-written `*Request` types in `api.ts`
      that C1 (UI-12) orphaned (the same-named `openapi.gen.ts` schemas are separate/generated), and the unused
      `ajv`/`ajv-formats` deps (UI-11 §B finding — `npm uninstall`; not imported anywhere). Gate
      (`config-ui-stays-functional`): `npm run check` (type-check + lint + orphans) + `npm run build` green — confirming
      everything removed was truly dead.
- [x] **UI-14** [UI] (P3) `[deferred]` — **DONE 2026-06-28.** config-ui efficiency + hardcoded-list/altitude (review
      §E). **Efficiency (behavior-preserving, gate-green):** E1 derived `hasChanges` instead of the state-via-effect
      anti-pattern on both Templates/Prompts pages (removed the effect + the redundant `setHasChanges(false)` calls —
      verified each coincided with `data===original`); E2 `TomlPreview` debounce → `useRef` (no re-render per keystroke);
      E3 all 14 `JSON.parse(JSON.stringify)` deep-copies → `structuredClone`; E5 memoized LemmasEditor's nested-loop
      suggestion scan + per-row conflict map. **E4 skipped** (`performAnalysis` also runs from a manual path → threading
      `currentHash` risks a cache-key mismatch; minor perf, real risk). **Altitude:** E6 the `ContractEditor`
      PARAMETER_TYPES/ENTITY_TYPES/ROOM_CONTEXTS dropdowns now derive from `satisfies Record<Union,…>` keys, so a backend
      donation-enum change **fails the build** instead of silently dropping options (the review's drift concern, fixed at
      compile time since a TS union can't be enumerated at runtime). **E7/E9/E10 spun out as UI-16** — E7 (component
      roster) + E9 (widget heuristics) are **blocked on backend schema metadata** (no `is_component`/`widget` hint
      exists); E10 (spaCy-attr i18n) is niche/low-value. **E8 assessed non-issue** — `LanguageTabs` display names are
      inherently UI + degrade gracefully; the `['en','ru']` fallback is a defensible default. Gate
      (`config-ui-stays-functional`): `npm run check` + `npm run build` green. Like UI-12, the review's §E altitude items
      were partly over-credited (most need backend signals or are non-issues); the genuine config-ui wins (efficiency +
      E6 drift-guard) are done.
- [x] **UI-16** [UI] (P3) `[deferred]` — **DONE 2026-07-15 (sprint-02 port arc, the travel-with row —
      the backend-metadata blocker dissolved by building the metadata).** **config-ui schema-driven
      sections/widgets + the spaCy-attr E10 finding** (review §E, spun out of UI-14). **E7:** the sections
      endpoint (`/configuration/config/schema/sections`) now returns **`component_sections`** — section →
      live-testable component name, sourced from `CONFIGURABLE_COMPONENT_SECTIONS` in the configuration
      component (adjacent to the API identities it names; the `text_processor→text_processing` divergence
      lives there ONCE, guarded by a new test asserting every key is a real CoreConfig section + a
      ComponentConfig flag). `ConfigurationPage` + `ConfigSection` derive the Test/Workflow roster from it
      (`testableComponent` prop) — both frontend hardcoded rosters + remap tables DELETED. **E9:**
      `_extract_model_schema` propagates a **`widget`** hint from `json_schema_extra`; 23 hints declared
      (`provider_select` ×8 incl. the component-schema base, `input_select`, `microphone_select`,
      `readonly` ×2, `env_var` ×7, `audio_output_select` ×4 on the audio provider schemas) — chosen by a
      mechanical audit of every model field against the old frontend predicates; the `ConfigWidget`
      factory now dispatches on `schema.widget` and the name/path heuristic stack is DELETED (the runtime
      `${...}`-value env detection stays — values can be env refs on any string field). Deliberate
      non-preservations, recorded: `fallback_providers`/`provider_cascade_order` (List fields) no longer
      hit the single-value ProviderSelect — the old name-match would REPLACE the array with a string on
      edit (a latent shape-corruption path); they fall to the array editor. `provider_class`/`provider`
      (NLU internals) render as plain strings. **E10 narrowed at execution intake:** the 21 English
      attribute descriptions were **dead data** — no caller ever rendered them (the picker shows keys
      only) — so per `dead-code-remove-not-fix` the i18n bypass was removed by deleting them
      (`SPACY_ATTRIBUTE_SUGGESTIONS` keys-only list; attribute keys stay technical per
      `donation-choice-surfaces-rule`). **Contract note (owner question answered in-session):** the REST
      surface is the `ui-openapi` repo-internal contract — the hints DO reach the generated artifact via
      the component model schemas, an additive regeneration (widget keys + one docstring), NOT a breaking
      reshape → `dump_openapi.py` re-run + `gen:api-types` (+3 lines), **no STAMP bump** per the
      convention; drift guard green. **Verified:** backend suite **1417/7 skip** (CI-style from repo root
      — the first from-`backend/` run's 76 failures were cwd-relative asset resolution, reproduced
      identically WITHOUT the change), 2 new tests (roster coherence + hints-reach-payload incl. nested);
      config-ui check + plugin build + vitest 44/44. docs: none — internal schema plumbing; config-ui
      behavior described in manifest nodes (edit/test/persist flows) is unchanged.
- [x] **UI-17** [UI][COMMONS] `[deferred]` — **DONE 2026-07-15 (sprint-02 port arc; the PROD-24 write-back
      ID; HK-11 corrections applied at intake the same day).** **config-ui → the Voice Workbench plugin.**
      `src/plugin.tsx` default-exports the `WorkbenchPlugin` (contract types from
      `locveil-workbench/contract`, devDep `file:`): **6-page cut** (donations, templates, prompts,
      localizations, monitoring, configuration) — `OverviewPage`, `Header`, `Layout`, `Sidebar` and
      `LanguageSwitcher` DELETED (shell chrome owns nav/locale/theme; the retiring components' types,
      `layout`/`overview` i18n namespaces, and the router usage went with them — the 6 surviving pages are
      router-free); the **status slot** preserves the Header's visibility (`checkConnection` +
      `getIntentStatus` → level ok/error + RU/EN text with handler count, shell-polled); **i18n =
      plugin-local instance** following the shell's `PageProps.locale` signal (persistence + `<html lang>`
      dropped — chrome owns both; collision-free by construction since react-i18next bundles per-plugin).
      **Packaging (HK-11)**: vite **lib build** → `dist/index.js` (ESM, singleton set external — verified
      bare specifiers in dist), `style.css` (Tailwind **preflight off**, tokens shell-owned), build-emitted
      `manifest.json` fragment (peers `^18/^18/^6/^0.1` — passes the shell's strict check incl. the 0.x
      strict-minor rule); `npm run dev` = `vite build --watch` per the HK-11 dev loop; orphan-guard entry →
      `plugin.tsx`. **Intake decisions recorded:** (a) contract-as-code has NO `backendTarget` (IMPL-1
      simplified `PageProps` to `{locale}`) — voice keeps its own base-URL mechanism (same-host:8080 +
      `window.__IRENE_API_BASE__` override; the nginx runtime-injection file retired with the container);
      (b) voice has NO REST report-write surface (intake is the ARCH-30 spoken dialog) — `reportHook` is a
      minimal in-plugin handler naming the voice-first path, a real write endpoint stays PROD-4-auth-gated;
      (c) **the standalone container fate** (side-find routed here): RETIRED with the app — `Dockerfile` /
      `nginx.conf` / `docker-entrypoint.sh` / `public/runtime-config.js` deleted, the `publish-ui` CI job +
      `build_ui` dispatch input removed (`locveil-voice-ui` stops publishing; existing GHCR tags remain
      pullable but frozen); the WB7 deployment was never affected (compose carries no UI service).
      **`config-ui-stays-functional` DoD re-anchored to the plugin build in CLAUDE.md (same change, HK-11
      owner ruling q5).** Shell mount landed in commons `workbench.config.json` (two real plugins now).
      **Verified:** `npm run check` + plugin build + vitest 44/44 + docs-manifest 8/8; full HTTP loading
      path against the served shell (runtime-config → voice manifest → entry 200 → styles 200); dist carries
      the default export and zero `process.env`. Browser render remains the honest caveat (IMPL-1
      precedent) — one `npm run serve` away. docs: quickstart, install, guides/build-docker (+ the non-root
      `config-ui/README.md`, rewritten — it still described the pre-UI-13 AJV standalone).
- [x] **UI-18** [UI][COMMONS] `[deferred]` — **DONE 2026-07-15 (filed + completed same session; sprint-02
      port-arc split, "voice UI-18" foundation row).** **Kit-first foundation: eslint-9 flat + `ui-kit-v1`
      + the 9 hand-built primitives swapped onto kit primitives.** (a) **eslint-9 flat config**: eslint
      8.57→9, `.eslintrc.cjs` → `eslint.config.mjs` (`typescript-eslint` meta-package, react-hooks 5), rule
      set preserved verbatim incl. the type-aware tuning — verified live via `--print-config`
      (`no-floating-promises`/`no-misused-promises`/`await-thenable` all error); `--ext` dropped from the
      lint script (v9), lint scope unchanged (ts/tsx). (b) **`locveil-ui-kit` file: sibling dep** +
      `presets:[preset]` + kit-dist content glob + `tokens.css` at the entry — both themes in the bundle
      (`.dark` class strategy; the standalone app stays light until a toggle exists — shell-owned at UI-17).
      (c) All **9 primitives** (`src/components/ui/`) rebuilt on kit primitives with their local prop APIs
      intact (composites untouched — that's UI-19): Badge→StatusChip (default/success/warning/error/info →
      pristine/persisted/edited/conflict/tested; custom→kit Badge outline), Input/TextArea→kit
      Input/Textarea+Label (a11y improved: `useId` replaces label-text ids), Toggle→kit Checkbox,
      Section→Card+Icon (collapse kept), ConfigurationStatus→Alert+Icon, TestConfigButton +
      WorkflowActionButtons→kit Button (variant/size mapped; conflict pill→StatusChip),
      WorkflowStatusIndicator→StatusChip (the state enum IS the kit `StatusVariant` set). **Side-find
      fixed upstream: commons IMPL-3** — the kit's StatusChip built classes via a template literal, so
      Tailwind never generated the real recipes (chips unstyled in every consumer) and the extracted `${h}`
      pseudo-candidate broke lightningcss minification (this build failure found it); fixed in the kit
      (static per-variant class map), voice's build is the live verification. Intake reconciliation: the
      sprint's "ci.yml guard-version prose batches in" side-find was already fixed by BUILD-38 — nothing to
      batch. **Verified:** `npm run check` (tsc + eslint strict + orphans) green, `npm run build` green,
      vitest 44/44, all five chip recipes + both theme token sets present in the built CSS (checked at the
      generated-utility level), HTTP smoke over `vite preview` (app + hashed assets served; browser render
      is one `npm run dev` away — IMPL-1-style honest caveat). docs: none — visual restyle of internal
      primitives; no manifest node describes config-ui's appearance (QUICKSTART's config-ui section is
      functional and unchanged).

- [x] **UI-19** [UI][COMMONS] `[deferred]` — **DONE 2026-07-15 (sprint-02 port arc, the flagged
      largest-risk row — landed same-day as its foundation).** **Full port body: 35 composites + 6 pages
      onto `locveil-ui-kit` primitives + tokens.** Real size at execution intake: ~11.7k lines / **1051
      raw palette class instances → 0** (checked mechanically over the whole tree; the planning "~32k /
      7 pages" was inflated — Overview had retired at UI-17). Executed as five parallel agents over
      disjoint file sets against one normative brief distilled from the stylebook; every file re-gated.
      **Structural swaps:** ~60 raw buttons → kit `Button` (variant/size per role; destructive actions →
      `destructive`/`text-destructive`, icon-only → ghost icon); **12 native selects → radix `Select`**
      (static/clean value sets) with **9 kept native** and token-styled (all carry legitimate
      `value=""` placeholder/sentinel semantics radix forbids — ConfigWidgets ×4, spaCy editors ×2,
      microphone device picker, LanguageTabs ×2); view-mode switchers → kit `Tabs` ×3 (Prompt/Template/
      Localization editors); the hand-rolled fixed-overlay modal → kit `Dialog` (BlockingConflictsDialog);
      ~20 feedback boxes → kit `Alert` (destructive/accent/default; kit has no warning variant — warning
      icons carry the edited-hue recipe); fake pulse-div loaders → kit `Skeleton`; search/text controls →
      kit `Input`/`Textarea`; booleans → kit `Checkbox`, range → kit `Slider`. **Meaning:** status pills →
      the local Badge/StatusChip vocabulary; inline status text/icons use the full-literal token recipes
      (Tailwind-extractable — verified present in the shipped CSS, light + dark, all five hues); no `*-50`
      washes survive. Pattern-card editors, LanguageTabs chrome, Monaco/syntax panes stayed custom per
      stylebook §7 (tokens only). **Recorded deviations:** `window.confirm` ×3 + native `title=` stay
      (`ui-kit-v1` ships no Toast/AlertDialog — commons IMPL-4 → voice UI-21); the two `fixed bottom-0`
      action bars (ApplyChangesBar, Localizations save bar) stay token-styled in place — the shell's
      bottom action-bar slot exists in chrome but the plugin contract exposes no API for it yet (a
      workbench-vX contract surface, PROD-24 arc); dense-row micro-icons keep explicit small sizes
      (stylebook's banned pattern is `!`-overrides, none used). **Verified:** whole-tree palette grep = 0;
      `npm run check` (tsc + eslint strict + orphans) green; plugin build green (lightningcss clean);
      vitest 44/44; recipe utilities confirmed in `dist/style.css` both themes; shell HTTP smoke (manifest
      → entry → styles 200). Browser render = the standing honest caveat (owner's `npm run serve` away).
      docs: none — appearance-only restyle; no manifest node describes config-ui's look, and the
      UI-17-era run instructions are unchanged.
- [x] **UI-20** [UI] `[deferred]` — **DONE 2026-07-15 (the HK-11 write-back side-find).** **Monaco
      bundled locally — no CDN at runtime.** `monaco-editor` **0.53.0** added (0.55 pinned back: it
      depends on a dompurify with open advisories — 0.53 keeps the 0-vulns bar; read-only DiffEditor
      usage unaffected); `src/utils/monacoLoader.ts` points `@monaco-editor/react`'s loader at the
      bundled instance (`loader.config({ monaco })`) and inlines the editor worker as a blob
      (`?worker&inline` — no worker-asset path to break under the import-map load); both consumers
      (TomlPreview, DiffViewer) import it at module top, so config runs before any render. Monaco's own
      dynamic imports code-split the dist (lazy editor core ~3 MB + per-language chunks, ALL LOCAL,
      resolved relative to the entry — exactly the ESM mechanism the HK-11 runtime assembly serves);
      monaco css folded into `style.css`. **Honest residual:** the jsdelivr URL still appears ONCE in
      the bundle as `@monaco-editor/loader`'s inert default-config object — dead data on a branch the
      provided instance short-circuits; zero external requests at runtime. Verified: check + build +
      vitest 44/44; served-shell smoke (entry, lazy editor core, a language chunk, styles — all 200
      from the plugin mount). TOML stays plaintext in the diff view (monaco ships no TOML grammar —
      unchanged from the CDN build). docs: none — invisible when online, works offline now; no
      manifest node describes the editor's loading mechanics.
- [x] **UI-21** [UI][COMMONS] `[deferred]` — **DONE 2026-07-15 (same session as its ungating —
      commons IMPL-4 shipped Toast/AlertDialog as ui-kit 0.1.1/`ui-kit-v1.1`).** **Toast/AlertDialog/
      Tooltip adoption sweep.** `window.confirm` ×3 (all in `ApplyChangesBar`'s save flow) → one
      promise-shaped kit **AlertDialog** (`askConfirm()` resolves the dialog's Cancel/Save-anyway
      choice — identical control flow to the old blocking confirm; new `applyBar.confirmTitle`/
      `saveAnyway` keys, RU+EN). **45 native `title=` sites → kit `Tooltip`** across 28 files (agent
      sweep + owner-files pass): icon-only triggers keep their accessible name via `aria-label`;
      dynamic/conditional expressions moved verbatim; multi-line titles (TestConfigButton preview,
      ConflictBadge) render `whitespace-pre-line`; one `TooltipProvider` at the plugin page root.
      Remaining `title=` occurrences are React component props (Section headings), not native
      tooltips — audited. Toast itself: no call sites yet (nothing user-facing needed it — the kit bus
      is available for future use; adopting it for save-success feedback is deliberate UX work, not a
      sweep). docs: none — interaction affordance polish; no manifest node describes tooltip behavior.
- [x] **UI-22** [UI][COMMONS] `[deferred]` — **DONE 2026-07-15 (filed + completed same session;
      IMPL-5 first consumer).** **Both bottom bars render through the shell's ActionBar slot.**
      `ApplyChangesBar` and the LocalizationsPage save bar now render `<ActionBar>` children into the
      kit's HK-11-singleton bus; the shell's `ActionBarHost` (workbench-v1.1, normal flex flow) owns
      the border/surface shell — the local `fixed bottom-0 … z-50 shadow-lg` wrappers and the
      DonationsPage `pb-20` overlap hack are DELETED; zero `fixed bottom-0` remains in the plugin
      (stylebook §8 now holds). Single-occupancy is safe by construction (the two bars live on
      different pages; latest-wins covers any transition). Verified: check + plugin build + vitest
      44/44; served-shell smoke — the shell dist carries `wb-bottom-slot`/Toaster, the rebuilt plugin
      (peers `^0.1` ≙ kit 0.1.2 under the 0.x strict-minor rule) serves entry+styles 200 and imports
      ActionBar/AlertDialog/TooltipProvider through the import map. Browser render = the standing
      caveat. docs: none — layout mechanics; no manifest node describes the bar placement.
- [x] **UI-23** [UI][COMMONS] `[deferred]` — **DONE 2026-07-15 (filed + completed same session;
      IMPL-6 consumer adjustment — voice was BROKEN against the controller until this).** **apiClient
      follows the shell-declared backend (`PageProps.backends.api`).** IMPL-6 (workbench-v1.2, additive)
      finally delivers the PROD-24-promised per-plugin backend targets: deployment facts (WB7 IP + port)
      live in the owner-edited shell config and reach pages as `PageProps.backends`. Before this, voice's
      `page()` wrapper destructured only `{ locale }` and apiClient resolved via the retired-nginx-era
      chain (build-time injection global + same-hostname fallback) — under the shell, same-hostname is
      the SHELL origin, so every fetch hit the serve script instead of the WB7. Fix: `setBaseUrl()` on
      the singleton + the wrapper re-points it **synchronously during render** — deliberately NOT a
      `useEffect`: React runs child effects before parent effects, so an effect here would fire AFTER the
      page's mount-time data loads and the first fetches would still hit the shell origin. The old chain
      stays as the explicit no-backends-configured fallback (comments rewritten to say so). Known
      wrinkle, recorded: `status()` is shell-polled outside any page — its first poll on activation can
      race the first page render and use the fallback once; the base sticks after that (contract gap if
      it ever matters: backends don't reach the plugin object, only pages). Verified: check + build +
      vitest 44/44; served runtime-config carries `{"api": "http://192.168.1.50:8080"}` for the voice
      mount. docs: none — deployment wiring internals; QUICKSTART's "talks to :8080" story unchanged
      (same-host dev still works via the fallback).
### Release Readiness (REL)
- [x] **REL-1** (P0) `[release]` — **DONE 2026-07-04 (interactive session). Definition-of-release SIGNED OFF.**
      Decisions: **(1) release artifact** = version tag **+ first real GHCR publish** (backend
      `standalone-x86_64`/`embedded-aarch64`/`embedded-armv7` RU-at-minimum + config-ui image), boot-validated
      where hardware allows → filed **BUILD-11** (dispatch + boot-check + real size budgets; the Docker clause
      was unproven — no `workflow_dispatch` had ever run); **(2) explicit scope tags** on all previously
      untagged open tasks — ARCH-8, QUAL-18, DOC-8, REL-2, REL-3 all `[release]` (user kept QUAL-18 and DOC-8
      in scope); **(3) coverage criterion** replaced with the three named nets (unit suite + smoke e2e + eval
      `make cli`) — no coverage-%; **(4) target** = milestone "scope-complete" (release when every `[release]`
      task is `[x]`), no calendar date. Criteria reconciled against reality at sign-off: 6 of 8 already met and
      checked with evidence (uv sync/boots, CI green, pyright **0 errors** standard mode, 10 import-linter
      contracts, three nets green, live model URLs); remaining open: docs/quickstart (REL-2), config-ui
      functional pass + Docker boot (REL-3 + BUILD-11). Checklist rewritten in `RELEASE_PLAN.md` header.
- [x] **REL-2** (P1) `[release]` — **DONE 2026-07-06. The release-time config story, driven by live
      first-touch evidence** (the user's own bare-`irene-cli` stumble earlier the same day became the
      acceptance test). Shipped: **(1) `configs/config-example.toml`** — curated text-first starter
      (hybrid NLU only, no model downloads, no keys; web API alongside; smart_home enabled with the
      bridge off → honest «умный дом не подключён»; every disabled capability comments its upgrade-path
      section in config-master) — boots + answers live («который час» → the time), passes the CI config
      gate (13/13 valid); **(2) the friendly no-config failure** — `requires_config_file=True` for the
      CLI + WebAPI runners (voice already had it): bare and `--headless` invocations now print "No
      configuration found … -c configs/config-example.toml … IRENE_CONFIG_FILE … QUICKSTART" instead of
      leaking component internals (the silent default-config fall-back could never work — empty NLU
      provider list); Docker unaffected (images bake `IRENE_CONFIG_FILE`); **(3) README** — stale status
      paragraph corrected (smart-home built, GHCR images real) + first-run one-liner; **(4) QUICKSTART
      finalized** — example-config-first flow, console-script invocations, smart-home moved from
      "not implemented" to in-scope-with-bridge, GHCR images noted, test count refreshed.
      Suite 1300, config gate 13/13, pyright 0.
- [x] **REL-3** (P1) `[release]` — **DONE 2026-07-06 (bar the tag ceremony). Version / changelog /
      functional pass.** Version **held at 15.0.0 for the entire release** (user 2026-07-06 — the bump rides
      the NEXT release, not this one), so the 'bump' is a confirmed no-op. `CHANGELOG.md` authored (the
      revival release — architecture / understanding / capabilities / operations) + README-linked. config-ui
      MANUAL functional pass PASSED against the running backend (the exit-criterion's human check) —
      sections incl. the new `reports`, donations, templates, localizations, ru/en switch, monitoring all
      live — and it earned its keep by catching **BUG-29** (default `web_port` 6000 was X11 / browser-blocked;
      swept to 8080). **The `git tag v15.0.0` is deliberately NOT created here:** the release artifact requires
      ARM boot validation (ARCH-25) and a clean `check_scope.py` (every `[release]` task `[x]`), so the tag is
      the FINAL release act, cut when ARCH-25 closes. REL-3's own deliverables (version decision, changelog,
      functional pass) are complete.

- [x] **REL-4** [REL] `[release]` — **DONE 2026-07-09.** Version renumbered `15.0.0` → **`0.5.0`**. The old number
      asserted fourteen prior major releases of this codebase; the only tags this repo ever carried are `8.1`
      (inherited 2023 upstream history) and `v12-final`. Owner's scheme: major `0` = the public API is not frozen
      (BUILD-21/22/23 will rename the package and extract the loader/logging), minor `5` = the fifth design
      generation — which fits 0.x semver exactly, since under 0.x the minor *is* the breaking axis. The "15th
      iteration overall" lineage fact moved to prose (CHANGELOG + `__version__.py`), because in the patch field it
      would collide with the only job patch has and be destroyed by the first bugfix.
      `irene/__version__.py` is the single source; `pyproject` (`attr`), FastAPI `info.version`, `/health` and
      `CoreConfig.version` all derive from it. `MAJOR_VERSION` — which never meant "package major", it printed
      `V15 Components`, i.e. the *architecture generation* — became an explicit `ARCH_GENERATION = 5`, no longer
      derived from the version (the log now reads `V5 Components`). **Deleted the `version = "15.0.0"` line from
      all 13 configs**: `CoreConfig.version` already defaults to `__version__`, so they were unvalidated copies
      that could only drift — and `configs/config-example.md` proved the point, still carrying `14.0.0`, a whole
      major behind. `config-master.toml` keeps a comment explaining the omission instead of a value.
      Regenerating `config-ui/openapi.json` also revealed it was **stale**: four schemas (`BridgeOutputConfig`,
      `ReportsConfig`, `SatelliteConfig`, `SatelliteTLSConfig`) had been added to the API and never re-dumped;
      nothing in CI regenerates it (filed as BUILD-26). Cross-repo cost was **zero** — the bridge never reads our
      version and eval-commons stamps only `bridge_version`; the one stale claim, D-11's "voice 15.x", was
      corrected in `productization.md`. Verified live: `/health` → `"version":"0.5.0"`, `openapi.info.version` =
      `0.5.0`, startup logs `V5 Components`, all 14 configs parse and inherit the version. pyright 0,
      import-linter 11/11, 1358 tests pass, `config-ui` check + build green.
