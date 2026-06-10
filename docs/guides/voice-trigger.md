# Voice trigger (wake word)

The voice trigger listens for a wake word and only then wakes the rest of the pipeline, so Irene isn't
transcribing all day. It runs where Irene has a local microphone; on a Wirenboard install the ESP32
satellite does this on-device instead (see [ESP32](../architecture/esp32.md)).

## Two providers

- **OpenWakeWord** (`openwakeword`) — general-purpose detection with pre-trained models, auto-downloaded.
  Runs on ONNX by default. The easy default for common English words.
- **microWakeWord** (`microwakeword`) — runs a **custom-trained** TF-Lite model via
  [pymicro-wakeword](https://github.com/OHF-Voice/pymicro-wakeword), which bundles the feature frontend and
  the runtime (no full TensorFlow). It's the same engine, and the **same model file**, the ESP32 satellites
  run on-device — so you train a wake word once and deploy it both places.

Exactly one provider is active, picked by `default_provider`. There's no fallback chain — they're
alternatives, not a cascade.

## Configuration

Wake words are declared **per provider**, as a list of entries with the same shape for both:

```toml
[voice_trigger]
enabled = true
default_provider = "microwakeword"

[voice_trigger.providers.microwakeword]
enabled = true
wake_words = [
    { name = "irene", model = "/models/irene_ru.tflite", threshold = 0.8, language = "ru" },
    { name = "boris", model = "/models/boris_ru.tflite", threshold = 0.8, language = "ru" },
]

[voice_trigger.providers.openwakeword]
enabled = false
inference_framework = "onnx"             # or "tflite"
wake_words = [
    { name = "hey_jarvis", model = "hey_jarvis", threshold = 0.7, language = "en" },
]
```

Each entry is `{ name, model, threshold, language }`:

- **`name`** — the label you'll see on a detection, and the key that lets a wake word *name a room*
  ("Irene" for the kitchen, "Boris" for the living room).
- **`model`** — a built-in catalog name (OpenWakeWord: `hey_jarvis`, `alexa`, `hey_mycroft`; microWakeWord:
  `okay_nabu`, …) **or** a path to a custom model file.
- **`threshold`** — detection cut-off, 0–1.
- **`language`** — two-letter tag, for your own bookkeeping.

Audio is 16 kHz / 16-bit mono PCM (the device's native rate is resampled up the pipeline).

## Custom (Russian) wake words

Built-in models are English. For per-room Russian names you train your own — the easiest path is the hosted
[microwakeword.com](https://microwakeword.com/): give it a phrase, it generates Piper samples and returns a
`.tflite` + a small JSON manifest. Point a `microwakeword` entry's `model` at that file (or the manifest) and
the same artifact drops onto the ESP32. Expect to tune `threshold` and listen for false accepts — custom
training is still finicky.

## Dependencies

Each provider declares its own extra (64-bit only — on a Wirenboard the satellite wakes on-device, so the
server runs none of this):

| Provider | Extra | Pulls |
|---|---|---|
| OpenWakeWord | `wake-onnx` | `openwakeword`, `onnxruntime` |
| microWakeWord | `wake-tflite` | `pymicro-wakeword` |

`voice-trigger` installs both. Adding a different engine follows the [provider recipe](howto-new-model.md).

## Web API

The component mounts endpoints under `/voice_trigger`:

| Endpoint | Does |
|---|---|
| `GET /voice_trigger/status` | current state + config |
| `POST /voice_trigger/configure` | update wake words / threshold |
| `GET /voice_trigger/providers` | list providers |
| `POST /voice_trigger/switch_provider` | switch the active provider |

## Troubleshooting

- **Model not found** (microWakeWord) — check a custom entry's `model` points at a real `.tflite`/manifest.
- **Never triggers** — lower the entry's `threshold`, confirm the word is listed, and that audio is 16 kHz mono.
- **`irene` on OpenWakeWord does nothing** — OpenWakeWord only knows its English catalog; a custom Russian
  word needs microWakeWord (or a custom OpenWakeWord model file).
- **False triggers** — raise `threshold`, or retrain with more negatives.
- **Debug** — set the `irene.components.voice_trigger_component` and `irene.providers.voice_trigger` loggers
  to `DEBUG`.
