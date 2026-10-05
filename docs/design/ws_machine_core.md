# Design — the WebSocket protocol's machine core (ARCH-60)

**Date:** 2026-10-05 · **Status:** AGREED 2026-10-05 — the satellite-side review returned
**approve-with-changes, no blocking objection**; every accepted answer and requested change is
folded in below and recorded in §10 · **IMPLEMENTED 2026-10-05** as `ws-protocol-v1.1.0` (§11 records what changed while building) · **Owner:** locveil-voice
(`ws-protocol` family) · **Consumers:**
locveil-satellite (ESP32 firmware, C++ / ESP-IDF — the FW-1a conformance test), locveil-commons
(the eval WS provider, hermetic conformance), in-repo `satellite/link.py`

**Decision of record:** council HK-13 decision 9 + PROD-28 voice delegation (d) (commons board).
Owner ruling: design AND implementation now, three slices in order — golden frames, JSONL
transcripts, JSON Schema — landing as ONE cut **`ws-protocol-v1.1.0`**; it never gates the
satellite's FW-1a and FW-1a never gates it. Implementation: **ARCH-61** and the tasks it is
split into at intake (§9).

**The approved invariant amendment (lands with the cut, verbatim):**
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
| 1 | golden frames | "Is THIS frame a valid `registered`? Which invalid frames may I reject, which unknown ones must I ignore?" |
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

### 2.2 The set for `ws-protocol-v1.1.0`

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
description consumers need (§3, §4) does not get a file of its own: it lands as a
"machine-readable core" section in `websocket-api.md` — already enumerated, already pinned,
and the only place allowed to be normative. **Review condition (Q3):** the pinned guide is
the firmware's ONLY contract — it cannot read this design — so that section carries
everything a harness relies on: every key meaning of §3.1 and §4, `retired`, the
`core_format` rule, "ignore unknown keys in fixture files too", the receiver obligations
(§3.4) and the transcript rules T-1..T-8.

### 2.3 One frames file vs one per frame type (decided at review: **A**)

| Option | Files | For | Against |
|---|---|---|---|
| **A — one file** `frames.golden.json` (**recommended**) | 1 | one load, filter by `channel`; one hash; the shared `error` frame is defined once; adding a case never changes the consumer's file list | a consumer that implements two of four channels still carries the operator-channel cases (~⅓ of the file); a pin-hash diff says "frames moved", not which |
| B — one per channel (`frames.audio.golden.json`, `frames.reply…`, `frames.output…`, `frames.observe…`) | 4 | maps onto consumer boundaries — firmware embeds only `audio` + `reply`; a cut that touches only an operator channel shows as "nothing changed for you" in the PIN hash map | the shared `error` frame is repeated or needs a fifth `common` file; four files to keep structurally identical |
| C — one per frame type (`frame.audio.register.json`, …) | ~20 | finest pin-hash granularity; a new frame type is literally a new file | file count; every new frame type edits the STAMP list; the smallest files hold two or three cases; cross-frame cases (unknown `type`) have no natural home |

