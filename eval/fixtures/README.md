# Audio fixtures

Record/synthesize these as **16 kHz, mono, 16-bit PCM WAV** (the `/ws/audio` wire format —
the provider validates this and won't resample, so tests measure the ASR, not a converter).

| File | Spoken (Russian) | Used by |
|---|---|---|
| `timer_10min.wav` | «поставь таймер на десять минут» | cases 1, 2, 3 |
| `light_unreachable.wav` | a command targeting a device that will be unreachable | case 4 |

Fixtures are git-ignored by default (binary). To version them, drop a `.gitignore`
exception or use git-lfs. Keep the spoken text in sync with the `reference:` vars in
`../promptfooconfig.yaml`.

Quick way to make a fixture from TTS, then conform the format:

```bash
# example: synthesize, then force 16k/mono/16-bit
ffmpeg -i raw.wav -ar 16000 -ac 1 -sample_fmt s16 timer_10min.wav
```
