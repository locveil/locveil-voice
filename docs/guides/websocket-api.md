# WebSocket API

**Protocol version: 1** (`ws-protocol-v1.2.0`) — the server confirms it as `protocol_version` in
every `registered` ack, so a client can check what it was built against instead of trusting
prose. That served number is the protocol's **major** version: it moves only on a breaking wire
change. The contract tag carries the full three-part version — an additive change to the wire is
a minor release, an edit to this document that leaves the wire untouched is a patch — and neither
of those changes the number the server sends.

Irene exposes four WebSocket channels. Two of them are the **voice wire protocol** — how a
satellite (an ESP32 in a room, or any client with a microphone) streams speech in and gets the
spoken reply back. The other two are **operator channels** — a push channel for deferred text
results and a live tap on the pipeline's event bus. REST endpoints are documented interactively
at `/docs`; this guide is the equivalent reference for the sockets.

![The four WebSocket channels](../images/ws-protocols.png)

Every channel speaks the same dialect: **JSON text frames** for control and **raw binary
frames** for audio. Every frame the server sends carries a `type` field, and so does every
client frame on the two voice channels; the opening frames of the two operator channels carry
none and are recognized by their position. Audio is always **16-bit little-endian PCM**. What
a device sends is **mono**; 16 kHz is the pipeline's canonical rate — declare your real rate at
registration and keep it honest, the server does not guess. What a device receives is in the
format it registered for its reply channel.

**Errors are terminal.** On a protocol violation the server answers
`{"type": "error", "error": "..."}` and then closes the connection: an `error` frame is always
the last frame on its socket. The text is for people and logs — do not parse it. A device that
receives one reconnects and registers again.

**Growing without breaking.** Ignore JSON keys you do not know, and ignore text frames whose
`type` you do not know — in every state of a connection, including before your registration is
confirmed. The server does the same: it ignores keys it does not know, and, once a channel's
opening frame has been accepted, frames of a type it does not know. (The opening frame is the
one exception — until it has arrived, any other frame is a violation.) This is what lets a
later release add a field or a frame without breaking a device already in the field; clients
are bound by it from `ws-protocol-v1.1.0` on.

## `/ws/audio` — voice input

The driving input for a device that already did wake-word detection on its own hardware (the
satellite case). One connection serves **many utterances**; the session — and with it room and
conversation continuity — lives as long as the socket.

**1. Register.** The first frame must be a text frame:

```json
{
  "type": "register",
  "client_id": "kitchen_node",
  "room_name": "Кухня",
  "sample_rate": 16000,
  "wants_audio": true,
  "mode": "streaming",
  "wants_trace": false
}
```

`client_id` is the device's stable identity — replies, timers and missed announcements are
addressed to it. `room_name` is the device's primary room. These two and `type` are the only
required keys: a registration without either is refused with an `error`. So is one in which a
key has the wrong JSON type — a `client_id` that is a number, a `sample_rate` written as a
string: the types are listed in the frame reference at the end of this document, and the server
checks them instead of guessing what was meant. `sample_rate` is the rate of the PCM you are
about to send, a positive integer; if you leave it out the server assumes 16000.
`covered_rooms` (optional list) adds rooms the device also manages. `wants_audio: true` asks for
spoken replies — which arrive on the **reply channel** (below), never on this socket.
`wants_trace: true` (default `false`) asks for the server's execution trace after each response
— see **Execution traces** below. Optional extras: `name` (human-friendly device name) and
`available_devices` (what the device can actuate — reserved for the smart-home integration).

A device should also report what it was **built against** — three optional version fields:
`protocol_version` (the protocol version its client code implements), `firmware_version`
(its own software version; the bundled satellite runner sends the Irene package version),
and `wake_pack_version` (the wake-word pack it has flashed, e.g. `"wake-pack-v1"` — for
devices that do their own wake-word detection). None of them gates registration; they let
the server's client registry spot a stale device instead of debugging it blind.

The server confirms: `{"type": "registered", "client_id": "...", "session_id": "...",
"trace": false, "protocol_version": "1"}` — `trace` is the explicit answer to `wants_trace`
(it stays `false` unless the server's operator has enabled remote trace requests), and
`protocol_version` is the server's wire-protocol version (the number at the top of this
document): if it isn't what your client was built against, expect breakage and say so loudly.

