# ws-protocol — the WebSocket wire protocol (owned)

The normative artifact **lives at [`docs/guides/websocket-api.md`](../../docs/guides/websocket-api.md)**
(`ws-protocol-doc-canonical` — a hand-written reference that doubles as the user guide; owned
surfaces that legitimately live elsewhere keep their home, per
`../locveil-commons/process/contracts.md` §2). This folder holds the version authority.

**The guide is enumerated whole** in `STAMP.json` → `artifacts`: that list is what consumers
pin and what the contract guard byte-locks. Any edit to the guide — a wire change or a typo —
is a version move, cut in the same change.

Versions have three levels (`process/contracts.md` §3):

| Level | When | Served `protocol_version` |
|---|---|---|
| major | a breaking wire change | moves — it IS the major |
| minor | the surface changed additively (a new optional field or frame; the pinned set gaining a file) | unchanged |
| patch | enumerated bytes moved, the wire did not (an editorial fix to the guide, STAMP metadata) | unchanged |

`backend/tests/test_ws_protocol_version.py` keeps the legs in agreement:

1. `STAMP.json` is the authority — a three-part `version`, `tag` = `ws-protocol-v<version>`;
2. the guide's "Protocol version" header line shows the **major** and names the STAMP's tag exactly;
3. the served constant `backend/src/locveil_voice/core/ws_protocol.py::WS_PROTOCOL_VERSION`
   (sent in every `registered` ack) equals the **major** — a minor or patch cut never changes
   what a fielded device compares.

Cutting a version: edit the artifact(s) + bump `STAMP.json` (`version`, `tag`, `date`) + the
guide's header tag in ONE commit, tag that commit `ws-protocol-vX.Y.Z`, push commit and tag
together (STAMP + tag are the only version authority — no prose version history). Consumers:
the satellite runner (`backend/src/locveil_voice/satellite/link.py`), the future ESP32 firmware, and
locveil-commons' `ws_audio_provider`; `../locveil-satellite` pins this contract
(`contracts/pins/ws-protocol/`) and reports `protocol_version` at register.
