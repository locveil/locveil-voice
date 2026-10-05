"""ARCH-22 #1 — ESP32 reply channel: CallbackReplyChannel framing + /ws/audio/reply lifecycle."""

import json

import pytest

from locveil_voice.core.interfaces.output import OutputModality
from locveil_voice.intents.context_models import RequestContext
from locveil_voice.outputs.remote_audio import CallbackReplyChannel
from locveil_voice.utils.audio_negotiation import AudioContract
from locveil_voice.utils.audio_stream import PCMStream


@pytest.mark.asyncio
async def test_callback_reply_channel_frames_begin_pcm_end():
    sent = []

    async def send_json(d):
        sent.append(("json", d))

    async def send_bytes(b):
        sent.append(("bytes", bytes(b)))

    ch = CallbackReplyChannel(AudioContract([22050], 22050, ["pcm16"], "pcm16", 1),
                              send_json, send_bytes, chunk_bytes=8)
    pcm = b"\x01\x02" * 10  # 20 bytes
    await ch.send_audio(pcm, sample_rate=22050, channels=1, sample_width=2)

    assert sent[0] == ("json", {"type": "speak_begin", "rate": 22050, "channels": 1, "width": 16, "seq": 1})
    assert sent[-1] == ("json", {"type": "speak_end", "seq": 1})
    body = b"".join(b for t, b in sent if t == "bytes")
    assert body == pcm
    assert len([1 for t, _ in sent if t == "bytes"]) > 1  # genuinely chunked
    assert ch.is_connected() is True


def _build_app(*, voice_rate=16000, voice_pcm=b"\x00\x00", negotiator=None):
    from fastapi import FastAPI
    from locveil_voice.runners.webapi_router import create_webapi_router
    from locveil_voice.outputs.manager import OutputManager

    class _FakeTTS:
        async def synthesize_to_stream(self, text, **kw):
            async def _f():
                yield voice_pcm
            return PCMStream(voice_rate, 1, 2, _f())

    class _PassNeg:
        output_sink = None

        async def to_device(self, audio_data, device, trace_context=None):
            return audio_data

    class _CM:
        def get_component(self, name):
            return _FakeTTS() if name == "tts" else None

    om = OutputManager()

    class _Core:
        def __init__(self):
            self.output_manager = om
            self.audio_negotiator = negotiator or _PassNeg()
            self.component_manager = _CM()
            self.config = None
            self.plugin_manager = None
            self.workflow_manager = None

    router = create_webapi_router(_Core(), asset_loader=None, web_input=None, start_time=0.0)
    app = FastAPI()
    app.include_router(router)
    return app, om


def test_ws_audio_reply_registers_routes_and_deregisters():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    app, om = _build_app()

    with TestClient(app).websocket_connect("/ws/audio/reply") as ws:
        ws.send_text(json.dumps({"type": "register-reply", "client_id": "kitchen_node",
                                 "audio_out": {"rate": 22050, "channels": 1, "width": 16}}))
        ack = ws.receive_json()
        assert ack["type"] == "registered" and ack["client_id"] == "kitchen_node"

        # A SPEECH result from this device origin-routes to its RemoteAudioOutput.
        ctx = RequestContext(session_id="s", client_id="kitchen_node")
        targets = om.select(OutputModality.SPEECH, ctx)
        assert len(targets) == 1 and targets[0].origin_key() == "kitchen_node"

    # After disconnect the output is deregistered.
    assert om.select(OutputModality.SPEECH, RequestContext(session_id="s", client_id="kitchen_node")) == []


def test_ws_audio_reply_rejects_bad_first_frame():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    app, _ = _build_app()
    with TestClient(app).websocket_connect("/ws/audio/reply") as ws:
        ws.send_text(json.dumps({"type": "register", "client_id": "x"}))  # wrong type
        msg = ws.receive_json()
        assert msg["type"] == "error"


