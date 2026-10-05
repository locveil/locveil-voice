# Design — the WebSocket protocol's machine core (ARCH-60)

**Date:** 2026-10-05 · **Status:** DRAFT — awaiting satellite-side review (nothing below is
implemented) · **Owner:** locveil-voice (`ws-protocol` family) · **Consumers:**
locveil-satellite (ESP32 firmware, C++ / ESP-IDF — the FW-1a conformance test), locveil-commons
(the eval WS provider, hermetic conformance), in-repo `satellite/link.py`

**Decision of record:** council HK-13 decision 9 + PROD-28 voice delegation (d) (commons board).
Owner ruling: design AND implementation now, three slices in order — golden frames, JSONL
transcripts, JSON Schema — landing as ONE cut **`ws-protocol-v1.1.0`**; it never gates the
satellite's FW-1a and FW-1a never gates it. Implementation task: **ARCH-61** (gated on this
review).

**The approved invariant amendment (lands with ARCH-61, verbatim):**
"`contracts/ws-protocol/` additionally holds the protocol's hand-written machine core (golden
frames, transcripts, schema). It is subordinate to the document: on disagreement the document
wins and the core is fixed. Never generated from code; a wire change updates document and core
in the same change."

---

## 1. What the core is, and what it is not

Today the protocol exists in exactly one normative form: prose plus examples in
`docs/guides/websocket-api.md`. A C++ firmware author reads it and writes a parser by hand;
nothing mechanical connects the parser to the prose, and nothing mechanical connects the prose
to what the server actually sends. The machine core closes both gaps with three hand-written
data artifacts:

| Slice | Artifact | Answers |
|---|---|---|
| 1 | golden frames | "Is THIS frame a valid `registered`? Which malformed frames must I reject, which unknown ones must I ignore?" |
| 2 | JSONL transcripts | "In what ORDER do frames flow on a connection — register, PCM, end, response; a reply burst; a reconnect?" |
| 3 | JSON Schema | "Give me one generalization of all the examples that a host-side tool can validate against." |

Authority, top to bottom — each level is checked against the one above, never the reverse:

1. **the document** (`websocket-api.md`) — the only normative text;
2. **golden frames + transcripts** — concrete instances of what the document says;
3. **the schema** — a generalization that must accept every valid golden case, reject every
   invalid one, and accept every real frame the server emits.

Not in the core, by construction: anything the document does not say (§7 lists what the server
accepts today but the document never promised); frame *semantics* (what a timer reply means);
audio content (binary frames are markers, never bytes); REST.

"Never generated from code" is taken literally: no script in this repo writes or refreshes these
files. The owner test (§5) *reads* real frames and *fails* on disagreement — a human then fixes
the document, the core, or the code, in that order of precedence.

---

## 2. File layout

### 2.1 Constraints (from HK-13 and the consumers)

- Pins are **flat**: a consumer's `contracts/pins/ws-protocol/` holds file names, not paths.
  Every enumerated file therefore needs a **unique basename**, and none may be called
  `README.md`, `PIN.json` or `STAMP.json`.
- Every file is **enumerated individually** in `STAMP.json` → `artifacts` (repo-root-relative
  paths, no globs). Adding a file is a minor cut by definition (the pinned set gains a file).
- Names are **stable and language-neutral**: lowercase ASCII, the same identifiers in file
  names, frame names, case ids and schema `$defs`. Nothing is renamed or removed inside a major.
- The firmware consumer builds with ESP-IDF and parses with a small C JSON library: files are
  strict JSON / JSONL, UTF-8 without BOM, no comments, shallow, and loadable with no schema
  engine.

### 2.2 Proposed set for `ws-protocol-v1.1.0`

All under `contracts/ws-protocol/` (beside the existing `README.md` + `STAMP.json`):

