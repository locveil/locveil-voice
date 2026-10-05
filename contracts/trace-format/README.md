# trace-format — the utterance-trace JSON format (owned)

The normative artifact **lives at [`docs/guides/tracing.md`](../../docs/guides/tracing.md) →
"The trace file format (reference)"** (`trace-format-doc-canonical` — a hand-written reference
inside the user guide; owned surfaces that legitimately live elsewhere keep their home, per
`../locveil-commons/process/contracts.md` §2). This folder holds the version authority.

**The guide is enumerated whole** in `STAMP.json` → `artifacts` (doc-canonical contracts lock
the whole file — there is no marked-region mechanism): the list is what a consumer pins and
what the contract guard byte-locks. Any edit to the tracing guide — in the reference section
or anywhere else in the file — is a version move, cut in the same change.

Versions have three levels (`process/contracts.md` §3):

| Level | When | Written `trace_version` |
|---|---|---|
| major | a key removed, renamed, or repurposed (breaks readers) | moves — it IS the major |
| minor | an additive key (readers ignore unknown keys) | unchanged |
| patch | the guide's bytes moved, the format did not | unchanged |

`backend/tests/test_trace_format_version.py` keeps the legs in agreement:

1. `STAMP.json` is the authority — a three-part `version`, `tag` = `trace-format-v<version>`;
2. the guide's "Trace format version" line shows the **major** and names the STAMP's tag exactly;
3. the written constant `backend/src/locveil_voice/core/trace_context.py::TRACE_FORMAT_VERSION`
   (stamped into every saved envelope as `trace_version`) equals the **major**.

Cutting a version: edit the guide + bump `STAMP.json` (`version`, `tag`, `date`) + the guide's
version-line tag in ONE commit, tag that commit `trace-format-vX.Y.Z`, push commit and tag
together.

Writers: `core/trace_context.py::TraceContext.build_envelope` (controller) and
`satellite/trace.py` (the merged room-node file — same envelope plus `controller_trace` /
`raw_mic` / `reply_audio`). Readers: `locveil-voice-replay-trace`, the satellite's own tooling,
and the eval framework's trace scorers when they land.