**Decision A** (review Q1 — "fallback B not needed"): the file is small (20 frame definitions, 70–80 cases, a few
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
      "types": { "type": "string", "client_id": "string", "session_id": "string",
                 "trace": "boolean", "protocol_version": "string" },
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

The `"0f3c…"` values above are an illustration for this document only. **In the files every
value is real** (review change 3): taken from frames the running server sent in the witness
suites — the owner test compares them (§5).

Field meanings (all key names are part of the stable surface):

- **frame name** — `<channel>.<wire type>` (`audio.register`, `reply.speak_begin`). The two
  opening frames that carry no `type` on the wire get position names: `output.hello`,
  `observe.subscribe` (their `"type"` is `null` in the definition).
- **`direction`** — `c2s` (client → server) or `s2c`. Never "in/out": the same file serves both
  ends.
- **`required` / `optional`** — the frame's top-level keys. **`types`** — the JSON type of
  each of those keys (`string`, `integer`, `number`, `boolean`, `object`, `array`, `null`; a
  list means "any of"). Added at ARCH-61 intake: without it a `wrong-json-type` verdict has
  nothing in slice 1 to be checked against, and the document never stated field types outside
  its examples (finding F-9, §7). **`opaque`** — keys whose value is a free-form object the
  protocol does not define (`response.metadata`, `trace.trace`, `event.payload`).
  **`volatile`** — keys whose value differs on every run (`session_id`, `timestamp`,
  `request_id`); a harness compares their presence and JSON type, never the value.
- **`verdict`** — `valid`, `invalid`, or `unknown`. **`violation`** (invalid only) — a closed
  vocabulary: `not-json`, `not-an-object`, `missing-type`, `missing-required`,
  `wrong-json-type`. New codes are additive (minor).
- **`json`** — the frame as a JSON object; **`raw`** — the literal text of a frame that is not
  valid JSON (so the case survives being stored in a JSON file).
- **`expect`** (c2s invalid cases — always present there, see §3.3) — the server's documented
  answer, by frame name: `{ "frame": "audio.error", "then": "close" }`.
- **`retired`** (optional, `true`) — the case is kept for symbol stability but no longer
  asserted (§6.2); harnesses skip it. **`note`** (optional) — free text for humans; no harness
  reads it.
- **`core_format`** — the fixture-file format generation (§6.3), independent of the wire.

**Names (review Q8 — one extra L1 rule).** Frame names, case ids, transcript names and file
names use only `[a-z0-9._/-]` and stay unique after every character outside `[a-z0-9]` is
mapped to `_` — ESP-IDF embed symbols and generated C test names apply exactly that mapping, so
two ids that differ only in punctuation would collide on the device.

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
  vs string, object vs null — s2c frames only, see below), `missing-type` once per
  channel/direction.
- **unknown** — one frame with a `type` the protocol does not define, for each direction of
  the two voice channels and for the s2c direction of the two operator channels (their
  opening frames carry no `type`, and the server ignores everything after them — F-8, F-10).
  Verdict `unknown`, not `invalid`: the receiver **ignores it and keeps the connection**
  (§7 F-1). This is the case that keeps a fielded device alive across a minor.
- **malformed** — `not-json` and `not-an-object` once, channel-independent (and once more
  inside each opening frame that rejects them, with `expect`).

**Which side an invalid case binds** (sharpened at ARCH-61 intake):

- **s2c invalid** cases are structural verdicts for the client's parser. They never carry
  `expect`; what the receiver owes them is §3.4.
- **c2s invalid** cases exist only where the document promises the server's reaction, and
  every one carries `expect`. They are the opening frames' shape violations (no `type`, a
  missing required key, not JSON, not an object) — the owner test replays each against the
  real handler (Q6). The server does not type-check registration values today (a numeric
  `client_id` is registered and echoed — filed as its own finding, §7 C-3), so a c2s
  `wrong-json-type` case would be a guess and is not in the core.
- **c2s unknown-type** cases bind the server after the handshake (it ignores them); the
  owner test replays those too.

### 3.4 What a receiver owes each verdict (review change 1 — lands as guide text)

The draft left the client's duty towards an s2c `invalid` frame unstated; a minimal parser
would then need a private allowlist, and a later "MUST reject" would be a new client
obligation arriving in a minor. The guide states, and this is binding from `v1.1.0`:

- **`valid`** — the receiver MUST accept the frame.
- **`unknown`** — the receiver MUST ignore the frame and keep the connection, **in every
  connection state, including before the ack** (review Q4: otherwise T-1 and F-1 collide on
  a future pre-ack frame; T-1 is therefore worded "ignoring frames of unknown type").
- **malformed** (`not-json`, `not-an-object`) — the receiver MUST survive it.
- **`invalid`** — the receiver MAY reject the frame (drop it, or close and reconnect) or
  tolerate it (use what it understands); it MUST NOT fault. This latitude is itself part of
  the contract inside major 1 — it is never tightened to "must reject" by a minor.

**Answer to the reviewer's question (a):** confirmed — the MAY-reject wording above is the
guide's wording for s2c `invalid`.

---

## 4. Slice 2 — transcripts (`transcript.<scenario>.jsonl`)

One scenario per file; one JSON object per line; lines are in wire order.

