# Golden traces

Recorded execution traces, replayed offline as **regression tests** — replay re-runs the recorded input
through the *current* pipeline and diffs against the recorded **oracle** (`text` / `success` / `actions`).
Exit `0` = still matches, `2` = behavior drifted. See `../trace.promptfooconfig.yaml` and
`../../docs/design/trace_system_testing.md`.

These are **committed** (unlike the `*.wav` fixtures, they're text JSON): a behavior change shows up as a
reviewable diff in the recorded oracle. The replay tool normalizes volatile fields (timestamps like a
timer's `started_at`) before diffing, so a deterministic handler stays a stable green golden.

**Partitioned by language** (`traces/<lang>/`), like the fixtures — a run selects a language via
`EVAL_LANG`, and the replay case resolves `traces/{{env.EVAL_LANG}}/<name>.json` under the run's config
(`{{env.IRENE_CONFIG_FILE}}`, the deployment the golden represents).

| Trace (per `<lang>/`) | Input | Tier |
|---|---|---|
| `ru/timer_set_10min.json` | «поставь таймер на 10 минут» → timer set | `trace-system` (deterministic) |
| `en/timer_set_10min.json` | "set a timer for ten minutes" → timer set (**pending recording**) | `trace-system` |

> The golden uses the digit «10 минут»; the spelled-out «десять минут» now sets a timer too (the number-word
> parsing gap was fixed), so a natural-speech golden can be added alongside it.

## Run

```bash
make replay                          # Russian goldens (EVAL_LANG=ru, default); needs the models present
make replay CONFIG=embedded-armv7-en # English goldens (EVAL_LANG=en) — once traces/en/* are recorded
make replay-judge                    # the trace-ux tier (LLM replies graded by DeepSeek; needs DEEPSEEK_API_KEY)
```

## Record a new golden

Tracing is enabled per-run with `--set` (no need to edit a config file). Record a known-good interaction
**under the language's config**, into that language's subdir, then commit the resulting JSON:

```bash
# 1. bring a SUT up with tracing on, writing traces into the LANGUAGE subdir (en shown; use the -en config):
irene-webapi --config configs/embedded-armv7-en.toml \
  --set trace.enabled=true --set "trace.traces_dir=$PWD/eval/traces/en"
# 2. drive the interaction (text shown here; audio works the same once a fixture exists):
curl -s -X POST localhost:6000/execute/command -H 'Content-Type: application/json' \
  -d '{"command":"set a timer for ten minutes"}'
# 3. rename <request-id>.json to something meaningful, confirm it replays green, commit it:
irene-replay-trace -t eval/traces/en/<name>.json --config configs/embedded-armv7-en.toml   # expect exit 0
```

**Tiering (curate deliberately):** put a trace in `trace-system` only when its path is deterministic
(ASR + cheap NLU + rule-handlers like timer/smart-home). LLM-driven replies vary run-to-run → mark them
`trace-ux` and let the judge grade the reply instead of asserting an exact match. The oracle drifts *on
purpose* when you change behavior — re-record and review the JSON diff; that's the workflow, not a breakage.
