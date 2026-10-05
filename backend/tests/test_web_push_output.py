"""ARCH-15 PR-6c — web built-in-app push output: identity-addressed delivery + WS registration.

The browser opens /ws/output, which registers a CallbackTextOutput on the shared OutputManager keyed
by a per-connection client_id. Deferred results (e.g. a browser-set timer) are routed to that exact
connection by **physical identity** (client_id), not by channel — so a REST caller's F&F never lands
in some random browser.
"""

import json
from types import SimpleNamespace

import pytest

from locveil_voice.core.interfaces.output import OutputModality
from locveil_voice.intents.context_models import RequestContext
from locveil_voice.intents.models import IntentResult
from locveil_voice.outputs.console import ConsoleOutput
from locveil_voice.outputs.manager import OutputManager

T = OutputModality.TEXT


# --- OutputManager identity addressing (the routing core) ----------------------------------

async def test_deferred_result_routed_by_client_id_not_channel():
    captured = []
    om = OutputManager()
    # registered keyed by the browser connection's client_id (origin = client_id)
    await om.add_output("browser_abc", ConsoleOutput(sink=captured.append, origin="browser_abc"))

    # a deferred notification: source is the generic "api" channel, but it carries the action's
    # physical identity (client_id) — delivery must follow the identity to the right connection.
    ctx = RequestContext(source="api", client_id="browser_abc")
    res = await om.deliver(IntentResult(text="таймер сработал"), ctx, T)

    assert len(res) == 1 and res[0].output_name == "console"
    assert captured == ["📝 таймер сработал"]


async def test_no_identity_match_delivers_nothing():
    captured = []
    om = OutputManager()
    await om.add_output("browser_abc", ConsoleOutput(sink=captured.append, origin="browser_abc"))

    ctx = RequestContext(source="api", client_id="other_browser")  # not registered
    res = await om.deliver(IntentResult(text="x"), ctx, T)

    assert res == [] and captured == []


async def test_remove_output_is_idempotent():
    om = OutputManager()
    await om.add_output("browser_abc", ConsoleOutput(origin="browser_abc"))
    assert "browser_abc" in om._outputs
    om.remove_output("browser_abc")
    assert "browser_abc" not in om._outputs
    om.remove_output("browser_abc")  # again — no error


# --- /ws/output registration lifecycle (real WS via TestClient) ----------------------------

def _app(output_manager):
    pytest.importorskip("fastapi")
    from fastapi import FastAPI
    from locveil_voice.runners.webapi_router import create_webapi_router

    core = SimpleNamespace(output_manager=output_manager, config=None,
                           workflow_manager=None, component_manager=None, plugin_manager=None)
    app = FastAPI()
    app.include_router(create_webapi_router(core, asset_loader=None, web_input=None, start_time=0.0))
    return app


def test_ws_output_registers_supplied_client_id():
    from fastapi.testclient import TestClient
    om = OutputManager()
    with TestClient(_app(om)).websocket_connect("/ws/output") as ws:
        ws.send_text(json.dumps({"client_id": "browser_abc"}))
        ack = ws.receive_json()
        assert ack["type"] == "connected" and ack["client_id"] == "browser_abc"
        # registered on the shared OutputManager, keyed by the client_id
        assert "browser_abc" in om._outputs


def test_ws_output_mints_client_id_when_absent():
    from fastapi.testclient import TestClient
    om = OutputManager()
    with TestClient(_app(om)).websocket_connect("/ws/output") as ws:
        ws.send_text(json.dumps({}))
        ack = ws.receive_json()
        assert ack["type"] == "connected" and ack["client_id"].startswith("web_")
        assert ack["client_id"] in om._outputs


# --- TEST-23: the pushed `message` frame and the `error` frame over the real socket ----------

def test_ws_output_pushes_a_deferred_result_as_a_message_frame():
    """hello → connected → a deferred result addressed to this client_id arrives as `message`."""
    from fastapi.testclient import TestClient
    om = OutputManager()
    with TestClient(_app(om)) as client, client.websocket_connect("/ws/output") as ws:
        ws.send_text(json.dumps({"client_id": "web_abc123"}))
        assert ws.receive_json() == {"type": "connected", "client_id": "web_abc123"}

        ctx = RequestContext(source="api", client_id="web_abc123")
        res = client.portal.call(om.deliver, IntentResult(text="Таймер на 10 минут завершён"), ctx, T)
        assert [r.delivered for r in res] == [True]
        assert ws.receive_json() == {"type": "message", "text": "Таймер на 10 минут завершён"}


def test_ws_output_answers_error_and_closes_when_web_push_is_unavailable():
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect
    with TestClient(_app(None)).websocket_connect("/ws/output") as ws:
        assert ws.receive_json() == {"type": "error", "error": "web push output unavailable"}
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()


def test_ws_output_never_rejects_its_opening_frame():
    """This channel is lenient by design: a first frame without a usable client_id — even one
    that is not JSON — gets a minted identity instead of an `error`."""
    from fastapi.testclient import TestClient
    om = OutputManager()
    with TestClient(_app(om)).websocket_connect("/ws/output") as ws:
        ws.send_text('{"client_id": ')
        ack = ws.receive_json()
        assert ack["type"] == "connected" and ack["client_id"].startswith("web_")
