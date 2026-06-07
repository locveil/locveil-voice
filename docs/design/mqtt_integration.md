# Smart-home integration design (ARCH-7 / ARCH-8)

**Status:** design AGREED 2026-06-06. The Irene-side design and the cross-project bridge contract are
both reconciled — see
[`voice_integration_contract_draft.md`](../../../wb-mqtt-bridge/docs/voice_integration_contract_draft.md)
(status AGREED 2026-06-06) in the sister repo for the definitive bridge shape. **ARCH-8 is
unblocked**; implementation sliced in §10.

> Supersedes `docs/archive/intent_mqtt.md` (the v13-era "MQTT intent handler with runtime method
> generation" design — explicitly rejected, see §2).

> **⚠️ RECONCILED with the I/O architecture (ARCH-15) — read §13 before implementing ARCH-8.** The
> hexagon below (§3–§7) predates the symmetric I/O design (`io_architecture.md`). The smart-home flows
> are unchanged in spirit, but the *seam shapes* are now expressed as **`OutputPort`s on the OutputManager**,
> not a bespoke `ActuationPort`: bridge actuation is a **request/response `OutputPort`** returning the rich
> `DeliveryResult` (echo/error), `device_command` is a delivery **modality**, Flow 1 is a terminal
> `OutputPort`, and `DeviceCatalogPort` stays a read port. §13 is the authoritative contract ARCH-8 builds
> against; where §3–§10 differ, §13 wins.

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
  domain resolves it to a canonical `DeviceCommand`; ~~an `ActuationPort` carries it~~ → **(§13) the
  OutputManager carries it to the bridge `OutputPort`** as a `device_command`-modality result; the
  bridge-client adapter POSTs it to the bridge; the bridge translates + actuates. This is the WB7 use
  case and the substrate **QUAL-35** (T2/T3 device NLU) builds on. **Goes via the bridge over REST**, not raw MQTT.
- **Flow 1 — content-agnostic output (secondary, deferred).** Ship an `IntentResult` to a non-audio
  sink (announce a response, publish "timer fired" as an event). **(§13)** a terminal `OutputPort`
  (`EVENT` modality) on the OutputManager — domain-unaware; gated by config. Defined here for
  completeness; **low priority, no confirmed consumer yet**, raw-MQTT (not the bridge). See §7.

These are **separate seams** — do not fuse them. **(§13) both are now `OutputPort`s on the one
OutputManager**, distinguished by modality (`device_command` request/response vs `event` terminal), not
by being separate port *types*.

## 4. Hexagonal placement (Irene side)

> **⚠️ (§13) This diagram predates the I/O architecture and is OBSOLETE on the actuation side.** There is
> no separate `ActuationPort`/`ActuationService`: the **bridge is an `OutputPort`** (`BridgeClient`)
> registered + `designate(DEVICE_COMMAND,"bridge")` on the OutputManager; the handler emits a
> `device_command` result and awaits the OutputManager's rich `DeliveryResult`. `DeviceCatalogPort`
> (read/query) and `DeviceCommand` (domain type) below are unchanged. See §13 for the live shape.

```
DOMAIN        device IntentHandler ──resolves utterance──▶ DeviceCommand (canonical, convention-blind)
  │                  │ depends on (ABC, intents/ports.py — the QUAL-24 pattern)
PORTS         DeviceCatalogPort (read)        [actuation: bridge OutputPort — §13, not a port here]
  │                  │ implemented inward by (application components import nothing outward)
APPLICATION   CatalogService
  │                  │ holds
ADAPTERS      providers/outputs/bridge: BridgeClient — an OutputPort (§13), POST canonical action (Flow 2)
                   └─ GET catalog/rooms/capabilities (startup pull → DeviceCatalog; CatalogService)
```

- **`DeviceCommand`** (new domain type, `irene/intents/`): `room_or_device_ref`, `capability`,
  `action`, `params: dict`. No topic, no broker, no native command name. This is the
  "domain-typed command, never a topic" boundary. _(Unchanged by §13.)_
- ~~**`ActuationPort`** (ABC)~~ → **(§13) DROPPED.** The bridge is an `OutputPort` (`core/interfaces/output.py`);
  device handlers emit a `device_command` result and await the OutputManager delivery — no bespoke actuation port.
- **`DeviceCatalogPort`** (ABC in `intents/ports.py`): the QUAL-24 read-port pattern — handlers depend on it; the
  application `CatalogService` inherits + injects it inward. _(Unchanged by §13 — it's a read/query port, not output.)_
- **`BridgeClient`** adapter under the `irene.providers.outputs` entry-point group: owns the HTTP
  client, base URL/auth, retries, and the REST contract with the bridge. **(§13) implements `OutputPort`**
  and returns the rich `DeliveryResult` (echo/error). The **only** module that knows the bridge exists.
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
        ──▶ DeviceCommand ──[§13: device_command modality ▶ OutputManager ▶ bridge OutputPort]──▶ BridgeClient ──▶ bridge ──▶ speak CommandResponse
```
> _§13 update: the `DeviceCommand → ActuationPort → BridgeClient` hop shown above is superseded — the
> handler emits a `device_command`-modality result that the OutputManager capability-routes to the
> designated bridge `OutputPort` (the `BridgeClient`), awaiting its rich `DeliveryResult`. Same effect,
> one delivery abstraction._

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

A **terminal `OutputPort` carrying `OutputModality.EVENT`** (a raw-MQTT `providers/outputs/mqtt` adapter
publishing e.g. `irene/{room}/event`), capability-routed to a designated output by the OutputManager.
Domain-unaware; gated by config. **Deferred** — no confirmed consumer yet; defined so the output seam is
complete and Flow 2 isn't mistaken for it. If/when a consumer appears, it lands as its own small slice.

> _§13 update: originally framed as "a thin OutputPort called by the workflow beside `_handle_tts_output`."
> Under the I/O architecture it is an ordinary OutputManager output (EVENT modality), not a workflow-side
> call — the OutputManager routes to it. (TTS itself remains the workflow's `_handle_tts_output` for the
> sync voice path; the local SPEECH OutputPort, ARCH-15 PR-8, handles deferred speech.)_

## 8. Config + entry-points

- New entry-point group `irene.providers.outputs` (`bridge` for Flow 2; `mqtt` for Flow 1 later).
- **(§13/PR-7 note) `OutputConfig` already exists** — ARCH-15 PR-7 added `[outputs]` (`OutputConfig`:
  `console`/`console_prefix`/`web_push`). ARCH-8 must **not** create a second top-level `OutputConfig`;
  add a **distinct bridge/actuation config** (bridge base URL, auth, request timeout, `enabled`, the
  `bridge/catalog/version` topic) — e.g. a `BridgeConfig` (or `outputs.bridge` sub-config) — registered
  in `auto_registry.py` (Invariant #4) and surfaced in `config-master.toml`.
- No new heavy deps for Flow 2 (an async HTTP client; `aiohttp` is already in core). Flow 1's raw-MQTT
  adapter would add an MQTT client lib when built.

## 9. Failure modes (fail-loud, not fail-fatal)

- **Bridge down at boot:** empty DeviceCatalog. Device commands clarify-or-fail gracefully (QUAL-30);
  the rest of the assistant is unaffected. Never block startup on the bridge.
- **Bridge down at actuation:** **(§13)** the bridge `OutputPort.deliver()` returns a failed/dropped
  `DeliveryResult` (with `error_code`); the handler composes a spoken apology; no crash. (Bounded-await
  timeout → degraded "не уверен, выполнилось ли".) The QUAL-27 data-contract rule (a failed result
  carries a reason) applies. _(Was: "`ActuationService` returns a failed result" — no ActuationService now.)_
- **Unknown device/room/capability:** resolution fails → clarification ("какое устройство?"), not a
  silent no-op.

## 10. PR slicing (ARCH-8 implementation)

> **⚠️ (§13.6) Slice deltas:** PR-1 **drops the `ActuationPort` ABC** (the bridge is an `OutputPort`); PR-2's
> `BridgeClient` **implements `core/interfaces/output.OutputPort`** + returns the rich `DeliveryResult` and
> **registers + `designate(DEVICE_COMMAND,"bridge")`** on the OutputManager; the reference handler (PR-4)
> **emits a `device_command` result and awaits the OutputManager delivery** (bounded). ARCH-8 builds on the
> already-landed PR-2/PR-5a/D-2 of ARCH-15. The slice *sequence/scope* below stands; the seam shapes follow §13.

Aligned with the **agreed vertical slice**: prove the whole stack against one live command —
**"включи свет в детской"** (one `wb-mr6c` channel, children's room) — before breadth. PR-1 is
adapter-free (fake bridge) so it lands **now**, before/parallel to the bridge's vertical slice;
PR-2+ integrate against the live `/system/catalog` + `/devices/{id}/canonical` as they come online.

- **PR-1** — `DeviceCommand` domain type (capability vocab §6) + `DeviceCatalogPort` (read ABC, QUAL-24
  pattern) + `CatalogService`; import-linter clean. Unit-tested against a fake bridge. **Unblocked now.**
  _(§13.6: no `ActuationPort`/`ActuationService` — the bridge is an `OutputPort`.)_
- **PR-2** — `BridgeClient` **`OutputPort`** adapter (returns rich `DeliveryResult`) + `irene.providers.outputs`
  group + config/schema + startup pull of `GET /system/catalog` → `DeviceCatalog` + subscribe
  `bridge/catalog/version` → re-pull; **registered + designated for `DEVICE_COMMAND` on the OutputManager**.
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

## 13. Reconciliation with the I/O architecture (ARCH-15) — the contract ARCH-8 builds against

Added 2026-06-07 (ARCH-15 PR-9.1). The smart-home *flows* (§3–§7) are unchanged; their *seam shapes* are
re-expressed under the symmetric I/O design (`io_architecture.md`, decisions D-2/D-6). **Where §3–§10 differ
from this section, this section wins.** The bridge contract (§5) and the catalog/resolution model are unaffected.

**13.1 Bridge actuation = a request/response `OutputPort` (not a bespoke `ActuationPort`).**
`OutputPort.deliver(result, context, modality) -> DeliveryResult` is the one delivery abstraction
(`core/interfaces/output.py`, PR-2). The bridge is an OutputPort whose `DeliveryResult` is **rich** —
`{success, echoed_value, error_code}` carries the ~500 ms synchronous value-echo + the 6-code error enum (§5b).
So **`ActuationPort` collapses into the bridge `OutputPort`**; there is no second port shape. The `BridgeClient`
REST adapter *is* that OutputPort, under the already-named `irene.providers.outputs` entry-point group, and it is
**registered + `designate(DEVICE_COMMAND, "bridge")`** on the process-wide `OutputManager` (built by composition,
PR-5a).

**13.2 `device_command` is a delivery modality (D-2).** `OutputModality.DEVICE_COMMAND` already exists (PR-2).
A device handler emits a `device_command`-modality result; the OutputManager **capability-routes it to the single
designated** bridge output (no fan-out → no double-actuation). The handler **awaits the rich `DeliveryResult`
in-turn under a bounded timeout** (timeout → degraded confirmation "не уверен, выполнилось ли" rather than blocking)
and composes the **origin-paired** spoken/text confirmation from it (success → "включаю свет"; `error_code` →
mapped phrase; `param_invalid` → clarify). So an actuation intent emits **two** outputs: the `device_command` to
the bridge (awaited) + the conversational confirmation to the origin channel.

**13.3 `DeviceCatalogPort` stays a read port (unchanged).** The startup catalog pull (`GET /system/catalog`, §5a)
and `bridge/catalog/version` refresh are an **input/query** dependency, not delivery — `DeviceCatalogPort` and the
in-memory `DeviceCatalog` are *not* OutputPorts and are untouched by this reconciliation.

**13.4 Flow 1 (content-agnostic event) = a terminal `OutputPort` (EVENT modality).** The deferred raw-MQTT
`irene/{room}/event` sink (§7) is an ordinary OutputPort carrying `OutputModality.EVENT`, capability-routed to a
designated output. It is a true OutputManager output (terminal — trivial ack `DeliveryResult`), distinct from the
request/response bridge output of 13.1. Remains deferred (no confirmed consumer).

**13.5 Observability + addressing (free under the I/O design).** Because actuation now flows through the
OutputManager, the `device_command` + its echo are published on the pipeline **event bus** → visible to the
`/ws/observe` debug tap (PR-6b). Delivery/confirmation addressing reuses `resolve_physical_id` (room/device
identity) exactly like every other channel — no MQTT-specific addressing scheme.

**13.6 ARCH-8 slice deltas (vs §10).** §10's slices stand, with these substitutions: **PR-1** keeps `DeviceCommand`
+ `DeviceCatalogPort` + application services, but **drops the `ActuationPort` ABC** (the bridge is an `OutputPort`);
**PR-2's `BridgeClient`** implements `core/interfaces/output.OutputPort` + returns the rich `DeliveryResult`, and
the slice **registers + designates** it on the OutputManager; **PR-4's** reference handler emits a `device_command`
result and awaits the OutputManager delivery (bounded) rather than calling a bespoke port. ARCH-8 therefore builds
on PR-2 (`OutputPort`/`DeliveryResult`), PR-5a (process-wide OutputManager), and D-2 (designated routing) — all
already landed.
