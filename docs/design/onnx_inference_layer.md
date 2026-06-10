# ONNX inference layer (sherpa-onnx) — ARCH-9 design

**Status:** design session in progress (2026-06-04). ASR + platform + build/asset decisions **locked**;
**VAD + wake-word** still open (separate discussion). Backs **ARCH-9** (design) → **ARCH-10** (implementation).

---

## 1. What this is (and is not)

**Trigger:** the new **alphacep VOSK** models — a Zipformer2 (icefall) family exported to **ONNX**, Apache-2.0 — and
the question "which other Irene models have a sherpa-onnx counterpart?". sherpa-onnx (k2-fsa) is the ONNX runtime that
loads these models.

**Thesis (unchanged from the ledger):** add a **sherpa-onnx ASR backend family** behind the existing ASR port. This is
**NOT a rip-and-replace** — whisper and silero stay first-class; the old Kaldi-`vosk` provider stays available (a config
choice, not removed). The real shared seam is the **ONNX runtime + model-asset management**, not a generic
torch/onnx/Kaldi abstraction.

**Net scope:** ARCH-9 is **ASR-centric**. TTS and wake-word are *not* sherpa-consolidation targets (see §3/§4).

---

## 2. The new VOSK models (alphacep, sherpa-onnx-runnable, Apache-2.0)

| Model | Mode | WER (CV-ru) | Profile |
|---|---|---|---|
| `vosk-model-ru` v0.54 | offline | **6.1%** | 64-bit server / high-accuracy |
| `vosk-model-streaming-ru` v0.56 | streaming | 11.3% | live/low-latency (later) |
| `vosk-model-small-streaming-ru` | streaming, small | — | edge (later) |
| **`vosk-model-small-ru`** | **offline, small** | — | **armv7 edge (chosen)** |

All are Zipformer2 transducer ONNX (encoder/decoder/joiner + tokens), loaded via sherpa-onnx
`OfflineRecognizer.from_transducer` (offline) / `OnlineRecognizer` (streaming).

**Decisions:** **offline first** (streaming "maybe later"); **run alongside** the existing Kaldi-`vosk` provider.

---

## 3. Current model → inference-engine inventory

| Modality | Provider | Engine | Local? | Lang |
|---|---|---|---|---|
| ASR | `vosk` | **Kaldi C++** (`vosk`) | local | RU |
| ASR | `whisper` | **PyTorch** (`openai-whisper`+`torch`) | local | multi |
| ASR | `google_cloud` | cloud | cloud | multi |
| TTS | `silero_v3`/`silero_v4` | **PyTorch** (`torch`) | local | RU |
| TTS | `vosk` (vosk-tts) | **pip `onnxruntime`** | local | RU |
| TTS | `elevenlabs` | cloud | cloud | multi |
| TTS | `pyttsx` | system (espeak/SAPI) | local | — |
| Wake | `openwakeword` / `microwakeword` | **TFLite** | local | EN/— |
| VAD | `utils/vad.py` | energy (numpy, no model) | local | — |

**Distinct local ML runtimes today: up to 4** — PyTorch · Kaldi C++ · pip-onnxruntime (vosk-tts) · TFLite. A "voice"
profile can load 3–4 in one process. That's the fragmentation ARCH-9 reduces.

### 3.1 What moves to sherpa-onnx, what doesn't

| Item | Today | Moves to sherpa? |
|---|---|---|
| **whisper ASR** | torch | ✅ **Whisper-ONNX** — off torch onto sherpa |
| **vosk ASR** | Kaldi | ✅ new VOSK Zipformer2 ONNX |
| silero TTS | torch | ❌ stays torch (RU quality leader; no sherpa-Silero) |
| vosk-tts | pip-onnxruntime | ❌ separate package/runtime — not a "move" (a model swap if ever) |
| wake-word | TFLite | ❌ sherpa-KWS has **no RU model** + accuracy concerns — TFLite stays |
| VAD | energy/numpy | ⚪ *optional* later (sherpa Silero-VAD-ONNX) |

**Result: ASR fully consolidates onto sherpa-onnx (torch *and* Kaldi leave the ASR path); torch shrinks to just
Silero TTS.** You do not reach a single runtime — TFLite (wake) and possibly vosk-tts's onnxruntime remain. That's fine.

