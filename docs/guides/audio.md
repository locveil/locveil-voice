# Audio

The audio component plays sound out — TTS replies, prompts, notifications. It's a capability with
interchangeable **playback providers**; which one you use depends on the platform and what's installed.
(Microphone *input* and resampling are configured alongside ASR; this guide is about output.)

## Playback providers

`[audio]` selects among five, discovered via `irene.providers.audio`:

| Provider | Needs | Platforms | Notes |
|---|---|---|---|
| **console** | nothing | all | headless/testing stub; the default and the fallback |
| **sounddevice** | `sounddevice`, `soundfile` + PortAudio & libsndfile | all | high-quality playback + device enumeration |
| **audioplayer** | `audioplayer` | all | simple cross-platform playback |
| **aplay** | ALSA `alsa-utils` | Linux only | shells out to the `aplay` binary |
| **simpleaudio** | `simpleaudio` + ALSA libs | all | lightweight, WAV only |

## Installation

The playback engines ship behind the **`audio-output`** extra (sounddevice, soundfile, audioplayer, plus
numpy/librosa). Their system libraries aren't pip-installable — add them per platform:

- **sounddevice** — PortAudio + libsndfile: `libportaudio2 libsndfile1` (Debian/Ubuntu), `portaudio
  libsndfile` (Alpine/macOS).
- **aplay** — `alsa-utils`.
- **simpleaudio** — `libasound2` (Ubuntu) / `alsa-lib` (Alpine). It is currently commented out of the extra
  over a build issue; install it yourself if you want it.

`console` needs nothing — which is why a fresh, model-free deployment still "speaks" (to the log).

## Configuration

```toml
[components]
audio = true

[audio]
enabled = true
default_provider = "sounddevice"
fallback_providers = ["console"]
concurrent_playback = false
```

`components.audio = true` turns the component on; `[audio]` picks the provider and a fallback (`console` is
the safe fallback everywhere). Note **TTS requires Audio** — enabling `[tts]` without `[audio]` is rejected
at startup.

## Sample rates & hardware

Irene runs internally at 16 kHz; a capture device at 44.1 / 48 kHz is resampled up the pipeline. Sample-rate
and resampling settings live with the microphone input (see [configuration](configuration.md)); the value
worth knowing is `resample_quality` — `fast` · `medium` · `high` · `best`. On a machine with several output
devices, the `sounddevice` provider can target a specific one.

## Troubleshooting

- **No sound** — confirm `components.audio` is on and `default_provider` isn't `console`; check the OS can
  play at all (`aplay test.wav`, `pactl list sinks`).
- **"No module / library" on startup** — the provider's system package is missing (PortAudio, libsndfile or
  ALSA, above), or the `audio-output` extra wasn't installed.
- **Device not found / wrong output** — list devices (`aplay -l`, `pactl list`), select one, and make sure
  your user is in the `audio` group.
- **Distorted or wrong-speed playback** — a sample-rate mismatch; let resampling handle it and keep the
  pipeline at 16 kHz.

For choosing or adding the TTS engine that *generates* the audio, see [adding a model](howto-new-model.md);
for how the component sits in the pipeline, see [components](../architecture/components.md).
