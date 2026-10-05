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

WS_PROTOCOL_VERSION = "1"
