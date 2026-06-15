# Torch-free inference & the armv7 voice stack — ARCH-24 design notes

**Status:** research/analysis session 2026-06-15 (**no code**). Captures findings + decisions so we can resume later.
Backs **ARCH-24**. Revises the ARCH-9 thesis ("whisper and silero stay first-class"): **torch is contained to the x86_64
standalone image; both ARM satellites (armv7 WB7 + aarch64 WB8/Pi) are torch-free sherpa-onnx.** See **§5** for the
canonical three-image matrix — it is the source of truth; §1–§4 are the supporting research.

**Trigger:** the deferred torch/transformers Dependabot alerts (see commits `05aa763`/`4e05a38` — torch ×4, transformers
×1, protobuf/sentencepiece) prompted the question: *"torch is heavy ML machinery and we only do inference — are there
slimmer options?"* Plus the user's concrete need: a **self-contained VAD + ASR + TTS on the Wirenboard 7 (armv7l)**.

---

## 1. Where torch actually lives (today)

Torch is **not** a core dependency. It is opt-in via two optional extras, and `transformers` is only ever transitive:

| Dep | How it enters | Imported by |
|---|---|---|
| `torch` / `torchaudio` | `advanced-asr` extra (`pyproject` "Required by Whisper") **+** direct import in Silero TTS | `providers/asr/whisper.py`, `providers/tts/silero_v3.py`, `providers/tts/silero_v4.py` |
| `transformers` | **transitive only** — via `runorm` (`text-multilingual` extra) | **nothing in our code** — `runorm` normalizer is `enabled = false` by default in `config-master.toml` |

So the default ONNX path (sherpa-onnx ASR, openWakeWord, Silero **VAD**) is already torch-free; Whisper ASR and Silero
**TTS** are the only torch holdouts. The codebase philosophy is already "ONNX everywhere" (pyproject annotates the
sherpa/openWakeWord paths "NO torch").

**Migration surface is tiny** (both are 2-call provider seams):
- Whisper: `whisper.load_model(size)` + `model.transcribe(path, language=)` → text.
- Silero: `torch.package.PackageImporter(.pt).load_pickle(...)` + `model.apply_tts(text, speaker, sample_rate)` → waveform.

---

## 2. The two replacements (research-backed)

### 2a. Whisper ASR → sherpa-onnx Whisper  ✅ low risk
- sherpa-onnx (**already shipped**, both arches) supports Whisper natively: `OfflineRecognizer.from_whisper(...)`.
  Same weights → accuracy parity; prebuilt int8 exports `csukuangfj/sherpa-onnx-whisper-*`.
- armv7l wheels confirmed; ORT is statically linked (no separate `onnxruntime` pip package).
- **Rejected alternatives:** faster-whisper/CTranslate2 (no armv7 wheel at all), onnx-asr / standalone-onnxruntime
  (Microsoft ships **no armv7l onnxruntime wheel** — aarch64 only), transformers pipeline (needs torch).
- Fallback if speed disappoints on-device: pywhispercpp (piwheels armv7 build, torch-free GGML).

