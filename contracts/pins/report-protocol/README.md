# report-protocol — the problem-report wire protocol pin (consumed)

A **pinned, one-way-inward copy** of the `locveil-commons`-owned problem-report machine
core (HK-3/PROD-6). Commons is the source of truth: artifact
`contracts/report-protocol/report-protocol.json` (the pinned tag is recorded in
`PIN.json`), normative prose `process/problem-reports.md`. Never hand-edit any file here —
the pin moves only by a re-pin task.

| File | Origin | What it is |
|---|---|---|
| `report-protocol.json` | commons (byte-identical) | The machine core: labels, title prefix, bundle path — what the triage queue queries key on |
| `STAMP.json` | commons (byte-identical) | The owner's version stamp for the artifact |
| `PIN.json` | **voice-stamped** | The pin record: which commons tag/commit voice validates against, file hashes, and when |

Conformance (layer 2): `backend/tests/test_report_protocol_conformance.py` — the
collector's emitted labels, title prefix, and bundle path, plus the deployment profiles'
`[reports].repo`, are asserted against this pin (a label mismatch makes tickets silently
invisible to the triage queue).

Re-pin (a deliberate ledger task; the tool copies the owner's enumerated set and stamps
`PIN.json` — nothing here is ever written by hand):

```bash
make -C eval repin CONTRACT=report-protocol
uv run pytest backend/tests/test_report_protocol_conformance.py -q
```
