"""trace-format version-surface conformance (PROD-16 convention, layer 2; DOC-14).

The utterance-trace JSON format's version exists as a TRIPLE — the "Trace format
version" line in `docs/guides/tracing.md` (`trace-format-doc-canonical`), the written
constant `core/trace_context.py::TRACE_FORMAT_VERSION` (stamped into every saved
envelope as `trace_version`), and `contracts/trace-format/STAMP.json` — and a bump
that misses one leg ships a lie (a reader checks the file's number against the doc it
was built from).
"""
import json
import re
from pathlib import Path

from locveil_voice.core.trace_context import TRACE_FORMAT_VERSION, TraceContext

_REPO_ROOT = Path(__file__).resolve().parents[2]
STAMP = json.loads(
    (_REPO_ROOT / "contracts" / "trace-format" / "STAMP.json").read_text(encoding="utf-8"))
DOC = (_REPO_ROOT / "docs" / "guides" / "tracing.md").read_text(encoding="utf-8")


def test_trace_format_version_triple():
    m = re.search(r"\*\*Trace format version: (\d+)\*\* \(`(trace-format-v\S+)`\)", DOC)
    assert m, "tracing.md lost its 'Trace format version' header line"
    doc_version, doc_tag = m.group(1), m.group(2)
    assert doc_version == str(TRACE_FORMAT_VERSION) == STAMP["version"]
    assert doc_tag == STAMP["tag"] == f"trace-format-v{TRACE_FORMAT_VERSION}"


def test_trace_stamp_core():
    assert STAMP["contract"] == "trace-format"
    assert STAMP["owner_repo"] == "locveil-voice"
    assert STAMP["artifact"] == "docs/guides/tracing.md"


def test_envelope_carries_the_stamped_version():
    envelope = TraceContext(enabled=False).build_envelope()
    assert envelope["trace_version"] == TRACE_FORMAT_VERSION