```
frames.golden.json                    slice 1 — every frame type, valid + invalid + unknown cases
transcript.audio-batch.jsonl          slice 2 — register → PCM → end → response (two utterances)
transcript.audio-streaming.jsonl      slice 2 — streaming mode: PCM → partial… → response, hard `end`
transcript.audio-trace.jsonl          slice 2 — trace granted: response then exactly one trace frame
transcript.audio-rejected.jsonl       slice 2 — bad first frame → error → server closes
transcript.reply-burst.jsonl          slice 2 — register-reply → speak_begin → PCM → speak_end (seq 1, 2)
transcript.satellite-pair.jsonl       slice 2 — both voice channels of one device, one utterance + its spoken reply
transcript.reconnect.jsonl            slice 2 — drop + reopen both channels, re-register, missed announcement on reply
transcript.output-push.jsonl          slice 2 — operator channel /ws/output: hello → connected → message
transcript.observe-tap.jsonl          slice 2 — operator channel /ws/observe: subscribe → subscribed → event
ws-protocol.schema.json               slice 3 — JSON Schema (draft 2020-12, the org-wide draft)
```

Eleven new files; with the guide the STAMP enumerates twelve artifacts. The format
description consumers need (§3, §4) does not get a file of its own: it lands as a short
"Machine-readable core" section in `websocket-api.md` — already enumerated, already pinned,
and the only place allowed to be normative (see open question Q3).

### 2.3 One frames file vs one per frame type (the question put to the satellite side)

| Option | Files | For | Against |
|---|---|---|---|
| **A — one file** `frames.golden.json` (**recommended**) | 1 | one load, filter by `channel`; one hash; the shared `error` frame is defined once; adding a case never changes the consumer's file list | a consumer that implements two of four channels still carries the operator-channel cases (~⅓ of the file); a pin-hash diff says "frames moved", not which |
| B — one per channel (`frames.audio.golden.json`, `frames.reply…`, `frames.output…`, `frames.observe…`) | 4 | maps onto consumer boundaries — firmware embeds only `audio` + `reply`; a cut that touches only an operator channel shows as "nothing changed for you" in the PIN hash map | the shared `error` frame is repeated or needs a fifth `common` file; four files to keep structurally identical |
| C — one per frame type (`frame.audio.register.json`, …) | ~20 | finest pin-hash granularity; a new frame type is literally a new file | file count; every new frame type edits the STAMP list; the smallest files hold two or three cases; cross-frame cases (unknown `type`) have no natural home |

Recommendation **A**: the file is small (20 frame definitions, 70–80 cases, a few
hundred lines), a C harness reads it once and filters, and the three-level rule (§6) already
tells a consumer what kind of change a cut carries without reading hashes. **B is a
no-regret fallback** if the firmware wants to embed only its channels — the structure inside
the file is identical, so choosing B later within major 1 would be additive (new files beside
the old one), not a rename. C is not recommended.

---

## 3. Slice 1 — golden frames (`frames.golden.json`)

### 3.1 Shape

```json
{
  "contract": "ws-protocol",
  "protocol_major": 1,
  "core_format": 1,
  "channels": {
    "audio":   { "path": "/ws/audio" },
    "reply":   { "path": "/ws/audio/reply" },
    "output":  { "path": "/ws/output" },
    "observe": { "path": "/ws/observe" }
  },
  "frames": {
    "audio.registered": {
      "channel": "audio", "direction": "s2c", "type": "registered",
      "required": ["type", "client_id", "session_id", "trace", "protocol_version"],
      "optional": [],
      "opaque": [],
      "volatile": ["session_id"],
      "cases": [
        { "id": "audio.registered/plain", "verdict": "valid",
          "json": { "type": "registered", "client_id": "kitchen_node", "session_id": "0f3c…",
                    "trace": false, "protocol_version": "1" } },
        { "id": "audio.registered/unknown-field", "verdict": "valid",
          "json": { "type": "registered", "client_id": "kitchen_node", "session_id": "0f3c…",
                    "trace": false, "protocol_version": "1", "x_future": 1 } },
        { "id": "audio.registered/missing-session-id", "verdict": "invalid",
          "violation": "missing-required",
          "json": { "type": "registered", "client_id": "kitchen_node",
                    "trace": false, "protocol_version": "1" } },
        { "id": "audio.registered/trace-not-boolean", "verdict": "invalid",
          "violation": "wrong-json-type",
          "json": { "type": "registered", "client_id": "kitchen_node", "session_id": "0f3c…",
                    "trace": "no", "protocol_version": "1" } }
      ]
    }
  },
  "unknown": [
    { "id": "audio.s2c/unknown-type", "channel": "audio", "direction": "s2c", "verdict": "unknown",
      "json": { "type": "x_future_frame", "anything": true } }
  ],
  "malformed": [
    { "id": "any/not-json", "verdict": "invalid", "violation": "not-json", "raw": "{\"type\": " },
    { "id": "any/not-an-object", "verdict": "invalid", "violation": "not-an-object", "raw": "[1, 2]" }
  ]
}
```