### 3.2 Per-platform runtime picture
- **armv7 edge (WB7):** sherpa-onnx (ASR) · TFLite (wake) · energy-VAD (numpy). **No torch, no Kaldi, no
  pip-onnxruntime, and no TTS** (see §4). Input-only node; responses produced elsewhere.
- **64-bit server:** sherpa-onnx (ASR incl. whisper-onnx) · torch (Silero TTS) · pip-onnxruntime (vosk-tts, if
  configured) · TFLite (wake).

---

## 4. The armv7 target is decisive — measured on real hardware (Wirenboard 7)

The key target is a **Wirenboard 7.2 (A40i)** controller. Measured via SSH + a container matching the real deployment:

- **Platform:** `armv7l` (Allwinner sun8i, **quad Cortex-A7 ~1 GHz**, NEON/VFPv4), **Debian 11 / glibc 2.31**
  (NOT Alpine/musl), host Python 3.9, Docker (overlay2, data-root on `/mnt/data`). **~375 MB RAM available**
  (shared with the wb-mqtt-bridge container), 256 MB swap.
- **Deployment is containerized** like wb-mqtt-bridge → `arm32v7/python:3.11-slim-bullseye`, buildx `linux/arm/v7`,
  GHCR. **The image carries Python 3.11**, so the host's 3.9 is irrelevant.

**Hands-on benchmark** (`arm32v7/python:3.11-slim`, `pip install sherpa-onnx==1.10.46`, `vosk-model-small-ru`):

```
TRANSCRIPT : 'родион потапыч высчитывал каждый новый вершок углубления и давно определил про себя'  (correct RU)
RTF        : 1.150   (8.14 s decode for 7.08 s audio, 4 threads)
PEAK RSS   : 110 MB
MODEL DISK : 26.7 MB int8   |   LOAD: 38.2 s
```

**armv7 constraints (now empirical, not assumed):**
1. **Pin `sherpa-onnx==1.10.46`.** Latest (1.13.2) fails to load on this kernel — `libonnxruntime.so: ELF load
   command address/offset not properly aligned` (an armv7 segment-alignment bug in the prebuilt wheel). 1.10.46 is the
   newest *working* armv7 build and still supports the Zipformer2 format. **→ track upstream; re-test newer releases.**
2. **`onnxruntime` (pip) has NO armv7 wheel** (`No matching distribution found`). sherpa-onnx works only because it
   **bundles its own onnxruntime**. This is why **vosk-tts and any plain-onnxruntime model cannot run on armv7**.
3. **RTF ≈ 1.15 → offline only, with a latency tax** (a 3 s command ≈ 3.5 s to transcribe). Rules out streaming on this
   box and **rules out the big 6.1-WER model** (would be ~5–10× — unusable). **armv7 = small model only.**
4. **~38 s model load — absorbed by the existing warm-up.** It's the onnxruntime graph init when the recognizer is
   constructed (every process start, distinct from the first-run *download* which is cached on the mount, §6). Irene
   already has a **warm-up procedure** — providers implement `warm_up()` gated by the **`preload_models`** config flag
   (whisper/vosk/silero/vosk-tts do this; plus a global `preload_essential_models`). The new provider follows the same
   pattern, and the **`embedded-armv7` profile sets `preload_models=True`** → the 38 s is paid **at boot during warm-up**
   (off the first-command critical path), not on the first user utterance. Lower-urgency further optimization:
   serialize onnxruntime's **optimized graph** once (`SessionOptions.optimized_model_filepath`) to shrink the warm-up
   window itself.
5. Needs **`libasound2`** (sherpa links ALSA).
6. **armv7 = no TTS** (user decision): silero needs torch (✗ armv7), vosk-tts needs pip-onnxruntime (✗ armv7), and
   sherpa-`OfflineTts` is available but out of scope per the decision. The edge does **input only**.
