"""trace-format version-surface conformance (contracts convention, layer 2; DOC-14, BUILD-49).

Three-level versions (`../locveil-commons/process/contracts.md` §3, HK-13): the STAMP is the
version authority and carries a three-part `version` (major = a key removed/renamed/
repurposed, minor = an additive key, patch = the guide's bytes moved with the format
untouched). The value written into every saved file carries the MAJOR only — a minor or
patch cut must never change what a saved trace's reader compares. The legs that must agree:

- `contracts/trace-format/STAMP.json` — `tag` == `trace-format-v<version>`, three-part;
- the "Trace format version" line in `docs/guides/tracing.md`
  (`trace-format-doc-canonical`) — shows the MAJOR and names the STAMP's tag exactly;
- the written constant `core/trace_context.py::TRACE_FORMAT_VERSION` (stamped into every
  saved envelope as `trace_version`) — equals the MAJOR.

A cut that misses one leg ships a lie (a reader checks the file's number against the doc
it was built from).
"""
import json
import re
from pathlib import Path

from locveil_voice.core.trace_context import TRACE_FORMAT_VERSION, TraceContext

_REPO_ROOT = Path(__file__).resolve().parents[2]
STAMP = json.loads(
    (_REPO_ROOT / "contracts" / "trace-format" / "STAMP.json").read_text(encoding="utf-8"))
DOC = (_REPO_ROOT / "docs" / "guides" / "tracing.md").read_text(encoding="utf-8")


def _major(version: str) -> str:
    return version.split(".")[0]


def test_trace_stamp_is_the_three_part_version_authority():
    assert re.fullmatch(r"\d+\.\d+\.\d+", STAMP["version"]), (
        "STAMP version must be three-part (major.minor.patch)")
    assert STAMP["tag"] == f"trace-format-v{STAMP['version']}"


def test_trace_doc_line_names_the_stamp_tag():
    m = re.search(r"\*\*Trace format version: (\d+)\*\* \(`(trace-format-v[0-9.]+)`\)", DOC)
    assert m, "tracing.md lost its 'Trace format version' line"
    doc_major, doc_tag = m.group(1), m.group(2)
    assert doc_tag == STAMP["tag"], "the guide's version line must name the STAMP's tag exactly"
    assert doc_major == _major(STAMP["version"]), "the guide's number is the MAJOR"


def test_written_trace_version_is_the_major_only():
    # A minor or patch cut never changes the written value — only a reader-breaking change does.
    assert isinstance(TRACE_FORMAT_VERSION, int)
    assert str(TRACE_FORMAT_VERSION) == _major(STAMP["version"])


def test_trace_stamp_core():
    assert STAMP["contract"] == "trace-format"
    assert STAMP["owner_repo"] == "locveil-voice"
    # doc-canonical: the WHOLE guide is enumerated (what consumers pin, what is byte-locked)
    assert "docs/guides/tracing.md" in STAMP["artifacts"]
    for artifact in STAMP["artifacts"]:
        assert (_REPO_ROOT / artifact).is_file(), f"enumerated artifact missing: {artifact}"
    # pointer fields resolve to real files
    constant_file, _, constant_name = STAMP["code_constant"].partition("::")
    assert (_REPO_ROOT / constant_file).is_file()
    assert constant_name == "TRACE_FORMAT_VERSION"


def test_envelope_carries_the_stamped_major():
    envelope = TraceContext(enabled=False).build_envelope()
    assert envelope["trace_version"] == TRACE_FORMAT_VERSION