@pytest.mark.parametrize("first_frame", [
    '{"type": ',                                                    # not JSON
    "[1, 2]",                                                       # JSON, but not an object
    json.dumps({"type": "register-reply", "client_id": "kitchen_node",
                "audio_out": {"rate": "fast"}}),                    # unusable audio contract
])
def test_ws_audio_reply_answers_error_and_closes_on_a_malformed_first_frame(first_frame):
    """BUG-46: a first frame the handler cannot parse is a protocol violation — it is answered
    with `error` and the server closes (it used to drop the socket with no frame at all)."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    app, om = _build_app()
    with TestClient(app).websocket_connect("/ws/audio/reply") as ws:
        ws.send_text(first_frame)
        msg = ws.receive_json()
        assert msg["type"] == "error" and msg["error"]
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()                                       # terminal: the server closed
    assert om._outputs == {}                                        # nothing was registered


def test_ws_audio_reply_answers_error_on_a_binary_first_frame():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    app, _ = _build_app()
    with TestClient(app).websocket_connect("/ws/audio/reply") as ws:
        ws.send_bytes(b"\x00\x01")
        assert ws.receive_json()["type"] == "error"
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()


# --- TEST-23: the speak burst through the REAL endpoint (it was asserted at callback level only) ---

def _real_negotiator():
    """The production conform-down seam (16 kHz mono canonical pipeline)."""
    from locveil_voice.core.audio_negotiator import AudioNegotiator
    from locveil_voice.utils.audio_negotiation import CanonicalFormat
    return AudioNegotiator(CanonicalFormat(16000, "pcm16", 1))


def _speak(client, om, text, client_id="kitchen_node"):
    """Deliver one spoken result to the device from inside the app's event loop."""
    from locveil_voice.intents.models import IntentResult
    return client.portal.call(om.deliver, IntentResult(text=text),
                              RequestContext(session_id="s", client_id=client_id),
                              OutputModality.SPEECH)


def _read_burst(ws):
    """One bracketed burst off the socket: (speak_begin, pcm bytes, binary frame count, speak_end)."""
    begin = ws.receive_json()
    assert begin["type"] == "speak_begin"
    pcm, frames = bytearray(), 0
    while True:
        msg = ws.receive()
        if msg.get("bytes") is not None:
            pcm.extend(msg["bytes"])
            frames += 1
            continue
        end = json.loads(msg["text"])
        assert end["type"] == "speak_end"
        return begin, bytes(pcm), frames, end


