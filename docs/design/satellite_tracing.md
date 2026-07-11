# Satellite tracing — the end-to-end utterance trace (ARCH-37)

**Status: AGREED 2026-07-07 (interactive design session). T-1..T-6 all user-approved.**

One utterance, one trace, two machines: the satellite captures its device-side story (mic →
VAD → wake gate → uplink → reply playback) AND receives the controller's execution trace over
a wire-contract extension, merging both into a single self-contained file. This is the
bring-up debugging story for room nodes — «it heard me but did nothing» becomes readable:
was it VAD, the wake gate, the uplink, ASR, or the intent?

Builds on ARCH-19 (the trace system — `TraceContext`, self-contained envelopes, save-every-
request policy, retention) and ARCH-35/36 (the satellite + the §3/§4 wire contracts).

## 1. Decisions

- **T-1 — delivery = in-band WS frame; `wants_trace` is a first-class contract field.**
  `register` gains `wants_trace` (**default `false`** — the ESP32 firmware implements the
  field, not merely tolerates a surprise frame; a device that doesn't ask never sees one).
  When granted, each `response` is followed by exactly one `{"type":"trace"}` TEXT frame
  carrying the controller's self-contained trace envelope. Correlation is socket ordering;
  the latency-critical `response` frame stays lean; the extension rides the nginx mTLS `/ws/`
  proxy unchanged (a REST pull would need a new hole in that wall). Applies to both `single`
  and `streaming` modes (one trace frame per response).
- **T-2 — controller gate: `[trace] allow_remote_request = false` by default.** A remote
  client asking the server to run capture is a capability, so it is deliberate opt-in per
  deployment. The grant is acknowledged in the `registered` frame (`"trace": true|false`) —
  the satellite knows deterministically whether trace frames will follow; a decline is
  recorded in the satellite's own trace file («controller declined»), visible, not silent.
  Remote-requested traces are NOT persisted on the controller unless its own `[trace]
  enabled` says so (the existing save-every-request policy is untouched).
- **T-3 — artifact = one merged self-contained file, written by the satellite** under its
  `<assets_root>/traces/` (existing ARCH-19 rotation/retention applies): device stages first,
  the controller's envelope nested as `controller_trace`, reply playback last. One file tells
  the whole story; `irene-replay-trace` learns to display the nested section. Controller
  stages replay on the controller as today — the merged file is the forensic/listening
  artifact, and the raw-mic stage stays replayable through the satellite pipeline for
  `[vad]` tuning.
- **T-4 — device capture = the full story.** Raw pre-canonical mic audio (`--trace-raw-mic`,
  bounded ring), per-frame VAD verdicts (`VoiceSegmenter(collect_vad_frames=True)`), wake
  detections with confidence + armed-window decisions (sent vs skipped-outside-window),
  uplink lifecycle (connect/re-register, the verbatim `response` or `error`, timing), and
  the reply audio exactly as played (captured at the `/ws/audio/reply` playback seam — no
  server help needed).
- **T-5 — scope: `single` mode.** Streaming mode bypasses VAD/wake on the device (the
  always-on model), so a device-side trace there is just the remote trace; v1 keeps `--trace`
  meaningful in `single` mode and notes the limitation. Reply audio is attached when it
  arrives before the next utterance (or shutdown) — no timers, deterministic.
- **T-6 — locveil-commons: no change required.** `wants_trace` defaults to `false`, so the
  existing `ws_audio_provider` register produces today's behavior byte-for-byte, and the
  voice WS protocol is not part of the bridge contract pin. Optional later enhancement:
  the eval provider requests traces to enrich failure diagnostics.

## 2. Wire contract extension (amends `python_satellite.md` §3 — the single written truth)

```
client → TEXT   {"type":"register", ..., "wants_trace":false}     # default false
server → TEXT   {"type":"registered", ..., "trace":true|false}    # the grant, explicit
...utterance cycle as before...
server → TEXT   {"type":"response", ...}
server → TEXT   {"type":"trace","request_id":..,"trace":{...}}    # only when granted; 1 per response
```

The `trace` payload is the controller's ARCH-19 envelope (`TraceContext.build_envelope()`),
self-contained and JSON-safe. Error paths: if the utterance errors server-side, the `error`
frame may be followed by a trace frame carrying whatever was captured.

## 3. The merged file (satellite side)

The satellite's `TraceContext` envelope, extended with two satellite-only keys:

- `controller_trace` — the received remote envelope (or `{"declined": true}` /
  `{"missing": "<reason>"}` when absent);
- `reply_audio` — `{data: base64 PCM, rate, channels}` as played.

Device stages recorded via the standard `record_stage` API: `wake_gate` (detections,
armed-window verdicts), `uplink` (send/response), plus `vad_frames` and the raw-mic
`replay.input`. Saved as `<traces_dir>/<request_id>.json`, same rotation cap as the
controller (`MAX_TRACE_FILES`).

## 4. Implementation (filed at design completion → ARCH-38)

1. `TraceConfig.allow_remote_request` (default false) + config-ui parity + config-master.
2. Server: `wants_trace` in register → grant in `registered` ack; per-utterance remote-
   requested `TraceContext` threaded through both WS branches; trace frame after response.
3. `SatelliteLink`: `wants_trace` + grant parse + trace-frame consumption (bounded wait).
4. Satellite recorder: raw-mic ring, VAD frames, wake/uplink stages, reply capture at the
   playback seam, merged-envelope save + rotation; wired under the runner's `--trace`.
5. `irene-replay-trace`: display the nested `controller_trace` section.
6. Tests (loopback: grant/decline, trace-follows-response, merged file shape) + guide/docs.
