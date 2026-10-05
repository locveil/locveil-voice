"""ws-protocol machine core — the owner test (design: docs/design/ws_machine_core.md §5).

`contracts/ws-protocol/` holds the protocol's hand-written machine core — golden frames,
transcripts, a schema. It is SUBORDINATE to `docs/guides/websocket-api.md`: on disagreement
the document wins and the core is fixed (`ws-protocol-doc-canonical`). Nothing here writes
or refreshes those files; this module only reads them and fails on disagreement with

- themselves (the fixtures obey their own definitions and the naming rule),
- the running server: the WS witness suites are re-run in a child pytest process with the
  frame tap (`tests/ws_frame_tap.py`) recording every frame at the server side of the
  socket — so "real frames" means frames the real handlers consumed and emitted,
- the real handlers once more, directly: every handshake case is replayed against them.

A red leg names the frame, the rule, and the test that produced the frame. Fix the document
first, then the core, then the code — in that order of precedence.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterator, List, Optional, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
CORE_DIR = REPO_ROOT / "contracts" / "ws-protocol"

FRAMES_FILE = CORE_DIR / "frames.golden.json"
GOLDEN = json.loads(FRAMES_FILE.read_text(encoding="utf-8"))
FRAMES: Dict[str, Dict[str, Any]] = GOLDEN["frames"]
CHANNELS: Dict[str, Dict[str, str]] = GOLDEN["channels"]

# The suites whose traffic the fixtures are checked against (design §5; review answer Q2).
WITNESS_SUITES = [
    "test_ws_driving_input",
    "test_ws_reply",
    "test_ws_streaming_asr",
    "test_observe_tap",
    "test_web_push_output",
    "test_arch36_satellite",
]

VERDICTS = {"valid", "invalid", "unknown"}
VIOLATIONS = {"not-json", "not-an-object", "missing-type", "missing-required", "wrong-json-type"}
UNKNOWN_FIELD = "x_future"          # the one key the `…/unknown-field` cases add


# ------------------------------------------------------------------------------------------
# Reading the core — pure functions shared by every leg
# ------------------------------------------------------------------------------------------

def json_type_ok(value: Any, spec: Any) -> bool:
    """Does `value` have the JSON type `spec` names? A list of names means "any of"."""
    if isinstance(spec, list):
        return any(json_type_ok(value, one) for one in spec)
    if spec == "string":
        return isinstance(value, str)
    if spec == "boolean":
        return isinstance(value, bool)
    if spec == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if spec == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if spec == "object":
        return isinstance(value, dict)
    if spec == "array":
        return isinstance(value, list)
    if spec == "null":
        return value is None
    raise AssertionError(f"unknown JSON type name in the core: {spec!r}")


def json_type_of(value: Any) -> str:
    for name in ("null", "boolean", "integer", "number", "string", "array", "object"):
        if json_type_ok(value, name):
            return name
    raise AssertionError(f"not a JSON value: {value!r}")


def problems(defn: Dict[str, Any], obj: Dict[str, Any], *, strict_keys: bool) -> List[str]:
    """Why `obj` is not a valid instance of the frame `defn` (empty list = valid).

    `strict_keys` additionally rejects a key outside `required ∪ optional` — the owner's
    strictness towards its own server and its own fixtures. A CONSUMER never applies it:
    receivers ignore keys they do not know.
    """
    found: List[str] = []
    wire_type = defn["type"]
    if wire_type is not None:
        if "type" not in obj:
            return ["missing-type"]
        if obj["type"] != wire_type and isinstance(obj["type"], str):
            return [f"type is {obj['type']!r}, not {wire_type!r}"]
    for key in defn["required"]:
        if key not in obj:
            found.append(f"missing-required:{key}")
    for key, value in obj.items():
        if key in defn["types"]:
            if not json_type_ok(value, defn["types"][key]):
                found.append(f"wrong-json-type:{key}")
        elif strict_keys:
            found.append(f"unknown-key:{key}")
    return found


def classify(channel: str, direction: str, obj: Dict[str, Any], *, first_c2s: bool) -> Optional[str]:
    """The frame name `obj` claims to be on this channel/direction, or None (unknown type).

    The two operator channels' opening frames carry no `type`: they are identified by
    position — the first client frame of the connection.
    """
    for name, defn in FRAMES.items():
        if defn["channel"] == channel and defn["direction"] == direction \
                and defn["type"] is not None and obj.get("type") == defn["type"]:
            return name
    if direction == "c2s" and first_c2s:
        opening = CHANNELS[channel]["opening"]
        if FRAMES[opening]["type"] is None:
            return opening
    return None


def masked(defn: Dict[str, Any], obj: Dict[str, Any]) -> Dict[str, Any]:
    """`obj` with what differs from run to run reduced to its JSON type: volatile keys and
    opaque values are compared by presence and type, never by value."""
    blind = set(defn["volatile"]) | set(defn["opaque"])
    return {k: (f"<{json_type_of(v)}>" if k in blind else v) for k, v in obj.items()}


def all_cases() -> Iterator[Tuple[Optional[str], Dict[str, Any]]]:
    for name, defn in FRAMES.items():
        for case in defn["cases"]:
            yield name, case
    for case in GOLDEN["unknown"]:
        yield None, case
    for case in GOLDEN["malformed"]:
        yield None, case


def live(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [c for c in cases if not c.get("retired")]


def valid_cases(name: str) -> List[Dict[str, Any]]:
    return [c for c in live(FRAMES[name]["cases"]) if c["verdict"] == "valid"]


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


class Conn:
    """One connection of a capture: its lines in wire order."""

    def __init__(self, label: str, channel: str, test: str) -> None:
        self.label = label
        self.channel = channel
        self.test = test
        self.lines: List[Dict[str, Any]] = []       # text / binary lines
        self.closed_by: Optional[str] = None

    def __repr__(self) -> str:
        return f"<{self.channel} connection {self.label} from {self.test}>"


def connections(lines: List[Dict[str, Any]]) -> List[Conn]:
    """Group capture lines per connection and name every text frame (`frame`: a definition
    name, or None for a frame of unknown type / a text that is not a JSON object)."""
    by_label: Dict[str, Conn] = {}
    for line in lines:
        kind = line["kind"]
        if kind == "open":
            by_label[line["conn"]] = Conn(line["conn"], line["channel"], line.get("test", ""))
            continue
        conn = by_label[line["conn"]]
        if kind == "close":
            conn.closed_by = conn.closed_by or line["by"]
            continue
        entry = dict(line)
        if kind == "text":
            first_c2s = entry["direction"] == "c2s" and not any(
                seen["kind"] == "text" and seen["direction"] == "c2s" for seen in conn.lines)
            entry["frame"] = (classify(conn.channel, entry["direction"], entry["json"],
                                       first_c2s=first_c2s) if "json" in entry else None)
        conn.lines.append(entry)
    return list(by_label.values())


@pytest.fixture(scope="session")
def capture(tmp_path_factory) -> List[Conn]:
    """Every WS frame the real handlers consumed and emitted while the witness suites ran —
    recorded by the tap in a CHILD pytest process, so the capture does not depend on what
    the outer run selected, its order, or its parallelism."""
    out = tmp_path_factory.mktemp("ws_tap") / "capture.jsonl"
    env = dict(os.environ)
    env["LOCVEIL_WS_TAP"] = str(out)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(BACKEND), env.get("PYTHONPATH")]))
    env.pop("PYTEST_CURRENT_TEST", None)
    suites = [str(BACKEND / "tests" / f"{name}.py") for name in WITNESS_SUITES]
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-c", str(BACKEND / "pyproject.toml"),
         "-p", "tests.ws_frame_tap", "-p", "no:cacheprovider", "-q", *suites],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, (
        "the witness suites failed under the frame tap:\n" + proc.stdout[-6000:] + proc.stderr[-2000:])
    conns = connections(load_jsonl(out))
    assert conns, "the tap recorded nothing — is the plugin loaded?"
    return conns


# ------------------------------------------------------------------------------------------
# L1 — the golden frames obey their own definitions
# ------------------------------------------------------------------------------------------

NAME_RE = re.compile(r"[a-z0-9._/-]+")


def _c_symbol(name: str) -> str:
    """What an embed/test-name generator makes of an id: everything outside [a-z0-9] → `_`."""
    return re.sub(r"[^a-z0-9]", "_", name)


def test_l1_header_and_channel_table():
    assert GOLDEN["contract"] == "ws-protocol"
    assert GOLDEN["core_format"] == 1
    from locveil_voice.core.ws_protocol import WS_PROTOCOL_VERSION
    assert str(GOLDEN["protocol_major"]) == WS_PROTOCOL_VERSION
    assert set(CHANNELS) == {"audio", "reply", "output", "observe"}
    for channel, entry in CHANNELS.items():
        assert entry["path"].startswith("/ws/")
        for role, direction in (("opening", "c2s"), ("ack", "s2c"), ("error", "s2c")):
            defn = FRAMES[entry[role]]
            assert (defn["channel"], defn["direction"]) == (channel, direction), (channel, role)
    for key, entry in GOLDEN["binary"].items():
        channel, direction = key.split(".")
        assert channel in CHANNELS and direction in ("c2s", "s2c")
        assert entry["content"] == "pcm_s16le"
        for pointer in ("rate_from", "channels_from"):
            if pointer in entry:
                frame, _, field = entry[pointer].rpartition(".")
                assert field in FRAMES[frame]["types"], f"binary.{key}.{pointer} → {entry[pointer]}"
        for frame in entry.get("only_between", []):
            assert frame in FRAMES


def test_l1_names_are_stable_identifiers_and_unique_as_c_symbols():
    """Review rule (Q8): names use only [a-z0-9._/-] and stay unique after every other
    character is mapped to `_` — the mapping ESP-IDF embed symbols and generated C test
    names apply."""
    namespaces = {
        "frame names": list(FRAMES),
        "case ids": [case["id"] for _, case in all_cases()],
        "core files": sorted(p.name for p in CORE_DIR.iterdir()
                             if p.name not in ("README.md", "STAMP.json")),
    }
    for what, names in namespaces.items():
        for name in names:
            assert NAME_RE.fullmatch(name), f"{what}: {name!r} uses a character outside [a-z0-9._/-]"
        symbols: Dict[str, str] = {}
        for name in names:
            symbol = _c_symbol(name)
            assert symbol not in symbols, (
                f"{what}: {name!r} and {symbols[symbol]!r} collide as the C symbol {symbol!r}")
            symbols[symbol] = name
    for name, defn in FRAMES.items():
        channel, _, tail = name.partition(".")
        assert channel == defn["channel"], name
        if defn["type"] is not None:
            assert tail == defn["type"], f"{name}: a frame is named <channel>.<wire type>"
        for case in defn["cases"]:
            assert case["id"].startswith(name + "/"), f"{case['id']} does not belong to {name}"


RELEASED_NAMES_FILE = Path(__file__).parent / "data" / "ws_core_names.major1.txt"


def test_l1_no_released_name_was_renamed_or_removed():
    """Inside a major, file names, frame names, case ids and transcript names are never
    renamed or removed — a consumer's test table must not lose a symbol between two pins.
    The baseline lists every name each cut released; a cut appends the names it adds. So a
    missing name here is a removal (retire the case instead), and a name absent from the
    baseline is an addition this cut forgot to record."""
    released = set()
    for line in RELEASED_NAMES_FILE.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            kind, name = line.split(" ", 1)
            released.add((kind, name))
    current = {("frame", name) for name in FRAMES}
    current |= {("case", case["id"]) for _, case in all_cases()}
    current |= {("file", p.name) for p in CORE_DIR.iterdir() if p.name not in ("README.md", "STAMP.json")}
    current |= {("file", "websocket-api.md")}
    current |= {("transcript", p.name[len("transcript."):-len(".jsonl")])
                for p in CORE_DIR.glob("transcript.*.jsonl")}
    assert not released - current, f"released names that no longer exist: {sorted(released - current)}"
    assert not current - released, (
        f"names this cut adds but backend/tests/data/{RELEASED_NAMES_FILE.name} does not list: "
        f"{sorted(current - released)}")


def test_l1_retired_cases_are_marked_and_explained():
    """`retired` is only ever `true`, and a retired case says why in its `note` — it is kept
    for its name alone: the server no longer sends such a frame and a receiver owes it nothing."""
    for _, case in all_cases():
        if "retired" in case:
            assert case["retired"] is True, case["id"]
            assert "retired at ws-protocol-v" in case.get("note", ""), case["id"]


def test_l1_definitions_are_well_formed():
    for name, defn in FRAMES.items():
        assert defn["direction"] in ("c2s", "s2c"), name
        keys = defn["required"] + defn["optional"]
        assert len(keys) == len(set(keys)), f"{name}: a key is listed twice"
        assert set(defn["types"]) == set(keys), f"{name}: `types` must cover exactly the listed keys"
        for key, spec in defn["types"].items():
            json_type_ok(None, spec)                 # raises on a type name outside the vocabulary
        if defn["type"] is not None:
            assert defn["required"][0] == "type" and defn["types"]["type"] == "string", name
        else:
            assert "type" not in keys, f"{name}: a typeless frame lists no `type` key"
        assert set(defn["opaque"]) <= set(keys) and set(defn["volatile"]) <= set(keys), name
        for key in defn["opaque"]:
            assert defn["types"][key] == "object", f"{name}.{key}: opaque values are objects"
        assert valid_cases(name), f"{name}: no valid case"
        assert valid_cases(name)[0]["id"] == f"{name}/plain", f"{name}: the first case is `plain`"
        assert any(c["id"] == f"{name}/unknown-field" for c in valid_cases(name)), (
            f"{name}: every frame carries the unknown-field case (forward compatibility)")


@pytest.mark.parametrize("frame,case",
                         [pytest.param(n, c, id=c["id"]) for n, c in all_cases() if n])
def test_l1_case_holds_its_verdict(frame, case):
    """A `valid` case satisfies its definition; an `invalid` case violates it in exactly the
    stated way — nothing else is wrong with it."""
    defn = FRAMES[frame]
    assert case["verdict"] in ("valid", "invalid")
    assert ("json" in case) != ("raw" in case), "a case carries `json` or `raw`, never both"

    if case["verdict"] == "valid":
        assert "violation" not in case and "expect" not in case
        if case["id"].endswith("/unknown-field"):
            # the deliberate exception: the plain frame plus ONE key no definition lists
            plain = dict(case["json"])
            assert plain.pop(UNKNOWN_FIELD) == 1
            assert plain == valid_cases(frame)[0]["json"]
            assert problems(defn, case["json"], strict_keys=False) == []
        else:
            assert problems(defn, case["json"], strict_keys=True) == []
        return

    violation = case["violation"]
    assert violation in VIOLATIONS
    if violation == "not-json":
        with pytest.raises(ValueError):
            json.loads(case["raw"])
    elif violation == "not-an-object":
        assert not isinstance(json.loads(case["raw"]), dict)
    else:
        found = problems(defn, case["json"], strict_keys=True)
        assert len(found) == 1 and found[0].split(":")[0] == violation, (
            f"stated {violation!r}, found {found}")

    # s2c invalid = a structural verdict for the client's parser (never an `expect`);
    # c2s invalid exists only where the document promises the server's reaction.
    if defn["direction"] == "s2c":
        assert "expect" not in case
    else:
        assert case["expect"] == {"frame": CHANNELS[defn["channel"]]["error"], "then": "close"}


def test_l1_unknown_and_malformed_cases():
    seen = set()
    for case in GOLDEN["unknown"]:
        channel, direction = case["channel"], case["direction"]
        assert case["id"] == f"{channel}.{direction}/unknown-type" and case["verdict"] == "unknown"
        assert classify(channel, direction, case["json"], first_c2s=False) is None, (
            f"{case['id']}: its type is DEFINED on this channel/direction")
        seen.add((channel, direction))
    # both directions of the two voice channels, the server's direction of the operator ones
    assert seen == {("audio", "c2s"), ("audio", "s2c"), ("reply", "c2s"), ("reply", "s2c"),
                    ("output", "s2c"), ("observe", "s2c")}
    for case in GOLDEN["malformed"]:
        assert case["id"].startswith("any/") and case["verdict"] == "invalid"
        if case["violation"] == "not-json":
            with pytest.raises(ValueError):
                json.loads(case["raw"])
        else:
            assert case["violation"] == "not-an-object"
            assert not isinstance(json.loads(case["raw"]), dict)


# ------------------------------------------------------------------------------------------
# L3 — real frames conform (strictly: the server may not grow a key without the core)
# ------------------------------------------------------------------------------------------

def test_l3_every_frame_the_server_sent_is_a_valid_instance_of_a_defined_frame(capture):
    wrong: List[str] = []
    for conn in capture:
        for line in conn.lines:
            if line["kind"] != "text" or line["direction"] != "s2c":
                continue
            if "json" not in line:
                wrong.append(f"{conn}: sent a text frame that is not a JSON object: {line['raw']!r}")
            elif line["frame"] is None:
                wrong.append(f"{conn}: sent a frame of a type the core does not define: {line['json']}")
            else:
                found = problems(FRAMES[line["frame"]], line["json"], strict_keys=True)
                if found:
                    wrong.append(f"{conn}: {line['frame']} {found}: {line['json']}")
    assert not wrong, "\n".join(wrong)


# ------------------------------------------------------------------------------------------
# L4 — every frame is witnessed, and the fixture values are real
# ------------------------------------------------------------------------------------------

def _recorded(capture: List[Conn], frame: str) -> List[Dict[str, Any]]:
    return [line["json"] for conn in capture for line in conn.lines
            if line["kind"] == "text" and line.get("frame") == frame]


@pytest.mark.parametrize("frame", list(FRAMES))
def test_l4_frame_is_witnessed_and_its_cases_are_recorded_frames(capture, frame):
    """Every definition crossed a real socket at least once; its `plain` case IS one of those
    frames; and on the server's side every valid case is — except the unknown-field one,
    which L1 derives from `plain`. Volatile keys and opaque values compare by JSON type."""
    defn = FRAMES[frame]
    recorded = [masked(defn, obj) for obj in _recorded(capture, frame)]
    assert recorded, f"{frame}: no witness suite puts this frame on a socket"
    cases = valid_cases(frame) if defn["direction"] == "s2c" else valid_cases(frame)[:1]
    for case in cases:
        if case["id"].endswith("/unknown-field"):
            continue
        assert masked(defn, case["json"]) in recorded, (
            f"{case['id']}: no recorded frame equals this case — fixture values must be real")


def test_l4_binary_runs_are_witnessed_where_the_core_declares_them(capture):
    for key in GOLDEN["binary"]:
        channel, direction = key.split(".")
        assert any(line["kind"] == "binary" and line["direction"] == direction
                   for conn in capture if conn.channel == channel for line in conn.lines), key
    # …and the server sends binary nowhere else (clients in the suites misbehave on purpose)
    for conn in capture:
        for line in conn.lines:
            if line["kind"] == "binary" and line["direction"] == "s2c":
                assert f"{conn.channel}.s2c" in GOLDEN["binary"], conn


# ------------------------------------------------------------------------------------------
# L4b — the handshake cases, replayed against the real handlers (review answer Q6)
# ------------------------------------------------------------------------------------------

@pytest.fixture()
def server(tmp_path):
    """All four channels on the real router, wired the way the engine wires them."""
    pytest.importorskip("fastapi")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from locveil_voice.core.audio_negotiator import AudioNegotiator
    from locveil_voice.core.durable_actions import JsonFileDurableActionStore, set_durable_action_store
    from locveil_voice.core.event_bus import EventBus
    from locveil_voice.intents.models import IntentResult
    from locveil_voice.outputs.manager import OutputManager
    from locveil_voice.runners.webapi_router import create_webapi_router
    from locveil_voice.utils.audio_negotiation import CanonicalFormat
    from locveil_voice.utils.audio_stream import PCMStream

    class _Pipeline:
        async def process_audio_input(self, audio_data, session_id=None, wants_audio=False,
                                      client_context=None, trace_context=None):
            return IntentResult(text="готово", metadata={})

    class _Voice:
        async def synthesize_to_stream(self, text, **kw):
            async def _pcm():
                yield b"\x01\x02" * 800
            return PCMStream(22050, 1, 2, _pcm())

    voice = _Voice()
    outputs = OutputManager()
    token = FRAMES["observe.subscribe"]["cases"][0]["json"]["token"]
    core = SimpleNamespace(
        workflow_manager=_Pipeline(), output_manager=outputs, plugin_manager=None,
        component_manager=SimpleNamespace(get_component=lambda name: voice if name == "tts" else None),
        audio_negotiator=AudioNegotiator(CanonicalFormat(16000, "pcm16", 1)),
        event_bus=EventBus(),
        config=SimpleNamespace(
            system=SimpleNamespace(observe_token=token, observe_allow_remote=True),
            trace=SimpleNamespace(allow_remote_request=True, enabled=False, max_stages=100,
                                  max_data_size_mb=10, capture_level="utterance")))
    app = FastAPI()
    app.include_router(create_webapi_router(core, asset_loader=None, web_input=None, start_time=0.0))
    # the reply channel drains undelivered notices at registration — not from the real assets tree
    set_durable_action_store(JsonFileDurableActionStore(tmp_path / "durable_actions.json"))
    try:
        with TestClient(app) as client:
            yield SimpleNamespace(client=client, outputs=outputs)
    finally:
        set_durable_action_store(None)


def _send_case(ws, case: Dict[str, Any]) -> None:
    ws.send_text(case["raw"] if "raw" in case else json.dumps(case["json"], ensure_ascii=False))


def _receive_frame(ws, channel: str) -> Tuple[str, Dict[str, Any]]:
    """The next server frame: (its frame name, the object) — which must be a strictly valid
    instance of a defined frame."""
    obj = ws.receive_json()
    name = classify(channel, "s2c", obj, first_c2s=False)
    assert name is not None, f"the server sent an undefined frame: {obj}"
    assert problems(FRAMES[name], obj, strict_keys=True) == [], (name, obj)
    return name, obj


def _opening_cases(verdict: str) -> List[Any]:
    out = []
    for channel, entry in CHANNELS.items():
        for case in live(FRAMES[entry["opening"]]["cases"]):
            if case["verdict"] == verdict:
                out.append(pytest.param(channel, case, id=case["id"]))
    return out


@pytest.mark.parametrize("channel,case", _opening_cases("valid"))
def test_l4b_valid_opening_frame_is_answered_by_the_ack(server, channel, case):
    """Proves the c2s `required` lists from the other side: every valid opening case —
    minimal, full, unknown-field — is accepted by the real handler."""
    with server.client.websocket_connect(CHANNELS[channel]["path"]) as ws:
        _send_case(ws, case)
        name, ack = _receive_frame(ws, channel)
        assert name == CHANNELS[channel]["ack"], f"{case['id']} was answered with {ack}"


@pytest.mark.parametrize("channel,case", _opening_cases("invalid"))
def test_l4b_invalid_opening_frame_gets_exactly_its_expect(server, channel, case):
    """Proves every `expect`: the stated frame, then the server closes."""
    from starlette.websockets import WebSocketDisconnect
    with server.client.websocket_connect(CHANNELS[channel]["path"]) as ws:
        _send_case(ws, case)
        name, _ = _receive_frame(ws, channel)
        assert name == case["expect"]["frame"]
        assert case["expect"]["then"] == "close"
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()


@pytest.mark.parametrize("case", valid_cases("audio.end"), ids=lambda c: c["id"])
def test_l4b_every_valid_end_frame_finalizes_the_utterance(server, case):
    with server.client.websocket_connect(CHANNELS["audio"]["path"]) as ws:
        _send_case(ws, valid_cases("audio.register")[0])
        assert _receive_frame(ws, "audio")[0] == "audio.registered"
        ws.send_bytes(b"\x00\x01" * 512)
        _send_case(ws, case)
        assert _receive_frame(ws, "audio")[0] == "audio.response"


def test_l4b_the_servers_opening_frame_table_equals_the_definitions():
    """The server refuses an opening frame whose documented keys have the wrong JSON type
    (BUG-48). Its table of those types is hand-written in `core/ws_protocol.py` — a third
    copy of what the guide's frame reference and the golden definitions state, so it is held
    to them here: same opening frames, same required keys, same type per key."""
    from locveil_voice.core.ws_protocol import OPENING_FRAMES
    assert set(OPENING_FRAMES) == {entry["opening"] for entry in CHANNELS.values()}
    for name, spec in OPENING_FRAMES.items():
        defn = FRAMES[name]
        keys = {k: v for k, v in defn["types"].items() if k != "type"}
        assert spec["types"] == keys, name
        assert list(spec["required"]) == [k for k in defn["required"] if k != "type"], name
        for nested in list(spec.get("inner", {})) + list(spec.get("items", {})):
            assert nested in keys, f"{name}: {nested} is not a key of the frame"


@pytest.mark.parametrize("frame,case", [
    pytest.param(entry["opening"], case, id=case["id"])
    for entry in CHANNELS.values() for case in live(FRAMES[entry["opening"]]["cases"])
    if "json" in case])
def test_l4b_the_servers_validator_gives_every_opening_case_its_verdict(frame, case):
    """…and the validator built on that table agrees with the core case by case. (`/ws/output`
    has no invalid cases: that channel mints an identity instead of refusing.)"""
    from locveil_voice.core.ws_protocol import opening_frame_violation
    violation = opening_frame_violation(frame, case["json"])
    if case["verdict"] == "valid":
        assert violation is None, f"{case['id']}: the server would refuse a valid frame — {violation}"
    elif problems(FRAMES[frame], case["json"], strict_keys=True)[0] not in (
            "missing-type", "wrong-json-type:type"):  # the frame's own `type` is the endpoint's check
        assert violation is not None, f"{case['id']}: the server would accept an invalid frame"


def _unknown_case(channel: str, direction: str) -> Dict[str, Any]:
    return next(c for c in GOLDEN["unknown"] if (c["channel"], c["direction"]) == (channel, direction))


def test_l4b_unknown_frame_after_the_handshake_is_ignored_on_audio(server):
    """The server's half of the forward-compatibility rule: a frame of a type it does not
    know is ignored — the utterance around it still completes on the same connection."""
    with server.client.websocket_connect(CHANNELS["audio"]["path"]) as ws:
        _send_case(ws, valid_cases("audio.register")[0])
        assert _receive_frame(ws, "audio")[0] == "audio.registered"
        ws.send_bytes(b"\x00\x01" * 512)
        _send_case(ws, _unknown_case("audio", "c2s"))
        ws.send_bytes(b"\x00\x01" * 512)
        _send_case(ws, valid_cases("audio.end")[0])
        assert _receive_frame(ws, "audio")[0] == "audio.response"


def test_l4b_unknown_frame_after_the_handshake_is_ignored_on_reply(server):
    from locveil_voice.core.interfaces.output import OutputModality
    from locveil_voice.intents.context_models import RequestContext
    from locveil_voice.intents.models import IntentResult

    opening = valid_cases("reply.register-reply")[0]
    with server.client.websocket_connect(CHANNELS["reply"]["path"]) as ws:
        _send_case(ws, opening)
        assert _receive_frame(ws, "reply")[0] == "reply.registered"
        _send_case(ws, _unknown_case("reply", "c2s"))
        ctx = RequestContext(session_id="s", client_id=opening["json"]["client_id"])
        server.client.portal.call(server.outputs.deliver, IntentResult(text="готово"), ctx,
                                  OutputModality.SPEECH)
        assert _receive_frame(ws, "reply")[0] == "reply.speak_begin"   # still served


# ------------------------------------------------------------------------------------------
# Slice 2 — the transcripts: `contracts/ws-protocol/transcript.<scenario>.jsonl`
# ------------------------------------------------------------------------------------------

TRANSCRIPT_NAMES = [
    "audio-batch", "audio-streaming", "audio-trace", "audio-rejected",
    "reply-burst", "satellite-pair", "reconnect", "output-push", "observe-tap",
]
ORDERING = "per-connection-and-direction"
LINE_KEYS = {
    "meta": {"kind", "transcript", "core_format", "protocol_major", "channels", "ordering", "note"},
    "open": {"kind", "conn", "channel"},
    "text": {"kind", "conn", "channel", "direction", "frame", "json", "repeat"},
    "binary": {"kind", "conn", "channel", "direction", "content", "bytes"},
    "close": {"kind", "conn", "by"},
}
CLOSED_BY = {"client", "server", "network"}


def transcript_path(name: str) -> Path:
    return CORE_DIR / f"transcript.{name}.jsonl"


def transcript_connections(name: str) -> List[Conn]:
    """A golden transcript as connections — the same shape `connections()` gives a capture
    (here every text line already NAMES its frame)."""
    by_label: Dict[str, Conn] = {}
    for line in load_jsonl(transcript_path(name))[1:]:
        if line["kind"] == "open":
            by_label[line["conn"]] = Conn(line["conn"], line["channel"], f"transcript.{name}")
        elif line["kind"] == "close":
            by_label[line["conn"]].closed_by = line["by"]
        else:
            by_label[line["conn"]].lines.append(line)
    return list(by_label.values())


def rule_violations(conn: Conn, *, cap_tolerant: bool) -> List[str]:
    """Rules T-1..T-4 and T-6..T-9 on ONE connection (T-5 spans connections). `cap_tolerant`
    admits what a recording may legitimately contain and a golden transcript does not: a batch
    `response` forced by the utterance cap instead of an `end` frame."""
    out: List[str] = []
    entry = CHANNELS[conn.channel]
    s2c = [ln for ln in conn.lines if ln["direction"] == "s2c"]
    s2c_known = [ln for ln in s2c if ln["kind"] == "text" and ln.get("frame")]

    # T-1: ignoring frames of unknown type, the first server frame is the ack or an error
    if s2c_known and s2c_known[0]["frame"] not in (entry["ack"], entry["error"]):
        out.append(f"T-1: the first server frame is {s2c_known[0]['frame']}")

    # T-2: an error frame is the last server frame, and the server closes after it
    for index, line in enumerate(s2c):
        if line.get("frame") == entry["error"]:
            if index != len(s2c) - 1:
                out.append("T-2: a server frame follows an error frame")
            if conn.closed_by != "server":
                out.append(f"T-2: after an error frame the connection was closed by {conn.closed_by}")

    # T-3 / T-4 / T-9: bursts pair by seq, seq counts from 1; binary only inside a burst;
    # bursts never overlap (no speak_begin while one is open)
    if conn.channel == "reply":
        open_bursts: List[int] = []
        begun = 0
        for line in s2c:
            if line["kind"] == "binary":
                if not open_bursts:
                    out.append("T-4: binary outside a speak_begin … speak_end bracket")
            elif line.get("frame") == "reply.speak_begin":
                if open_bursts:
                    out.append(f"T-9: speak_begin seq {line['json']['seq']} inside the open burst "
                               f"{open_bursts[-1]}")
                begun += 1
                if line["json"]["seq"] != begun:
                    out.append(f"T-3: burst {begun} of the connection carries seq {line['json']['seq']}")
                open_bursts.append(line["json"]["seq"])
            elif line.get("frame") == "reply.speak_end":
                if line["json"]["seq"] not in open_bursts:
                    out.append(f"T-3: speak_end seq {line['json']['seq']} closes no open burst")
                else:
                    open_bursts.remove(line["json"]["seq"])

    if conn.channel == "audio":
        ack = next((ln for ln in s2c_known if ln["frame"] == "audio.registered"), None)
        frames = [ln.get("frame") for ln in s2c if ln["kind"] == "text"]
        # T-6: traces granted → exactly one trace after each response; not granted → none
        if ack is not None and ack["json"]["trace"]:
            for index, frame in enumerate(frames):
                if frame == "audio.response":
                    following = frames[index + 1:index + 3]
                    if following[:1] != ["audio.trace"] or following[1:2] == ["audio.trace"]:
                        out.append("T-6: a response is not followed by exactly one trace")
        elif "audio.trace" in frames:
            out.append("T-6: a trace frame on a connection that was not granted traces")
        # T-8: in batch mode a response follows the end frame that closed its utterance
        register = next((ln for ln in conn.lines if ln.get("frame") == "audio.register"), None)
        if register is not None and register["json"].get("mode") != "streaming":
            ends = responses = 0
            audio_since_response = False
            for line in conn.lines:
                if line["kind"] == "binary" and line["direction"] == "c2s":
                    audio_since_response = True
                elif line.get("frame") == "audio.end":
                    ends += 1
                elif line.get("frame") == "audio.response":
                    responses += 1
                    if responses > ends:
                        if cap_tolerant and audio_since_response:
                            ends = responses          # force-finalized at the utterance cap
                        else:
                            out.append("T-8: a batch response precedes the end frame of its utterance")
                    audio_since_response = False

    # T-7: the ack is sent only after the client's opening frame was received
    seen_client_text = False
    for line in conn.lines:
        if line["kind"] == "text" and line["direction"] == "c2s":
            seen_client_text = True
        elif line.get("frame") == entry["ack"] and not seen_client_text:
            out.append("T-7: the ack precedes the client's opening frame")
    return out


def session_ids(conns: List[Conn]) -> List[str]:
    return [ln["json"]["session_id"] for conn in conns for ln in conn.lines
            if ln.get("frame") == "audio.registered"]


def test_l5_the_transcript_set_is_exactly_the_documented_one():
    on_disk = sorted(p.name for p in CORE_DIR.glob("transcript.*"))
    assert on_disk == sorted(f"transcript.{name}.jsonl" for name in TRANSCRIPT_NAMES)


@pytest.mark.parametrize("name", TRANSCRIPT_NAMES)
def test_l5_transcript_is_well_formed_and_obeys_the_rules(name):
    raw = transcript_path(name).read_text(encoding="utf-8")
    assert raw.endswith("\n") and "\n\n" not in raw and not raw.startswith("﻿")
    lines = load_jsonl(transcript_path(name))

    meta = lines[0]
    assert meta["kind"] == "meta" and all(line["kind"] != "meta" for line in lines[1:])
    assert meta["transcript"] == name and NAME_RE.fullmatch(name)
    assert meta["core_format"] == GOLDEN["core_format"]
    assert meta["protocol_major"] == GOLDEN["protocol_major"]
    assert meta["ordering"] == ORDERING

    alive: Dict[str, str] = {}
    ever: Dict[str, str] = {}
    for number, line in enumerate(lines, start=1):
        where = f"transcript.{name}.jsonl:{number}"
        kind = line["kind"]
        assert set(line) <= LINE_KEYS[kind], f"{where}: unknown key {set(line) - LINE_KEYS[kind]}"
        if kind == "meta":
            continue
        label = line["conn"]
        if kind == "open":
            assert label not in ever, f"{where}: a reconnect takes a NEW conn label"
            assert line["channel"] in CHANNELS
            alive[label] = ever[label] = line["channel"]
            continue
        assert label in alive, f"{where}: {label} is not open"
        if kind == "close":
            assert line["by"] in CLOSED_BY
            del alive[label]
            continue
        assert line["channel"] == alive[label], f"{where}: channel disagrees with the open line"
        assert line["direction"] in ("c2s", "s2c")
        if kind == "binary":
            assert f"{line['channel']}.{line['direction']}" in GOLDEN["binary"], where
            assert line["content"] == GOLDEN["binary"][f"{line['channel']}.{line['direction']}"]["content"]
            assert isinstance(line["bytes"], int) and line["bytes"] > 0 and line["bytes"] % 2 == 0
        else:
            defn = FRAMES[line["frame"]]
            assert (defn["channel"], defn["direction"]) == (line["channel"], line["direction"]), where
            assert problems(defn, line["json"], strict_keys=True) == [], where
            assert line.get("repeat", True) is True, f"{where}: `repeat` is only ever true"
    assert not alive, f"{name}: connections left open: {sorted(alive)}"
    assert meta["channels"] == sorted(set(ever.values())), "meta.channels lists the channels used"

    conns = transcript_connections(name)
    for conn in conns:
        assert rule_violations(conn, cap_tolerant=False) == [], conn
    ids = session_ids(conns)
    assert len(ids) == len(set(ids)), "T-5: a new connection gets a new session_id"


def test_l5_the_rules_hold_on_every_recorded_connection(capture):
    """T-1..T-9 are stated in the document as facts about the server. Here they are checked
    against everything the real handlers did in the witness suites — not just the fixtures."""
    wrong = [f"{conn}: {violation}" for conn in capture
             for violation in rule_violations(conn, cap_tolerant=True)]
    assert not wrong, "\n".join(wrong)
    ids = session_ids(capture)
    assert len(ids) == len(set(ids)), "T-5: two connections shared a session_id"


# ------------------------------------------------------------------------------------------
# L6 — every transcript is witnessed by a real recording
# ------------------------------------------------------------------------------------------

def _direction_tokens(conn: Conn, direction: str) -> List[Dict[str, Any]]:
    """One direction of a connection as comparable tokens; a run of binary frames is one token."""
    tokens: List[Dict[str, Any]] = []
    for line in conn.lines:
        if line["direction"] != direction:
            continue
        if line["kind"] == "binary":
            if not (tokens and tokens[-1]["kind"] == "binary"):
                tokens.append({"kind": "binary"})
            continue
        frame = line.get("frame")
        tokens.append({"kind": "text", "frame": frame, "repeat": bool(line.get("repeat")),
                       "json": masked(FRAMES[frame], line["json"]) if frame else line.get("json")})
    return tokens


def _sequence_matches(golden: List[Dict[str, Any]], recorded: List[Dict[str, Any]]) -> bool:
    """`recorded` equals `golden`, where a golden `repeat` line stands for zero or more frames
    of that type (its own value is one example and is not compared)."""
    if not golden:
        return not recorded
    head, rest = golden[0], golden[1:]
    if head.get("repeat"):
        if _sequence_matches(rest, recorded):
            return True
        return bool(recorded) and recorded[0]["kind"] == "text" \
            and recorded[0]["frame"] == head["frame"] and _sequence_matches(golden, recorded[1:])
    if not recorded or recorded[0]["kind"] != head["kind"]:
        return False
    if head["kind"] == "text" and (recorded[0]["frame"], recorded[0]["json"]) != (head["frame"], head["json"]):
        return False
    return _sequence_matches(rest, recorded[1:])


def _connection_matches(golden: Conn, recorded: Conn) -> bool:
    if golden.channel != recorded.channel:
        return False
    # the tap sits at the server: a handler parked on something other than the socket never
    # observes the client leaving, so a recording may lack its close line — never contradict it
    if recorded.closed_by is not None and recorded.closed_by != golden.closed_by:
        return False
    return all(_sequence_matches(_direction_tokens(golden, d), _direction_tokens(recorded, d))
               for d in ("c2s", "s2c"))


def _assign(golden: List[Conn], recorded: List[Conn]) -> bool:
    """Is there a one-to-one assignment of ALL the test's connections to the transcript's?"""
    if not golden:
        return not recorded
    return any(_connection_matches(golden[0], candidate)
               and _assign(golden[1:], recorded[:i] + recorded[i + 1:])
               for i, candidate in enumerate(recorded))


@pytest.mark.parametrize("name", TRANSCRIPT_NAMES)
def test_l6_transcript_is_a_real_recording(capture, name):
    """Per connection and per direction the golden sequence equals what ONE witness test
    really put on the wire — same frames in the same order, same values (volatile keys and
    opaque values by JSON type), binary runs collapsed, `repeat` lines matching any number
    of frames. The order of one direction against the other is not compared here (rules
    T-7/T-8 cover what the document promises about it)."""
    golden = transcript_connections(name)
    by_test: Dict[str, List[Conn]] = {}
    for conn in capture:
        by_test.setdefault(conn.test, []).append(conn)
    witnesses = [test for test, conns in by_test.items() if _assign(golden, conns)]
    assert witnesses, (
        f"transcript.{name}.jsonl: no witness test produced exactly this conversation — "
        "the transcript must be a real recording, not an illustration")


# ------------------------------------------------------------------------------------------
# Slice 3 — the schema: `contracts/ws-protocol/ws-protocol.schema.json`
# L7 — schema ≡ fixtures, and every real frame validates
# ------------------------------------------------------------------------------------------

SCHEMA_FILE = CORE_DIR / "ws-protocol.schema.json"
SCHEMA = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
DIRECTIONS = sorted({f"{d['channel']}.{d['direction']}" for d in FRAMES.values()})


def _validator(def_name: str):
    """A validator for ONE `$defs` entry (a frame name, or `<channel>.<direction>`)."""
    import jsonschema
    return jsonschema.Draft202012Validator({"$ref": f"#/$defs/{def_name}", "$defs": SCHEMA["$defs"]})


def _accepts(def_name: str, instance: Any) -> bool:
    return _validator(def_name).is_valid(instance)


def _walk(node: Any) -> Iterator[Dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def test_l7_schema_is_a_valid_2020_12_schema_open_everywhere():
    import jsonschema
    assert SCHEMA["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    jsonschema.Draft202012Validator.check_schema(SCHEMA)
    assert SCHEMA["type"] == "object", "the one thing true of every frame: it is a JSON object"
    for node in _walk(SCHEMA):
        # the schema encodes the RECEIVER's obligation — unknown keys are ignored, never rejected
        assert "additionalProperties" not in node and "unevaluatedProperties" not in node


def test_l7_schema_mirrors_the_frame_definitions_key_for_key():
    """Hand-written, like the fixtures — and mechanically the same statement: same frames,
    same required keys, same JSON type per key, one union per channel and direction."""
    assert set(SCHEMA["$defs"]) == set(FRAMES) | set(DIRECTIONS)
    for name, defn in FRAMES.items():
        entry = SCHEMA["$defs"][name]
        assert entry["type"] == "object", name
        assert entry["required"] == defn["required"], name
        assert list(entry["properties"]) == defn["required"] + defn["optional"], name
        for key, spec in defn["types"].items():
            prop = entry["properties"][key]
            if key == "type":
                assert prop == {"const": defn["type"]}, name
            else:
                assert prop["type"] == spec, f"{name}.{key}"
    for key in DIRECTIONS:
        channel, direction = key.split(".")
        members = [ref["$ref"].rsplit("/", 1)[-1] for ref in SCHEMA["$defs"][key]["anyOf"]]
        assert members == [n for n, d in FRAMES.items()
                           if (d["channel"], d["direction"]) == (channel, direction)], key


@pytest.mark.parametrize("frame,case",
                         [pytest.param(n, c, id=c["id"]) for n, c in all_cases() if n])
def test_l7_schema_gives_every_case_its_verdict(frame, case):
    defn = FRAMES[frame]
    union = f"{defn['channel']}.{defn['direction']}"
    if case["verdict"] == "valid":
        assert _accepts(frame, case["json"])
        assert _accepts(union, case["json"])
        return
    if case["violation"] == "not-json":
        return                                           # not JSON at all: nothing to validate
    instance = json.loads(case["raw"]) if "raw" in case else case["json"]
    errors = list(_validator(frame).iter_errors(instance))
    assert errors, f"{case['id']}: the schema accepts an invalid case"


def test_l7_schema_rejects_unknown_types_and_non_objects():
    for case in GOLDEN["unknown"]:
        key = f"{case['channel']}.{case['direction']}"
        assert not _accepts(key, case["json"]), f"{case['id']} is accepted as a {key} frame"
    for case in GOLDEN["malformed"]:
        if case["violation"] == "not-an-object":
            for def_name in SCHEMA["$defs"]:
                assert not _accepts(def_name, json.loads(case["raw"])), (case["id"], def_name)


def test_l7_schema_accepts_every_transcript_line():
    for name in TRANSCRIPT_NAMES:
        for line in load_jsonl(transcript_path(name)):
            if line["kind"] == "text":
                assert _accepts(line["frame"], line["json"]), (name, line)


def test_l7_schema_accepts_every_real_frame(capture):
    """The generalization must hold for the server's actual output, and for every client
    frame the server ACCEPTED (the suites also send deliberately bad ones: those are the
    frames of a connection that never got its ack)."""
    wrong: List[str] = []
    for conn in capture:
        entry = CHANNELS[conn.channel]
        accepted = any(line.get("frame") == entry["ack"] for line in conn.lines)
        for line in conn.lines:
            frame = line.get("frame")
            if line["kind"] != "text" or frame is None:
                continue
            if line["direction"] == "c2s" and not accepted:
                continue
            if line["direction"] == "c2s" and FRAMES[frame]["type"] is None \
                    and frame == CHANNELS["output"]["opening"] \
                    and problems(FRAMES[frame], line["json"], strict_keys=False):
                continue        # `/ws/output` never rejects: its ack does not vouch for the frame
            for def_name in (frame, f"{conn.channel}.{line['direction']}"):
                if not _accepts(def_name, line["json"]):
                    wrong.append(f"{conn}: not a valid {def_name}: {line['json']}")
    assert not wrong, "\n".join(wrong)


# ------------------------------------------------------------------------------------------
# L2 — document ≡ core. The guide is the only normative text and the only thing a consumer's
# pin gives a firmware author to read, so (a) nothing in it may contradict the core, and
# (b) everything a harness relies on must be IN it.
# ------------------------------------------------------------------------------------------

GUIDE_FILE = REPO_ROOT / "docs" / "guides" / "websocket-api.md"
GUIDE = GUIDE_FILE.read_text(encoding="utf-8")
STAMP = json.loads((CORE_DIR / "STAMP.json").read_text(encoding="utf-8"))
CORE_SECTION_TITLE = "The machine-readable core"


def guide_sections() -> Dict[str, str]:
    """The guide split at its `## ` headings; the text before the first one is ''."""
    sections: Dict[str, str] = {}
    title = ""
    for line in GUIDE.splitlines(keepends=True):
        if line.startswith("## "):
            title = line[3:].strip()
            sections[title] = ""
        else:
            sections[title] = sections.get(title, "") + line
    return sections


def _section_channel(title: str) -> Optional[str]:
    match = re.match(r"`(/ws/[a-z/]+)`", title)
    if not match:
        return None
    return next(ch for ch, entry in CHANNELS.items() if entry["path"] == match.group(1))


def _frame_examples(text: str) -> List[Dict[str, Any]]:
    """Every frame the prose shows: fenced json blocks, frames on their own line in a plain
    fenced block, and `{…}` snippets inline (which may wrap across lines)."""
    found: List[Any] = []
    for lang, body in re.findall(r"```(\w*)\n(.*?)```", text, re.S):
        if lang == "json":
            found.append(json.loads(body))
        elif lang == "":
            found.extend(json.loads(line) for line in body.splitlines() if line.startswith("{"))
    prose = re.sub(r"```.*?```", "", text, flags=re.S)
    for snippet in re.findall(r"`(\{.*?\})`", prose, re.S):
        found.append(json.loads(" ".join(snippet.split())))
    assert all(isinstance(obj, dict) for obj in found)
    return found


def _is_valid_frame_of(obj: Dict[str, Any], channel: Optional[str]) -> bool:
    for defn in FRAMES.values():
        if channel is not None and defn["channel"] != channel:
            continue
        if defn["type"] is None and "type" in obj:
            continue
        if problems(defn, obj, strict_keys=True) == []:
            return True
    return False


def test_l2_every_frame_the_guide_shows_is_a_valid_instance():
    """An example in the prose that the core would call invalid — or a key the core does not
    list — means document and core disagree. The document wins: fix the core (or the typo)."""
    shown = 0
    for title, text in guide_sections().items():
        channel = _section_channel(title)
        if title and channel is None:
            continue                      # the Python sample; the core's own section
        for obj in _frame_examples(text):
            shown += 1
            assert _is_valid_frame_of(obj, channel), (
                f"guide section {title or '(introduction)'!r} shows a frame the core rejects: {obj}")
    assert shown >= 15, "the guide lost its frame examples (or this parser lost the guide)"


def _core_section() -> str:
    return guide_sections()[CORE_SECTION_TITLE]


def _table_rows(text: str, heading: Optional[str] = None) -> List[List[str]]:
    """The body rows of the first markdown table after `heading` (or in `text`)."""
    if heading is not None:
        text = text.split(heading, 1)[1]
    rows: List[List[str]] = []
    started = False
    for line in text.splitlines():
        if line.startswith("|"):
            started = True
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not set(cells[0]) <= set("-: ") and cells[0] not in ("File", "Frame"):
                rows.append(cells)
        elif started:
            break
    return rows


def _typed_keys(cell: str) -> List[Tuple[str, Any]]:
    out = []
    for key, spec in re.findall(r"`([a-z_]+):([a-z/]+)`", cell):
        names = spec.split("/")
        out.append((key, names if len(names) > 1 else names[0]))
    return out


def test_l2_frame_reference_table_equals_the_definitions():
    """The table in the guide is the normative statement of every frame's keys and types;
    the definitions in frames.golden.json instantiate it. Same frames in the same order,
    same keys, same types, same opaque and volatile marks."""
    rows = _table_rows(_core_section(), "### Frame reference")
    assert [row[0].strip("`") for row in rows] == list(FRAMES)
    for name, direction, required, optional, opaque, volatile in rows:
        defn = FRAMES[name.strip("`")]
        assert direction == defn["direction"], name
        assert [k for k, _ in _typed_keys(required)] == defn["required"], name
        assert [k for k, _ in _typed_keys(optional)] == defn["optional"], name
        assert dict(_typed_keys(required) + _typed_keys(optional)) == defn["types"], name
        assert re.findall(r"`([a-z_]+)`", opaque) == defn["opaque"], name
        assert re.findall(r"`([a-z_]+)`", volatile) == defn["volatile"], name


def _core_files() -> List[str]:
    return sorted(p.name for p in CORE_DIR.iterdir() if p.name not in ("README.md", "STAMP.json"))


def test_l2_the_guide_lists_exactly_the_core_files_and_the_stamp_enumerates_them():
    listed = sorted(row[0].strip("`") for row in _table_rows(_core_section()))
    assert listed == _core_files(), "the guide's file table and contracts/ws-protocol/ disagree"
    guide_rel = GUIDE_FILE.relative_to(REPO_ROOT).as_posix()
    assert sorted(STAMP["artifacts"]) == sorted(
        [guide_rel] + [f"contracts/ws-protocol/{name}" for name in _core_files()]), (
        "STAMP.json must enumerate the guide and every core file — each one individually")
    basenames = [artifact.rsplit("/", 1)[-1] for artifact in STAMP["artifacts"]]
    assert len(basenames) == len(set(basenames)), "pins are flat: basenames must be unique"
    assert not {"README.md", "PIN.json", "STAMP.json"} & set(basenames)
    assert STAMP["guard"].endswith(Path(__file__).name)


def _named_in_core_section(word: str) -> bool:
    """Is `word` named — as code, inside backticks — in the guide's core section?"""
    return re.search(r"`[^`\n]*(?<![A-Za-z0-9_-])" + re.escape(word) + r"(?![A-Za-z0-9_-])[^`\n]*`",
                     _core_section()) is not None