When the connection comes through the fleet's mutual-TLS gate, the certificate is the
identity: a `client_id` that doesn't match the certificate's common name is refused at
registration. Plain connections on a trusted network are not affected.

**2. Stream audio.** Send binary PCM frames. What ends an utterance depends on the mode:

- **`mode: "streaming"`** — for always-on devices. If the configured speech recognizer supports
  true streaming, the **server** detects the end of the utterance from the audio itself; the
  device just keeps streaming (silence included) and never needs to signal anything. You'll
  receive `{"type": "partial", "text": "..."}` frames as recognition progresses — how many
  depends on the recognizer, and they arrive while you are still sending audio. A device may
  still send `{"type": "end"}` to hard-finalize, and a client that stops sending mid-utterance
  is finalized after a 10-second idle timeout rather than left hanging. If the recognizer does
  not support streaming, the connection behaves as batch even though you asked for streaming.
- **default (batch)** — any other `mode` value, or none at all. For push-to-talk-style
  clients. Stream the utterance's PCM, then send `{"type": "end"}`. As a safety net, an
  utterance is force-finalized at 60 seconds if the end frame never comes.

**3. Get the result.** One frame per utterance:

```json
{
  "type": "response",
  "text": "Таймер на 5 минут запущен",
  "success": true,
  "error": null,
  "confidence": 1.0,
  "intent_name": "timer.set",
  "timestamp": 1750000000.0,
  "metadata": { "...": "raw execution metadata" }
}
```

This is the same canonical result shape the REST `/execute/command` endpoint returns — `text`
is the reply, `intent_name` says what was recognized, `success`/`error` report the outcome.
All eight keys are always present. A command that fails is still a `response`: `success` is
`false` and `error` holds the reason; `error` and `intent_name` are `null` when there is
nothing to report. Then the loop re-arms for the next utterance.

**4. Execution traces (optional).** If registration asked for traces *and* the server granted
them (`"trace": true` in the confirmation), each response is followed by exactly one extra
text frame:

```json
{ "type": "trace", "request_id": "…", "trace": { "…": "the full execution trace" } }
```

The payload is the same self-contained trace document the server's own tracing writes —
every pipeline stage with its timing, the recognition verdicts, the recorded output (see
[tracing & replay](tracing.md)). Granting is the server operator's decision:
`[trace] allow_remote_request = true` in the server's configuration; without it,
`wants_trace` is answered with `"trace": false` and no trace frames are ever sent. A client
that didn't ask never sees this frame — firmware can ignore the feature entirely by
registering with the default.

## `/ws/audio/reply` — spoken replies

The return half of the satellite pair. The device opens this socket, registers, and then only
**listens** — the server pushes synthesized speech whenever a reply (or a later event, like a
timer firing) is addressed to this device.

Register with the device's *output* audio contract:

```json
{ "type": "register-reply", "client_id": "kitchen_node", "audio_out": { "rate": 22050, "channels": 1 } }
```

`type` and `client_id` are required. `audio_out` states what the device can play: `rate` in Hz
and `channels`, both positive integers. It may be left out — the server then assumes 22050 Hz
mono — but a device should always state it. As on `/ws/audio`, a key of the wrong JSON type —
a numeric `client_id`, a `rate` written as a string — is refused with an `error`. After this
opening frame the device has nothing more to say: the server ignores anything else it sends
on this socket.

The same certificate rule as `/ws/audio` applies behind the mutual-TLS gate: a device can only
claim its own reply channel — otherwise it would receive another room's speech.

After `{"type": "registered", "client_id": "...", "protocol_version": "1"}`, each spoken
reply arrives as a bracketed binary burst:

```
{"type": "speak_begin", "rate": 22050, "channels": 1, "width": 16, "seq": 1}
<binary PCM frames>
{"type": "speak_end", "seq": 1}
```

