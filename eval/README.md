# eval/ — declarative system + UX tests for wb-mqtt-voice

Pure-YAML test cases. All execution logic lives in the shared **`eval-commons`** package
(sibling repo: `../../eval-commons`). See its `ARCHITECTURE.md` for the full design.

## What it tests

| # | Case | Kind | How it's judged |
|---|---|---|---|
| 1 | ASR accuracy of a timer utterance | system | WER via `jiwer` (`wer_scorer.py`) |
| 2 | Intent recognition (`timer.set`) | system | parse final-response metadata |
| 3 | Russian confirmation wording | UX | `llm-rubric` → **DeepSeek** judge |
| 4 | Polite failure on unreachable device | UX | `llm-rubric` → **DeepSeek** judge |

All four drive the shipped streaming-ASR endpoint **`/ws/audio`** (ARCH-10). The
smart-home/MQTT surface is a commented FUTURE block in the config (bridge REST is
design-only today).

## Setup

```bash
# 1. Runner
npm install -g promptfoo            # or use npx promptfoo@latest below

# 2. Shared providers/assertions (puts eval_commons on PYTHONPATH for the providers)
pip install -e ../../eval-commons

# 3. Env
cp ../../eval-commons/examples/.env.example .env
#   set DEEPSEEK_API_KEY, and WS_AUDIO_URL=ws://localhost:6000/ws/audio
export $(grep -v '^#' .env | xargs)

# 4. Record fixtures (see fixtures/README.md) — 16 kHz mono PCM16 WAV:
#      fixtures/timer_10min.wav        "поставь таймер на десять минут"
#      fixtures/light_unreachable.wav  an utterance targeting an unreachable device
```

## Run

```bash
# Irene must be running and serving /ws/audio on the configured port.
cd eval
promptfoo eval            # add `--no-cache` while iterating
promptfoo view           # open the results UI
```

If promptfoo can't import `eval_commons`, point it at the right interpreter:
`PROMPTFOO_PYTHON=$(which python) promptfoo eval`.

## Notes / TODO

- **Intent name** in case 2 is a placeholder (`timer.set`) — confirm the exact name Irene's
  timer handler emits against a live run and adjust.
- **DeepSeek-as-judge on Russian is unvalidated.** Before trusting UX pass/fail in CI,
  hand-score a handful of replies and check judge agreement (ARCHITECTURE.md §7.1). Treat
  current UX verdicts as indicative, not authoritative.
- One audio run feeds all of a case's assertions via per-assertion `transform` (the
  single-run fan-out described in ARCHITECTURE.md §4).
