# ESP32 + wake-word review (QUAL-19) — keep / fix / cut

> Evidence-based review of the ESP32 satellite story and the wake-word/VAD providers, with an upstream
> study of the microWakeWord ecosystem. Produced in an interactive session (2026-06-09). The acting-on-it
> work is **QUAL-20** (redefined at the foot of this doc). Findings carry a one-time `→ tracked as <ID>`
> pointer; status lives in the ledger (Invariant #5/#6).

## TL;DR

- The repo conflates **two different "microWakeWords"** across **two deployment models**, and the design's
  premise that *both* server wake-word providers were hallucinated is **wrong** — `openwakeword` works.
- **Upstream microWakeWord is a real, maintained Apache-2.0 ecosystem** (OHF-Voice / Nabu Casa / ESPHome),
  and crucially it now ships **server-side Python libraries** (`pymicro-wakeword`, `pymicro-vad`,
  `pymicro-features`) that bundle the micro frontend + tflite inference + a precompiled tflite C lib. This
  flips the broken backend provider from *"hand-port the DSP, not worth it"* to *"wrap a maintained lib."*
- **microWakeWord + microVAD form one coherent "micro" stack** that runs *identically* on the ESP32
  (on-device, TFLite-Micro via ESPHome) and server-side (via the `pymicro-*` libs) from the **same
  custom-trained `.tflite` artifact**. That makes the long-stated "one wake-word pipeline for the whole
  project" goal **actually achievable** — train a custom Russian phrase once (microwakeword.com), deploy to
  device *and* server.

## Deployment models (the frame everything hangs on)

| Model | Wake / VAD | Server role |
|---|---|---|
| **WB7 / ESP32 satellite** (primary) | **on-device** (ESP32 microWakeWord + microVAD) | `skip_wake_word=True`; **no server-side voice-trigger** (`ws_esp32_transport.md:20-21`, `webapi_router.py:787,814`) |
| **Standalone 64-bit, local mic** (kept — user 2026-06-09) | **server-side** (openWakeWord or microWakeWord; energy/silero/microVAD) | runs its own wake + VAD |

Server-side wake/VAD only matters for the standalone-local-mic model. On the satellite path the server never
runs a wake provider — so `embedded-armv7.toml`'s server-side `default_provider = "openwakeword"` (`:90`) is
simply wrong (see armv7 below).

## Upstream microWakeWord study (researched 2026-06-09)

| Source | Finding |
|---|---|
| `OHF-Voice/micro-wake-word` (Apache-2.0) | Training framework for microcontrollers (TFLite-Micro). 40 spectrogram features / 10 ms, streaming MixConv. "Early release," custom training "still difficult." |
| `OHF-Voice/pymicro-wakeword` (Apache-2.0, **v2.3.0 Jun 2026**) | **Complete server-side Python inference** — bundles micro frontend + tflite inference + precompiled tflite C lib. API: `MicroWakeWord.from_config(manifest)` / `__init__(tflite_model, probability_cutoff, sliding_window_size, trained_languages, libtensorflowlite_c_path, …)`. **Custom models supported** (`from_config` reads an arbitrary `.tflite` + JSON manifest). |
| `rhasspy/pymicro-vad` (PyPI, prebuilt wheels) | Self-contained server-side VAD; 10 ms / 16 kHz / 16-bit; threshold-configurable; **shares the `pymicro-features` micro frontend** with microWakeWord. |
| `esphome/micro-wake-word-models` (Apache-2.0) | v2 models `alexa`, `hey_jarvis`, `hey_mycroft`, `okay_nabu` (all `trained_languages:["en"]`) **+ `vad.tflite`/`vad.json`**. Manifest: `{type:"micro", wake_word, model, trained_languages, version:2, micro:{probability_cutoff, feature_step_size:10, sliding_window_size, tensor_arena_size, minimum_esphome_version}}`. Raw URL: `raw.githubusercontent.com/esphome/micro-wake-word-models/main/models/v2/<name>.tflite`. |
| `microwakeword.com` | Hosted "train custom wake words for ESP32 & ESPHome" (Piper synthetic samples). Output = `.tflite` + manifest — the *same* artifact `pymicro-wakeword.from_config` consumes server-side. Cyrillic unproven (custom-train + accept experimental quality). |
| ESPHome `micro_wake_word` | On-device VAD model (`vad:` block, `vad.json@main`, TFLite-Micro) that **gates wake-word detection** to cut non-speech false-accepts. Same micro frontend as the on-device wake word. |

## Keep / fix / cut, per piece

### 1. ESP32 firmware subsystem (`ESP32/`) — **KEEP as reference (quarantine)**
~5k LOC C++17: a *real but incomplete* skeleton. Solid state machine, I2S audio, WiFi/TLS/WebSocket,
TFLite-Micro wake-word integration + MFCC frontend, cert tooling. **But** it won't link (absent embedded
model + certs: `kitchen/main/CMakeLists.txt:9-12`), the ES8311 codec and display drivers are stubs, and
`ws_esp32_transport.md:12` already declares it **stale (rev 2, Jul 2025) — inspiration only; the server
contract is authoritative and the firmware is (re)written to match.**
- **Decision (user 2026-06-09): keep in-repo for now**, but mark it clearly as stale/reference so nobody
  mistakes it for buildable firmware. A future rewrite tracks the WS contract + the on-device micro stack
  (below), not this skeleton. Moving it to a separate firmware repo stays a later option.