The audio is already converted to the rate/channel count you registered — play it as it comes.
The server converts in both directions: a voice recorded at a lower rate is brought up to your
rate, a richer one down, and a mono voice is spread over the channels you asked for; a reply
that cannot be converted is not sent at all. `speak_begin` states what is being sent — `rate`
in Hz, `channels`, and `width`, the sample size in bits, which is always 16 — and its `rate`
and `channels` always equal what you registered. `seq` pairs the begin/end brackets and counts
the bursts of the connection: 1, 2, 3, … (a new connection starts again at 1). Bursts never
overlap: when two replies are due at the same moment — a spoken answer and a timer
announcement — the second waits, and its `speak_begin` comes only after the first one's
`speak_end`. Binary frames arrive only between a `speak_begin` and its `speak_end`. One more
thing happens at connect time: if anything fired while the device was offline — a timer that
rang during a reboot — the missed announcement is spoken to the device as soon as the channel
is up.

## `/ws/output` — pushed text results

The push channel for text clients (the built-in web app uses it). Synchronous commands get
their answer in the HTTP response of `POST /execute/command`; this socket exists for the
**deferred** results — a timer set from the browser fires ten minutes later, and the
notification needs somewhere to go.

Send a first frame with your identity, or an empty `{}` to have one minted:

```json
{ "client_id": "web_abc123" }
```

The server answers `{"type": "connected", "client_id": "web_abc123"}`. Include that same
`client_id` in your `POST /execute/command` metadata, and deferred results addressed to it
arrive here as `{"type": "message", "text": "..."}` frames. Requires `[outputs] web_push`
(on by default).

This channel never rejects its opening frame: a first frame without a usable `client_id` — an
empty object, a `client_id` that is not a string, even text that is not JSON — simply gets a
minted identity. The one `error` you
can meet here is sent before your frame is read, when the push channel is switched off. After
the opening frame the server ignores whatever the client sends.

## `/ws/observe` — live pipeline tap

A read-only debugging tap on the event bus: watch inputs arrive, results being produced and
outputs delivered, live, for the whole system or one room. Off by default — it exposes what the
household says. Enable it by setting `[system] observe_token`; remote (non-localhost) access
additionally needs `[system] observe_allow_remote = true`.

Authenticate and optionally filter in the first frame:

```json
{ "token": "...", "filter": { "room_name": "Кухня", "types": ["result.produced"] } }
```

`token` is required — a missing or wrong one is answered with an `error` — and `filter` is
optional; a `filter` that is not an object, or one of whose keys has the wrong type, is refused
the same way. After `{"type": "subscribed"}`, events stream in:

```json
{ "type": "event", "event": "result.produced", "session_id": "...", "client_id": "kitchen_node",
  "room_name": "Кухня", "source": "ws_audio", "payload": { "...": "..." }, "timestamp": 1750000000.0 }
```

The filter accepts `types` (a list of event names) and the strings `session_id`, `client_id`,
`room_name` and `source`; omit it to see everything. In an event the four identity keys are always present and are `null` when the event
has no such origin. After the opening frame the server ignores whatever the client sends. See
[the workflow guide](../architecture/workflow.md) for what the events mean.

## Trying it from Python

A minimal batch-mode exchange, start to finish:

```python
import asyncio, json, wave, websockets

async def say(wav_path: str):
    async with websockets.connect("ws://localhost:8080/ws/audio") as ws:
        await ws.send(json.dumps({"type": "register", "client_id": "probe",
                                  "room_name": "Тест", "sample_rate": 16000}))
        print(json.loads(await ws.recv()))          # {"type": "registered", ...}
        with wave.open(wav_path, "rb") as w:        # 16 kHz mono PCM16
            await ws.send(w.readframes(w.getnframes()))
        await ws.send(json.dumps({"type": "end"}))
        print(json.loads(await ws.recv()))          # {"type": "response", "text": ...}

asyncio.run(say("command.wav"))
```

For scripted testing against these endpoints, the evaluation suite in [`eval/`](../../eval/README.md)
drives `/ws/audio` with recorded fixtures — see [how to add a test](howto-new-test.md).

## The machine-readable core

Everything above is the protocol. Beside it, the folder `contracts/ws-protocol/` holds the same
protocol as data — written for a test harness rather than a reader, so that a client in any
language can check its parser and its state machine against files instead of against prose:

