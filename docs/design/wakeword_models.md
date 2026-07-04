# Wake-word model acquisition — server-side microWakeWord (ARCH-29)

**Status: decided 2026-07-04 (interactive session). Implementation: ASSET-5.**

How the standalone/server-side `microwakeword` voice-trigger provider obtains wake-word models —
the counterpart of the TTS-voice story (piper's per-voice catalog), adapted to what a wake-word
artifact actually is. Satellites are out of scope here: an ESP32 gets its model flashed into
firmware (`esp32_satellite.md` D-9); this design is for the server side — all-in-one deployments
and, importantly, **testing freshly trained models before any device exists**.

## The artifact (D-1)

A wake-word model is a **two-file v2 pack**: a JSON manifest + the streaming `.tflite` it
references. `pymicro_wakeword.MicroWakeWord.from_config` resolves the tflite **relative to the
manifest** (`manifest_dir / config["model"]`), so the two files must live side by side. This is
the same artifact for every source — the esphome v2 repo, microwakeword.com output, and the
in-house training factory (`~/development/wakeword-training` → the user's HF repos, e.g.
`droman42/microwakeword-irina-ru`). On disk, each word is a directory:
`<assets_root>/models/microwakeword/<word>/<word>.json + <word>.tflite`.

## Resolution order (D-2)

`_build_detector` resolves each `wake_words` entry's `model` ref through four rungs, most
specific first:

1. **Local manifest path** (`model = "/path/to/word.json"`) — pre-release testing of a model
   straight out of the training pipeline. No copy, no download.
2. **Built-in** — the four stock English packs (`alexa`, `okay_nabu`, `hey_jarvis`,
   `hey_mycroft`) ship **inside the pymicro-wakeword wheel**, byte-identical to the esphome v2
   repo. They resolve via `from_builtin`: zero download, works offline. (This is why the esphome
   repo is *not* in the catalog — the wheel already carries its four models; «Alexa» as the EN
   counterpart of «Ирина» costs nothing.)
3. **v2 manifest URL** (`model = "https://…/word.json"`) — the generic escape hatch: any
   microwakeword.com published model, or a self-trained HF model *before* it is blessed into the
   catalog. The manifest is downloaded together with its sibling `.tflite` (same base URL, `.json
   → .tflite`) through the AssetManager into `models/microwakeword/<name>/`.
4. **Released catalog** — a class-level catalog on the provider (piper-voices pattern,
   `_get_default_model_urls`): word → the two pack-file URLs. Starts with **`irina`** (the user's
   HF repo). Each new validated word («Валера», «Наташа», …) is a **one-line catalog addition**,
   filed as that model's consume-task.

A ref that resolves on no rung is skipped with a warning (existing behavior) — one bad word never
takes down the other detectors.

## Downloads go through the AssetManager (D-3)

Same rule ASSET-4 established for VAD: **no provider self-downloads.** The AssetManager gains
first-class **multi-file model support**: a catalog entry may carry `files: {filename: url}`
instead of `url`; the files are fetched into a staging directory and atomically renamed into
place (the existing archive-extraction idiom), under the existing per-model lock, with the
existing partial-download healing. Downloads happen in the provider's async `_do_initialize` —
never on the audio hot path.

## Wake words stay semantics-free (D-4)

A wake-word *name* is a routing identity in the target architecture (name = room = satellite),
but the trigger layer does not know that: the spec stays `{name, model, threshold, language}`,
the provider keeps reporting *which* word fired in `WakeWordResult.word`, and the word → room
mapping is designed when multi-room actuation lands (ARCH-22 / QUAL-35) — where an actual
consumer exists. The server-side multi-detector (one detector per configured word, all streamed
in parallel) is already sufficient for standalone testing of several names at once.

## Naming roster (D-5)

Pilot: **«Ирина»** (validated 2026-07-04, HF `droman42/microwakeword-irina-ru`). Next:
**«Валера»**, **«Наташа»**. «Борис» is **dropped** — 2 syllables, too false-accept-prone (the
same reason the training repo deferred it). EN counterpart for parity testing: **Alexa**
(built-in).

## Out of scope

- ESP32 firmware consumption (esp32_satellite.md owns that).
- openWakeWord provider (its .onnx catalog is untouched; microWakeWord is the "micro" stack).
- Per-word room/device fields (D-4 defers to multi-room).