### 2. On-device wake-word + VAD (ESP32) — **KEEP, this is microWakeWord's real home**
microWakeWord (TFLite-Micro) + microVAD (`vad.tflite`, gating) on the satellite, trained via
microwakeword.com, embedded as the firmware's wake/VAD models. This is the ecosystem's intended target and
needs no backend code — it's a firmware + asset story. The absent `jarvis_medium.tflite` is replaced by a
custom-trained Russian phrase per unit.

### 3. Backend microWakeWord **Python** provider (`microwakeword.py`) — **FIX via `pymicro-wakeword`**
Today a broken stub: `_extract_features` returns `np.random` (`:306`), 404 model URL (`:436`), TODO11 open,
training removed at `886d4d1`. **Fix = thin wrapper over `pymicro-wakeword`, not a DSP hand-port** (the hard
frontend is now a bundled dependency). See "Agreed plan" → QUAL-20. Russian story: custom-train per ESP32
unit (user); the same `.tflite` loads server-side via `from_config`. → tracked as **QUAL-20**.

### 4. openWakeWord provider — **KEEP, demote to quick-start**
Functional (`openwakeword.py:274`), multilingual custom-training UX, English-biased embeddings. Stays as the
no-custom-model server-side quick-start / alternative. Polish: default `inference_framework` to ONNX (today
`tflite`, `:27`), split deps into a `wake-onnx` extra, support a custom `model_path`. → **QUAL-20**.

### 5. Porcupine — **CUT**
Orphan: `PorcupineProviderSchema` exists (`schemas.py:249`) with no provider file and no entry-point. Remove
the schema. → **QUAL-20**.

### 6. Server-side VAD — **ADD microVAD as a 3rd `VADEngine`**
ARCH-10 PR-4 shipped the `VADEngine` ABC with `energy` + `silero`. Add `microvad` (`pymicro-vad`) as a third
toml-selectable impl. Coherence: `silero` rides the sherpa runtime (loaded for sherpa ASR); `microvad` rides
the tflite family (loaded when microWakeWord is the active wake provider) and shares its frontend. Not a
replacement for silero — a runtime-coherent alternative. → **QUAL-20** (bundled: same `pymicro-*` dep family).

### 7. armv7 build + config — **FIX (cut server-side wake on armv7)**
`Dockerfile.armv7` exists (BUILD-5). `embedded-armv7.toml:88-94` sets a **server-side** `openwakeword`
default — wrong on two counts: openWakeWord is 64-bit-only by design, and the WB7 wakes **on-device**. Fix:
the armv7 profile runs `voice_trigger` disabled / `skip_wake_word=True`, **no server wake provider**. → **QUAL-20**.

### 8. Training references / docs — **CUT in-repo refs, point external**
`irene-train-wake-word` / `wake_word_training` removed at `886d4d1`; now external (microwakeword.com + the
upstream training repo). Cut residual in-repo training refs; ESP32 docs (`docs/architecture/esp32.md`,
`ESP32/docs/*`) reconcile to "firmware = stale reference; on-device micro stack = the real story." → **QUAL-20**.

