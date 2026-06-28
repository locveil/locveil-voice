# Golden traces

Recorded execution traces, replayed offline as **regression tests** — replay re-runs the recorded input
through the *current* pipeline and diffs against the recorded **oracle** (`text` / `success` / `actions`).
Exit `0` = still matches, `2` = behavior drifted. See `../trace.promptfooconfig.yaml` and
`../../docs/design/trace_system_testing.md`.

These are **committed** (unlike the `*.wav` fixtures, they're text JSON): a behavior change shows up as a
reviewable diff in the recorded oracle. The replay tool normalizes volatile fields (timestamps like a
timer's `started_at`) before diffing, so a deterministic handler stays a stable green golden.

| Trace | Input | Tier |
|---|---|---|
| `timer_set_10min.json` | «поставь таймер на 10 минут» → timer set | `trace-system` (deterministic) |

> **Note (BUG-1):** the golden uses the **digit** «10 минут» because the spelled-out «десять минут» does
> not currently set a timer (Russian-numeral parsing gap). Once BUG-1 is fixed, add a natural-speech golden.

## Run

```bash
make replay        # offline deterministic replay (trace-system); needs the models present
make replay-judge  # the trace-ux tier (LLM replies graded by DeepSeek; needs DEEPSEEK_API_KEY)
```

## Record a new golden

Tracing is enabled per-run with `--set` (no need to edit a config file). Record a known-good interaction,
then commit the resulting JSON:

```bash
# 1. bring a SUT up with tracing on, writing traces straight into this dir:
irene-webapi --config configs/embedded-armv7.toml \
  --set trace.enabled=true --set "trace.traces_dir=$PWD/eval/traces"
# 2. drive the interaction (text shown here; audio works the same once a fixture exists):
curl -s -X POST localhost:6000/execute/command -H 'Content-Type: application/json' \
  -d '{"command":"поставь таймер на 10 минут"}'
# 3. rename <request-id>.json to something meaningful, confirm it replays green, commit it:
irene-replay-trace -t eval/traces/<name>.json --config configs/embedded-armv7.toml   # expect exit 0
```

**Tiering (curate deliberately):** put a trace in `trace-system` only when its path is deterministic
(ASR + cheap NLU + rule-handlers like timer/smart-home). LLM-driven replies vary run-to-run → mark them
`trace-ux` and let the judge grade the reply instead of asserting an exact match. The oracle drifts *on
purpose* when you change behavior — re-record and review the JSON diff; that's the workflow, not a breakage.