| File | What it holds |
|---|---|
| `frames.golden.json` | every JSON frame of the four channels: its keys and their types, and example frames that are valid, invalid, or of an unknown type |
| `transcript.audio-batch.jsonl` | batch mode: register, then two utterances on one connection (the second command fails) |
| `transcript.audio-streaming.jsonl` | streaming mode: the server ends the first utterance itself, the device ends the second with `end` |
| `transcript.audio-trace.jsonl` | execution traces granted: a `response`, then one `trace` |
| `transcript.audio-rejected.jsonl` | a wrong first frame: `error`, then the server closes |
| `transcript.reply-burst.jsonl` | the reply channel: two spoken replies as bracketed bursts |
| `transcript.satellite-pair.jsonl` | both voice channels of one device: an utterance and its spoken reply |
| `transcript.reconnect.jsonl` | both channels drop and are reopened; a missed announcement is spoken |
| `transcript.output-push.jsonl` | `/ws/output`: identify, then a pushed `message` |
| `transcript.observe-tap.jsonl` | `/ws/observe`: subscribe with a filter, then an `event` |
| `ws-protocol.schema.json` | a JSON Schema (draft 2020-12) for every frame, for host-side tools |

These files are written by hand and are **subordinate to this document**: where one of them
disagrees with the text above, the text is right and the file has a bug. They are checked
against the reference server on every change: apart from the cases built to carry a key that
no version defines, every valid server frame in them is a frame it really sent, and every
transcript is a conversation it really had. They are released together with this document
under the same version tag.

### Ground rules for a harness

- The files are strict JSON (`.json`) or one JSON object per line (`.jsonl`), UTF-8, no
  comments. Text values are deliberately not all ASCII (`"Кухня"`).
- **Ignore keys you do not know in these files too.** The format grows by adding keys;
  `core_format` is `1` and stays `1` as long as that is all that happens. A reshaping that
  would break a harness is never done in place — it would arrive as new files with new names
  beside the old ones.
- **Names are stable.** File names, frame names, case ids and transcript names are never
  renamed or removed while the protocol version at the top of this document stays `1`. They use
  only the characters `a`–`z`, `0`–`9`, `.`, `_`, `/` and `-`, and stay unique when every
  character other than a letter or digit is replaced by `_` — so they can be turned into
  identifiers in generated code. A case that should no longer be checked is kept and marked
  `"retired": true`; skip it. A retired case states nothing any more — the server no longer
  sends such a frame (or no longer answers that way) and a receiver owes it nothing, whatever
  its `verdict` still says; its `note` says which release retired it and why.
- **What a release of the core means.** Anything a harness can observe — a case, a transcript
  or a file added, a case corrected — is a minor release. A patch release never changes what a
  harness sees.
- Binary frames are never stored. They are described (`binary` in the frames file) or marked
  (a `binary` line in a transcript); the audio itself is not part of any file.

### Frame reference

A frame is named `<channel>.<type>`. The channels are `audio` (`/ws/audio`), `reply`
(`/ws/audio/reply`), `output` (`/ws/output`) and `observe` (`/ws/observe`). The two opening
frames that carry no `type` are named after what they do: `output.hello` and
`observe.subscribe`. The direction is `c2s` (client to server) or `s2c` (server to client).

Each key is listed with its JSON type: `string`, `integer` (a number without a fractional
part), `number`, `boolean`, `object`, `array`, or `null`; `string/null` means either. A
required key is always present in a valid frame.