Field meanings (all key names are part of the stable surface):

- **frame name** — `<channel>.<wire type>` (`audio.register`, `reply.speak_begin`). The two
  opening frames that carry no `type` on the wire get position names: `output.hello`,
  `observe.subscribe` (their `"type"` is `null` in the definition).
- **`direction`** — `c2s` (client → server) or `s2c`. Never "in/out": the same file serves both
  ends.
- **`required` / `optional`** — the frame's top-level keys. **`opaque`** — keys whose value is
  a free-form object the protocol does not define (`response.metadata`, `trace.trace`,
  `event.payload`). **`volatile`** — keys whose value differs on every run (`session_id`,
  `timestamp`, `request_id`); a harness compares their presence and JSON type, never the value.
- **`verdict`** — `valid`, `invalid`, or `unknown`. **`violation`** (invalid only) — a closed
  vocabulary: `not-json`, `not-an-object`, `missing-type`, `missing-required`,
  `wrong-json-type`. New codes are additive (minor).
- **`json`** — the frame as a JSON object; **`raw`** — the literal text of a frame that is not
  valid JSON (so the case survives being stored in a JSON file).
- **`expect`** (c2s invalid cases only, optional) — the server's documented answer, by frame
  name: `{ "frame": "audio.error", "then": "close" }`.
- **`core_format`** — the fixture-file format generation (§6.3), independent of the wire.

Binary frames have no JSON form. `frames.golden.json` carries one descriptive block per
channel/direction that may carry them (`"binary": { "audio.c2s": { "content": "pcm_s16le",
"channels": 1, "rate_from": "audio.register.sample_rate" }, "reply.s2c": { "content":
"pcm_s16le", "rate_from": "reply.speak_begin.rate", "only_between": ["reply.speak_begin",
"reply.speak_end"] } }`) — a description, not a test vector.

### 3.2 Frame inventory for major 1 (derived from the document, checked against the code)

| Channel | c2s | s2c |
|---|---|---|
| audio | `audio.register`, `audio.end`, binary PCM | `audio.registered`, `audio.partial`, `audio.response`, `audio.trace`, `audio.error` |
| reply | `reply.register-reply` | `reply.registered`, `reply.speak_begin`, binary PCM, `reply.speak_end`, `reply.error` |
| output | `output.hello` (typeless) | `output.connected`, `output.message`, `output.error` |
| observe | `observe.subscribe` (typeless) | `observe.subscribed`, `observe.event`, `observe.error` |

Twenty JSON frame definitions. `*.error` is one shape (`type`, `error`) defined per channel
so every channel's s2c set is closed and self-contained.

### 3.3 What counts as a case (the satellite's "valid AND invalid, incl. unknown-type")

Per frame type, at minimum:

- **valid** — a minimal instance (required keys only), a full instance (every documented
  optional key), an instance with a non-ASCII value where the field is free text (`room_name:
  "Кухня"` — the product is Russian-first; a parser that mangles UTF-8 fails on day one), and
  **one instance with an unknown extra key** (must still be accepted — §7 F-1).
- **invalid** — one `missing-required` per required key that a receiver actually depends on,
  one `wrong-json-type` per key whose type a C parser would mis-read (boolean vs string, number
  vs string, object vs null), `missing-type` once per channel/direction.
- **unknown** — one frame per channel/direction with a `type` the protocol does not define.
  Verdict `unknown`, not `invalid`: the receiver **ignores it and keeps the connection**
  (§7 F-1). This is the case that keeps a fielded device alive across a minor.
- **malformed** — `not-json` and `not-an-object` once, channel-independent.

