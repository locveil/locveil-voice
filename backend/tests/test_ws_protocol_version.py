"""ws-protocol / wake-pack version-surface conformance (contracts convention, layer 2).

Three-level versions (`../locveil-commons/process/contracts.md` §3, HK-13): the STAMP is the
version authority and carries a three-part `version` (major = breaking wire change, minor =
additive wire change, patch = enumerated bytes moved with the wire untouched). A
runtime-served version carries the MAJOR only — a minor or patch cut must never change what
a fielded device compares. So the legs that must agree are:

- `contracts/ws-protocol/STAMP.json` — `tag` == `ws-protocol-v<version>`, three-part;
- the "Protocol version" header line of `docs/guides/websocket-api.md`
  (`ws-protocol-doc-canonical`) — shows the MAJOR and names the STAMP's tag exactly;
- the served constant `core/ws_protocol.py::WS_PROTOCOL_VERSION` — equals the MAJOR.

A cut that misses one leg ships a lie (a client checks the served number against the doc it
was built from). The wake-pack sidecar stamp likewise must mirror the in-code released
catalog (`_get_default_model_urls`): a word published in code but absent from the stamp (or
vice versa) breaks the satellite's flash-time hash verification.
"""
import json
import re
from pathlib import Path

from locveil_voice.core.ws_protocol import WS_PROTOCOL_VERSION
from locveil_voice.providers.voice_trigger.microwakeword import MicroWakeWordProvider

_REPO_ROOT = Path(__file__).resolve().parents[2]
WS_STAMP = json.loads((_REPO_ROOT / "contracts" / "ws-protocol" / "STAMP.json").read_text(encoding="utf-8"))
PACK_STAMP = json.loads((_REPO_ROOT / "contracts" / "wake-pack" / "STAMP.json").read_text(encoding="utf-8"))
DOC = (_REPO_ROOT / "docs" / "guides" / "websocket-api.md").read_text(encoding="utf-8")


def _major(version: str) -> str:
    return version.split(".")[0]


def test_ws_stamp_is_the_three_part_version_authority():
    assert re.fullmatch(r"\d+\.\d+\.\d+", WS_STAMP["version"]), (
        "STAMP version must be three-part (major.minor.patch)")
    assert WS_STAMP["tag"] == f"ws-protocol-v{WS_STAMP['version']}"


def test_ws_doc_header_names_the_stamp_tag():
    m = re.search(r"\*\*Protocol version: (\d+)\*\* \(`(ws-protocol-v[0-9.]+)`\)", DOC)
    assert m, "websocket-api.md lost its 'Protocol version' header line"
    doc_major, doc_tag = m.group(1), m.group(2)
    assert doc_tag == WS_STAMP["tag"], "the doc header must name the STAMP's tag exactly"
    assert doc_major == _major(WS_STAMP["version"]), "the doc header number is the MAJOR"


def test_served_protocol_version_is_the_major_only():
    # A minor or patch cut never changes the served value — only a breaking change does.
    assert WS_PROTOCOL_VERSION == _major(WS_STAMP["version"])
    assert "." not in WS_PROTOCOL_VERSION


def test_ws_stamp_core():
    assert WS_STAMP["contract"] == "ws-protocol"
    assert WS_STAMP["owner_repo"] == "locveil-voice"
    # doc-canonical: the WHOLE guide is enumerated (what consumers pin, what is byte-locked)
    assert "docs/guides/websocket-api.md" in WS_STAMP["artifacts"]
    for artifact in WS_STAMP["artifacts"]:
        assert (_REPO_ROOT / artifact).is_file(), f"enumerated artifact missing: {artifact}"
    # pointer fields resolve to real files
    constant_file, _, constant_name = WS_STAMP["code_constant"].partition("::")
    assert (_REPO_ROOT / constant_file).is_file()
    assert constant_name == "WS_PROTOCOL_VERSION"


def test_wake_pack_stamp_mirrors_released_catalog():
    catalog = MicroWakeWordProvider._get_default_model_urls()
    stamped = PACK_STAMP["pack"]
    assert stamped["word"] in catalog, "stamped word not in the released catalog"
    catalog_files = catalog[stamped["word"]]["files"]
    stamp_files = {name: entry["url"] for name, entry in stamped["files"].items()}
    assert stamp_files == catalog_files, "wake-pack STAMP urls drifted from _get_default_model_urls"
    for entry in stamped["files"].values():
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]), "content hash must be sha256 hex"


def test_wake_pack_stamp_core():
    assert PACK_STAMP["contract"] == "wake-pack"
    assert re.fullmatch(r"\d+\.\d+\.\d+", PACK_STAMP["version"]), (
        "STAMP version must be three-part (major.minor.patch)")
    assert PACK_STAMP["tag"] == f"wake-pack-v{PACK_STAMP['version']}"
    assert PACK_STAMP["owner_repo"] == "locveil-voice"


def test_wake_pack_stamp_declares_empty_artifacts_with_a_resolving_guard():
    # Binary-pack sidecar shape: the STAMP is the whole pinned set, so `artifacts` is
    # declared EMPTY — legal only with a `guard` pointer that resolves (path[::name]).
    assert PACK_STAMP["artifacts"] == []
    guard_file, _, guard_name = PACK_STAMP["guard"].partition("::")
    assert (_REPO_ROOT / guard_file).is_file()
    assert Path(guard_file).name == Path(__file__).name, "the guard pointer names this file"
    assert guard_name == test_wake_pack_stamp_mirrors_released_catalog.__name__