def test_ws_audio_reply_pushes_bracketed_bursts_with_a_per_connection_seq():
    """register-reply → registered → speak_begin / PCM / speak_end, twice: `seq` pairs each
    bracket and counts the bursts of this connection from 1."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    voice = b"\x01\x02" * 5000                      # 10000 bytes of 22.05 kHz mono PCM16
    app, om = _build_app(voice_rate=22050, voice_pcm=voice, negotiator=_real_negotiator())

    with TestClient(app) as client, client.websocket_connect("/ws/audio/reply") as ws:
        ws.send_text(json.dumps({"type": "register-reply", "client_id": "kitchen_node",
                                 "audio_out": {"rate": 22050, "channels": 1}}))
        assert ws.receive_json() == {"type": "registered", "client_id": "kitchen_node",
                                     "protocol_version": "1"}

        delivered = _speak(client, om, "Таймер на 5 минут запущен")
        assert [d.delivered for d in delivered] == [True]
        begin, pcm, frames, end = _read_burst(ws)
        assert begin == {"type": "speak_begin", "rate": 22050, "channels": 1, "width": 16, "seq": 1}
        assert pcm == voice and frames > 1            # the whole utterance, genuinely chunked
        assert end == {"type": "speak_end", "seq": 1}

        _speak(client, om, "Таймер на 5 минут завершён")
        begin, pcm, _, end = _read_burst(ws)
        assert begin["seq"] == 2 and end == {"type": "speak_end", "seq": 2}
        assert pcm == voice


def _register_and_hear(voice_rate, voice_pcm, audio_out):
    """Register a reply channel with `audio_out`, deliver one result spoken by a voice of
    `voice_rate`, return (speak_begin, pcm)."""
    from fastapi.testclient import TestClient
    app, om = _build_app(voice_rate=voice_rate, voice_pcm=voice_pcm, negotiator=_real_negotiator())
    with TestClient(app) as client, client.websocket_connect("/ws/audio/reply") as ws:
        ws.send_text(json.dumps({"type": "register-reply", "client_id": "kitchen_node",
                                 "audio_out": audio_out}))
        assert ws.receive_json()["type"] == "registered"
        delivered = _speak(client, om, "готово")
        assert [d.delivered for d in delivered] == [True]
        begin, pcm, _, _ = _read_burst(ws)
        return begin, pcm


def test_ws_audio_reply_converts_a_lower_rate_voice_up_to_the_registered_rate():
    """BUG-50: the reply is ALWAYS in the format the device registered. A 16 kHz voice reaches
    a device that registered 22.05 kHz AT 22.05 kHz (it used to arrive at 16 kHz with only
    `speak_begin` telling the truth) — a satellite plays what arrives and never resamples."""
    pytest.importorskip("fastapi")
    seconds = 0.5
    voice = b"\x01\x02" * int(16000 * seconds)                 # half a second of 16 kHz mono
    begin, pcm = _register_and_hear(16000, voice, {"rate": 22050, "channels": 1})

    assert begin == {"type": "speak_begin", "rate": 22050, "channels": 1, "width": 16, "seq": 1}
    samples = len(pcm) / 2
    assert len(pcm) % 2 == 0
    assert abs(samples - 22050 * seconds) <= 2, "the burst must last what the utterance lasted"
    assert len(pcm) != len(voice)                              # really resampled, not relabelled


def test_ws_audio_reply_converts_a_higher_rate_voice_down_to_the_registered_rate():
    """…and the other direction, which always worked: a 22.05 kHz voice for a 16 kHz device."""
    pytest.importorskip("fastapi")
    seconds = 0.5
    voice = b"\x01\x02" * int(22050 * seconds)
    begin, pcm = _register_and_hear(22050, voice, {"rate": 16000, "channels": 1})

    assert begin == {"type": "speak_begin", "rate": 16000, "channels": 1, "width": 16, "seq": 1}
    assert abs(len(pcm) / 2 - 16000 * seconds) <= 2


def test_ws_audio_reply_spreads_a_mono_voice_over_the_registered_channels():
    """The channel count is part of what was registered too: a mono voice for a device that
    registered two channels arrives as two-channel audio (the same signal on both)."""
    pytest.importorskip("fastapi")
    voice = bytes(range(200)) * 10                             # 1000 distinct mono samples
    begin, pcm = _register_and_hear(22050, voice, {"rate": 22050, "channels": 2})

    assert begin == {"type": "speak_begin", "rate": 22050, "channels": 2, "width": 16, "seq": 1}
    assert len(pcm) == 2 * len(voice)
    left = b"".join(pcm[i:i + 2] for i in range(0, len(pcm), 4))
    right = b"".join(pcm[i + 2:i + 4] for i in range(0, len(pcm), 4))
    assert left == voice and right == voice


def test_ws_audio_reply_drops_a_delivery_it_cannot_convert_rather_than_mislabel_it():
    """If the conversion does not produce the registered format, nothing is sent: a burst in
    another format would be played at the wrong speed."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    app, om = _build_app(voice_rate=16000, voice_pcm=b"\x01\x02" * 800)   # pass-through negotiator
    with TestClient(app) as client, client.websocket_connect("/ws/audio/reply") as ws:
        ws.send_text(json.dumps({"type": "register-reply", "client_id": "kitchen_node",
                                 "audio_out": {"rate": 22050, "channels": 1}}))
        assert ws.receive_json()["type"] == "registered"
        delivered = _speak(client, om, "готово")
        assert [d.delivered for d in delivered] == [False]
    # (nothing was pushed: the context manager closed a socket with no pending frames to read)


def test_ws_audio_reply_register_without_audio_out_assumes_22050_mono():
    """`audio_out` may be omitted: the server assumes 22.05 kHz mono (a 48 kHz voice is then
    converted down to it)."""
    pytest.importorskip("fastapi")
    pytest.importorskip("numpy")
    from fastapi.testclient import TestClient

    app, om = _build_app(voice_rate=48000, voice_pcm=b"\x01\x02" * 4800,
                         negotiator=_real_negotiator())
    with TestClient(app) as client, client.websocket_connect("/ws/audio/reply") as ws:
        ws.send_text(json.dumps({"type": "register-reply", "client_id": "kitchen_node"}))
        assert ws.receive_json()["type"] == "registered"
        _speak(client, om, "готово")
        begin, _, _, _ = _read_burst(ws)
        assert begin["rate"] == 22050 and begin["channels"] == 1


