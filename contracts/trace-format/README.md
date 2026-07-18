# trace-format — the utterance-trace JSON format (owned)

The normative artifact **lives at [`docs/guides/tracing.md`](../../docs/guides/tracing.md) →
"The trace file format (reference)"** (`trace-format-doc-canonical` — a hand-written reference
inside the user guide; owned surfaces that legitimately live elsewhere keep their home, per
`../locveil-commons/process/contracts.md` §2). This folder holds the version authority only.

The version exists in a **triple**, asserted equal by
`backend/tests/test_trace_format_version.py`:

1. the guide's "Trace format version" line,
2. the written constant `backend/src/locveil_voice/core/trace_context.py::TRACE_FORMAT_VERSION`
   (stamped into every saved envelope as `trace_version`),
3. `STAMP.json` here.

Compatibility rule (stated in the guide): additive keys keep the version — readers ignore
unknown keys; a key removed, renamed, or repurposed bumps all three legs together and tags
`trace-format-vN`. The STAMP deliberately carries no `artifacts` byte-enumeration: the guide's
prose evolves freely, and the normative surface is the tested triple (same posture as
`ws-protocol`).

Writers: `core/trace_context.py::TraceContext.build_envelope` (controller) and
`satellite/trace.py` (the merged room-node file — same envelope plus `controller_trace` /
`raw_mic` / `reply_audio`). Readers: `locveil-voice-replay-trace`, the satellite's own tooling,
and the eval framework's trace scorers when they land.