## Config decision — uniform "which wake word" across both providers

Wake-word selection stays **per-provider** (consistent with ASR/LLM/TTS, where model selection is a provider
field — `whisper.model_size`, `sherpa_onnx.model`, `openai.model`), with an **identical sub-schema** across
both providers. Uniformity = shared *shape*, not a component-level lift.

```toml
[voice_trigger]
default_provider = "microwakeword"     # single-active; NO fallback list for wake word

[voice_trigger.providers.microwakeword]
[[voice_trigger.providers.microwakeword.wake_words]]     # shared WakeWordSpec
name = "irene"; model = "wake/irene_ru"; threshold = 0.8; language = "ru"

[voice_trigger.providers.openwakeword]
inference_framework = "onnx"                              # provider-specific, outside the entry
[[voice_trigger.providers.openwakeword.wake_words]]      # same shape
name = "irene"; model = "wake/irene_ru"; threshold = 0.8; language = "ru"
```

- `WakeWordSpec = {name, model, threshold, language}` — shared by both provider schemas. `name` is the
  provider-agnostic identity (carried in `WakeWordResult` metadata; feeds the room/satellite mapping via
  ClientRegistry/ARCH-6). `model` is an AssetManager-resolved ref (custom artifact for the RU per-unit case,
  or a builtin catalog name). `threshold` maps to oWW `threshold` / µWW `probability_cutoff` (a manifest's
  own cutoff is overridden by toml — config-truth).
- Provider-specifics stay at the provider level: oWW `inference_framework`; µWW `sliding_window_size`
  (default or from a sidecar manifest beside the model). The lib-owned frontend params drop from the schema
  (`num_mfcc_features`, `window/stride_duration_ms`, `feature_buffer_size`, `detection_window_size`).
- **Invariant #4:** reshaping `OpenWakeWordProviderSchema` / `MicroWakeWordProviderSchema` → config-ui needs a
  `wake_words` array-of-objects editor in the same change.

## Cross-task de-tangle (Invariant #6)

microWakeWord's keep/fix/cut was previously referenced in **three** places — **ARCH-10 PR-5** (wake-word
greenfield), **QUAL-19** (this review), **QUAL-20** (act on it). This review consolidates: **QUAL-20 owns the
entire wake-word + microVAD rebuild**; ARCH-10 PR-5 is **subsumed by QUAL-20** (same work). The design doc
(`onnx_inference_layer.md` §11) is updated to reflect the pymicro-* approach and the corrected "openWakeWord
works" premise.

## Agreed plan → QUAL-20 (redefined)

Single implementation task, 64-bit-only (server side; armv7 wakes on-device):

1. **Backend microWakeWord = thin wrapper over `pymicro-wakeword`.** Delete `_extract_features` (np.random),
   the manual `feature_buffer`/`np.roll`, the hand-rolled tflite plumbing, the consecutive-detection logic
   (`microwakeword.py:237-330`). Use `MicroWakeWordFeatures().process_streaming()` → `MicroWakeWord` (one
   instance per `wake_words` entry, `from_config`/explicit ctor). Feed 10 ms / 160-sample 16 kHz chunks.
2. **Dep:** `pymicro-wakeword` in a `wake-tflite` extra (bundles the tflite C lib → drop direct
   `tflite-runtime`); 64-bit markers.
3. **openWakeWord polish:** ONNX default, `wake-onnx` extra, custom `model_path`.
4. **Uniform schema:** shared `WakeWordSpec` across both providers (above) + config-ui `wake_words` editor.
5. **Server-side microVAD:** `microvad` `VADEngine` impl over `pymicro-vad`, toml-selectable beside
   energy/silero (extends ARCH-10 PR-4).
6. **Cut Porcupine** (orphan schema). **Fix armv7 config** (no server wake; on-device). **Cut training refs;
   reconcile ESP32 docs.**
7. **Asset management:** custom model files are deployment-supplied (RU per-unit); optional `from_builtin`
   English models as a dev quick-start; close TODO11.
8. **Tests:** real detection vs a builtin model + a `from_config` custom smoke; microVAD seam test.

**Verify at build time:** precompiled `libtensorflowlite_c` platform coverage in the `pymicro-*` wheels
(x86_64/aarch64). **WB7 hardware re-validation** stays deferred to ARCH-10 completion.
