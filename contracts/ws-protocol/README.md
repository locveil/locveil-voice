# ws-protocol — the WebSocket wire protocol (owned)

The normative artifact **lives at [`docs/guides/websocket-api.md`](../../docs/guides/websocket-api.md)**
(`ws-protocol-doc-canonical` — a hand-written reference that doubles as the user guide; owned
surfaces that legitimately live elsewhere keep their home, per
`../locveil-commons/process/contracts.md` §2). This folder holds the version authority and, since
`ws-protocol-v1.1.0`, the protocol's **machine core**.

## The machine core

Hand-written data for test harnesses — the firmware's conformance test, the eval WS provider:

| File | Slice |
|---|---|
| `frames.golden.json` | every JSON frame: key lists, JSON types, valid / invalid / unknown-type cases |
| `transcript.<scenario>.jsonl` (nine) | one recorded conversation per file, binary runs as markers |
| `ws-protocol.schema.json` | JSON Schema 2020-12, one `$defs` entry per frame and per channel/direction |

**The core is subordinate to the document.** On disagreement the document wins and the core is
fixed. It is never generated from code: no script writes or refreshes these files. A wire change
updates the document and the core in the same change. The file format, the receiver obligations
and the transcript rules are described in the guide's section "The machine-readable core" — and
only there, because the pinned guide is the one document a consumer holds.

`backend/tests/test_ws_machine_core.py` is the owner test. It re-runs the WS suites in a child
pytest process with a frame tap on the server side of the socket (`backend/tests/ws_frame_tap.py`)
and fails when the core disagrees with what the real handlers did, with itself, with the schema,
or with the guide:

| Leg | Asserts |
|---|---|
| L1 | the fixtures obey their own definitions and the naming rule |
| L2 | document ≡ core: every frame the guide shows is valid, its frame table equals the definitions, it names every key the files use, it lists exactly the enumerated files |
| L3 | every frame the server sent is a strictly valid instance of a defined frame |
| L4 / L4b | every frame was witnessed on a real socket and the fixture values are real; every handshake case is replayed against the real handlers |
| L5 / L6 | transcripts are well-formed, the rules hold on every recorded connection, each transcript equals a real recording |
| L7 | the schema mirrors the definitions and accepts every real frame |

A red leg is fixed in this order: the document, then the core, then the code.

## Versions

**Every file above and the guide are enumerated** in `STAMP.json` → `artifacts`: that list is what
consumers pin (flat — unique file names) and what the contract guard byte-locks. Any edit to any
of them — a wire change, a corrected case, a typo — is a version move, cut in the same change.

Versions have three levels (`process/contracts.md` §3):

| Level | When | Served `protocol_version` |
|---|---|---|
| major | a breaking wire change | moves — it IS the major |
| minor | the surface changed additively: a new optional field or frame; a case, transcript or file added; a case corrected (anything a conformance harness can observe) | unchanged |
| patch | enumerated bytes moved and no harness can tell (an editorial fix to the guide, a case's `note`, STAMP metadata) | unchanged |

Inside a major, file names, frame names, case ids and transcript names are never renamed or
removed; a case that should no longer be asserted is marked `"retired": true`.

`backend/tests/test_ws_protocol_version.py` keeps the version legs in agreement:

1. `STAMP.json` is the authority — a three-part `version`, `tag` = `ws-protocol-v<version>`;
2. the guide's "Protocol version" header line shows the **major** and names the STAMP's tag exactly;
3. the served constant `backend/src/locveil_voice/core/ws_protocol.py::WS_PROTOCOL_VERSION`
   (sent in every `registered` ack) equals the **major** — a minor or patch cut never changes
   what a fielded device compares.

Cutting a version: edit the artifact(s) + bump `STAMP.json` (`version`, `tag`, `date`; a new file
is added to `artifacts`) + the guide's header tag + the registry row in ONE commit, tag that commit
`ws-protocol-vX.Y.Z`, push commit and tag together (STAMP + tag are the only version authority —
no prose version history). Consumers: the satellite runner
(`backend/src/locveil_voice/satellite/link.py`), the ESP32 firmware and locveil-commons'
`ws_audio_provider`; `../locveil-satellite` pins this contract (`contracts/pins/ws-protocol/`) and
reports `protocol_version` at register.
