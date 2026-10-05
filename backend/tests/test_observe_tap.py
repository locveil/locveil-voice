"""ARCH-15 PR-6b — observation tap: gating (D-5) + bus→queue bridging + WS auth rejection."""

from types import SimpleNamespace

import pytest

from locveil_voice.core.event_bus import EventBus, EventType, PipelineEvent, identity_filter
from locveil_voice.core.observe import authorize_observer, subscribe_to_queue


# --- gating (D-5) --------------------------------------------------------------------------

def test_tap_disabled_without_configured_token():
    # No token configured ⇒ tap is off, even from localhost with a token.
    assert authorize_observer("127.0.0.1", "x", configured_token=None, allow_remote=False) is False


def test_localhost_allowed_with_matching_token():
    assert authorize_observer("127.0.0.1", "secret", configured_token="secret", allow_remote=False) is True
    assert authorize_observer("::1", "secret", configured_token="secret", allow_remote=False) is True


def test_remote_denied_unless_allowed():
    assert authorize_observer("10.0.0.5", "secret", configured_token="secret", allow_remote=False) is False
    assert authorize_observer("10.0.0.5", "secret", configured_token="secret", allow_remote=True) is True


def test_token_must_match():
    assert authorize_observer("127.0.0.1", "wrong", configured_token="secret", allow_remote=True) is False


# --- bus → queue bridge --------------------------------------------------------------------

async def test_subscribe_to_queue_funnels_filtered_events():
    bus = EventBus()
    queue, unsubscribe = subscribe_to_queue(bus, identity_filter(room_name="Кухня"))

    await bus.publish(PipelineEvent(type=EventType.RESULT_PRODUCED, room_name="Кухня"))
    await bus.publish(PipelineEvent(type=EventType.RESULT_PRODUCED, room_name="Спальня"))

    assert queue.qsize() == 1
    ev = queue.get_nowait()
    assert ev.room_name == "Кухня"
    unsubscribe()

    # after unsubscribe, nothing more is queued
    await bus.publish(PipelineEvent(type=EventType.RESULT_PRODUCED, room_name="Кухня"))
    assert queue.qsize() == 0


async def test_queue_overflow_drops_oldest_not_blocks():
    bus = EventBus()
    queue, _ = subscribe_to_queue(bus, maxsize=2)
    for i in range(5):
        await bus.publish(PipelineEvent(type=EventType.INPUT_RECEIVED, payload={"n": i}))
    # bounded at 2, never blocks; keeps the most recent two
    assert queue.qsize() == 2
    assert [queue.get_nowait().payload["n"] for _ in range(2)] == [3, 4]


# --- WS endpoint auth rejection (synchronous; no cross-loop publish needed) -----------------

def _router_app(token, allow_remote, bus):
    pytest.importorskip("fastapi")
    from fastapi import FastAPI
    from locveil_voice.runners.webapi_router import create_webapi_router

    sysc = SimpleNamespace(observe_token=token, observe_allow_remote=allow_remote, web_port=8000)
    core = SimpleNamespace(config=SimpleNamespace(system=sysc), event_bus=bus,
                           workflow_manager=None, component_manager=None, plugin_manager=None)
    app = FastAPI()
    app.include_router(create_webapi_router(core, asset_loader=None, web_input=None, start_time=0.0))
    return app


def test_ws_observe_rejects_when_disabled():
    import json
    from fastapi.testclient import TestClient
    app = _router_app(token=None, allow_remote=True, bus=EventBus())
    with TestClient(app).websocket_connect("/ws/observe") as ws:
        ws.send_text(json.dumps({"token": "anything"}))
        msg = ws.receive_json()
        assert msg["type"] == "error" and msg["error"] == "unauthorized"


def test_ws_observe_rejects_wrong_token():
    import json
    from fastapi.testclient import TestClient
    app = _router_app(token="secret", allow_remote=True, bus=EventBus())
    with TestClient(app).websocket_connect("/ws/observe") as ws:
        ws.send_text(json.dumps({"token": "nope"}))
        msg = ws.receive_json()
        assert msg["type"] == "error" and msg["error"] == "unauthorized"


def test_ws_observe_malformed_first_frame_gets_error_then_close():
    """BUG-46: the catch-all path answers `error` AND closes (an `error` frame is terminal)."""
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect
    app = _router_app(token="secret", allow_remote=True, bus=EventBus())
    with TestClient(app).websocket_connect("/ws/observe") as ws:
        ws.send_text('{"token": ')
        msg = ws.receive_json()
        assert msg["type"] == "error" and msg["error"]
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()


# --- TEST-23: `subscribed` and `event` over the real socket ------------------------------------

def test_ws_observe_streams_filtered_events_after_subscribed():
    """subscribe (token + filter) → subscribed → only the matching bus events arrive as `event`."""
    import json
    from fastapi.testclient import TestClient
    bus = EventBus()
    app = _router_app(token="observe-secret", allow_remote=True, bus=bus)
    with TestClient(app) as client, client.websocket_connect("/ws/observe") as ws:
        ws.send_text(json.dumps({"token": "observe-secret",
                                 "filter": {"room_name": "Кухня", "types": ["result.produced"]}}))
        assert ws.receive_json() == {"type": "subscribed"}

        # filtered out twice over: another room, then another event type
        client.portal.call(bus.publish, PipelineEvent(type=EventType.RESULT_PRODUCED,
                                                      room_name="Спальня"))
        client.portal.call(bus.publish, PipelineEvent(type=EventType.INPUT_RECEIVED,
                                                      room_name="Кухня"))
        client.portal.call(bus.publish, PipelineEvent(
            type=EventType.RESULT_PRODUCED, session_id="5f0c1d7a9b3e4c62a8d4e1f0b7c39a25",
            client_id="kitchen_node", room_name="Кухня", source="ws_audio",
            payload={"text": "Таймер на 5 минут запущен", "success": True}))

        ev = ws.receive_json()
        assert ev.pop("timestamp") > 0
        assert ev == {"type": "event", "event": "result.produced",
                      "session_id": "5f0c1d7a9b3e4c62a8d4e1f0b7c39a25",
                      "client_id": "kitchen_node", "room_name": "Кухня", "source": "ws_audio",
                      "payload": {"text": "Таймер на 5 минут запущен", "success": True}}