```jsonl
{"kind":"meta","transcript":"audio-batch","core_format":1,"protocol_major":1,"channels":["audio"],"ordering":"per-connection-and-direction","note":"batch mode: two utterances on one connection"}
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
- **`ordering`** (meta) — always `per-connection-and-direction` (review change 2; the draft
  said `per-connection`, which over-specified streaming): order is normative within one
  `conn` **and one direction**. In streaming mode the server's `partial` frames interleave
  asynchronously with the client's PCM, so the order of a c2s line against an s2c line is
  not asserted — except for the two causal pairs the document does promise (T-7, T-8). A
  transcript never asserts ordering between two sockets either (the reply burst and the
  `response` frame travel on different connections and may be observed in either order).
  The LINE order of a file is still an order the wire can produce, so a harness may replay
  a file top to bottom (it is the recorded order, except that a streaming transcript shows a
  binary run and its `repeat` line once where the real interleaving is finer).
- **`repeat`** (text lines, optional, `true`) — the frame may occur any number of times at
  this point, including not at all (the `partial` frames of a streaming utterance: their
  count depends on the recognizer). Added before the key names freeze (§6.2), as the review
  asked. A `binary` line needs no such mark — it already stands for a run.
- **`note`** (meta, optional) — free text for humans.

No assertion language. Cross-frame rules are a short closed list, stated once in the
document's new section and applied by every harness to every transcript:

- **T-1** ignoring frames of unknown type, the first s2c frame on a connection is that
  channel's ack (`registered` / `connected` / `subscribed`) or an `error`;
- **T-2** an `error` frame is the last s2c frame on its connection, and the server closes
  the connection after it (§7 F-4);
- **T-3** `speak_begin`/`speak_end` pair by `seq`; `seq` counts the bursts of one connection
  (it starts at 1 and increases; a new connection starts again);
- **T-4** s2c binary on `reply` occurs only between a `speak_begin` and its `speak_end`;
- **T-5** `session_id` belongs to the connection: a new `conn` gets a new one;
- **T-6** when traces are granted, each `response` is followed by exactly one `trace` on the
  same connection before the next `response`;
- **T-7** (causal) a channel's ack is sent only after the client's opening frame was
  received — an `error` may arrive at any time, even before it;
- **T-8** (causal) in batch mode a `response` follows the `end` frame that closed its
  utterance (or the 60-second cap); in streaming mode `partial` and `response` frames may
  arrive at any time after the ack.

---

## 5. The owner-side test (`backend/tests/test_ws_machine_core.py`)

"Validated against REAL frames from the existing WS suites" is implemented as a **tap**, not as
a second copy of the suites.

**The tap.** A small pytest plugin module records every WebSocket frame at the **server side of
the socket** — it wraps Starlette's `WebSocket.send` / `WebSocket.receive` for the duration of
a run. That seam sits behind every endpoint regardless of what drives it (the in-process
`TestClient` or a real loopback server with the real satellite client), so what it records is
exactly what the real handlers emitted and consumed. It writes one JSONL file in the **same
line format as §4** (one `binary` line per frame — the reader collapses runs), plus the
producing test's node id. The tap records facts and never names a frame: classification
against the golden definitions is the owner test's job. Live captures and golden transcripts
are therefore read by the same code.

**The run.** The owner test launches the witness suites in a child pytest process with the tap
enabled — deterministic, independent of `-k`, ordering or parallelism in the outer run:
`test_ws_driving_input`, `test_ws_reply`, `test_ws_streaming_asr`, `test_observe_tap`,
`test_web_push_output`, and — review Q2 — `test_arch36_satellite` (the only suite that drives
the endpoints with the real satellite client over a real loopback server). Its fake reply
server is fixed in the same work: it omitted `protocol_version` and `width`, both read by
firmware.

**The legs** (each is one test function; a failure names the frame, the rule and the producing
test):

| Leg | Asserts | Slice |
|---|---|---|
| L1 self-consistency | every name obeys the §3.1 naming rule (charset + unique after the `_` mapping); every `valid` case satisfies its own definition (`required` present, `types` hold; the one deliberate exception is the `unknown-field` case), every `invalid` case violates it in exactly the stated way; c2s invalid cases all carry `expect`, s2c ones never do | 1 |
| L2 document ≡ core | every JSON example in `websocket-api.md` (fenced blocks and inline frames) parses and is a `valid` instance of a frame of the section's channel; the guide's frame reference table (F-9) and the definitions agree key for key, type for type; the files the guide lists are exactly the enumerated set | cut |
| L3 **real frames conform** | every s2c text frame the tap recorded is a `valid` instance of a frame of its channel — **strictly**: a key outside `required ∪ optional` fails (the server grew a field without the core). c2s text frames are classified leniently (unknown keys tolerated — the suites send deliberate bad frames) and kept for L6 | 1 |
| L4 **every frame is witnessed, values are real** | every frame definition (both directions) was recorded live at least once; each definition's FIRST valid case equals a recorded frame — volatile keys and opaque values compared by JSON type only | 1 |
| L4b **the handshake cases are proven** (Q6) | every valid opening-frame case, sent first to the real handler, is answered by that channel's ack; every c2s invalid case gets exactly its `expect` (the `error` frame, then the server closes); c2s unknown-type frames sent after the handshake leave the connection working | 1 |
| L5 transcripts well-formed | line shape, `meta` first, `conn` lifecycle, every `text` line `valid` for its named frame, rules T-1..T-8 hold — on every golden transcript AND on every connection the tap recorded | 2 |
| L6 **transcripts are witnessed** | each golden transcript equals a real recording: per `conn` and per direction the sequence of (kind, frame) matches — binary runs collapsed, a `repeat` line matching zero or more frames — each non-repeat frame equals the recorded one (volatile keys and opaque values by JSON type only), `close.by` agrees, and all connections of one transcript come from ONE producing test | 2 |
| L7 schema ≡ fixtures | every `valid` case validates against its `$defs` entry, every `invalid` case fails, every `unknown` case fails every definition of its channel/direction; every tap-recorded frame validates | 3 |

**Answer to the reviewer's question (b):** yes — L6 tolerates a variable number of `partial`
frames. It compares per connection and per direction, and a line marked `repeat` matches zero
or more recorded frames; the cross-direction order is checked only through T-7/T-8.

L3 is strict on the server's output and lenient on client input on purpose: the strictness is
the mechanical form of "a wire change updates document and core in the same change", while a
consumer reading the same files must *tolerate* unknown keys (F-1).

**Coverage the suites do not yet give** (verified against the tree, 2026-10-05). On a
real socket today: `audio.register/registered/end/partial/response`,
`reply.register-reply/registered/error`, `output.hello/connected`,
`observe.subscribe/error`. **Not witnessed on a real socket:** `audio.trace` and
`audio.error` (exercised only in `test_arch36_satellite`), `reply.speak_begin`/`speak_end`
and the reply binary run (asserted at callback level in `test_ws_reply`, never through the
endpoint), `output.message`, `output.error`, `observe.subscribed`, `observe.event`. L4 and L6
therefore require **small real-socket tests added to the suites that own those channels**,
plus the flows no suite drives end to end today (two utterances on one batch connection, a
streaming utterance endpointed by the server, the satellite pair, the reconnect with a missed
announcement) — filed as their own task (§9). They are ordinary endpoint tests that happen to
be missing; the core only makes the gap visible.

Cost: the child run re-executes six small suites — about three seconds on top of a ~30 s
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

One commit ENUMERATES: the guide's edits (header tag, the new section, the accepted F-items
of §7) + `STAMP.json` (`version` `1.1.0`, twelve `artifacts`) + the registry row + the
CLAUDE.md invariant amendment + the document leg of the owner test → tag → pushed together.
The eleven core files and the rest of the owner test are built in the preceding commits
(§9); they become contract bytes at the cut. Minor:
the pinned set gains files; the wire does not change; `WS_PROTOCOL_VERSION` stays `"1"`.
`re-pin owed: satellite, commons`.

---

## 7. What the document must gain in the same cut

Because the core is subordinate, it cannot assert anything the document does not say. Writing
the inventory against the code surfaced places where the document is silent or imprecise.
**Review (Q4, Q5): F-1 accepted as binding from `v1.1.0`; F-2..F-6 accepted as guide edits;
F-7 accepted as an explicit exclusion.** F-8..F-10 and the corrections marked ⟲ were found at
ARCH-61 intake, when every claim in this table was re-run against the handlers
(`task-start-reconciliation`); they are document edits of the same kind and ride the same cut.

| # | Finding | Shipped behavior (verified in `webapi_router.py`) | Proposed document text |
|---|---|---|---|
| **F-1** | **No forward-compatibility rule.** The three-level rule promises that a minor never changes what a fielded device compares — which is only true if receivers tolerate additions. The guide never says so. | The server complies with one exception ⟲: unknown register keys are dropped; an unknown-`type` text frame after registration is ignored on `/ws/audio`; the other channels ignore all inbound frames after the handshake. **Before** the handshake the first frame must be the channel's opening frame — any other frame, known or not, is a violation answered with `error`. | Clients ignore JSON keys they do not know and text frames whose `type` they do not know, **in every connection state, including before the ack** (review Q4) — a NEW obligation on clients. The server does the same for keys always and for frame types after the opening frame. |
| F-2 | "JSON text frames for control (each carries a `type` field)" contradicts the guide's own examples. | The opening frames of `/ws/output` (`{"client_id": …}` or `{}`) and `/ws/observe` (`{"token": …}`) carry no `type` and are identified by position. | Reword to "every frame the server sends carries a `type`; so does every client frame on the two voice channels". |
| F-3 | Which `register` keys are required is never stated. | `client_id` and `room_name` are required (the server answers `error` without either); `sample_rate` defaults to 16000 when absent although the guide says to declare it. | One sentence naming the two required keys and the default. |
| F-4 | Whether `error` ends the connection is never stated. | ⟲ Handshake rejections close explicitly. A failure caught by an endpoint's catch-all (a first frame that is not JSON, a mid-stream pipeline failure) sends `error` and merely returns: a real ASGI server then closes the socket, but nothing in the handler does — under the in-process test client the connection stays open. The sentence is made literally true by the code fix C-2. | "An `error` frame is terminal: the server closes the connection after sending it." (rule T-2; proven by L4b/L5) |
| F-5 | `speak_begin.width` is shown as `16` without a unit; `audio_out` lists `rate` and `channels` only. | `width` is bits per sample and always 16; an `audio_out.width` sent by a client is ignored. | Two small clarifications. |
| F-6 | `mode` names only `"streaming"`. | Every other value means batch; the in-repo satellite runner sends `"single"`. | Say that any other value, or none, selects batch. The core types `mode` as a string, not an enum. |
| F-8 | "On any protocol violation the server answers `error`" is not true of `/ws/output`. | ⟲ By design that channel never rejects its opening frame: anything without a usable `client_id` — an empty object, text that is not JSON — gets a minted identity. | Say so in the `/ws/output` section; scope the violation sentence to what is a violation. No `expect` cases for `output.hello`. |
| F-9 | The guide states field types and required-ness only through examples. | — | A compact **frame reference table** in the new section: every frame, its required and optional keys, each key's JSON type. It is the normative statement the `types` lists of §3.1 instantiate, and L2 compares the two mechanically. |
| F-10 | `register-reply` without `audio_out` is accepted. | The server assumes 22050 Hz mono. | One sentence stating the default (the twin of F-3's `sample_rate` default). `audio_out` is therefore optional in the core. Also stated, for the server's half of F-1: after the opening frame the server ignores whatever a client sends on `/ws/audio/reply`, `/ws/output` and `/ws/observe`. |
| F-7 | Keys the server accepts but the guide never mentions: `primary_room` (alias of `room_name`), `model_version`, `language`, `location`, `client_type`, `capabilities`, `metadata`, and `audio_out` on `/ws/audio`. | Accepted and stored. | **None — they stay OUT of the core.** Undocumented means not protocol. Whether to document or stop accepting them is a separate owner decision, not part of this cut. |

Places where the **code** disagrees with the document (the document wins, so the code is
what gets fixed — review Q5 accepted C-1 riding the implementation; at intake it is filed as
its own bug task so the fix is one commit, §9):

- **C-1** — the guide says "on any protocol violation the server answers `{"type": "error",
  …}`". On `/ws/audio/reply` the first frame is read and parsed outside any handler, so ⟲ ANY
  failure there — not JSON, JSON that is not an object, a binary first frame, a non-numeric
  `audio_out` value — drops the connection with no `error` frame.
- **C-2** ⟲ — the catch-all paths of `/ws/audio` and `/ws/observe` send `error` without
  closing (F-4). They close explicitly after the fix, so "terminal" holds on every server and
  is visible to the tap.

Found at intake, NOT part of this cut (filed as their own tasks — `review-then-remediate`):

- **C-3** — the handshakes do not type-check values: `{"type": "register", "client_id": 5, …}`
  is registered and the ack echoes the number. The core therefore asserts no c2s
  `wrong-json-type` case (§3.3).
- **C-4** — nothing serializes two deliveries to one reply channel: a deferred announcement
  landing while a reply is being sent can interleave two `speak_begin … speak_end` bursts.
  T-3/T-4 are worded so they hold either way; "bursts never overlap" is NOT asserted until the
  code guarantees it.

---

## 8. Slice 3 — the schema (`ws-protocol.schema.json`)

- JSON Schema **draft 2020-12** (what the bridge's descriptor schema and the commons manifest
  schema already use).
- `$defs` keyed by the frame names of §3 (`"audio.registered"`, …), plus one union per
  channel/direction (`"audio.s2c"`, `"reply.c2s"`, …) for "any legal frame here". The
  typeless opening frame `output.hello` has no required key, so ANY object validates as
  `output.c2s` — which is exactly finding F-8, and why there is no `unknown` case for that
  channel/direction.
- **`additionalProperties` is left open everywhere** — the schema encodes the receiver's
  obligation (F-1), not the owner test's strictness (which reads the key lists of slice 1).
- Opaque values (`metadata`, `trace`, `payload`) are `{"type": "object"}` and nothing more.
- Hand-written; the Pydantic models and `serialize_intent_result` are never consulted to
  produce it. L7 is what ties it to the fixtures and to live frames.
- The firmware is not expected to run a schema engine on the device; the schema is for
  host-side tooling (the commons eval provider's conformance test, CI lint of captured
  traffic). The golden frames remain the primary artifact for C++.

---

## 9. Execution plan (split at ARCH-61 intake)

The draft planned one task and one commit. At intake the work turned out to be six separable
changes, and `one task = one commit` wins: each lands on its own, leaves the suite green, and
is filed `[release]` (PROD-28 tagging ruling).

| Order | Task | Change |
|---|---|---|
| 1 | **BUG-46** | C-1 + C-2: every WS error path answers `error` and closes |
| 2 | **TEST-23** | the missing real-socket witness tests (§5) + the conforming fake reply server (Q2) |
| 3 | **ARCH-62** | slice 1 — `frames.golden.json`, the tap plugin, legs L1, L3, L4, L4b |
| 4 | **ARCH-63** | slice 2 — the nine transcripts, legs L5, L6 |
| 5 | **ARCH-64** | slice 3 — `ws-protocol.schema.json`, leg L7 |
| 6 | **ARCH-61** | THE CUT — guide edits (§7), leg L2, STAMP (`1.1.0`, twelve `artifacts`), registry row, `contracts/ws-protocol/README.md`, the CLAUDE.md amendment (verbatim), tag `ws-protocol-v1.1.0`, push |

The draft rejected separate commits because "the files would sit in `contracts/ws-protocol/`
unlocked and unpinnable, and a consumer could not tell a draft from a contract". The first
half is true and harmless: until the cut they are NOT contract — no STAMP enumerates them, and
repin derives a pin's file set from the owner's STAMP at a tag, so no consumer can take them.
The second half is what the STAMP answers. What the split must not do is leak guide edits
early: `websocket-api.md` and `STAMP.json` are byte-locked, so every guide sentence of §7 and
the whole format section land in step 6 and nowhere else.

Nothing here waits for anything: contract-guard v4 byte-locks an enumerated list of any
length, and the pytest trigger on `contracts/**` exists since BUILD-47.

---

## 10. Review record (satellite side, 2026-10-05)

**Verdict: approve-with-changes, no blocking objection.** The firmware's conformance test
becomes a data-driven table over `frames.golden.json` plus four transcripts (`audio-batch`,
`reply-burst`, `satellite-pair`, `reconnect`); it skips the operator channels. The satellite's
pin gains eleven flat files (twelve artifacts).

| # | Question | Answer at review | Where it landed |
|---|---|---|---|
| **Q1** | One frames file, one per channel, or one per frame type? | **Accept** — one `frames.golden.json` keyed by frame name with a `channel` field; fallback B not needed. | §2.3 |
| **Q2** | Is `test_arch36_satellite` a witness suite? | **Accept** — and fix its fake reply server (it omits `protocol_version` and `width`, both read by firmware). | §5 |
| **Q3** | A guide section or a separate enumerated file for the fixture format? | **Accept with a condition** — a section, but everything a harness relies on must be IN it: the §3.1 key meanings, `retired`, the `core_format` rule, "ignore unknown keys in fixture files", T-1..T-6. Firmware cannot consume this design. | §2.2 |
| **Q4** | Is F-1 binding on clients from `v1.1.0`? | **Accept** — and state that it holds in EVERY connection state, including before the ack. | §3.4, T-1, F-1 |
| **Q5** | F-2..F-6 as guide edits, F-7 excluded? | **Accept**, C-1 riding the implementation (F-4 "error is terminal" simplifies the firmware state machine). | §7 |
| **Q6** | Replay the handshake invalid cases against the real handlers? | **Accept** — the c2s `required` lists and `expect` must be proven. | §5 L4b |
| **Q7** | Negative transcripts now or later? | **Accept a later minor.** | — (not in `v1.1.0`) |
| **Q8** | Case-id and file-name style? | **Accept as proposed, plus one L1 rule** — only `[a-z0-9._/-]`, unique after mapping every other character to `_`. | §3.1, §5 L1 |

**Changes requested (non-blocking; all land before the cut):**

1. *s2c `invalid` needs a stated client obligation* — accepted; the sentence is §3.4 and goes
   into the guide.
2. *Streaming order is over-specified* — accepted; order is normative per connection AND
   direction plus the causal pairs (T-7, T-8), and repeatable lines carry `"repeat": true`
   (§4).
3. *Fixture values must be real* — accepted; L4 and L6 compare every first valid case and
   every transcript line with a recorded frame (§5).

**Versioning (§6):** no objection — a corrected case is a minor, names are never renamed
inside a major, `core_format` accepted as written.

**The reviewer's two questions back:** (a) the MAY-reject wording for s2c `invalid` —
**confirmed** (§3.4); (b) will L6 tolerate a variable number of `partial` frames — **yes**
(§5: per-direction comparison, a `repeat` line matches zero or more).

---

## 11. Implementation record (ARCH-61..64, 2026-10-05)

Built as §9 planned; `ws-protocol-v1.1.0` enumerates the guide and the eleven files. What
changed against the text above while building, and why:

- **`channels` in `frames.golden.json` names each channel's `opening`, `ack` and `error`
  frame** (not in §3.1). A data-driven harness applies T-1/T-7 without a table of its own.
- **Every s2c valid case is a recorded frame**, not only the first (§5 L4 is stricter than
  planned); the one synthetic valid case per frame is `…/unknown-field`, derived from `plain`.
- **F-11 (found by the witness tests): reply audio is conformed DOWN only.** The guide said
  the burst is "already converted to the rate/channel count you registered"; a lower-rate
  voice arrives at its own rate, and `speak_begin` is what a device plays by. Guide corrected;
  case `reply.speak_begin/lower-rate-than-registered`.
- **F-12: `mode: "streaming"` against a recognizer that cannot stream behaves as batch.**
  Shipped and tested since ARCH-10, never stated. Guide sentence added.
- **L7 checks client frames the server ACCEPTED**, not all that were sent: the schema types
  `audio_out.rate`, the shallow definitions do not, and the server does reject a non-numeric
  one.
- **L2 landed with the cut and gained a fourth check** — every key name and vocabulary value
  the files use must be named in the guide's section (the mechanical form of review
  condition Q3).
- **The CLAUDE.md amendment is NOT in the cut commit** — see ARCH-65.
