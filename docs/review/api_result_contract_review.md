# Review — API execution-result response contract (consistency)

**Date:** 2026-06-27 · **Scope:** how the shared `WorkflowResult`/`IntentResult` (`.text`, `.success`,
`.confidence`, `.metadata`) is serialized across the endpoints that execute an intent —
`irene/runners/webapi_router.py` (REST `/execute/*`, `/trace/*`; WS `/ws/audio`) + the internal
pipeline-event emitters in `irene/core/workflow_manager.py`.

**Trigger:** surfaced while wiring the `eval/` WS system suite — the `ws_audio_provider` reads
`metadata.intent_name`, which `/ws/audio` never emits. Frozen evidence; this doc asserts no task status.

## Root cause
**There is no shared serializer for the execution result.** Each endpoint hand-builds its own response
dict from the same `WorkflowResult`, so the shapes have drifted. `/execute/command` is the only one that
*normalizes* the result; everyone else passes raw internal metadata through (or omits fields). Findings
1–5 are all symptoms of this one gap.

## Findings

### F1 — reply-text field name: `response` vs `text`
- `/execute/command` (`webapi_router.py:245`) and `/execute/audio` (`:339`) return the reply under **`response`**.
- `/trace/command` (`:427`), `/trace/audio` (`:605`), and `/ws/audio` (`:842`,`:869`) return it under **`text`**.
- Same `result.text`, two names. → **tracked as QUAL-55** (canonical serializer).

### F2 — intent exposure is 3-way inconsistent  *(the trigger)*
- `/execute/command` (`:249`) → `metadata.intent_name`, remapped from `original_intent`. ✓
- `/execute/audio` (`:342`) → intent **not surfaced** (metadata is file-info only).
- `/trace/*` (`:429`,`:607`) and `/ws/audio` (`:843`,`:870`) → raw `result.metadata`, i.e. `original_intent`,
  **no `intent_name`**. A client reading `intent_name` gets `null` here.
- The orchestrator is the producer and writes `original_intent` (`irene/intents/orchestrator.py:232,301,376,535,599`).
- → WS half fixed now (**tracked as QUAL-54**); full unification **tracked as QUAL-55**.

### F3 — same response model, different payloads
- `/execute/command` and `/execute/audio` both declare `CommandResponse` (`irene/api/schemas.py:682`) but
  return entirely different `metadata`: intent-focused (`intent_name`,`confidence`,`execution_time`) vs
  file-focused (`filename`,`file_size_bytes`,`room_context`). The schema promises one shape; the endpoints
  deliver two. → **tracked as QUAL-55**.

### F4 — `confidence` placement differs
- `/execute/command` lifts `result.confidence` into `metadata.confidence` (`:250`); `/trace/*` and `/ws/audio`
  dump raw `result.metadata` (confidence present only if it happens to be in there). → **tracked as QUAL-55**.

### F5 — the same key bug bites internal code (live `None`)
- `workflow_manager.py:482` and `:637` emit pipeline `RESULT_PRODUCED` events with
  `"intent": result.metadata.get("intent_name")` — but the orchestrator writes `original_intent`, so this
  field was **always `None`** in production. Masked by `test_pipeline_events.py`, whose fake returned
  `metadata={"intent_name": …}` (the wrong key) — green test, hidden bug. → **fixed under QUAL-54** (code
  reads `original_intent`; the fake now mirrors the real contract).

## Remediation split
- **QUAL-54** (targeted, done 2026-06-27): fix F2's WS half + F5's internal misreads — the live-bug subset.
- **QUAL-55** (open): introduce one canonical `WorkflowResult → API` serializer and route all five execution
  surfaces through it, retiring F1/F3/F4 and the rest of F2. Touches the response schemas → `config-ui`
  (`apiClient.ts`, `src/types/*`) is a co-change (`config-ui-stays-functional`).