def test_l2_the_guide_defines_everything_a_harness_relies_on():
    """The review's condition: a firmware author holds the pinned guide and nothing else. So
    every key name the fixture files use, and every value of their closed vocabularies, must
    be named in the guide's section — a key the guide never mentions is a key nobody outside
    this repo can know the meaning of."""
    keys = set(GOLDEN) | {"retired", "note"}
    for entry in CHANNELS.values():
        keys |= set(entry)
    for entry in GOLDEN["binary"].values():
        keys |= set(entry)
    for defn in FRAMES.values():
        keys |= set(defn)
    for _, case in all_cases():
        keys |= set(case)
        keys |= set(case.get("expect", {}))
    for name in TRANSCRIPT_NAMES:
        for line in load_jsonl(transcript_path(name)):
            keys |= set(line)
    vocabulary = (VERDICTS | VIOLATIONS | set(LINE_KEYS) | CLOSED_BY | {ORDERING}
                  | {"c2s", "s2c", "pcm_s16le", "close"}
                  | {"string", "integer", "number", "boolean", "object", "array", "null"}
                  | set(CHANNELS) | {f"transcript.{n}.jsonl" for n in TRANSCRIPT_NAMES})
    missing = sorted(word for word in keys | vocabulary if not _named_in_core_section(word))
    assert not missing, f"used by the fixture files but never named in the guide's section: {missing}"
    for number in range(1, 10):
        assert f"**T-{number}**" in _core_section(), f"rule T-{number} is not stated in the guide"
    for obligation in ("must accept", "must ignore", "must survive", "may reject", "must not fault"):
        assert f"**{obligation}**" in _core_section(), obligation


def test_l2_core_and_stamp_agree_on_the_version():
    major = STAMP["version"].split(".")[0]
    assert str(GOLDEN["protocol_major"]) == major
    assert f"`{STAMP['tag']}`" in GUIDE.split("\n## ", 1)[0], "the guide's header names the STAMP tag"