| Frame | Direction | Required keys | Optional keys | Opaque | Volatile |
|---|---|---|---|---|---|
| `audio.register` | c2s | `type:string` `client_id:string` `room_name:string` | `sample_rate:integer` `wants_audio:boolean` `mode:string` `wants_trace:boolean` `covered_rooms:array` `name:string` `available_devices:array` `protocol_version:string` `firmware_version:string` `wake_pack_version:string` | — | — |
| `audio.end` | c2s | `type:string` | — | — | — |
| `audio.registered` | s2c | `type:string` `client_id:string` `session_id:string` `trace:boolean` `protocol_version:string` | — | — | `session_id` |
| `audio.partial` | s2c | `type:string` `text:string` | — | — | — |
| `audio.response` | s2c | `type:string` `text:string` `success:boolean` `error:string/null` `confidence:number` `intent_name:string/null` `timestamp:number` `metadata:object` | — | `metadata` | `timestamp` |
| `audio.trace` | s2c | `type:string` `request_id:string` `trace:object` | — | `trace` | `request_id` |
| `audio.error` | s2c | `type:string` `error:string` | — | — | — |
| `reply.register-reply` | c2s | `type:string` `client_id:string` | `audio_out:object` | — | — |
| `reply.registered` | s2c | `type:string` `client_id:string` `protocol_version:string` | — | — | — |
| `reply.speak_begin` | s2c | `type:string` `rate:integer` `channels:integer` `width:integer` `seq:integer` | — | — | — |
| `reply.speak_end` | s2c | `type:string` `seq:integer` | — | — | — |
| `reply.error` | s2c | `type:string` `error:string` | — | — | — |
| `output.hello` | c2s | — | `client_id:string` | — | — |
| `output.connected` | s2c | `type:string` `client_id:string` | — | — | — |
| `output.message` | s2c | `type:string` `text:string` | — | — | — |
| `output.error` | s2c | `type:string` `error:string` | — | — | — |
| `observe.subscribe` | c2s | `token:string` | `filter:object` | — | — |
| `observe.subscribed` | s2c | `type:string` | — | — | — |
| `observe.event` | s2c | `type:string` `event:string` `session_id:string/null` `client_id:string/null` `room_name:string/null` `source:string/null` `payload:object` `timestamp:number` | — | `payload` | `timestamp` |
| `observe.error` | s2c | `type:string` `error:string` | — | — | — |

An **opaque** key holds a free-form object whose content this protocol does not define — pass
it on or ignore it, never depend on its shape. A **volatile** key has a different value on
every run; a harness compares that it is present and has the right JSON type, never its
value. The `error` text of an `error` frame is not volatile but is wording, not protocol —
do not compare it either. `audio_out` and `filter` are objects whose keys are described in
their channels' sections above.

### `frames.golden.json`

The top level:

- `contract`, `protocol_major`, `core_format` — which protocol this is, the protocol version
  at the top of this document, and the format of the file itself.