For **s2c** invalid cases the core records the structural verdict only — the document does not
say what a client does with a malformed server frame, so neither does the core. For **c2s**
invalid cases at the handshake the document does say (the server answers `error`), so those
cases carry `expect`.

---

## 4. Slice 2 — transcripts (`transcript.<scenario>.jsonl`)

One scenario per file; one JSON object per line; lines are in wire order.

```jsonl
{"kind":"meta","transcript":"audio-batch","core_format":1,"protocol_major":1,"channels":["audio"],"ordering":"per-connection","doc":"/ws/audio — voice input"}
{"kind":"open","conn":"a1","channel":"audio"}
{"kind":"text","conn":"a1","channel":"audio","direction":"c2s","frame":"audio.register","json":{"type":"register","client_id":"kitchen_node","room_name":"Кухня","sample_rate":16000,"wants_audio":true}}
{"kind":"text","conn":"a1","channel":"audio","direction":"s2c","frame":"audio.registered","json":{"type":"registered","client_id":"kitchen_node","session_id":"0f3c…","trace":false,"protocol_version":"1"}}
{"kind":"binary","conn":"a1","channel":"audio","direction":"c2s","content":"pcm_s16le","bytes":640}
{"kind":"text","conn":"a1","channel":"audio","direction":"c2s","frame":"audio.end","json":{"type":"end"}}
{"kind":"text","conn":"a1","channel":"audio","direction":"s2c","frame":"audio.response","json":{"type":"response","text":"Таймер на 5 минут запущен","success":true,"error":null,"confidence":1.0,"intent_name":"timer.set","timestamp":1750000000.0,"metadata":{}}}
{"kind":"close","conn":"a1","by":"client"}
```

- **`kind`** — `meta` (first line, exactly once), `open`, `text`, `binary`, `close`.
- **`conn`** — a connection label local to the file. A reconnect is a `close` followed by an
  `open` with a **new** label on the same `channel`; the satellite pair is two labels alive at
  once.
- **`channel`**, **`direction`**, **`frame`** — the same identifiers as `frames.golden.json`;
  every `text` line's `json` must be a `valid` instance of the frame it names.
- **`binary`** — a **marker for a run of one or more binary frames**; frame boundaries carry no
  meaning in this protocol, so a run is one line. `bytes` is illustrative; no audio is stored.
- **`close.by`** — `client`, `server`, or `network` (an unclean drop — the reconnect scenario).
- **`ordering`** (meta) — always `per-connection`: order is normative within one `conn`; a
  transcript never asserts ordering between two sockets (the reply burst and the `response`
  frame travel on different connections and may be observed in either order).

No assertion language. Cross-frame rules are a short closed list, stated once in the
document's new section and applied by every harness to every transcript:

- **T-1** the first s2c frame on a connection is that channel's ack (`registered` /
  `connected` / `subscribed`) or an `error`;
- **T-2** an `error` frame is the last s2c frame on its connection (§7 F-4);
- **T-3** `speak_begin`/`speak_end` pair by `seq`; `seq` increases within a connection;
- **T-4** s2c binary on `reply` occurs only between a `speak_begin` and its `speak_end`;
- **T-5** `session_id` belongs to the connection: a new `conn` gets a new one;
- **T-6** when traces are granted, each `response` is followed by exactly one `trace` on the
  same connection before the next `response`.

---

## 5. The owner-side test (`backend/tests/test_ws_machine_core.py`)

"Validated against REAL frames from the existing WS suites" is implemented as a **tap**, not as
a second copy of the suites.

**The tap.** A small pytest plugin module records every WebSocket frame at the **server side of
the socket** — it wraps Starlette's `WebSocket.send` / `WebSocket.receive` for the duration of
a run. That seam sits behind every endpoint regardless of what drives it (the in-process
`TestClient` or a real loopback server with the real satellite client), so what it records is
exactly what the real handlers emitted and consumed. It writes one JSONL file in the **same
line format as §4**, plus the producing test's node id. Live captures and golden transcripts
are therefore read by the same code.

**The run.** The owner test launches the witness suites in a child pytest process with the tap
enabled — deterministic, independent of `-k`, ordering or parallelism in the outer run:
`test_ws_driving_input`, `test_ws_reply`, `test_ws_streaming_asr`, `test_observe_tap`,
`test_web_push_output` (open question Q2 proposes adding `test_arch36_satellite`).

