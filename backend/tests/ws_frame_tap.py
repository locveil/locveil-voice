"""Server-side WebSocket frame tap — a pytest plugin for the ws-protocol owner test.

`test_ws_machine_core.py` re-runs the WS witness suites in a child pytest process with this
plugin loaded (`-p tests.ws_frame_tap`) and the `LOCVEIL_WS_TAP` environment variable naming
an output file. The plugin wraps Starlette's `WebSocket.send` / `WebSocket.receive` — the
seam behind every `/ws/*` endpoint, whatever drives it (the in-process `TestClient` or a
real loopback uvicorn server with a real client) — and appends one JSON line per event:

    {"kind": "open",   "conn": "c1", "channel": "audio", "test": "<pytest node id>"}
    {"kind": "text",   "conn": "c1", "channel": "audio", "direction": "c2s", "json": {...}}
    {"kind": "text",   ...,          "direction": "c2s", "raw": "<text that is not a JSON object>"}
    {"kind": "binary", "conn": "c1", "channel": "audio", "direction": "c2s",
     "content": "pcm_s16le", "bytes": 640}
    {"kind": "close",  "conn": "c1", "by": "client" | "server" | "network", "code": 1000}

That is the line format of the golden transcripts (`docs/guides/websocket-api.md` → "The
machine-readable core"), so live captures and golden transcripts are read by the same code.
The tap records facts only — it does not know the golden files and never names a frame;
classification and every verdict belong to the owner test.

What is recorded is what the REAL handlers consumed and emitted: a frame is logged after
the underlying receive/send succeeded, so a frame that never reached the wire is absent.
Without `LOCVEIL_WS_TAP` the plugin does nothing.
"""

import itertools
import json
import os
import threading
from typing import Any, Dict, Optional

from starlette.websockets import WebSocket

ENV_VAR = "LOCVEIL_WS_TAP"

# The four protocol channels, by endpoint path. Other sockets are not the wire protocol.
CHANNEL_BY_PATH = {
    "/ws/audio": "audio",
    "/ws/audio/reply": "reply",
    "/ws/output": "output",
    "/ws/observe": "observe",
}

# A close code the server-side stack reports when the peer vanished without a closing
# handshake (TCP reset / power loss) — the transcripts' `"by": "network"`.
ABNORMAL_CLOSE_CODE = 1006

_SCOPE_KEY = "locveil.ws_tap"


class _Tap:
    def __init__(self, path: str) -> None:
        self._fh = open(path, "a", encoding="utf-8")
        self._lock = threading.Lock()  # TestClient runs each app in its own thread
        self._counter = itertools.count(1)

    def _state(self, ws: WebSocket) -> Optional[Dict[str, Any]]:
        channel = CHANNEL_BY_PATH.get(ws.scope.get("path", ""))
        if channel is None:
            return None
        state = ws.scope.get(_SCOPE_KEY)
        if state is None:
            with self._lock:
                label = f"c{next(self._counter)}"
            state = {"conn": label, "channel": channel, "closed": False}
            ws.scope[_SCOPE_KEY] = state
        return state

    def _write(self, line: Dict[str, Any]) -> None:
        with self._lock:
            self._fh.write(json.dumps(line, ensure_ascii=False) + "\n")
            self._fh.flush()

    def _payload(self, state: Dict[str, Any], direction: str, message: Dict[str, Any]) -> None:
        base = {"conn": state["conn"], "channel": state["channel"], "direction": direction}
        if message.get("bytes") is not None:
            self._write({"kind": "binary", **base, "content": "pcm_s16le",
                         "bytes": len(message["bytes"])})
            return
        text = message.get("text")
        if text is None:
            return
        try:
            obj = json.loads(text)
        except ValueError:
            obj = None
        if isinstance(obj, dict):
            self._write({"kind": "text", **base, "json": obj})
        else:
            self._write({"kind": "text", **base, "raw": text})

    def _close(self, state: Dict[str, Any], by: str, code: Any) -> None:
        if state["closed"]:
            return  # the first close wins: who ended the connection
        state["closed"] = True
        self._write({"kind": "close", "conn": state["conn"], "by": by, "code": code})

    def received(self, ws: WebSocket, message: Dict[str, Any]) -> None:
        state = self._state(ws)
        if state is None:
            return
        kind = message.get("type")
        if kind == "websocket.connect":
            self._write({"kind": "open", "conn": state["conn"], "channel": state["channel"],
                         "test": os.environ.get("PYTEST_CURRENT_TEST", "").split(" (")[0]})
        elif kind == "websocket.receive":
            self._payload(state, "c2s", message)
        elif kind == "websocket.disconnect":
            code = message.get("code")
            self._close(state, "network" if code == ABNORMAL_CLOSE_CODE else "client", code)

    def sent(self, ws: WebSocket, message: Dict[str, Any]) -> None:
        state = self._state(ws)
        if state is None:
            return
        kind = message.get("type")
        if kind == "websocket.send":
            self._payload(state, "s2c", message)
        elif kind == "websocket.close":
            self._close(state, "server", message.get("code"))


def install(path: str) -> None:
    """Wrap `WebSocket.receive` / `WebSocket.send` for the life of the process."""
    tap = _Tap(path)
    original_receive = WebSocket.receive
    original_send = WebSocket.send

    async def receive(self: WebSocket) -> Any:
        message = await original_receive(self)
        tap.received(self, message)
        return message

    async def send(self: WebSocket, message: Any) -> None:
        await original_send(self, message)
        tap.sent(self, message)

    WebSocket.receive = receive  # type: ignore[method-assign]
    WebSocket.send = send  # type: ignore[method-assign]


def pytest_configure(config: Any) -> None:
    path = os.environ.get(ENV_VAR)
    if path:
        install(path)