# --- BUG-47: two deliveries to ONE reply connection must not interleave ------------------------

@pytest.mark.asyncio
async def test_callback_reply_channel_serializes_concurrent_bursts():
    """The channel owns its send path: a second `send_audio` waits for the first burst's
    `speak_end` — even when every send yields to the event loop (as a real socket does)."""
    import asyncio
    sent = []

    async def send_json(d):
        await asyncio.sleep(0)
        sent.append(d["type"] + str(d["seq"]))

    async def send_bytes(b):
        await asyncio.sleep(0)
        sent.append("pcm")

    ch = CallbackReplyChannel(AudioContract([22050], 22050, ["pcm16"], "pcm16", 1),
                              send_json, send_bytes, chunk_bytes=8)
    await asyncio.gather(*(ch.send_audio(b"\x01\x02" * 12, sample_rate=22050, channels=1,
                                         sample_width=2) for _ in range(3)))
    burst = ["pcm"] * 3
    assert sent == (["speak_begin1"] + burst + ["speak_end1"]
                    + ["speak_begin2"] + burst + ["speak_end2"]
                    + ["speak_begin3"] + burst + ["speak_end3"])


def test_ws_audio_reply_concurrent_deliveries_arrive_as_whole_bursts():
    """The race on a real socket: a spoken reply and a deferred announcement are delivered to
    the same device AT THE SAME TIME (the `/ws/audio` handler routes one, the notification loop
    the other). Each must arrive as a whole bracketed burst — never one inside the other."""
    pytest.importorskip("fastapi")
    import asyncio
    from fastapi.testclient import TestClient
    from locveil_voice.intents.models import IntentResult

    voice = b"\x01\x02" * 10000                       # 5 binary frames per burst
    app, om = _build_app(voice_rate=22050, voice_pcm=voice, negotiator=_real_negotiator())

    async def _both_at_once():
        ctx = RequestContext(session_id="s", client_id="kitchen_node")
        return await asyncio.gather(
            om.deliver(IntentResult(text="Таймер на 5 минут запущен"), ctx, OutputModality.SPEECH),
            om.deliver(IntentResult(text="Таймер на 1 минуту завершён"), ctx, OutputModality.SPEECH))

    with TestClient(app) as client, client.websocket_connect("/ws/audio/reply") as ws:
        ws.send_text(json.dumps({"type": "register-reply", "client_id": "kitchen_node",
                                 "audio_out": {"rate": 22050, "channels": 1}}))
        assert ws.receive_json()["type"] == "registered"

        outcomes = client.portal.call(_both_at_once)
        assert [d.delivered for pair in outcomes for d in pair] == [True, True]

        for seq in (1, 2):                            # two WHOLE bursts, in seq order
            begin, pcm, frames, end = _read_burst(ws)
            assert begin["seq"] == seq and end == {"type": "speak_end", "seq": seq}
            assert pcm == voice and frames == 5


# --- BUG-48: the documented keys carry their documented JSON types -------------------------------

@pytest.mark.parametrize("patch", [
    {"client_id": 5}, {"audio_out": 22050}, {"audio_out": [22050, 1]},
    {"audio_out": {"rate": "22050", "channels": 1}}, {"audio_out": {"rate": 22050, "channels": "1"}},
    {"audio_out": {"rate": 0, "channels": 1}}, {"audio_out": {"rate": 22050, "channels": 0}},
])
def test_ws_audio_reply_register_with_a_wrongly_typed_key_is_refused(patch):
    """`"rate": "22050"` used to be coerced and a numeric `client_id` registered; both are
    refused now — `error`, the server closes, no output is paired."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    app, om = _build_app()
    frame = {"type": "register-reply", "client_id": "kitchen_node",
             "audio_out": {"rate": 22050, "channels": 1}, **patch}
    with TestClient(app).websocket_connect("/ws/audio/reply") as ws:
        ws.send_text(json.dumps(frame))
        msg = ws.receive_json()
        assert msg["type"] == "error" and msg["error"], msg
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()
    assert om._outputs == {}
