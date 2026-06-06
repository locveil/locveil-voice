# Smart-home integration design (ARCH-7 / ARCH-8)

**Status:** design AGREED 2026-06-06. The Irene-side design and the cross-project bridge contract are
both reconciled — see
[`voice_integration_contract_draft.md`](../../../wb-mqtt-bridge/docs/voice_integration_contract_draft.md)
(status AGREED 2026-06-06) in the sister repo for the definitive bridge shape. **ARCH-8 is
unblocked**; implementation sliced in §10.

> Supersedes `docs/archive/intent_mqtt.md` (the v13-era "MQTT intent handler with runtime method
> generation" design — explicitly rejected, see §2).

---

## 1. The decision in one line

**Irene does not own smart-home device knowledge or MQTT conventions.** The sister project
**`wb-mqtt-bridge` is the single device authority**; Irene is a pure voice front-end that (a) pulls a
device/room/capability **catalog** from the bridge on startup and (b) sends **canonical device
commands** to the bridge, which translates them to native commands and the right MQTT/transport
convention. Irene speaks one small canonical vocabulary end-to-end and is blind to wb-rules vs Home
Assistant vs anything else.

```
  utterance ──▶ Irene (NLU + resolution) ──canonical DeviceCommand──▶ wb-mqtt-bridge ──▶ {native WB | AV | HA later}
                     ▲                                                      │
                     └────────────── catalog pull (devices/rooms/caps) ◀────┘
```

## 2. Why — and what this rejects

The real deployment is one Wirenboard 7 controller that is **both the MQTT broker and the home**.
Everything lives on its broker under the WB convention `/devices/{dev}/controls/{ctrl}`:

- **Native WB gear** (managed by `wb-mqtt-serial` + `wb-rules`, *not* in wb-mqtt-bridge today): lights
  & dimmers (`wb-mr6c`, `wb-mdm3`, `wb-mrgbw-d`), curtains (`dooya`), HVAC, per-room multi-sensors
  (`wb-msw-v3`), metering, leak. Control names are hardware-technical; there is no device-type
  taxonomy, capability model, or room mapping in the raw topic tree.
- **wb-mqtt-bridge's virtual devices** (AV gear with no native WB support): TVs, Apple TVs, eMotiva —
  published onto the *same* broker, but *with* rich capability maps + param schemas + rooms.

Two rejected alternatives:

- **Irene → raw broker directly.** Irene would re-implement the device/capability/room model
  wb-mqtt-bridge already has, only for the native half, against a semantically poor topic tree, with a
  large hand-authored overlay. Two fidelity levels, duplicated modeling, Irene shaped to one vendor.
- **The archived `intent_mqtt.md` design** (fat `MQTTDynamicHandler` owning an MQTT client + HA
  discovery + **runtime Python method generation** inside an intent handler). This fuses domain +
  transport + a discovery subsystem into a vertical silo — the opposite of the hexagon, and the
  QUAL-era "generate it at runtime" anti-pattern. Dropped entirely.

The chosen split puts device knowledge and convention-handling in the project **built** for it
(wb-mqtt-bridge is a hexagonal device-control bridge with capability maps), and keeps Irene a thin,
convention-agnostic voice layer. The agnosticism boundary moves to the correct place: **the bridge
owns conventions; Irene owns voice.**

## 3. Two output flows (the seam, named)

MQTT/the bridge surfaces in two architecturally different places. Naming them keeps the design honest:

- **Flow 2 — actuation (primary).** "Включи свет в гостиной." The intent *is* device control. The
  domain resolves it to a canonical `DeviceCommand`; an `ActuationPort` carries it; the bridge-client
  adapter POSTs it to the bridge; the bridge translates + actuates. This is the WB7 use case and the
  substrate **QUAL-35** (T2/T3 device NLU) builds on. **Goes via the bridge over REST**, not raw MQTT.
- **Flow 1 — content-agnostic output (secondary, deferred).** Ship an `IntentResult` to a non-audio
  sink (announce a response, publish "timer fired" as an event). The exact analog of
  `_handle_tts_output` — workflow-driven, parallel to TTS, domain-unaware. Defined here for
  completeness; **low priority, no confirmed consumer yet**, raw-MQTT (not the bridge). See §7.

These are **separate seams with separate adapters** — do not fuse them.

## 4. Hexagonal placement (Irene side)

```
DOMAIN        device IntentHandler ──resolves utterance──▶ DeviceCommand (canonical, convention-blind)
  │                  │ depends on (ABC, intents/ports.py — the QUAL-24 pattern)
PORTS         ActuationPort          DeviceCatalogPort                 OutputPort (Flow 1)
  │                  │ implemented inward by (application components import nothing outward)
APPLICATION   ActuationService ─────────┐         CatalogService
  │                                      │ holds                  │ holds
ADAPTERS      providers/outputs/bridge:  BridgeClient (REST)      └─ providers/outputs/mqtt (Flow 1)
                   ├─ GET  catalog/rooms/capabilities  (startup pull → DeviceCatalog)
                   └─ POST canonical action            (Flow 2 actuation)
```

- **`DeviceCommand`** (new domain type, `irene/intents/`): `room_or_device_ref`, `capability`,
  `action`, `params: dict`. No topic, no broker, no native command name. This is the
  "domain-typed command, never a topic" boundary.
- **`ActuationPort`** / **`DeviceCatalogPort`** (ABCs in `intents/ports.py`): the QUAL-24 pattern —
  device handlers depend only on these; the application `ActuationService`/`CatalogService` inherit
  them and inject inward (components import nothing → no new edges; enforced by the import-linter).
- **`BridgeClient`** adapter under a new `irene.providers.outputs` entry-point group: owns the HTTP
  client, base URL/auth, retries, and the REST contract with the bridge. The **only** module that
  knows the bridge exists.
- **DeviceCatalog** (in-memory, built from the startup pull): the device/room/capability/param model
  the NLU and `DeviceEntityResolver` consume — this is what turns today's all-`generic` `entity_type`
  into real `device`/`room` entries (the ARCH-6/QUAL-35 device-half substrate).

`DeviceCatalog` is **not** `ClientRegistry`. ClientRegistry = what's physically wired to a given ESP32
satellite (room context for *a microphone*). DeviceCatalog = everything actuable in the house. They
intersect on **room** (both carry room names) but serve different jobs; the catalog references rooms
the bridge defines.

## 5. The Irene ↔ bridge contract (AGREED)

Three interactions, all **REST** (synchronous responses give Irene a result to *speak*). The agreed
shapes (definitive spec in the bridge draft):

### 5a. Read — catalog pull (`GET /system/catalog`, startup)

One dedicated, flat, capability-shaped endpoint — **not** the Layer-3 layout manifest (that's
UI-oriented). Irene pulls it on boot and builds the DeviceCatalog:

```jsonc
{ "version": "<content-hash>",
  "rooms":   [ {"id":"children_room", "names":{"ru":"Детская","en":"Kids Room"}, "devices":["wb-mr6c_47"]},
               {"id":"global",        "names":{"ru":"Весь дом"},                 "devices":["all_lights"]} ],
  "devices": [ {"id":"wb-mr6c_47", "names":{"ru":"Свет в детской","en":"…"}, "class":"WbPassthrough",
                "room":"children_room",
                "capabilities":[ {"name":"power","actions":[{"name":"on"},{"name":"off"}]} ]},
               {"id":"wb-msw-v3_220", "names":{…}, "room":"children_room",
                "capabilities":[ {"name":"sensor","fields":[{"name":"temperature","type":"float","unit":"°C","labels":{…}}]} ]} ] }
```

- **All locales for both rooms and devices** — Irene knows the request language and picks the matching
  label. (`device_name` widened string→`names:{…}` bridge-side; Irene just consumes `names`.)
- **Capability-shaped & matches the write vocabulary**: Irene learns *"wb-mr6c_47, in Детская,
  supports `power`"* and speaks `power.on` back. One vocabulary end to end.
- **Sensors** = one read-only `sensor` capability with `fields` (no actions) — drives the **read**
  flow (§6), not actuation.
- **One device, one room** (`room: Optional[str]` — *tightened from a multi-room draft 2026-06-06*).
  **`global` is a regular room that holds whole-house AGGREGATE devices** (e.g. an `all_lights` device
  that wb-rules on the controller maps to the real per-light fan-out). "Выключи свет везде" resolves to
  such an aggregate device in `global` and fires **one** canonical command (§6). **Irene never iterates
  rooms or synthesizes a group** — group/scene controls are aggregate *devices* in the catalog; Irene
  relies on their availability and just actuates them like any other device.
- **Refresh:** Irene subscribes to retained **`bridge/catalog/version`** (content hash, bumped on
  bridge config change / `/reload`) and re-pulls `/system/catalog` when it changes.

### 5b. Write — canonical actuation (`POST /devices/{id}/canonical`)

```
POST /devices/{device_id}/canonical
  body: { "capability": "power", "action": "on", "params": {} }
  200:  { "success": true,  "device_id", "capability", "action", "state": {…}, "error": null }
  4xx:  { "success": false, "device_id", "error": { "code", "message", "field?", "reason?" } }
```

**Synchronous with a 500 ms value-topic echo** (configurable per driver; covers/curtains declare
longer): the response carries the **post-action state**, so Irene confirms from real state, not hope.

**The 6-code error enum maps straight to spoken feedback** — this is why structured errors matter for
voice:

| `error.code` | HTTP | Irene says (ru, illustrative) |
|---|---|---|
| `device_not_found` | 404 | "Не нашёл такого устройства" (→ clarify) |
| `capability_not_supported` | 404 | "Это устройство так не умеет" |
| `action_not_supported` | 404 | "Не могу это сделать с устройством" |
| `param_invalid` (`field`,`reason`) | 400 | reason-driven (out_of_range → "Яркость от 0 до 100") → clarify/slot-fill |
| `device_unreachable` | 503 | "Устройство не отвечает, попробуйте ещё раз" (transient) |
| `internal_error` | 500 | "Что-то пошло не так" |

Irene's `BridgeClient.actuate(DeviceCommand)` POSTs this and maps `success`/`error.code` to the result
the workflow speaks. `param_invalid.reason ∈ {missing, out_of_range, wrong_type, unknown_choice}`
feeds the clarification/slot-fill path (QUAL-30/31) — though Irene also validates against the catalog
schema *before* the call, so most of these never round-trip.

### 5c. Read — sensor / device state (`GET /devices/{id}/state`)

"Какая температура в детской" is a **read**, not an actuation. Irene resolves room → device with a
`sensor` capability → field → reads the value from the bridge's state cache (`GET /devices/{id}/state`)
and speaks it. (The catalog gives the field *schema*; this gives the live *value*.)

## 6. Resolution flow (utterance → DeviceCommand)

```
ASR text ──▶ NLU (QUAL-35 T2/T3) ──▶ intent: device-control
                                       entities: device/room ref, capability, action, value
        ──▶ DeviceEntityResolver (against DeviceCatalog + room list)
                 ├─ resolve room  ("в гостиной" → room_id via ru names)
                 ├─ resolve device ("телевизор" → device in that room)
                 └─ resolve capability+action ("сделай громче" → volume.up)
        ──▶ validate/clarify params against the catalog schema (QUAL-30 / QUAL-31)
                 ("какую яркость?" when range param missing/out of bounds)
        ──▶ DeviceCommand ──ActuationPort──▶ BridgeClient ──▶ bridge ──▶ speak CommandResponse
```

- **NLU (QUAL-35):** today's T1 NLU can't carry device+room+capability+value. The T2/T3 tiers are the
  paired prerequisite — ARCH-7/8 define the seams; QUAL-35 authors the device handlers + NLU on top.
- **Entity resolution:** the DeviceCatalog populates real `device`/`room`/`location` entities, so the
  `entity_type`-driven resolver swap (relocated from ARCH-6, owned with QUAL-35) finally has substrate
  instead of being an inert branch.
- **Clarification/slot-filling:** the per-param schema from the catalog is exactly what QUAL-30
  (deterministic single-turn) and QUAL-31 (multi-turn slot-filling) need to ask "какую яркость?" and
  validate the answer before publish.

**Canonical capability vocabulary** (agreed; Irene's `DeviceCommand.capability` ∈):
`power`(on/off) · `brightness`(set/up/down) · `color`(set rgb) · `cover`(open/close/stop/set_position) ·
`climate`(set_mode/set_setpoint/set_fan) · `sensor`(read-only fields) · plus the AV set
`volume`/`input`/`playback`/`menu`. Irene never needs the per-device native names — the bridge owns
canonical→native. (The bridge aligns with HA's namespace where it fits, but its config is the truth.)

**Three interaction kinds** the resolver dispatches to:
1. **Actuate** — single device → one `POST …/canonical` (§5b).
2. **Whole-house / group** ("выключи свет везде") — Irene resolves to the matching **aggregate device
   in the `global` room** (e.g. `all_lights`) and fires **one** `…/canonical` call; wb-rules on the
   controller performs the actual per-light fan-out. This is just an `Actuate` (kind 1) against an
   aggregate device — **no client-side fan-out, no N-call partial-failure handling.** Irene relies on
   the aggregate device being **available** in the catalog; if it isn't, the command is unsupported →
   clarify/decline. (Same principle for any room-level group: it's a device the bridge models, not an
   iteration Irene performs.)
3. **Read** ("какая температура…") — `GET /devices/{id}/state` (§5c), speak the value.

## 7. Flow 1 — content-agnostic output (deferred)

A thin `OutputPort` called by the workflow beside `_handle_tts_output`, fanning an `IntentResult` to
enabled non-audio sinks (a raw-MQTT `providers/outputs/mqtt` adapter publishing e.g.
`irene/{room}/event`). Domain-unaware; gated by config like `wants_audio`. **Deferred** — no confirmed
consumer yet; defined so the output seam is complete and Flow 2 isn't mistaken for it. If/when a
consumer appears (an event bus, an announcement speaker), it lands as its own small slice.

## 8. Config + entry-points

- New entry-point group `irene.providers.outputs` (`bridge` for Flow 2; `mqtt` for Flow 1 later).
- `OutputConfig` / `ActuationConfig` in `config/models.py` (bridge base URL, auth, request timeout,
  `enabled`, the `bridge/catalog/version` topic) + a registered schema in `config/schemas.py` +
  `auto_registry.py` (Invariant #4 — the same schema seam ARCH-10 hit). Surfaced in
  `config-master.toml`.
- No new heavy deps for Flow 2 (an async HTTP client; `aiohttp` is already in core). Flow 1's raw-MQTT
  adapter would add an MQTT client lib when built.

## 9. Failure modes (fail-loud, not fail-fatal)

- **Bridge down at boot:** empty DeviceCatalog. Device commands clarify-or-fail gracefully (QUAL-30);
  the rest of the assistant is unaffected. Never block startup on the bridge.
- **Bridge down at actuation:** `ActuationService` returns a failed result with a spoken apology; no
  crash. The QUAL-27 data-contract rule (a failed result carries a reason) applies.
- **Unknown device/room/capability:** resolution fails → clarification ("какое устройство?"), not a
  silent no-op.

## 10. PR slicing (ARCH-8 implementation)

Aligned with the **agreed vertical slice**: prove the whole stack against one live command —
**"включи свет в детской"** (one `wb-mr6c` channel, children's room) — before breadth. PR-1 is
adapter-free (fake bridge) so it lands **now**, before/parallel to the bridge's vertical slice;
PR-2+ integrate against the live `/system/catalog` + `/devices/{id}/canonical` as they come online.

- **PR-1** — `DeviceCommand` domain type (capability vocab §6) + `ActuationPort`/`DeviceCatalogPort`
  (ABCs, QUAL-24 pattern) + the application services; import-linter clean. Unit-tested against a fake
  bridge. **Unblocked now.**
- **PR-2** — `BridgeClient` REST adapter + `irene.providers.outputs` group + config/schema + startup
  pull of `GET /system/catalog` → `DeviceCatalog` + subscribe `bridge/catalog/version` → re-pull.
  Validated against a recorded catalog, then the live bridge slice.
- **PR-3** — wire `DeviceCatalog` into `DeviceEntityResolver` (real `device`/`room` entities, ru-name
  room match) — the ARCH-6 device-half activation, with QUAL-35.
- **PR-4** — reference device handler end-to-end: "включи свет в детской" → `power.on` →
  `POST …/canonical` → 500 ms echo → spoken confirm. Includes the error-code→speech mapping (§5b) and
  the `param_invalid`→clarify path. Broad device coverage + T2/T3 NLU = QUAL-35.
- **PR-5** — sensor **read** flow (`sensor` capability → `GET /devices/{id}/state`). (No "everywhere"
  fan-out work: whole-house "выключи свет везде" is just an `Actuate` against the `global` `all_lights`
  aggregate device — covered by PR-4's actuation path; it only needs that device to exist in the catalog.)
- **(later)** — Flow 1 OutputPort + raw-MQTT adapter, if/when a consumer appears; batched room/group
  endpoint (bridge v2) only if N-call latency hurts.

## 11. Resolved in the bridge session (2026-06-06)

All ARCH-7 open questions are now settled in the AGREED contract:

1. **Canonical endpoint** → `POST /devices/{id}/canonical {capability, action, params}`, thin façade
   over the reconciler; 6-code structured error enum (§5b); 500 ms synchronous value-topic echo,
   per-driver configurable.
2. **Catalog read** → dedicated **`GET /system/catalog`** (not the Layer-3 manifest); flat,
   capability-shaped, **all locales** for rooms *and* devices; one read-only `sensor` capability;
   **one device / one room** (`room: Optional[str]`). Refresh via retained **`bridge/catalog/version`**.
3. **Native onboarding** (bridge-side) → generic data-driven `WbPassthroughDevice` driver +
   capability-adapter composition layer (RGB/HVAC) + new caps `brightness`/`color`/`cover`/`climate`/
   `sensor`; wb-rules stays on the controller, the bridge **mirrors** state (loop-guarded).
4. **Rooms** → `rooms.json` bootstrapped from WB HomeUI; **ru name is the resolution key**; one device
   belongs to exactly one room; **`global` is a regular room holding whole-house aggregate devices**
   (e.g. `all_lights`). "Выключи свет везде" → Irene fires **one** canonical command at that aggregate
   device; it never iterates rooms or synthesizes a group (§6).

Deferred to bridge **v2**: a batched room/group actuation endpoint (Irene does N client-side calls
for v1).

## 12. Cross-project tracking

- **Irene side:** ARCH-7 (this design) → ARCH-8 (implement, §10) + QUAL-35 (device NLU + handlers).
- **Bridge side:** tracked in `wb-mqtt-bridge/docs/action_plan.md`; the requirements are drafted in
  `wb-mqtt-bridge/docs/voice_integration_contract_draft.md` for the bridge session. ARCH-8 is blocked
  on that work.