**The legs** (each is one test function; a failure names the frame, the rule and the producing
test):

| Leg | Asserts | Slice |
|---|---|---|
| L1 self-consistency | every case id is unique and well-formed; every `valid` case satisfies its own definition (`required` present, no key outside `required ∪ optional`), every `invalid` case violates it in the stated way | 1 |
| L2 document ⊂ core | every JSON example in `websocket-api.md` (fenced blocks and inline frames) parses and is a `valid` instance of a frame of the section's channel; every frame `type` the guide names has a definition, and every definition's `type` appears in the guide | 1 |
| L3 **real frames conform** | every s2c text frame the tap recorded is a `valid` instance of a frame of its channel — **strictly**: a key outside `required ∪ optional` fails (the server grew a field without the core). c2s text frames are classified leniently (unknown keys tolerated — the suites send deliberate bad frames) and kept for L6 | 1 |
| L4 **every frame is witnessed** | every s2c frame definition was recorded live at least once; no golden s2c frame exists that the server never sends | 1 |
| L5 transcripts well-formed | line shape, `meta` first, `conn` lifecycle, every `text` line `valid` for its named frame, rules T-1..T-6 hold | 2 |
| L6 **transcripts are witnessed** | each golden transcript's normalized sequence — per `conn`: (direction, kind, frame), binary runs collapsed, volatile values dropped — equals a real connection's sequence in the capture | 2 |
| L7 schema ≡ fixtures | every `valid` case validates against its `$defs` entry, every `invalid` case fails, every `unknown` case fails every definition of its channel/direction; every tap-recorded frame validates | 3 |

L3 is strict on the server's output and lenient on client input on purpose: the strictness is
the mechanical form of "a wire change updates document and core in the same change", while a
consumer reading the same files must *tolerate* unknown keys (F-1).

**Coverage the five suites do not yet give** (verified against the tree, 2026-10-05). On a
real socket today: `audio.register/registered/end/partial/response`,
`reply.register-reply/registered/error`, `output.hello/connected`,
`observe.subscribe/error`. **Not witnessed on a real socket:** `audio.trace` and
`audio.error` (exercised only in `test_arch36_satellite`), `reply.speak_begin`/`speak_end`
and the reply binary run (asserted at callback level in `test_ws_reply`, never through the
endpoint), `output.message`, `output.error`, `observe.subscribed`, `observe.event`. L4 and L6
therefore require **about six small real-socket tests added to the suites that own those
channels** — part of ARCH-61, in the slice that needs them. They are ordinary endpoint tests
that happen to be missing; the core only makes the gap visible.

Cost: the child run re-executes five or six small suites — a few seconds on top of a ~30 s
suite.

---

## 6. Versioning (the three-level rule applied to the core)

### 6.1 Levels

| Level | Trigger | Served `protocol_version` |
|---|---|---|
| **patch** | bytes of an enumerated file moved and **no harness can observe it**: wording in the guide, a case's free-text note, key order, whitespace | unchanged |
| **minor** | anything a conformance harness can observe: a case, transcript or file **added**; a case's `json`, `verdict`, `violation` or `expect` **corrected**; a frame definition's key lists changed; the schema following any of those; an additive wire change (new optional key, new frame type) with its document text | unchanged |
| **major** | a breaking wire change | moves — it is the major |

This is the consumers' "additions = minor, byte edits = patch", sharpened at one point: a
**correction** to an existing case is a minor, not a patch. A patch must stay re-pinnable with
zero conformance effect (the release gates warn on a patch gap and fail on a minor — a "patch"
that flips a test red in the firmware would break that promise).

### 6.2 Stability inside a major

File names, frame names, case ids, transcript names, `violation` codes and every key name in
§3/§4 are **never renamed or removed inside major 1**. A case that turns out to be wrong is
corrected in place (same id, minor); a case that should no longer be asserted is kept and
marked `"retired": true` (harnesses skip it) rather than deleted, so a consumer's test table
never loses a symbol between pins.

### 6.3 `core_format`

