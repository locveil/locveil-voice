# WebSocket streaming-input transport (ESP32) — design (ARCH-6)

**Status:** core implemented 2026-06-03 (transport + identity). Device-model half deferred (see §7).
**Deliverable of:** ARCH-6 [WS]. **Pairs with:** ARCH-7 [MQTT] (return/actuation), ARCH-9 [INFER].

## 0. Why this exists
The old driving-input audio path — `InputManager._input_queue` fed by a base64 `AUDIO_DATA:` text frame
(`inputs/web.py`) — was a broken placeholder (P0-8). ARCH-6 replaces it with a proper **WebSocket streaming
driving-input adapter**: an ESP32 mic-node streams raw audio over a WS connection that first **registers its
physical identity** (room + devices), and the server runs the full pipeline and streams a response back.

**Server-first design.** The in-repo `ESP32/` firmware spec (rev 2, Jul 2025) is **stale** and treated as
*inspiration only*. This document defines the contract the **server** expects; the firmware is (re)written to match.
_QUAL-19 (2026-06-09) reviewed the `ESP32/` tree:_ a real-but-incomplete ~5k-LOC skeleton (solid state machine /
I2S / WiFi-TLS-WebSocket / TFLite-Micro wake-word integration, but won't link — absent embedded model+certs,
`kitchen/main/CMakeLists.txt:9-12`; ES8311 codec + display are stubs). **Kept in-repo as quarantined reference**
(not buildable firmware). On-device wake **and** VAD are the **microWakeWord + microVAD "micro" stack** (ESPHome
`micro_wake_word` with `vad:` gating, TFLite-Micro) — the same model artifacts run server-side via the `pymicro-*`
libs (`onnx_inference_layer.md` §11). Evidence + keep/fix/cut: `docs/review/esp32_wakeword_review.md`.

## 1. Transport
- **WebSocket over TLS (`wss`)**, mutual-TLS terminated by an **nginx reverse-proxy** in front of the Irene
  WebAPI (the firmware spec's model; the app itself sees a plain WS after nginx). The app does not implement TLS.
- **Audio:** raw **PCM, 16 kHz, 16-bit, mono**, little-endian, sent as **binary** WS frames. (Matches the existing
  `/asr/binary` convention so the ASR side is unchanged.)
- **Wake word runs on-device** (ESP32 microWakeWord). The device only opens the stream *after* a local wake — so
  the server runs with **`skip_wake_word=True`** for this transport; there is no server-side voice-trigger on this
  path (server VAD/voice-trigger remains only for a local-mic input).

## 2. Connection lifecycle
```
client → server:  WS connect (wss, mutual-TLS via nginx)
client → server:  TEXT frame  — registration handshake (JSON, §3)
server → client:  TEXT frame  — handshake ack { "type":"registered", "client_id", "session_id" }
client → server:  BINARY frames — raw PCM, streamed until end-of-utterance
client → server:  TEXT frame  — { "type":"end" }   (or a short silence / client-side VAD close)
server:           AudioData → workflow_manager.process_audio_input(client_context=…)  (full pipeline)
server → client:  TEXT frame  — { "type":"response", "text", "metadata" }
server → client:  BINARY frames (optional) — TTS audio if wants_audio (ARCH-7 return channel; phase 2)
  … loop (next utterance reuses the same registered session) …
```

## 3. Registration handshake — the identity linchpin
The first text frame registers the node in the **`ClientRegistry`** (the Q6/QUAL-28 physical-identity store),
which is what makes contextual "stop"/"louder" resolve to the right room even after the conversation session ends.

```json
{
  "type": "register",
  "client_id": "kitchen_node",
  "room_name": "Кухня",
  "available_devices": [
    { "id": "kitchen_light", "name": "потолочный свет", "type": "light",
      "capabilities": {"dimmable": true}, "location": "Кухня" }
  ]
}
```
Maps 1:1 onto the existing `ClientRegistration` / `ClientDevice` dataclasses (no model change). The adapter calls
`get_client_registry().register_client(registration)`, then threads `client_id`/`room_name`/`device_context` into
every subsequent utterance's `client_context`.

## 4. The activation — `resolve_physical_id`
`resolve_physical_id(client_id, room_name, session_id)` already returns `client_id or room_name or session_id`.
It needs **no rewrite** — it activates the moment the handshake populates `client_id`. The adapter passes
`client_context={client_id, room_name, device_context, skip_wake_word: True}` into
`workflow_manager.process_audio_input(...)`, which builds the `RequestContext` (it already reads exactly these
keys), so `context.client_id`/`room_name` flow through and the action store + contextual resolution key off the
**physical origin** instead of the ephemeral session id. **This is the whole "room/device story switches on" step.**

## 5. Pipeline wiring
Audio frames are accumulated into an `AudioData` and handed to `core.workflow_manager.process_audio_input(
audio_data, session_id=<registered>, wants_audio=<from handshake>, client_context=<§3>)` — the same full
ASR→NLU→intent→action path the `/asr` JSON endpoint uses (NOT the ASR-only `/asr/binary` transcription utility).
The `IntentResult` text is returned as a `response` text frame; audio response is the ARCH-7 phase-2 return channel.

## 6. Endpoint
`/ws/audio` on the WebAPI (driving input), distinct from the existing ASR-utility `/asr/stream` (JSON transcription)
and `/asr/binary` (binary transcription). One registered session per connection; reconnect re-registers.

## 7. Deferred to ARCH-7 / QUAL-35 (device-model half)
At design time **no device/room handlers exist** (all 13 donation `entity_type` decls are `generic`; no
device/room/location params; no smart-home/MQTT handler). Authoring non-generic `entity_type`/`room_context` and
swapping the `_is_device_entity`/`_is_location_entity` heuristics for declarative resolver-selection now would build
an **inert branch** (the ledger's own warning). These move to where their handlers will live:
- **ARCH-7 [MQTT]** — the Wirenboard device commands + the return/actuation channel.
- **QUAL-35** — T2/T3 NLU for the complex device/room commands.
The handshake already *carries* `available_devices`, so the registry is populated and ready the day those land.

## 8. Out of scope here
TLS/cert provisioning (nginx + the firmware's local-CA), OTA, the ESP32 firmware itself, and the TTS audio
return channel (ARCH-7). Server-side voice-trigger + the `WakeWordResult` bug are a local-mic concern, not this path.
