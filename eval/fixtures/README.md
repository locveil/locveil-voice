# Audio fixtures

Record/synthesize these as **16 kHz, mono, 16-bit PCM WAV** (the `/ws/audio` wire format —
the provider validates this and won't resample, so tests measure the ASR, not a converter).

**Partitioned by language** (`fixtures/<lang>/`) — same scenario filenames across languages, so a
run selects a language via `EVAL_LANG` and the cases resolve `fixtures/{{env.EVAL_LANG}}/<file>`.
Coverage parity between languages is a directory diff.

| File (per `<lang>/`) | Spoken — `ru` | Spoken — `en` | Used by |
|---|---|---|---|
| `timer_10min.wav` | «поставь таймер на десять минут» | "set a timer for ten minutes" | cases 1, 2, 3 |
| `light_unreachable.wav` | «включи свет в гараже» | "turn on the light in the garage" | case 4 |

`fixtures/ru/*` are recorded + committed; `fixtures/en/*` are **pending recording**.

These fixtures **are committed** — `eval/fixtures/**/*.wav` is carved out of the repo's
blanket `*.wav` ignore, because they're versioned test *inputs*: committing them keeps WER
reproducible (everyone scores the same recording) and lets the WS suite run in CI, where
there's no microphone. They're small; switch to git-lfs only if that ever changes. The
spoken text lives in each case's `reference:` var in `../ws.promptfooconfig.yaml` — the
recorder reads it to you, so it stays in sync.

## Record them: `make record`

One-time setup (adds the mic deps), then record the missing fixtures interactively:

The language is selected by `EVAL_LANG` (or a `-en` `CONFIG`), which points the recorder at the right
`fixtures/<lang>/` subdir and reads the matching `reference:` line to speak:

```bash
make setup-record                 # adds sounddevice + soxr to the venv (once)
cp profiles/recording.env.example profiles/recording.env   # then set REC_INPUT_DEVICE
make record-devices               # ... find your device name/index for that file
make record-list                  # what's needed/missing for EVAL_LANG (no mic)
make record                       # Russian (EVAL_LANG=ru, default) — record every missing fixture
make record EVAL_LANG=en          # English — record the fixtures/en/* set
make record EVAL_LANG=en FIXTURE=timer_10min   # just one
```

The recorder (locveil-eval' `eval-fixture-record`) shows the line to read, records from
the configured mic, lets you re-take, and writes a conformant **16 kHz / mono / PCM16** WAV —
validated on save against the same check the `/ws/audio` provider applies.

### Alternative: synthesize from TTS, then conform the format

```bash
ffmpeg -i raw.wav -ar 16000 -ac 1 -sample_fmt s16 timer_10min.wav
```
