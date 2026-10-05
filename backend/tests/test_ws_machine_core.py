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