7. **🔴 The armv7 image MUST be Debian/glibc, NOT Alpine/musl — required change (user-approved 2026-06-04).**
   The *current* `Dockerfile.armv7` is **Alpine** (`FROM python:3.11-alpine`, `apk add`, analyzer `--platform
   linux.alpine`). **Proven on the WB7:** on Alpine/musl, sherpa-onnx's compiled native module is absent →
   `import sherpa_onnx` fails (`No module named 'sherpa_onnx.lib._sherpa_onnx'`); its bundled onnxruntime is glibc-built
   and there is no musllinux build. On **Debian/glibc** (`arm32v7/python:3.11-slim-bullseye`) it installs and transcribes
   (the §4 benchmark). So `Dockerfile.armv7` must **switch Alpine→Debian** (matching wb-mqtt-bridge's armv7 image). The
   armv7 Docker build was **never tested yet**, so this is a clean change. Consequences in §7.1/§9.

---

## 5. Architecture

### 5.1 The provider
A new **`sherpa_onnx` ASR provider** behind the existing `ASRPlugin`/ASR port, loading the Zipformer2 transducer family
first and **Whisper-ONNX** next (same runtime, same provider, selected by config `model_type`). Runs **alongside** the
existing `vosk` (Kaldi) and `whisper` (torch) providers — selectable by config; deprecate the old paths only after parity.

### 5.2 The shared seam = assets + policy, NOT a shared session (decided)
Decoupling the *inference engine* into a runtime object that every provider routes through is **overkill and partly
impossible**: `import sherpa_onnx` is already a process singleton (library shared for free), each model is a **separate
ONNX session** (can't be shared), and sherpa's high-level API doesn't expose the `OrtEnv`/thread-pool. So the session
**stays inside each provider**. What we *do* decouple:

- **(a) Asset management** — extend `core/assets.AssetManager` for **sherpa model packs** (multi-file
  encoder/decoder/joiner/tokens; per-profile small-vs-big selection; download/cache/validate). See §6.
- **(b) A small inference *policy*** the sherpa providers read — `num_threads` budget per platform (armv7 conservative
  so it doesn't oversubscribe the 4 A7 cores while the bridge runs; server generous), CPU execution provider, graph-opt
  level, int8 preference. A dataclass + platform defaults, not an adapter.

---

## 6. AssetManager extensions (`core/assets.py`)

The new provider's models are **multi-file packs**, not a single URL. Extend the AssetManager to:
- Resolve a **model pack** (a set of files: `encoder.int8.onnx`, `decoder.int8.onnx`, `joiner.int8.onnx`, `tokens.txt`)
  to a local directory, downloading/caching from HF (`alphacep/vosk-model-*`) under the existing cache root.
- Support **per-profile model selection** (the `embedded-armv7` profile → `vosk-model-small-ru`; 64-bit → `vosk-model-ru`)
  so only the configured pack is fetched.
- **First-run download into the asset-loader folder (decided, user 2026-06-04):** models are **not baked into the
  image**; the AssetManager downloads the configured pack on first run into its asset/cache directory — a path the
  asset loader defines, **usually a volume mounted outside the container** so it **persists across container
  recreation** (downloaded once, reused thereafter). The image stays lean; the WB7's `/mnt/data` is the natural mount.
- Validate the pack (files present, non-empty) at startup (ties to QUAL-23 startup validation).

---

## 7. Per-platform dependency functions (the build system)

**Design principle — invariant (user, 2026-06-04):** the **contribution mechanism stays**. Every provider/component
**self-declares** its dependencies — Python (as pyproject extra *group names*, §7.1) and system packages (per platform)
— through the `EntryPointMetadata` metadata methods; `build_analyzer` collects only the **enabled** providers'
contributions for a profile; the Dockerfiles consume them. This is what builds lean, per-profile images, and it must be
preserved. **What is mutable:** *what* a provider contributes (package names/versions) and the **platform taxonomy
itself** (the `linux.ubuntu`/`linux.alpine`/`macos`/`windows` identifiers) — these are free to change to match real
targets. Both current real builds are **Debian/glibc/apt → `linux.ubuntu`**; the `linux.alpine` contributions are now
**vestigial** (the armv7 Alpine→Debian move in §4.7 is an instance of this flexibility — the *principle* is untouched,
only the target platform changed). The taxonomy can be re-trimmed to the actual targets later without touching the
mechanism.

The new provider encodes the WB7 findings (contribution mechanism unchanged):

```python
@classmethod
def get_python_dependencies(cls) -> List[str]:
    # CONTRACT (EntryPointMetadata): return pyproject [project.optional-dependencies] GROUP NAMES,
    # NOT raw requirement strings — the build runs `uv sync --extra <name>`. The per-arch version
    # split (and "no torch") lives in the extra definition below, where uv evaluates the markers.
    return ["asr-onnx"]

@classmethod
def get_platform_dependencies(cls) -> Dict[str, List[str]]:
    return {"linux.ubuntu": ["libasound2"], "linux.alpine": ["alsa-lib"], "macos": [], "windows": []}

@classmethod
def get_platform_support(cls) -> List[str]:
    return ["linux.ubuntu", "linux.alpine", "macos", "windows"]   # armv7 + x86_64/aarch64

@classmethod
def _get_default_model_urls(cls) -> Dict[str, str]:
    return {"vosk-model-small-ru": "...", "vosk-model-ru": "..."}   # small + big packs
```

```toml
# pyproject.toml — the per-arch version split lives HERE (uv sync evaluates the markers in the
# per-platform build context: armv7 build → 1.10.46; x86_64/aarch64 → latest). NO torch.
[project.optional-dependencies]
asr-onnx = [
    "sherpa-onnx==1.10.46; platform_machine=='armv7l'",   # the only working armv7 build
    "sherpa-onnx>=1.11;    platform_machine!='armv7l'",
]
```

### 7.1 Build-system finding (investigated 2026-06-04) — a real correction is needed

The build flow is: `build_analyzer` collects each enabled provider's `get_python_dependencies()` into
`BuildRequirements.python_dependencies`; `Dockerfile.armv7`/`.x86_64` then run **`uv sync --extra <each value>`**.
So the values **must be pyproject extra group names**. The `EntryPointMetadata` docstring confirms this contract
(`["asr"]`, `["tts"]`, …).

**Bug:** the *existing* providers violate it — `whisper.get_python_dependencies()` returns
`["openai-whisper>=20230314", "torch>=1.13.0", "torchaudio>=0.13.0"]` (requirement strings), `vosk` returns
`["vosk>=0.3.45"]`, silero returns `["torch>=1.13.0"]`, etc. Passed to `uv sync --extra "torch>=1.13.0"` these are
**invalid extra names** → the per-profile `--extra` install is broken/latent (builds fall back to a full `uv sync`).
This is pre-existing debt — relates to **QUAL-3** (get_python_dependencies wiring) and **BUILD-5** (build-analyzer
audit). **Correction to fold into BUILD-5/QUAL-3:** make `get_python_dependencies()` return **extra group names**
across all providers, and define those extras in pyproject. The new `sherpa_onnx` provider is written **correctly**
(returns `["asr-onnx"]`) and is the reference. **The PEP 508 marker per-arch split works** *because* the markers sit in
the pyproject extra that `uv sync` resolves in the per-arch build — not in a provider-returned string.

---

## 8. Config & profiles (Invariant #4)

- **New provider config schema** (model name, model_type vosk-zipformer|whisper-onnx, num_threads, decoding_method) →
  **must be surfaced in config-ui** (Invariant #4; gated in ARCH-10).
- **`embedded-armv7` profile:** `sherpa_onnx` ASR with `vosk-model-small-ru`, offline, conservative threads; **no TTS**.
- **64-bit profiles:** `sherpa_onnx` ASR with `vosk-model-ru` (+ whisper-onnx option); TTS = silero (and vosk-tts if
  configured — kept, a config story, not removed).

---

## 9. Two Docker builds

- **`Dockerfile.armv7` — rewrite Alpine→Debian (required, user-approved; never tested yet):**
  - **Base:** all three stages (analyzer/builder/runtime) `python:3.11-alpine` → **`arm32v7/python:3.11-slim-bullseye`**
    (glibc — matches wb-mqtt-bridge). This is what makes sherpa-onnx work (§4.7).
  - **System packages:** `apk add` → **`apt-get install`**; analyzer call `--platform linux.alpine` → **`linux.ubuntu`**;
    extract `system_packages['ubuntu']` instead of `['alpine']`. The sherpa provider's `get_platform_dependencies`
    already declares both keys, so the Debian base just selects **`libasound2`** (the `linux.ubuntu` value).
  - **Result:** `sherpa-onnx==1.10.46` (via the `asr-onnx` extra marker), `libasound2`, small VOSK pack downloaded to the
    mounted asset folder, **no torch / no Kaldi / no pip-onnxruntime / no TTS**.
- **`Dockerfile.x86_64`** (already Debian `python:3.11-slim` + apt): add the `asr-onnx` extra → latest sherpa-onnx, big
  VOSK pack + whisper-onnx; torch only where silero TTS is configured. No base change needed.

---

## 10. Open questions / next

**Resolved (user 2026-06-04):**
- **One provider** — single `sherpa_onnx` ASR provider, family chosen by TOML config `model_type`
  (`vosk-transducer` → `OfflineRecognizer.from_transducer`; `whisper` → `OfflineRecognizer.from_whisper`). Confirmed
  feasible — both are `OfflineRecognizer` factory methods on the same runtime.
- **Models: first-run download** into the asset-loader folder (mounted volume), not baked into the image (§6).
- **armv7 image Alpine→Debian** + the system-dep flow flip (apk→apt, `linux.alpine`→`linux.ubuntu`) — approved
  ("modify both; never tested yet"). Required for sherpa-onnx to load on armv7 (§4.7/§9).
- **WB7 VAD + wake-word = on the ESP32 satellite, NOT in Irene** (reconciled with ARCH-6, 2026-06-04). **Wake-word:**
  microWakeWord *tool* (GitHub) → **C-header** → ESP32 firmware (tflite-micro on the MCU). **VAD:** **numeric/energy
  on-device** (no VAD micro-model for the ESP32) — detects speech start + end-of-utterance. **On wake** the ESP32 opens
  the ARCH-6 WS (`/ws/audio`), registers (ClientRegistry), and streams raw PCM until its VAD closes the utterance
  (`{"type":"end"}`); Irene runs **offline sherpa-onnx ASR with `skip_wake_word=True`** — no server-side wake-word/VAD on
  this path. Matches `ws_esp32_transport.md` + the `/ws/audio` adapter exactly. **⇒ the WB7/armv7 Irene image needs no
  wake-word/VAD providers → the `tflite-runtime` armv7 question is MOOT; the edge image is ASR-only.** (Irene's
  server-side `microwakeword` *provider* is broken/placeholder per QUAL-19, but irrelevant to this path.)
- **VAD + wake-word — standalone 64-bit (local-mic) — designed in §11** (user 2026-06-04): two wake-word providers
  (`openwakeword` ONNX / `microwakeword` tflite) **mutually exclusive via toml**; two VAD impls (`energy` bug-fixed /
  `silero` sherpa-onnx) **mutually exclusive via toml**. Today's voice-trigger providers are hallucinated cruft →
  rebuild greenfield (QUAL-19/20).

**Still open:**
- **38 s load — handled** by the existing warm-up (`preload_models=True` on armv7 → paid at boot, §4.4); optional
  later spike: onnxruntime optimized-graph caching to shrink the warm-up window.
- **Build-system fix** — `get_python_dependencies` should return extra *group names* across all providers (§7.1) → BUILD-5.

---

## 11. VAD + wake-word — standalone 64-bit (local-mic) scenario

This is the **only** path where Irene runs its own VAD + voice-trigger (the WB7 path delegates both to the ESP32, §10).
It is therefore **64-bit-only** — none of this enters the armv7 image. _Premise corrected by QUAL-19 (2026-06-09):_
`openwakeword` is **functional** (not hallucinated); only `microwakeword` was a stub — and it's **fixable, not
greenfield**, because OHF-Voice now ships server-side Python libs (`pymicro-wakeword`/`pymicro-vad`/`pymicro-features`,
Apache-2.0) that bundle the micro frontend + tflite inference + a precompiled tflite C lib. The `VoiceTriggerProvider`
ABC port stays. Full evidence + keep/fix/cut: `docs/review/esp32_wakeword_review.md`; implementation = **QUAL-20**.

### 11.1 Wake-word — two providers, mutually exclusive via toml (decided 2026-06-04)
Exactly **one** is active, selected by the voice-trigger component's `default_provider` (the existing single-active
pattern — **no fallback list** for wake-word; the two are alternatives, not a chain).

| Provider | Runtime | Why it's here | Russian story |
|---|---|---|---|
| `openwakeword` | **ONNX** (onnxruntime — stays in the no-torch ONNX-family image) | Functional today. Multilingual custom-training UX. The no-custom-model **quick-start / alternative**. | Custom-trained phrase; experimental quality (English-biased embedding). |
| `microwakeword` | **tflite** via **`pymicro-wakeword`** (bundles a precompiled tflite C lib) | **Unifies with the ESP32** — the *same* custom `.tflite` artifact runs on-device (TFLite-Micro) AND server-side via `pymicro-wakeword.from_config`. The **primary** for the satellite fleet. | Custom-train per ESP32 unit (microwakeword.com); same artifact loads server-side. |

- `microwakeword` is a **thin wrapper over `pymicro-wakeword`** (NOT a from-scratch DSP port — the micro frontend is a
  bundled dep). `openwakeword` stays functional + gets polish (ONNX default, custom `model_path`). Deps via the
  contribution principle (§7): `openwakeword` → extra `wake-onnx` (`openwakeword`, `onnxruntime`); `microwakeword` →
  `wake-tflite` (`pymicro-wakeword`, which carries its own tflite lib — no `tflite-runtime`). Both **64-bit only**
  (`get_platform_support` excludes armv7; the WB7 wakes on-device).
- **Uniform config (QUAL-19):** wake-word selection stays **per-provider** (consistent with ASR/LLM model selection)
  with an **identical `WakeWordSpec = {name, model, threshold, language}`** sub-schema across both providers. `name` =
  provider-agnostic identity (→ room/satellite mapping); `model` = AssetManager-resolved artifact ref; `threshold` ↔
  oWW `threshold` / µWW `probability_cutoff`. Provider-specifics (`inference_framework`; `sliding_window_size`) stay in
  the provider block. Invariant #4: config-ui gets a `wake_words` array editor.
- **Future swap-in:** `sherpa-onnx KWS` is the architectural ideal (zero-training open-vocabulary via `text2token`, joins
  the shared sherpa layer) but has **no Russian base model today** (only zh/en/zh+en). The ABC port lets us add it as a
  third provider if/when a Russian KWS base model lands.

### 11.2 VAD — two impls, mutually exclusive via toml (decided 2026-06-04)
VAD is currently a **util** (`irene/utils/vad.py`), not a selectable seam. Promote it to a small VAD provider/port with
**two mutually-exclusive impls**, chosen by toml:

| Impl | Engine | Notes |
|---|---|---|
| `energy` | today's `irene/utils/vad.py` | dependency-free; keep, but **bug-fix/improve** it (per user). The default. |
| `silero` | **SileroVAD-ONNX via sherpa-onnx** | more robust in noise; **joins the shared sherpa layer** (same thread/CPU policy). Opt-in. |
| `microvad` | **microVAD via `pymicro-vad`** (added by QUAL-19, 2026-06-09) | tiny; **shares the `pymicro-features` micro frontend** with `microwakeword` and matches the ESP32 on-device VAD. Opt-in. |

- Exactly one active (mutually exclusive), `energy` default. **Runtime coherence picks the opt-in:** `silero` reuses the
  sherpa runtime (loaded for sherpa ASR); `microvad` reuses the tflite family (loaded when `microwakeword` is the active
  wake provider) and its frontend. Not rivals on accuracy — pick the one whose runtime is already resident.
- 64-bit only (the WB7 ESP32 does VAD on-device — see the unified micro stack below).
- **Unified "micro" stack (QUAL-19):** `microwakeword` + `microVAD` share one frontend + one model-artifact ecosystem and
  run *identically* on the ESP32 (on-device, TFLite-Micro via ESPHome's `micro_wake_word` `vad:` gating) and server-side
  (via the `pymicro-*` libs). This is the realized "one pipeline, device + server" goal. Implementation = **QUAL-20**.

---

## 12. Implementation slices (ARCH-10)

1. **PR-1:** `sherpa_onnx` ASR provider — **vosk-zipformer, offline**; AssetManager pack support; inference policy;
   dependency functions; `embedded-armv7` + 64-bit config; config-ui surfacing. (Proven feasible on the WB7.)
2. **PR-2:** **Whisper-ONNX** on the same provider/runtime (drops torch from 64-bit ASR images that don't need silero).
3. **PR-3 (later):** streaming (`OnlineRecognizer` + streaming models).
4. **PR-4:** VAD seam (§11.2) — `energy` (bug-fixed) + `silero` (SileroVAD-ONNX on the shared runtime), toml-selectable.
5. **PR-5:** Wake-word greenfield (§11.1) — rebuild `openwakeword` (ONNX) + `microwakeword` (tflite) as two
   mutually-exclusive providers; cut the hallucinated stubs (QUAL-19/20). 64-bit only.

---

## Appendix A — upstream issue to track
`sherpa-onnx >= 1.11` armv7 wheels fail to load on the WB7 kernel (`ELF load command address/offset not properly
aligned`). Pinned to **1.10.46**. File/track upstream and re-test newer releases to lift the pin.