### 2b. Silero TTS → **no torch-free Silero exists**; use Piper  ⚠️ quality trade-off
- **Definitive finding:** nobody has ported Silero TTS to ONNX/sherpa, and it's **blocked at the source.** Silero
  refuses ONNX export of the TTS net (issue #283, verbatim: exposing it would reveal the accentor/homograph internals);
  no Russian ONNX TTS exists in `models.yml`; architecture is undisclosed Tacotron-lineage (not VITS); sherpa-onnx has
  no Silero loader and would need new C++ even given an ONNX. **Every** public "Silero TTS" artifact is still torch.
- **The clean torch-free path = Piper** (OHF-Voice/piper1-gpl), VITS, ONNX-native, **also runs through sherpa-onnx**
  (`OfflineTts`, VITS family). Official `ru_RU` voices: irina/denis/dmitri/ruslan, pre-packaged in the k2-fsa zoo
  (`vits-piper-ru_RU-*-medium`), tiny (~60–75 MB), armv7-capable.
- **Trade-off:** Piper Russian phonemizes via **espeak-ng**, weaker on lexical stress/homographs than Silero's bundled
  accentor. Mitigation: **RUAccent** (Den4ikAI/ruaccent, Apache-2.0, onnxruntime+numpy, **torch-free**, ~0.96 acc,
  homographs + ё) as a **preprocessing step** — but see the armv7 wall in §4.

---

## 3. Provider inventory & armv7 viability

**ASR** (one provider runs on armv7: `sherpa_onnx`; the Kaldi `vosk` provider does **not**):

| Provider | armv7? | Note |
|---|---|---|
| `sherpa_onnx` | ✅ | the armv7 ASR; loads vosk-model **or** whisper-int8 (one provider, choice of model) |
| `vosk` (Kaldi) | ❌ | not on armv7 |
| `whisper` (torch) | ❌ | → folds into sherpa_onnx |
| `google_cloud` | ✅* | cloud, not offline |

**VAD** — already solved torch-free: `silero` VAD loads `silero_vad.onnx` (dep `asr-onnx`, reuses sherpa runtime) ✅;
`energy` (pure-python) ✅; `microvad` (tflite) ❌ 64-bit only.

**TTS:**

| Provider | Dep | armv7? | Note |
|---|---|---|---|
| `console` | none | ✅ | debug only (current armv7 default) |
| `pyttsx` | pyttsx3 → espeak-ng | ✅ | works today, tiny, torch-free — robotic |
| `elevenlabs` | httpx (cloud) | ✅* | needs internet + key, not offline |
| `vosk_tts` | onnxruntime + 746 MB model | ❌ | no armv7 ORT wheel **and** OOM/disk — aarch64/x86 only |
| `silero_v3/v4` | torch | ❌ | excluded |
| **`piper` (new)** | sherpa-onnx runtime | ✅ | base provider — all envs incl. armv7; the WB7 TTS |
| **`piper_ruaccent` (new)** | `piper` + `ruaccent` (onnxruntime + transformers) | ❌ armv7 | subclasses `piper`, adds RU stress; **x86_64/aarch64 only** (ORT wall) |

---

## 4. armv7 ground truth — the real WB7 (SSH 192.168.110.250, 2026-06-15)

| Fact | Value | Consequence |
|---|---|---|
| SoC | Allwinner sun8i **Cortex-A7 quad**, armv7l, NEON/vfpv4 | weak cores → Piper RTF may be 1–3× (consider Piper **"low"** model) |
| RAM | **1 GB total. ~367 MB available *with SprutHub running*; ~712 MB after SprutHub was stopped+disabled (2026-06-15, frees ~343 MB)** + 256 MB swap | the three deploy containers fit in ~712 MB |
| Disk | **`/mnt/data` = 4.7 GB, 2.3 GB free** (docker root = `/mnt/data/.docker`); rootfs `/` has only ~785 MB free **but images + models live on `/mnt/data`** | disk is **NOT** the constraint (my earlier "784 MB" cited the wrong partition); vosk_tts/Whisper-small are barred by **RAM**, not disk |
| glibc | **2.31** | newer `sherpa-onnx-core` needs ≥2.35 → **stays pinned at `sherpa-onnx==1.10.46`** (matches pyproject) |
| Python | **3.9** | wheels must be cp39 |
| Deployment | **dockerized** — Irene runs as a container alongside `wb-mqtt-bridge` + `wb-mqtt-ui` (Irene's own `config-ui` is **NOT** deployed on WB7) | armv7 images already on GHCR (`ghcr.io/droman42/*`, linux/armv7) |

> **Topology (corrected 2026-06-15):** the **ESP32 satellites** own mic capture, **VAD**, **wake-word/voice-trigger**, and
> audio **playback**. WB7's Irene is the **back half only** — it receives a gated, segmented utterance, runs
> **ASR → NLU → intent → TTS**, and streams TTS PCM **back** to the ESP32 (ARCH-21/22 reply channel). So WB7 has **no
> server-side VAD, no voice-trigger, no local mic/speaker** (`skip_wake_word=True`).

**The armv7 ORT wall:** anything depending on the **standalone `onnxruntime` pip package** (RUAccent, vosk_tts,
onnx-asr) is blocked on armv7l — no Microsoft armhf wheel — and **cannot** borrow sherpa-onnx's statically-linked ORT.
So on WB7: **Piper *direct only*** (espeak-ng stress). RUAccent + vosk_tts are **64-bit-only** options.

### Honest per-model memory (disk + approx resident RAM, int8; estimates, not WB7-benchmarked)

| Stage / model | Disk | RAM | WB7 |
|---|---|---|---|
| VAD Silero (ONNX) | ~2 MB | ~30 MB | **ESP32, not WB7** (✅ on 64-bit standalone) |
| ASR vosk-model-small-ru | ~27 MB | ~120 MB | ✅ **recommended** |
| ASR Whisper tiny / base / small int8 | 75 / 145 / 470 MB | ~200 / ~350 / ~800 MB | tiny⚠ base⚠ small❌ |
| TTS Piper ru medium (+espeak-data) | ~75 MB | ~150 MB | ✅ **recommended** |
| TTS pyttsx/espeak | ~5 MB | ~25 MB | ✅ fallback |
| RUAccent | ~50–200 MB | ~300–500 MB | ❌ (ORT wall) |
| vosk_tts model | 746 MB | >1 GB | ❌ |
| torch (any Silero) | — | ~1–2 GB | ❌ |

**Recommended WB7 stack (satellite-server role):** Irene = **ASR (sherpa/vosk-small) + NLU + intent + TTS (Piper-direct)**
only — no VAD/voice-trigger (ESP32's job), no local audio. Models ≈ **~114 MB** (vosk-small 27 + Piper ru-med 75 +
espeak-data 12), runtime ≈ **~280–350 MB RAM**; prefer **lazy TTS load** over the profile's blanket `preload_models = true`.

**Three-container WB7 budget (post-SprutHub, measured 2026-06-15):**

| Container | Disk | RAM (est.) |
|---|---|---|
| wb-mqtt-bridge | ~155 MB | ~120–200 MB |
| wb-mqtt-ui | ~40 MB | ~10–20 MB (nginx static) |
| Irene (backend; no config-ui) | ~120–180 MB img + ~114 MB models | ~280–350 MB |
| **Total** | **~430–490 MB of 2.3 GB free** | **~410–570 MB of 712 MB** (+256 MB swap) |

Fits with ~140–300 MB RAM headroom. Softest number = the bridge's runtime RSS (estimate, not measured).

**Whisper is NOT for WB7** — RAM bars it, and tiny/base are worse at Russian than vosk-small. Whisper-via-sherpa
is the **64-bit** win (small/medium fit there).

---

## 5. Deployment matrix — the three images (BUILD-3, decided 2026-06-15) ★ source of truth

Three Docker images, **split by architecture** (base image + wheels + system packages differ); the **role/providers** are
set by the baked `CONFIG_PROFILE` fed to the build-analyzer. **torch is contained to one image** (x86_64 standalone); both
ARM satellites are torch-free sherpa-onnx.

| Image | Arch | Role | ASR | TTS | Stack | Config |
|---|---|---|---|---|---|---|
| **`Dockerfile.x86_64`** (repurpose) | x86_64 | **standalone** full-voice (`voice` runner: mic→VAD→wake→ASR→NLU→TTS→playback) | **torch Whisper** (existing) | **Silero v4** (existing) | **torch** — only torch image | **baked default + external override** (built "full"-deps so an override reaches any provider) |
| **`Dockerfile.aarch64`** (NEW) | aarch64 — **WB8.5 / Pi** | satellite-server (ASR+TTS for ESP32) | **Whisper-small via sherpa** (T1) | **Piper + RUAccent** (T2) | **sherpa**, torch-free | **baked** `embedded-aarch64.toml` |
| **`Dockerfile.armv7`** | armv7 — **WB7** | satellite-server (ASR+TTS for ESP32) | vosk-small (sherpa) | **Piper-direct** (T2) | **sherpa**, torch-free | **baked** `embedded-armv7.toml` (redo) |

**WB8.5 hardware (researched 2026-06-15, spec-only — no WB8 on hand):** Allwinner **T507, quad Cortex-A53 @ 1.5 GHz,
aarch64 (64-bit)**, 2/4 GB LPDDR4 (**4 GB** target), Debian 11 / glibc 2.31, 16–64 GB eMMC + writable `/mnt/data`, **no NPU**
(CPU inference only). Verdict: WB8 is aarch64 → the **armv7 ORT wall does not apply** (Microsoft ships onnxruntime aarch64
wheels) **and torch aarch64 wheels exist** (`torch-2.7.1-…-manylinux_2_28_aarch64`, installs on glibc 2.31). So torch
*could* run on WB8 — but it is **deliberately excluded** there (footprint + A53 latency): the aarch64 satellite runs the
same torch-free sherpa stack as armv7, just with **bigger models** (Whisper-small + RUAccent) that WB7 can't fit.

**Two satellites, one role:** aarch64 and armv7 are the *same* satellite-server (ESP32 owns VAD/VT/audio; Irene =
ASR→NLU→intent→TTS, streams PCM back). They differ only in model allowance. standalone (x86_64) is the lone different
role (full local pipeline, torch). The two satellites share most of their config — differ mainly in the model picks above.

**Config strategy:** the two satellites **bake** their profile (build-analyzer reads it at build time → a minimal,
immutable appliance image). standalone **bakes a default + lets a mounted/env config override it** — and since the
build-analyzer fixes installed deps from the baked config, standalone is built with a **generous/full dep set** so an
override can switch *providers* (not just params) without a rebuild.

**Provider work each image needs (ARCH-24):** standalone → **none** (existing torch Whisper + Silero v4); aarch64 → **T1**
(sherpa-Whisper — **already implemented**, just needs a `whisper-small` pack + on-device verify) **+ T2** (`piper` +
`piper_ruaccent`); armv7 → **T2** (`piper` only). So **T2 (Piper) is the real new provider work**; T1 is a pack entry +
verification; standalone needs nothing new.

**Verify on aarch64 before committing:** (a) `sherpa-onnx`/`sherpa-onnx-core ≥1.13` aarch64 wheel installs on glibc 2.31
(very likely — aarch64 wheels are manylinux2014/2.17); (b) Whisper-small RTF on the A53 (no WB8 to benchmark yet).

---

## 6. Decisions in principle (updated 2026-06-15)

1. **Whisper → sherpa-onnx** (T1) — the **aarch64 satellite's** ASR (Whisper-small int8). Sole consumer; armv7 uses
   vosk-small, standalone keeps torch-Whisper. **Agreed.**
2. **Silero v4 stays torch — and only in the x86_64 standalone image.** Excluded from *both* ARM satellites (armv7 by the
   no-wheel wall; aarch64 by choice — footprint + A53 latency), enforced by packaging + the T3 validator.
3. **Two Piper TTS providers** via sherpa-onnx `OfflineTts` (not one provider with an optional stage):
   (a) **`piper`** — plain VITS + espeak-ng phonemization, **all environments incl. armv7** (the WB7 TTS);
   (b) **`piper_ruaccent`** — **subclasses `piper`**, injects RUAccent stress/ё preprocessing before synth, overriding
   **only** the text-prep hook; **`x86_64`/`aarch64` only** (RUAccent needs the standalone onnxruntime wheel → armv7 ORT wall).
4. **armv7 role = satellite-*server* (NOT standalone).** The ESP32 satellites own mic + VAD + voice-trigger + playback;
   WB7's Irene is the back half — ASR/NLU/intent/TTS, `skip_wake_word=True`, **no** server VAD, mic, speaker, or
   `config-ui`. It evolves today's headless `embedded-armv7.toml` (which returns text only) by turning **TTS synthesis
   on** + wiring the ESP32 reply-channel transport — *not* by adding local mic/playback. Runs **dockerized** beside
   `wb-mqtt-bridge` + `wb-mqtt-ui`.

## 7. Work threads (for ARCH-24 when scheduled)

- **T1** Whisper-in-sherpa — **ALREADY IMPLEMENTED** (discovered 2026-06-15). The `sherpa_onnx` ASR provider already
  branches on `model_type`: `vosk-transducer`→`from_transducer`, **`whisper`→`from_whisper`** (`sherpa_onnx.py:128-143`),
  with `whisper-tiny`/`whisper-base` packs declared (`:358-372`). It is **ONE provider with a `model_type` discriminator —
  NOT a separate provider, NOT a base/derived split** (branch surface ~3 points: build closure + language list + streaming
  flag; the decode loop / numpy-free audio conversion / asset download / policy are all shared). **Remaining for the
  aarch64 satellite:** add a `whisper-small` pack to `_get_default_model_urls()` + **verify on-device** (Russian parity,
  A53 RTF). The torch `whisper.py` provider **stays** as the standalone image's ASR (its caching is the openai-whisper
  library's, not the Silero pattern — so it does **not** need `TorchModelCache`).
- **T2** **Two** Piper TTS providers (sherpa `OfflineTts`/VITS) + a `ru_RU` voice asset:
  - **`PiperTTSProvider`** (entry point `piper`) — base; espeak-ng phonemization; `get_platform_support()` = all incl.
    `armv7l`; deps = the already-shipped sherpa-onnx runtime. This is the WB7 TTS.
  - **`PiperRuAccentTTSProvider(PiperTTSProvider)`** (entry point `piper_ruaccent`) — overrides **only** the text-prep
    hook to run RUAccent (stress `+`/ё) before the inherited synth; adds the `ruaccent` dep; `get_platform_support()` =
    `x86_64`/`aarch64` **only** (armv7 ORT wall). Model load / synth / streaming all inherited from the base.
- **T3** Platform taxonomy + validation: add `armv7l` to provider `get_platform_support()` taxonomy; extend the CI
  `dependency_validator --platforms` to include armv7 so **any armv7 profile enabling a torch provider fails the build**;
  evolve the `embedded-armv7` profile from headless-ASR-satellite → **ASR+TTS satellite-server** (TTS synthesis on +
  stream PCM back to the ESP32; VAD/voice-trigger/mic/playback stay **off** — ESP32's job; no `config-ui`; lazy TTS load).
- **T4 (packaging) → BUILD-3:** **three Docker images, split by architecture** (canonical matrix = **§5**):
  `Dockerfile.x86_64`→**standalone** (torch: Whisper + Silero v4), **NEW `Dockerfile.aarch64`**→**WB8/Pi satellite**
  (sherpa: Whisper-small + Piper+RUAccent), `Dockerfile.armv7`→**WB7 satellite** (sherpa: vosk-small + Piper-direct).
  Config: **bake** for the two satellites; **baked default + external override** (full-dep build) for standalone. Each
  image gets one manually-triggerable (`workflow_dispatch`) buildx→GHCR workflow (bridge `v<date>-<sha>`+`latest` style).
  **Prerequisite: T1 (for aarch64) + T2 (for both satellites) implemented FIRST** — a baked config can't name
  `piper`/Whisper-in-sherpa before the provider exists. Then (interactive) config per target → Dockerfile design
  (baked-in vs mounted volumes, ports, `/dev/snd`, entrypoint) → per-image workflow. This is **BUILD-3** in the ledger.

- **T5 (shared-runtime helpers — refactor, triggered by T2; for sherpa AND torch).** **Not** a generic engine abstraction
  — the per-library APIs don't unify and ORT is bundled inside sherpa, so a grand abstraction is correctly absent. The
  shared seam that *does* generalize (model-asset management via `get_asset_manager()`) is already abstracted. T5 closes the
  **narrow, intra-runtime** gaps:
  - **Sherpa:** Piper-via-sherpa makes the sherpa family = ASR + VAD + TTS (3 consumers). Extract a thin
    `SherpaSession`/`InferencePolicy` helper (resolve model-dir from the asset manager + apply the platform thread policy +
    build off the event loop) and fold in `SherpaInferencePolicy` (today only in `sherpa_onnx.py:39-57`) + the silero VAD
    (which currently **ignores** the policy and hardcodes sherpa defaults — `utils/vad_silero.py:52-58`), so `num_threads`
    is set consistently across all sherpa providers on the A7/A53. Introduce **with T2**, not by copying the boilerplate a
    third time. (Session construction stays per-provider — `from_transducer`/`from_whisper`/`OfflineTts`/`VAD` don't unify.)
  - **Torch:** optional `TorchModelCache` for `silero_v3`/`silero_v4` — near-identical copy-pasted class-level
    `_model_cache` + lock + `_get_or_load_cached_model` (~30 lines each). The torch `whisper.py` provider does **NOT** need
    it (caching delegated to `whisper.load_model()`; one lazy instance, no manual cache/lock to dedupe).

- **Open checks:** (a) ~~verify `sherpa-onnx==1.10.46` cp39 armv7 wheel exposes `OfflineTts`/VITS on the real WB7~~ —
  **✅ VERIFIED 2026-06-15 on 192.168.110.250.** Downloaded `sherpa_onnx-1.10.46-cp39-cp39-linux_armv7l.whl` (14.5 MB),
  imported under the box's Python 3.9 — the compiled `.so` **loads and runs** on glibc 2.31 / Cortex-A7, and exposes both
  `OfflineRecognizer` (ASR) and `OfflineTts` + `OfflineTtsConfig` + **`OfflineTtsVitsModelConfig`** (Piper/VITS), plus
  Matcha/Kokoro configs. The "one sherpa-onnx engine carries both ASR and TTS on WB7" premise **holds on the real hardware.**
  (b) Piper medium vs "low" RTF on the A7 — still TODO; (c) on-device RAM peak with both models loaded — still TODO.

## 8. Dependabot linkage

The two **ARM satellite images** (armv7 + aarch64) are torch-free, so they carry **none** of the deferred torch ×4 /
protobuf/sentencepiece alerts. torch survives **only in the x86_64 standalone image** (existing Whisper + Silero v4) —
acceptable per the user's stance (torch is fine on the big standalone install). So the alerts aren't "resolved" so much as
**contained to one image**; they stay deferred (low/medium, opt-in ML extras only).

**transformers:** `piper_ruaccent`'s `ruaccent` dep pulls `transformers` back in (torch-free, np-tokenization only) on the
**aarch64 satellite** (and any standalone override that enables it) — `ruaccent` *replaces* `runorm` as the reason
transformers exists. The **armv7 image stays transformers-free** (plain `piper`); aarch64 carries it by design.
