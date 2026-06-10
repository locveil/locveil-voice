# Voice activity detection (VAD)

VAD decides which slices of incoming audio actually contain speech, so the rest of the pipeline (ASR, then
intent) sees real utterances instead of every chunk of silence. It is a **built-in utility**
(`irene/utils/vad.py`), not a provider you swap — but it has two interchangeable *engines*.

It runs only where Irene has a local microphone. On a Wirenboard install the ESP32 satellite does VAD
on-device, so this guide is for the standalone-mic case.

## How it's wired

VAD sits in the audio processor, ahead of ASR. Two switches must **both** be on for it to run:

- `[vad] enabled = true` — the master switch.
- `[workflows.unified_voice_assistant] enable_vad_processing = true` — the pipeline flag.

## Engines

`[vad] vad_implementation` picks the engine:

- **`energy`** (default) — a lightweight energy / zero-crossing detector, no extra dependencies,
  sub-millisecond per chunk. Setting `use_zero_crossing_rate` or `adaptive_threshold` upgrades the simple
  detector to an adaptive one that tracks the noise floor.
- **`silero`** — the Silero VAD ONNX model (run via sherpa-onnx, 64-bit only; reuses the ASR-ONNX
  dependency). More robust in noise; the model downloads on first use. Tuned with `silero_threshold`.
- **`microvad`** — `pymicro-vad` (64-bit only; the `vad-tflite` extra). Self-contained — bundles its model
  and runtime, nothing to download — and shares its frontend with the microWakeWord trigger, so the two are
  one stack and match what the ESP32 runs on-device. Tuned with `microvad_threshold`. Pick whichever runtime
  your build already loads: `silero` if you're on sherpa-onnx ASR, `microvad` if you're on microWakeWord.

## Configuration

Every real `[vad]` knob:

| Field | Default | Range | Engine |
|---|---|---|---|
| `enabled` | true | — | master switch |
| `vad_implementation` | `energy` | energy / silero / microvad | selector |
| `energy_threshold` | 0.01 | 0–1 | energy |
| `sensitivity` | 0.5 | 0.1–3.0 | energy |
| `voice_duration_ms` | 100 | 10–1000 | both |
| `silence_duration_ms` | 200 | 50–2000 | both |
| `voice_frames_required` | 2 | ≥1 | energy |
| `silence_frames_required` | 5 | ≥1 | energy |
| `use_zero_crossing_rate` | true | — | energy → advanced |
| `adaptive_threshold` | false | — | energy → advanced |
| `noise_percentile` | 15 | 1–50 | energy (advanced) |
| `voice_multiplier` | 3.0 | 1–10 | energy (advanced) |
| `max_segment_duration_s` | 10 | 1–60 | both |
| `buffer_size_frames` | 100 | ≥10 | both |
| `silero_threshold` | 0.5 | 0–1 | silero |
| `silero_model_url` | k2-fsa release URL | — | silero |
| `microvad_threshold` | 0.5 | 0–1 | microvad |
| `normalize_for_asr` | true | — | both |
| `asr_target_rms` | 0.15 | 0.01–0.3 | both |
| `enable_fallback_to_original` | true | — | both |

VAD works on 16 kHz / 16-bit mono PCM; keep `sample_rate = 16000` across microphone/asr (the device's native
rate is resampled up the pipeline). The last three knobs normalise a detected segment's loudness before ASR.

## Tuning

Start from `energy` and adjust by symptom:

- **Noisy room** — raise `energy_threshold`, lower `sensitivity`, try `adaptive_threshold = true` (or switch
  to `silero`).
- **Quiet speaker, words clipped** — lower `energy_threshold`, raise `sensitivity`.
- **Choppy segments** (one sentence split in two) — raise `silence_duration_ms` / `silence_frames_required`.
- **Laggy** (waits too long to cut off) — lower them.

## Performance

The energy engine is effectively free; Silero adds a small ONNX inference cost but stays real-time. On weak
hardware stay on `energy` and leave `use_zero_crossing_rate` / `adaptive_threshold` off. The real limits on
segment handling are `max_segment_duration_s` (caps a runaway segment) and `buffer_size_frames`.

## Troubleshooting

- **No speech detected** — confirm both switches are on; lower `energy_threshold` / raise `sensitivity`;
  check the mic actually produces audio (see [audio](audio.md)).
- **False positives** (noise triggers it) — raise `energy_threshold`, lower `sensitivity`, try
  `adaptive_threshold` or `silero`.
- **Choppy or merged segments** — tune the timing knobs above.
- **Poor ASR on short commands** — segments may be too small; raise `voice_duration_ms`; keep
  `normalize_for_asr` on.

At startup VAD logs `INFO … VAD audio processor initialized: threshold=…, sensitivity=…`. To watch live
levels, a chunk's RMS is `sqrt(mean(samples²)) / 32768`.

Reference configs to copy: `configs/vad-development.toml`, `configs/vad-production.toml`, and the documented
`[vad]` section of `configs/config-master.toml`.