The fixture FILE format (the key names of §3/§4) is not the wire. If it ever needs a breaking
reshape, forcing `protocol_version` to `"2"` for a fixture reshuffle would be absurd. Rule:
`core_format` stays `1` and evolves additively (consumers ignore unknown keys in fixture files
too); a breaking reshape ships as NEW files with new basenames beside the old ones (a minor),
and the old ones retire at the next wire major.

### 6.4 The cut `ws-protocol-v1.1.0`

One commit: the eleven files + the guide's edits (header tag, the new section, the F-items of
§7 that are accepted) + `STAMP.json` (`version` `1.1.0`, twelve `artifacts`) + the CLAUDE.md
invariant amendment + the owner test + the added suite tests → tag → pushed together. Minor:
the pinned set gains files; the wire does not change; `WS_PROTOCOL_VERSION` stays `"1"`.
`re-pin owed: satellite, commons`.

---

## 7. What the document must gain in the same cut

Because the core is subordinate, it cannot assert anything the document does not say. Writing
the inventory against the code surfaced places where the document is silent or imprecise.
Each needs an explicit yes/no at review; **F-1 is the only one the design depends on.**

| # | Finding | Shipped behavior (verified in `webapi_router.py`) | Proposed document text |
|---|---|---|---|
| **F-1** | **No forward-compatibility rule.** The three-level rule promises that a minor never changes what a fielded device compares — which is only true if receivers tolerate additions. The guide never says so. | The server already complies: unknown register keys are dropped; an unknown-`type` text frame after registration is ignored on `/ws/audio`; the other channels ignore all inbound frames after the handshake. | "Both sides ignore JSON keys they do not know and text frames whose `type` they do not know. This is what lets the protocol grow without a new major version." — a NEW obligation on clients. |
| F-2 | "JSON text frames for control (each carries a `type` field)" contradicts the guide's own examples. | The opening frames of `/ws/output` (`{"client_id": …}` or `{}`) and `/ws/observe` (`{"token": …}`) carry no `type` and are identified by position. | Reword to "every frame the server sends carries a `type`; so does every client frame on the two voice channels". |
| F-3 | Which `register` keys are required is never stated. | `client_id` and `room_name` are required (the server answers `error` without either); `sample_rate` defaults to 16000 when absent although the guide says to declare it. | One sentence naming the two required keys and the default. |
| F-4 | Whether `error` ends the connection is never stated. | Every `error` the server sends is followed by the server closing the socket (handshake rejections close explicitly; a mid-stream failure ends the handler). | "An `error` frame is terminal: the server closes the connection after sending it." (rule T-2; to be proven by a test in slice 1 before the sentence lands) |
| F-5 | `speak_begin.width` is shown as `16` without a unit; `audio_out` lists `rate` and `channels` only. | `width` is bits per sample and always 16; an `audio_out.width` sent by a client is ignored. | Two small clarifications. |
| F-6 | `mode` names only `"streaming"`. | Every other value means batch; the in-repo satellite runner sends `"single"`. | Say that any other value, or none, selects batch. The core types `mode` as a string, not an enum. |
| F-7 | Keys the server accepts but the guide never mentions: `primary_room` (alias of `room_name`), `model_version`, `language`, `location`, `client_type`, `capabilities`, `metadata`, and `audio_out` on `/ws/audio`. | Accepted and stored. | **None — they stay OUT of the core.** Undocumented means not protocol. Whether to document or stop accepting them is a separate owner decision, not part of this cut. |

One place where the **code** disagrees with the document (the document wins, so the code is
what gets fixed):

