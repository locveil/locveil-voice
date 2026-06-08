# Voice trigger (wake word)

The voice trigger listens for a wake word and only then wakes the rest of the pipeline, so Irene isn't
transcribing all day. It runs where Irene has a local microphone; on a Wirenboard install the ESP32
satellite does this on-device instead (see [ESP32](../architecture/esp32.md)).

## Two providers

- **OpenWakeWord** (`openwakeword`) — general-purpose detection with pre-trained models (ONNX / TF-Lite),
  auto-downloaded. The easy default for common words.
- **microWakeWord** (`microwakeword`) — runs a **custom-trained** TF-Lite model, small enough for
  microcontrollers (~1–5 MB), via the lightweight `tflite-runtime` (~50 MB, not full TensorFlow). This is
  the engine behind the per-room ESP32 wake words.

## Configuration

```toml
[components]
voice_trigger = true

[voice_trigger]
enabled = true
default_provider = "openwakeword"
wake_words = ["irene", "jarvis"]
confidence_threshold = 0.8
buffer_seconds = 1.0
timeout_seconds = 5.0
```

Provider-specific settings go under `[voice_trigger.providers.<name>]` — microWakeWord, for instance, needs a
model:

```toml
[voice_trigger.providers.microwakeword]
model_path = "/models/irene.tflite"
detection_window_size = 3        # consecutive detections required
```

Audio is 16 kHz / 16-bit mono PCM (the device's native rate is resampled up the pipeline).

## microWakeWord models

OpenWakeWord ships its own models; microWakeWord needs one you train (see the
[microWakeWord project](https://github.com/kahrendt/microWakeWord)). The shape of the process:

1. Generate samples (Piper TTS or recordings).
2. Extract MFCC features — 40 features every 10 ms.
3. Train a streaming model in TensorFlow.
4. Quantise to TF-Lite, then validate false-accept / false-reject rates.

The model takes `[1, 49, 40]` (≈490 ms of 40-MFCC frames) and outputs a probability. One trained word per
room is what lets the wake word *name* a room — "Irene" for the kitchen, "Boris" for the living room (see
[ESP32](../architecture/esp32.md)).

## Dependencies

Behind the **`voice-trigger`** extra: `openwakeword`, `tflite-runtime`, `numpy`, `aiohttp`. (OpenWakeWord
pulls `openwakeword`; microWakeWord needs only `tflite-runtime` + `numpy`.) Adding a different engine follows
the [provider recipe](howto-new-model.md).

## Web API

The component mounts endpoints under `/voice_trigger`:

| Endpoint | Does |
|---|---|
| `GET /voice_trigger/status` | current state + config |
| `POST /voice_trigger/configure` | update wake words / threshold |
| `GET /voice_trigger/providers` | list providers |
| `POST /voice_trigger/switch_provider` | switch the active provider |

## Troubleshooting

- **Model not found** (microWakeWord) — check `model_path` points at a real `.tflite`.
- **Never triggers** — lower `confidence_threshold`, confirm the word is in `wake_words`, and that audio is
  16 kHz mono.
- **False triggers** — raise `confidence_threshold` (or, for microWakeWord, retrain with more negatives).
- **Debug** — set the `irene.components.voice_trigger_component` and `irene.providers.voice_trigger` loggers
  to `DEBUG`.