- `channels` — for each channel its `path`, and the names of three frames: `opening` (the
  frame a client must send first), `ack` (the server's confirmation of it) and `error`.
- `binary` — where binary frames occur, keyed by `<channel>.<direction>`: `content` (always
  `pcm_s16le`), `channels` when fixed, `rate_from` / `channels_from` (the frame key that states
  the sample rate / channel count), and `only_between` (the two frames that bracket a burst).
- `frames` — one entry per frame name: `channel`, `direction`, `type` (the value of the
  frame's `type` key, or `null` for the two opening frames that have none), `required` and
  `optional` (the frame's keys), `types` (the JSON type of each key, as in the table above;
  a list means "either"), `opaque`, `volatile`, and `cases`.
- `unknown` — frames whose `type` no version of this protocol defines, each with the
  `channel` and `direction` it would arrive on.
- `malformed` — text frames that are not a JSON object at all; they belong to no channel.

A case has an `id` (unique in the file: `<frame>/<what it shows>`), a `verdict`, and the
frame itself: `json` (a JSON object) or, when the frame is not a JSON object, `raw` (its
literal text). An invalid case names its `violation`. A case may carry a `note` — a remark
for people, never for a harness — and `retired`.

**What a receiver owes each verdict.** This is part of the protocol:

- `valid` — the receiver **must accept** the frame. Every frame has one case named
  `<frame>/unknown-field`: an ordinary frame plus one key that no version defines. It is
  valid, and must be accepted.
- `unknown` — the receiver **must ignore** the frame and keep the connection, in every state
  of the connection, including before registration is confirmed.
- malformed (the `malformed` list) — the receiver **must survive** it.
- `invalid` — the receiver **may reject** the frame (drop it, or close the connection and
  reconnect) or **may tolerate** it (use the parts it understands); it **must not fault**.
  This freedom is itself part of the contract: no later release with protocol version `1`
  will turn it into "must reject".

The `violation` of an invalid case is one of `not-json`, `not-an-object`, `missing-type`
(the `type` key is absent), `missing-required` (one required key is absent) and
`wrong-json-type` (one key has the wrong JSON type). Exactly one thing is wrong with each
invalid case. More codes may be added later.

Cases of frames the **client** sends are read from the server's side. A valid opening frame
is one the server accepts as far as its shape goes: unless something else stands in the way
(a wrong token, a certificate that does not match), it is answered with the channel's `ack`.
An invalid one carries `expect` — what the server does with it: `frame`, the name of the
frame it answers with, and `then`, which is `close`. The core marks a client frame invalid
only where this document promises that reaction, so every such case has an `expect`; cases of
frames the server sends never have one. From `ws-protocol-v1.2.0` on that covers an opening
frame in which a key has the wrong JSON type (`wrong-json-type`), on the three channels that
refuse one; `output.hello` has no invalid cases, because `/ws/output` answers an unusable
opening frame with a minted identity instead of an `error`. An `unknown` frame from the client
is ignored by the server once the opening frame has been accepted.

### Transcripts

A transcript is one scenario: one JSON object per line, in an order the wire can produce, so
a harness may replay a file from top to bottom. Every line has a `kind`:

- `meta` — the first line, exactly once: `transcript` (the scenario's name, as in the file
  name), `core_format`, `protocol_major`, `channels` (the channels the scenario uses),
  `ordering` (see below) and a `note` for people.
- `open` — a connection is opened: `conn`, a label for it that is local to the file, and its
  `channel`. A reconnect is a `close` followed by an `open` with a **new** label on the same
  channel; two labels can be alive at once (a device's two voice channels).
- `text` — one JSON text frame: `conn`, `channel`, `direction`, `frame` (its name in
  `frames.golden.json`) and `json` (the frame — always a valid instance of the frame it
  names). A line marked `"repeat": true` may occur any number of times at that point,
  including not at all: the `partial` frames of a streaming utterance.
- `binary` — a **run of one or more** binary frames: `conn`, `channel`, `direction`,
  `content` (`pcm_s16le`) and `bytes`. How a run is split into frames carries no meaning in
  this protocol, so a run is one line. `bytes` is the size of the run in the recording the
  transcript was taken from — an illustration, never something to assert.
- `close` — the connection ends: `conn` and `by`, which is `client`, `server`, or `network`
  (the connection dropped without a closing handshake — a power loss).

`ordering` is always `per-connection-and-direction`: the order of the lines is binding within
one connection **and one direction**. A transcript does not promise how the frames of one
direction fall between the frames of the other — in streaming mode the server's `partial`
frames interleave with the device's audio as the recognizer pleases — nor how two connections
interleave: a spoken reply and the `response` it belongs to travel on different sockets and
may be observed in either order. What the protocol does promise across directions is stated
in rules T-7 and T-8.

The rules below hold on every connection. A harness applies them to every transcript:

- **T-1** — ignoring frames of unknown type, the first frame the server sends on a
  connection is the channel's `ack` or an `error`.
- **T-2** — an `error` frame is the last frame the server sends on its connection, and the
  server closes the connection after it.
- **T-3** — `speak_begin` and `speak_end` pair by `seq`; `seq` counts the bursts of one
  connection, starting at 1.
- **T-4** — binary frames from the server on the reply channel occur only between a
  `speak_begin` and its `speak_end`.
- **T-5** — a `session_id` belongs to its connection: a new connection gets a new one.
- **T-6** — when traces are granted, each `response` is followed by exactly one `trace` on
  the same connection before the next `response`; when they are not, no `trace` is ever sent.
- **T-7** — the server sends a channel's `ack` only after it has received the client's
  opening frame. An `error` may arrive at any time, even before the opening frame is read.
- **T-8** — in batch mode a `response` follows the `end` frame that closed its utterance
  (or the 60-second safety net). In streaming mode `partial` and `response` frames may arrive
  at any time after the `ack`.
- **T-9** — bursts on the reply channel never overlap: the server sends no `speak_begin`
  while a burst is open, that is, before the `speak_end` of the previous one.

### The schema

`ws-protocol.schema.json` restates the frame reference as a JSON Schema for tools that already
speak that language (linting captured traffic, a host-side conformance check). Under `$defs`
it has one entry per frame name and one per channel and direction (`audio.s2c`: any frame the
server may send on `/ws/audio`); validate a frame against one of those. It accepts unknown
keys everywhere, as a receiver must. It is the least of the three: a generalization of the
golden frames, which are themselves instances of this document.
