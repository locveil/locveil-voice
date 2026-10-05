"""The WS wire-protocol version — the served half of the `ws-protocol` contract (ARCH-47).

`docs/guides/websocket-api.md` is the single source of truth for the wire protocol
(`ws-protocol-doc-canonical`); this constant is its machine-readable twin, sent in every
`registered` ack so a consumer (the satellite runner, ESP32 firmware, locveil-commons'
`ws_audio_provider`) can check what it was built against without parsing prose.

The served value is the contract's MAJOR version only: it states wire compatibility and
moves only on a breaking wire change. The full three-part version lives in
`contracts/ws-protocol/STAMP.json` (minor = additive wire change, patch = a byte edit to
an enumerated artifact with the wire untouched) — neither changes this constant.
`backend/tests/test_ws_protocol_version.py` asserts the agreement: this constant == the
doc's "Protocol version" header number == the STAMP version's major, and the doc header
names the STAMP's tag exactly.
"""

from typing import Any, Dict, Optional

WS_PROTOCOL_VERSION = "1"


# --- Opening-frame validation (BUG-48) -------------------------------------------------------
#
# The JSON type of every key a client may send in a channel's OPENING frame, exactly as the
# guide's frame reference states them (`docs/guides/websocket-api.md` → "Frame reference";
# `ws-protocol-doc-canonical` — the document wins, this table is the server catching up with
# it). A hand-written twin of the document, like `WS_PROTOCOL_VERSION`: the machine-core owner
# test (`backend/tests/test_ws_machine_core.py`) asserts it equals the golden definitions key
# for key, so the three cannot drift apart silently.
#
# `required` keys must be present; every listed key that IS present must have its type; keys
# not listed are ignored (the forward-compatibility rule). `inner` types the documented keys
# of a nested object, `items` the elements of an array.

OPENING_FRAMES: Dict[str, Dict[str, Any]] = {
    "audio.register": {
        "required": ("client_id", "room_name"),
        "types": {
            "client_id": "string", "room_name": "string", "sample_rate": "integer",
            "wants_audio": "boolean", "mode": "string", "wants_trace": "boolean",
            "covered_rooms": "array", "name": "string", "available_devices": "array",
            "protocol_version": "string", "firmware_version": "string",
            "wake_pack_version": "string",
        },
        "items": {"covered_rooms": "string", "available_devices": "object"},
    },
    "reply.register-reply": {
        "required": ("client_id",),
        "types": {"client_id": "string", "audio_out": "object"},
        "inner": {"audio_out": {"rate": "integer", "channels": "integer"}},
    },
    "output.hello": {
        "required": (),
        "types": {"client_id": "string"},
    },
    "observe.subscribe": {
        "required": ("token",),
        "types": {"token": "string", "filter": "object"},
        "inner": {"filter": {"types": "array", "session_id": "string", "client_id": "string",
                             "room_name": "string", "source": "string"}},
    },
}

_TYPE_PHRASE = {"string": "a string", "integer": "an integer", "boolean": "true or false",
                "object": "an object", "array": "an array"}


def _has_json_type(value: Any, json_type: str) -> bool:
    if json_type == "string":
        return isinstance(value, str)
    if json_type == "boolean":
        return isinstance(value, bool)
    if json_type == "integer":  # a JSON number without a fractional part; `true` is not a number
        if isinstance(value, bool):
            return False
        return isinstance(value, int) or (isinstance(value, float) and value.is_integer())
    if json_type == "object":
        return isinstance(value, dict)
    if json_type == "array":
        return isinstance(value, list)
    raise ValueError(f"unknown JSON type name: {json_type!r}")


def opening_frame_violation(frame: str, obj: Any) -> Optional[str]:
    """Why `obj` is not an acceptable `frame` opening frame, in words fit for the `error`
    frame — or None when its shape is fine. Checks shape only: presence of the required
    keys and the JSON type of every documented key. (The frame's own `type` value, identity
    and authorization are the endpoint's business.)"""
    spec = OPENING_FRAMES[frame]
    if not isinstance(obj, dict):
        return "the frame must be a JSON object"
    for key in spec["required"]:
        if key not in obj:
            return f'"{key}" is required'
    for key, json_type in spec["types"].items():
        if key not in obj:
            continue
        value = obj[key]
        if not _has_json_type(value, json_type):
            return f'"{key}" must be {_TYPE_PHRASE[json_type]}'
        item_type = spec.get("items", {}).get(key)
        if item_type is not None and not all(_has_json_type(item, item_type) for item in value):
            return f'every element of "{key}" must be {_TYPE_PHRASE[item_type]}'
        for inner_key, inner_type in spec.get("inner", {}).get(key, {}).items():
            if inner_key in value and not _has_json_type(value[inner_key], inner_type):
                return f'"{key}.{inner_key}" must be {_TYPE_PHRASE[inner_type]}'
    return None