- **C-1** — the guide says "on any protocol violation the server answers `{"type": "error",
  …}`". On `/ws/audio/reply` a first frame that is not JSON is parsed outside any handler, so
  the connection drops with no `error` frame (the other three channels do answer). A two-line
  fix; proposed to ride ARCH-61 slice 1 with the `any/not-json` case that exposes it, unless
  the owner prefers it filed as its own bug.

---

## 8. Slice 3 — the schema (`ws-protocol.schema.json`)

- JSON Schema **draft 2020-12** (what the bridge's descriptor schema and the commons manifest
  schema already use).
- `$defs` keyed by the frame names of §3 (`"audio.registered"`, …), plus one union per
  channel/direction (`"audio.s2c"`, `"reply.c2s"`, …) for "any legal frame here".
- **`additionalProperties` is left open everywhere** — the schema encodes the receiver's
  obligation (F-1), not the owner test's strictness (which reads the key lists of slice 1).
- Opaque values (`metadata`, `trace`, `payload`) are `{"type": "object"}` and nothing more.
- Hand-written; the Pydantic models and `serialize_intent_result` are never consulted to
  produce it. L7 is what ties it to the fixtures and to live frames.
- The firmware is not expected to run a schema engine on the device; the schema is for
  host-side tooling (the commons eval provider's conformance test, CI lint of captured
  traffic). The golden frames remain the primary artifact for C++.

---

## 9. Execution plan (ARCH-61, after review)

One ledger task, one commit, one tag — the slices are built and proven in order inside it:

1. **Slice 1** — `frames.golden.json`; the tap plugin; L1–L4; the missing real-socket tests;
   the F-4 proof.
2. **Slice 2** — the nine transcripts; L5–L6; the remaining missing flows (reply burst through
   the endpoint, the satellite pair, reconnect).
3. **Slice 3** — the schema; L7.
4. **The cut** — guide edits, STAMP, registry row, `contracts/ws-protocol/README.md`, the
   CLAUDE.md amendment (verbatim), docs-manifest check, tag, push.

Landing the slices as three separate commits was considered and rejected: until the cut
enumerates them the files would sit in `contracts/ws-protocol/` unlocked and unpinnable, and a
consumer could not tell a draft from a contract.

Nothing here waits for the HK-13 sweep (BUILD-51): contract-guard v3.1 already byte-locks an
enumerated list of any length, and the pytest trigger on `contracts/**` exists since BUILD-47.

---

## 10. Open questions for the review

| # | Question | Recommendation |
|---|---|---|
| **Q1** | One frames file, one per channel, or one per frame type (§2.3)? | **One file**; per-channel as the fallback if the firmware wants to embed only `audio` + `reply`. |
| **Q2** | Is `test_arch36_satellite` added to the witness suites? It is the only suite that drives the endpoints with the real satellite client over a real loopback server (and the only one producing `audio.trace` / `audio.error` today) — but its fake reply server emits frames that do not conform (`registered` without `protocol_version`, `speak_begin` without `width`), which the tap would need to exclude or the fake would need fixing. | **Yes, and fix the fake** — a test double that violates the protocol is itself a finding. |
| **Q3** | Is a section in `websocket-api.md` the right home for the fixture-format description (§3/§4, T-1..T-6), or does the C++ side want a separate enumerated guide file next to the fixtures? The approved amendment names "golden frames, transcripts, schema" — a fourth file kind would stretch it. | **A section in the guide.** |
| **Q4** | F-1 is a new client obligation. Does the firmware accept "ignore unknown keys and unknown frame types" as binding from `v1.1.0`? Without it the unknown-`type` cases have no verdict to assert. | **Yes** — it is the precondition for every future minor. |
| **Q5** | Are F-2..F-6 accepted as document edits in this cut, and F-7 as an explicit exclusion? | **Yes to all**; F-4 only after its proving test is green. |
| **Q6** | Do c2s invalid cases get replayed against the real handlers (prove that each golden bad `register` really is answered with `error`), or is the tap's passive observation enough? The suites witness only three rejection situations today. | **Replay the handshake cases** — a dozen cheap in-process connections; without it the `expect` fields are unproven. |
| **Q7** | Negative transcripts (binary outside a speak burst, a second `register`, `speak_end` with a foreign `seq`) — in `v1.1.0` or a later minor? The document does not define the receiver's reaction to any of them. | **Later minor**, once the document says what a receiver does. |
| **Q8** | Case-id and file-name style: `audio.registered/missing-session-id`, `transcript.audio-batch.jsonl`. Any C-identifier constraint on the firmware side (ids used as test names)? | Keep as proposed unless the firmware needs `[a-z0-9_]` only — then ids switch to `audio_registered__missing_session_id` before the first cut, never after. |
