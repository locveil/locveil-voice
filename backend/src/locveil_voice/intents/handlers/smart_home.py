"""Smart-home device handler (ARCH-8 PR-4 + QUAL-35 T1) — utterance → canonical command → speech.

The reference handler of the vertical slice: it turns a resolved smart-home intent into ONE
canonical command on the Irene↔bridge boundary and speaks the rich delivery outcome.

Address-form routing follows the depth doctrine (`canonical_first.md` §10, VWB-23): resolve only
as deep as the utterance specifies.

- A **group noun** («свет», «шторы», «жалюзи» — the donation's `group_noun` CHOICE, whose
  canonical values ARE catalog `CatalogCapability.group` names) → a **room-group command**
  `{room, group, action, scope}`; the BRIDGE picks the device via its `group_defaults`.
  Singular → `scope: auto`; «весь»/«все» → `scope: all` (force fan-out).
- A **named device** (the `target` param, resolved by the catalog-backed resolver, PR-3) → a
  **device command** `{device_id, capability, action, params}`. Scenarios ride this form.
- **No target at all** («поставь на паузу», «поставь 22 градуса») → capability lookup in the
  request room: one capable device → device form; several → clarification (F20/F21, the v1
  policy — priorities are QUAL-63).

Everything spoken comes from `assets/templates/smart_home/`; the §5b error-code enum maps to
phrases, `param_invalid`/ambiguity arm a one-shot clarification (QUAL-30/31), and a room-group
delivery speaks its per-member aggregate incl. partial failures («…, бра не ответило» — §10.4).

Dependencies (injected, QUAL-24): `DeviceCatalogPort` (the world) +
`DeviceCommandDeliveryPort` (awaited delivery). No HTTP, no bridge knowledge here.
"""

import asyncio
import dataclasses
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from ..models import Intent, IntentResult
from ..context_models import UnifiedConversationContext
from ..device_catalog import CatalogDevice, DeviceCatalog
from ..device_commands import (
    CanonicalCommand,
    DeviceCommand,
    GroupScope,
    RoomGroupCommand,
    is_slow_action,
    published_wait_ms,
    size_request_timeout,
)
from ..ports import DeviceCatalogPort, DeviceCommandDeliveryPort, ScenarioJobEventsPort
from ..scenario_jobs import (
    STALE_RESUME_S,
    JobEvent,
    JobEventKind,
    JobFailure,
    JobLookup,
    JobLookupMiss,
    JobRecord,
    ceiling_bucket,
    hard_cap_seconds,
    remaining_seconds,
    watchdog_seconds,
)
from .base import IntentHandler
from ...core.client_registry import resolve_physical_id
from ...core.donations import MissingRequiredParameter
# the ONE surface-normalization + RU-stem truth — shared with the catalog resolver so a value
# matched here behaves identically to a device name matched there
from ...core.entity_resolver import _norm, _stem_match, _MORPH_FUZZ_THRESHOLD, _STEM_MATCH_SCORE
from ...utils.text_normalizers import latin_to_cyrillic_hint
from ...utils.text_processing import plural_form

# «весь свет» / «все шторы» — the plural/total signal → scope: all (VWB-23)
_ALL_SCOPE_RE = re.compile(r"\b(?:весь|все|всё|everywhere|all)\b", re.IGNORECASE)

# read quantities → the catalog field names that carry them, preference-ordered (PR-5).
# `room_temperature` is the measured value on climate/HVAC devices; bare `temperature` is the
# dedicated sensors' field (shower_sauna_sensors), where it IS the measurement — keep it first.
# (Pre-DRV-28 the AC advertised a `temperature` field that was its SETPOINT, so «какая
# температура» in an AC room answered the set target; the DRV-28 rename to `setpoint` retired
# that wrong answer without a voice change.)
_QUANTITY_FIELDS = {
    "temperature": ("temperature", "room_temperature"),
    "humidity": ("humidity",),
}

# BUG-37: the unit-forms template key each read speaks its value with
_QUANTITY_UNIT_KEY = {
    "temperature": "unit_degrees",
    "humidity": "unit_percent",
}

# ARCH-67: the final result's metadata key carrying the acknowledgement spoken mid-turn
ACKNOWLEDGEMENT_METADATA_KEY = "acknowledgement"

# ARCH-67: `set*` on these speaks «ставлю» (a value), on anything else «переключаю» (a choice)
_VALUE_CAPABILITIES = frozenset({"temperature", "climate", "brightness", "cover", "volume"})

# ARCH-69: the final result's metadata key carrying the accepted job (id, room, ceiling)
SCENARIO_JOB_METADATA_KEY = "scenario_job"
# the one-per-room durable action name — the bridge's room id is the lock key (design §3)
SCENARIO_JOB_ACTION_PREFIX = "scenario_job:"


@dataclasses.dataclass
class RunningJob:
    """The handler's in-memory index entry for a room's running job (design §3): what the
    durable record persists, kept beside it so "voice owns the room's record" is one lookup."""
    job_id: str
    room_id: str
    kind: str                    # "switch" | "stop"
    target: str                  # scenario id, or "none"
    label: str                   # spoken name, request language (resolved at launch)
    max_duration_ms: int
    accepted_at: float

# capability each method actuates, in preference order when a device carries several
_METHOD_CAPABILITY = {
    "power": ("power", "climate", "fan", "playback"),
    "cover": ("cover",),
    "climate": ("climate",),
    "brightness": ("brightness",),
    "playback": ("playback",),
    "scenario": ("scenario",),
}


class SmartHomeIntentHandler(IntentHandler):
    """Actuates the house through the bridge boundary — one utterance, one canonical command."""

    def __init__(self):
        super().__init__()
        self.catalog_port: Optional[DeviceCatalogPort] = None
        self.command_port: Optional[DeviceCommandDeliveryPort] = None
        # ARCH-67 (PROD-18 round 2): the ONE flag — `[outputs.bridge] acknowledge_slow_actions`
        self.acknowledge_slow_actions: bool = True
        # ARCH-69: the scenario-job events port (None = the synchronous ARCH-67 path) + the
        # per-room index of jobs voice follows (bridge room id → RunningJob)
        self.events_port: Optional[ScenarioJobEventsPort] = None
        self._jobs: Dict[str, RunningJob] = {}

    def set_device_command_services(self, catalog_port: DeviceCatalogPort,
                                    command_port: DeviceCommandDeliveryPort,
                                    acknowledge_slow_actions: bool = True) -> None:
        """Application injection (QUAL-24): the catalog world + the awaited delivery seam +
        the acknowledgement policy (one flag, default on)."""
        self.catalog_port = catalog_port
        self.command_port = command_port
        self.acknowledge_slow_actions = acknowledge_slow_actions

    def set_scenario_job_events_port(self, events_port: Optional[ScenarioJobEventsPort]) -> None:
        """Application injection (ARCH-69): the bridge's scenario-job event source. With it
        wired, scenario commands go out as jobs (`wait: false`) and are followed durably."""
        self.events_port = events_port

    async def can_handle(self, intent: Intent) -> bool:
        return intent.domain == "smart_home"

    async def execute(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        result = await self.execute_with_donation_routing(intent, context)
        # ARCH-67: what was acknowledged mid-turn rides the final result's metadata, so a
        # client / the eval / a trace can see that an interim utterance preceded this text
        acknowledged = self._take_acknowledgement(context)
        if acknowledged:
            result.metadata[ACKNOWLEDGEMENT_METADATA_KEY] = acknowledged
        return result

    # --- shared plumbing ---------------------------------------------------------------------

    def _catalog(self) -> Optional[DeviceCatalog]:
        return self.catalog_port.catalog() if self.catalog_port is not None else None

    def _lang(self, context: UnifiedConversationContext) -> str:
        return context.language or "ru"

    def _no_catalog_result(self, language: str) -> IntentResult:
        return IntentResult(text=self._get_template("err_no_catalog", language),
                            should_speak=True, success=False,
                            error="smart home catalog unavailable")

    async def _ask_slot(self, intent: Intent, context: UnifiedConversationContext,
                        param: str) -> IntentResult:
        """Explain-and-ask for one missing slot via the shared QUAL-30 boundary (arms the
        one-shot QUAL-31 resume). The spoken detail comes from this handler's templates."""
        detail = self._get_template(f"slot_{param}", self._lang(context))
        return await self._clarify(intent, context,
                                   MissingRequiredParameter(param, intent.name, detail))

    def _device_name(self, device: CatalogDevice, language: str) -> str:
        return device.names.get(language) or device.names.get("ru") or device.id

    def _unit_form(self, key: str, n: Any, language: str) -> str:
        """BUG-37: the declined unit for numeral `n`, picked from the template's |-separated
        forms («градус|градуса|градусов») — templates carry the language, code picks the form."""
        forms = [f.strip() for f in self._get_template(key, language).split("|")]
        try:
            return plural_form(float(n), forms, language)
        except (TypeError, ValueError):
            return forms[-1]

    @staticmethod
    def _speakable_number(n: Any) -> Any:
        """Integral floats speak (and read) as integers: 22.0 → 22 (BUG-37)."""
        if isinstance(n, float) and n == int(n):
            return int(n)
        return n

    def _room_spoken_name(self, catalog: DeviceCatalog, room_id: str, language: str) -> str:
        room = catalog.room(room_id)
        if room is None:
            return room_id
        return room.names.get(language) or room.names.get("ru") or room.id

    def _group_noun_surface(self, intent: Intent, group: str, language: str) -> str:
        """The word the user actually said for the group («жалюзи», not "cover") — recovered
        from the donation's choice_surfaces; falls back to the first declared surface."""
        spec = self._find_param_spec(intent, "group_noun")
        surfaces = (spec.choice_surfaces or {}).get(group, []) if spec else []
        text_norm = intent.raw_text.lower()
        for surface in surfaces:
            if re.search(rf"\b{re.escape(surface.lower())}\w*", text_norm):
                return surface
        return surfaces[0] if surfaces else group

    def _verified_group_noun(self, intent: Intent) -> Optional[str]:
        """The extracted group noun, kept only if one of its surfaces stands as a word in the
        utterance — the CHOICE fuzzy match alone would let «подсветка потолка» (a NAMED accent
        light) trigger the light group and break the depth doctrine."""
        group = self.get_param(intent, "group_noun", None)
        if not group:
            # Raw NLU tiers (QUAL-50 LLM) copy the spoken noun verbatim into `target` — «выключи
            # свет» arrives as target="свет", never as the donation CHOICE param. Re-read the
            # target as a group noun when it IS one; the surface-in-utterance verification below
            # still gates it, so a named device can't be demoted to its group.
            group = self._group_for_surface(self.get_param(intent, "target", None), intent)
        if not group:
            return None
        spec = self._find_param_spec(intent, "group_noun")
        surfaces = list((spec.choice_surfaces or {}).get(group, [])) if spec else []
        surfaces.append(group)  # the canonical is self-matchable (en: "light")
        text_norm = intent.raw_text.lower()
        for surface in surfaces:
            if re.search(rf"(?:^|\s){re.escape(surface.lower())}(?:\s|$)", text_norm):
                return group
        return None

    def _group_for_surface(self, value: Optional[Any], intent: Intent) -> Optional[str]:
        """The group whose declared surface (or canonical) equals `value` word-for-word —
        «свет» → light, «шторы» → cover. None for anything that isn't a bare group noun."""
        if not value or not isinstance(value, str):
            return None
        spec = self._find_param_spec(intent, "group_noun")
        if spec is None:
            return None
        needle = value.strip().lower()
        for group, surfaces in (spec.choice_surfaces or {}).items():
            if needle == group.lower() or any(needle == s.lower() for s in surfaces):
                return group
        return None

    def _requested_room(self, intent: Intent, context: UnifiedConversationContext,
                        catalog: DeviceCatalog) -> Tuple[Optional[str], Optional[IntentResult]]:
        """The room the command addresses: the mentioned room (already resolved by PR-3's
        D-15 pass) or the client's room. Returns (room_id, error_result)."""
        language = self._lang(context)
        # the raw extracted room word (donation param `room`) — its RESOLVED form is what we
        # consume below; kept here for the miss log so an unmatched room isn't silently dropped
        raw_room = self.get_param(intent, "room", None)
        if intent.entities.get("room_resolution_type") == "uncovered_room":
            resolved = intent.entities.get("room_resolved") or {}
            return None, IntentResult(
                text=self._get_template("err_uncovered_room", language,
                                        room=resolved.get("name", "")),
                should_speak=True, success=False, error="room not covered by this device")
        resolved = intent.entities.get("room_resolved")
        if isinstance(resolved, dict) and resolved.get("room_id"):
            return resolved["room_id"], None
        if raw_room:
            self.logger.debug(f"room word '{raw_room}' did not resolve to a catalog room; "
                              f"falling back to the client's room")
        room_name = context.get_room_name()
        if room_name:
            from ...core.entity_resolver import match_catalog_room
            room = match_catalog_room(room_name, catalog, language)
            if room is not None:
                return room.id, None
        return None, None

    # --- delivery + speech ---------------------------------------------------------------------

    async def _deliver(self, command: CanonicalCommand,
                       context: UnifiedConversationContext) -> Optional[Any]:
        """Size the request from the catalog's published timing, acknowledge a slow action
        before it goes out, then await the honest outcome (ARCH-67; PROD-18 round 2, decision 8).

        - `published_wait_ms` reads what the bridge promises to wait for THIS command (a
          capability's `confirm_timeout_ms`, a scenario value's `max_duration_ms`); the request
          timeout is `× 1.25 + 2 s` above it. Nothing published → the command carries no
          timeout and the delivery layer applies the configured fallback.
        - Above ~3 s the user hears an immediate «включаю»-class acknowledgement — a statement of
          intent, never of success — on the request's own channel, then the confirmation or
          failure exactly as before. One flag turns the acknowledgement off; the sizing stays.
        """
        if self.command_port is None:
            return None
        catalog = self._catalog()
        bound_ms = published_wait_ms(catalog, command) if catalog is not None else None
        if bound_ms is not None:
            command = dataclasses.replace(command, timeout_seconds=size_request_timeout(bound_ms))
            # ARCH-69: a job request (`wait: false`) is acknowledged by the turn's own reply
            # once the 202 lands (with the ceiling) — not mid-turn
            if (self.acknowledge_slow_actions and is_slow_action(bound_ms)
                    and getattr(command, "wait", None) is not False):
                await self._acknowledge(command, context)
        return await self.command_port.deliver_device_command(command, context)

    def _ack_template_key(self, command: CanonicalCommand) -> str:
        """The action family's acknowledgement («включаю» for power on, «запускаю сценарий»…)."""
        capability = command.capability if isinstance(command, DeviceCommand) else command.group
        action = command.action
        if capability == "scenario":
            return "ack_scenario_off" if action == "off" else "ack_scenario"
        if action in ("on", "turn_on"):
            return "ack_on"
        if action in ("off", "turn_off"):
            return "ack_off"
        if action == "open":
            return "ack_open"
        if action == "close":
            return "ack_close"
        if action.startswith("set"):
            return "ack_set" if capability in _VALUE_CAPABILITIES else "ack_switch"
        return "ack_generic"

    async def _acknowledge(self, command: CanonicalCommand,
                           context: UnifiedConversationContext) -> None:
        """Speak the acknowledgement on the request's channel (never raises, never blocks the
        command: the notification service queues it and the OutputManager routes it by the
        request's identity, exactly as a deferred completion travels)."""
        service = self._notification_service
        if service is None:
            return
        language = self._lang(context)
        text = self._get_template(self._ack_template_key(command), language)
        try:
            queued = await service.send_acknowledgement(
                session_id=context.session_id, domain="smart_home", message=text,
                source=getattr(context, "request_source", None),
                physical_id=resolve_physical_id(context.client_id, context.room_name,
                                                context.session_id),
                room_name=context.client_id or context.room_name, language=language)
        except Exception as e:  # an ack must never cost the action
            self.logger.warning(f"acknowledgement not spoken: {e}")
            return
        if queued:
            context.get_handler_context("smart_home")[ACKNOWLEDGEMENT_METADATA_KEY] = text

    @staticmethod
    def _take_acknowledgement(context: UnifiedConversationContext) -> Optional[str]:
        """Pop the acknowledgement spoken during this turn (one-shot; never leaks into the next)."""
        slot = context.handler_contexts.get("smart_home")
        return slot.pop(ACKNOWLEDGEMENT_METADATA_KEY, None) if slot else None

    async def _speak_outcome(self, delivery: Optional[Any], ok_text: str, language: str,
                       catalog: Optional[DeviceCatalog] = None,
                       clarify_intent: Optional[Intent] = None,
                       context: Optional[UnifiedConversationContext] = None) -> IntentResult:
        """Map the rich DeliveryResult (§5b) — or its absence — to speech."""
        if delivery is None:
            return IntentResult(text=self._get_template("err_not_sure", language),
                                should_speak=True, success=False,
                                error="device command delivery unavailable/timed out")

        if delivery.delivered:
            partial = self._failed_members(delivery, catalog, language)
            if partial:
                return IntentResult(
                    text=self._get_template("confirm_partial", language,
                                            ok=ok_text, failed=partial),
                    should_speak=True,
                    metadata={"device_command_echo": delivery.echoed_value})
            return IntentResult(text=ok_text, should_speak=True,
                                metadata={"device_command_echo": delivery.echoed_value})

        code = delivery.error_code or "internal_error"
        if code == "param_invalid" and clarify_intent is not None and context is not None:
            # §5b: field+reason ride DeliveryResult.detail — the clarify path takes over
            return await self._clarify(clarify_intent, context, MissingRequiredParameter(
                "param", clarify_intent.name, delivery.detail or ""))
        template_key = {
            "device_not_found": "err_device_not_found_bridge",
            "capability_not_supported": "err_capability",
            "action_not_supported": "err_action",
            "param_invalid": "err_param_invalid",
            "device_unreachable": "err_device_unreachable",
            "internal_error": "err_internal",
            "bridge_unreachable": "err_bridge_down",
        }.get(code, "err_internal")
        return IntentResult(text=self._get_template(template_key, language),
                            should_speak=True, success=False,
                            error=f"bridge error {code}: {delivery.detail}")

    def _failed_members(self, delivery: Any, catalog: Optional[DeviceCatalog],
                        language: str) -> Optional[str]:
        """Names of room-group members that failed/skipped (the §10.4 aggregate speech)."""
        echoed = delivery.echoed_value
        if not isinstance(echoed, list):
            return None
        failed_names: List[str] = []
        for member in echoed:
            if isinstance(member, dict) and member.get("status") in ("failed", "skipped"):
                device_id = member.get("device_id", "")
                device = catalog.device(device_id) if catalog else None
                failed_names.append(self._device_name(device, language) if device else device_id)
        return ", ".join(failed_names) if failed_names else None

    def _ambiguous_result(self, intent: Intent, context: UnifiedConversationContext,
                          candidates: List[Dict[str, Any]], param: str) -> IntentResult:
        """Name-level or capability-level ambiguity → one-shot clarification (v1 policy; QUAL-63
        adds priority rules later).

        BUG-39: identical names are qualified by room — an option list the user cannot tell
        apart is a question they cannot answer. All-same-name-different-rooms asks room-led
        (rooms stay nominative, so no declension is needed); a mixed list qualifies only the
        colliding names; when the rooms coincide too, the device id is the last honest
        distinguishing attribute. The answer resumes through the QUAL-31 combined re-run, so
        naming the room resolves the original command.
        """
        language = self._lang(context)
        catalog = self._catalog()
        sep = " или " if language == "ru" else " or "

        def name_of(c: Dict[str, Any]) -> str:
            return c.get("name") or c.get("device_id", "?")

        def room_of(c: Dict[str, Any]) -> Optional[str]:
            room_id = c.get("room")
            if catalog is None or not room_id:
                return None
            return self._room_spoken_name(catalog, room_id, language)

        context.set_pending_clarification(intent.name, param, intent.raw_text)
        metadata = {"clarification": True, "clarification_reason": "ambiguous_device",
                    "candidates": [c.get("device_id") for c in candidates]}

        names = [name_of(c) for c in candidates]
        rooms = [r for c in candidates if (r := room_of(c))]
        if len(set(names)) == 1 and len(rooms) == len(candidates) \
                and len(set(rooms)) == len(rooms):
            return IntentResult(
                text=self._get_template("clarify_which_room", language,
                                        name=names[0], options=sep.join(rooms)),
                should_speak=True, metadata=metadata)

        def label(c: Dict[str, Any]) -> str:
            name = name_of(c)
            if names.count(name) == 1:
                return name
            room = room_of(c)
            same_name_same_room = sum(1 for o in candidates
                                      if name_of(o) == name and room_of(o) == room)
            if room is None or same_name_same_room > 1:
                return f"{name} — {c.get('device_id', '?')}"
            return f"{name} — {room}"

        return IntentResult(
            text=self._get_template("clarify_which", language,
                                    options=sep.join(label(c) for c in candidates)),
            should_speak=True, metadata=metadata)

    # --- target selection ------------------------------------------------------------------------

    def _room_scope_refusal(self, intent: Intent, context: UnifiedConversationContext,
                            catalog: DeviceCatalog, language: str) -> Optional[IntentResult]:
        """The two ways a named room forbids the command outright — speak, actuate nothing (BUG-38).

        D-15 rule 2b: the room is real but this client does not cover it. And the room-is-king
        consequence: the named room holds no device by that name, so we refuse rather than quietly
        actuating one somewhere else (the resolver marks this `no_device_in_room`).
        """
        if intent.entities.get("room_resolution_type") == "uncovered_room":
            resolved = intent.entities.get("room_resolved") or {}
            return IntentResult(
                text=self._get_template("err_uncovered_room", language,
                                        room=resolved.get("name", "")),
                should_speak=True, success=False,
                error="room not covered by this device")

        if intent.entities.get("target_resolution_type") == "no_device_in_room":
            meta = (intent.entities.get("_resolution_metadata") or {}).get("target") or {}
            room_id = meta.get("room_id")
            ref = self.get_param(intent, "target", None) or intent.raw_text
            if not isinstance(room_id, str) or not room_id:
                # the resolver always stamps room_id with this type; if it somehow didn't, say the
                # honest generic thing rather than naming a room we don't have
                return IntentResult(
                    text=self._get_template("err_device_not_found", language, ref=str(ref)),
                    should_speak=True, success=False,
                    error=f"no device matching '{ref}' in the named room")
            return IntentResult(
                text=self._get_template("err_no_device_in_room", language,
                                        room=self._room_spoken_name(catalog, room_id, language),
                                        ref=str(ref)),
                should_speak=True, success=False,
                error=f"no device matching '{ref}' in room '{room_id}'")
        return None

    def _resolved_target(self, intent: Intent) -> Tuple[Optional[Dict[str, Any]],
                                                        Optional[List[Dict[str, Any]]], bool]:
        """(device, ambiguous_candidates, resolution_failed) from the PR-3 resolver output."""
        resolved = intent.entities.get("target_resolved")
        if intent.entities.get("target_resolution_type") == "ambiguous" \
                and isinstance(resolved, list):
            return None, resolved, False
        if isinstance(resolved, dict):
            return resolved, None, False
        return None, None, bool(intent.entities.get("target_resolution_failed"))

    # DRV-28: one user goal, two catalog dialects. The three ACs became `MitsubishiHvac` with
    # `temperature.set{value}` / `mode.set{value}` / `fan.set{value}`; the heating_loop floors keep
    # `climate` (`set_setpoint{temp}`; floors never carried set_mode/set_fan). Binding is per-DEVICE
    # and catalog-driven — new dialect first, old as fallback — so the handler is correct against
    # EITHER live catalog and the bridge/voice redeploy order cannot matter.
    _SETPOINT_BINDINGS = (("temperature", "set", "value"), ("climate", "set_setpoint", "temp"))
    # QUAL-82 (board PROD-18 round 1): the louvers ride the same table. `vane` is the vertical /
    # positional axis (auto, swing, pos_1..5), `widevane` the horizontal / directional one (swing,
    # far_left..far_right, split) — both DRV-28-only, there was never a voice consumer of the old
    # `climate.set_vane`, so no legacy fallback is invented. The spoken noun («заслонка») and the
    # verb patterns live in the donation; the catalog carries only the value labels.
    _CHOICE_BINDINGS = {
        "mode": (("mode", "set", "value"), ("climate", "set_mode", "mode")),
        "fan": (("fan", "set", "value"), ("climate", "set_fan", "fan")),
        "vane": (("vane", "set", "value"),),
        "widevane": (("widevane", "set", "value"),),
    }

    @staticmethod
    def _binding(device: CatalogDevice,
                 bindings: Tuple[Tuple[str, str, str], ...]) -> Optional[Tuple[str, str, str]]:
        """(capability, action, param) — the first binding this device actually carries."""
        for cap_name, action_name, param_name in bindings:
            cap = device.capability(cap_name)
            if cap is not None and cap.action(action_name) is not None:
                return cap_name, action_name, param_name
        return None

    def _capable_devices(self, catalog: DeviceCatalog, room_id: Optional[str],
                         capability: Union[str, Tuple[str, ...]], language: str) -> List[Dict[str, Any]]:
        wanted = (capability,) if isinstance(capability, str) else capability
        devices = catalog.devices_in_room(room_id) if room_id else catalog.devices
        return [{"device_id": d.id, "room": d.room, "name": self._device_name(d, language)}
                for d in devices if any(d.capability(c) is not None for c in wanted)]

    def _pick_capability(self, device: CatalogDevice, wanted: Tuple[str, ...]) -> Optional[str]:
        for name in wanted:
            if device.capability(name) is not None:
                return name
        return None

    # --- the actuation core ------------------------------------------------------------------------

    async def _actuate(self, intent: Intent, context: UnifiedConversationContext, *,
                       kind: str, device_action: str, group_action: Optional[str] = None,
                       params: Optional[Dict[str, Any]] = None,
                       ok_key_device: str = "", ok_key_room: str = "") -> IntentResult:
        """Shared depth-doctrine routing for power/cover: group noun → room form; named device →
        device form; ambiguity → clarify."""
        language = self._lang(context)
        catalog = self._catalog()
        if catalog is None:
            return self._no_catalog_result(language)

        group = self._verified_group_noun(intent)
        if group is not None:
            return await self._room_group(intent, context, catalog, group=group,
                                          action=group_action or device_action,
                                          ok_key=ok_key_room)

        # D-15 on the named-device path (BUG-38). Rule 2b: a real room this client does not cover →
        # speak the refusal, actuate nothing. The resolver already flags it on the `room` entity; only
        # the group branch ever consumed it, so a satellite naming an uncovered room used to actuate.
        room_refusal = self._room_scope_refusal(intent, context, catalog, language)
        if room_refusal is not None:
            return room_refusal

        device, ambiguous, failed = self._resolved_target(intent)
        if ambiguous:
            return self._ambiguous_result(intent, context, ambiguous, "target")
        if device is None:
            original = self.get_param(intent, "target", None) or intent.raw_text
            if failed:
                return IntentResult(text=self._get_template("err_device_not_found", language,
                                                            ref=str(original)),
                                    should_speak=True, success=False,
                                    error=f"unresolvable device reference: {original}")
            # no target and no group noun — nothing to actuate on
            return await self._ask_slot(intent, context, "target")

        catalog_device = catalog.device(device["device_id"])
        if catalog_device is None:
            return IntentResult(text=self._get_template("err_device_not_found", language,
                                                        ref=device.get("name", device["device_id"])),
                                should_speak=True, success=False, error="device left the catalog")
        capability = self._pick_capability(catalog_device, _METHOD_CAPABILITY[kind])
        if capability is None:
            return IntentResult(
                text=self._get_template("err_capability", language),
                should_speak=True, success=False,
                error=f"{catalog_device.id} lacks {kind} capability")

        # power-verb fallback (Slice 2): «включи обогрев» → climate.on, «включи вытяжку» →
        # fan.set(level=2) — devices without a power capability still obey on/off verbs
        if kind == "power" and capability == "climate":
            device_action, params = device_action, params  # climate has real on/off
        elif kind == "power" and capability == "fan":
            if device_action == "on":
                device_action, params = "set", {"level": 2}
            else:
                device_action, params = "off", None
        elif kind == "power" and capability == "playback":
            # Slice 3: «глуши/выключи магнитофон» — a playback-only device (tape deck) obeys
            # power verbs as play/stop; play_pause covers devices with only the toggle
            wanted = "play" if device_action == "on" else "stop"
            cap_obj = catalog_device.capability("playback")
            has_wanted = cap_obj is not None and cap_obj.action(wanted) is not None
            device_action, params = (wanted if has_wanted else "play_pause"), None
        command = DeviceCommand(device_id=catalog_device.id, capability=capability,
                                action=device_action, params=params)
        delivery = await self._deliver(command, context)
        ok_text = self._get_template(ok_key_device, language,
                                     name=self._device_name(catalog_device, language))
        return await self._speak_outcome(delivery, ok_text, language, catalog,
                                   clarify_intent=intent, context=context)

    async def _room_group(self, intent: Intent, context: UnifiedConversationContext,
                          catalog: DeviceCatalog, *, group: str, action: str,
                          ok_key: str) -> IntentResult:
        language = self._lang(context)
        room_id, room_error = self._requested_room(intent, context, catalog)
        if room_error is not None:
            return room_error
        if room_id is None:
            return await self._ask_slot(intent, context, "room")

        # bind the noun to catalog truth: the room must actually have members of this group
        if not catalog.group_members(room_id, group) and catalog.group_default(room_id, group) is None:
            return IntentResult(
                text=self._get_template("err_no_group_in_room", language,
                                        noun=self._group_noun_surface(intent, group, language),
                                        room=self._room_spoken_name(catalog, room_id, language)),
                should_speak=True, success=False,
                error=f"room {room_id} has no {group} group members")

        scope = GroupScope.ALL if _ALL_SCOPE_RE.search(intent.raw_text) else GroupScope.AUTO
        command = RoomGroupCommand(room_id=room_id, group=group, action=action, scope=scope)
        delivery = await self._deliver(command, context)
        ok_text = self._get_template(ok_key, language,
                                     noun=self._group_noun_surface(intent, group, language),
                                     room=self._room_spoken_name(catalog, room_id, language))
        return await self._speak_outcome(delivery, ok_text, language, catalog,
                                   clarify_intent=intent, context=context)

    async def _single_capable_or_clarify(self, intent: Intent,
                                         context: UnifiedConversationContext,
                                         capability: Union[str, Tuple[str, ...]]
                                         ) -> Tuple[Optional[CatalogDevice],
                                                    Optional[IntentResult]]:
        """No named target: exactly one `capability`-capable device in the room → it; several →
        clarify (the F20/F21 v1 policy); none → spoken miss. A tuple means "any of" — one user
        goal can bind different capabilities per device since DRV-28 (set-temperature is
        `climate` on a floor, `temperature` on an AC)."""
        language = self._lang(context)
        catalog = self._catalog()
        if catalog is None:
            return None, self._no_catalog_result(language)

        device, ambiguous, failed = self._resolved_target(intent)
        if ambiguous:
            return None, self._ambiguous_result(intent, context, ambiguous, "target")
        if device is not None:
            catalog_device = catalog.device(device["device_id"])
            if catalog_device is not None:
                return catalog_device, None
        if failed:
            original = self.get_param(intent, "target", None) or ""
            return None, IntentResult(
                text=self._get_template("err_device_not_found", language, ref=str(original)),
                should_speak=True, success=False, error="unresolvable device reference")

        room_id, room_error = self._requested_room(intent, context, catalog)
        if room_error is not None:
            return None, room_error
        capable = self._capable_devices(catalog, room_id, capability, language)
        if not capable:
            return None, IntentResult(
                text=self._get_template("err_nothing_capable", language),
                should_speak=True, success=False,
                error=f"no {capability if isinstance(capability, str) else '/'.join(capability)}"
                      f"-capable device in scope")
        if len(capable) > 1:
            return None, self._ambiguous_result(intent, context, capable, "target")
        return catalog.device(capable[0]["device_id"]), None

    # --- donation-routed methods ---------------------------------------------------------------

    async def _handle_power_on(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        return await self._actuate(intent, context, kind="power", device_action="on",
                                   ok_key_device="confirm_on", ok_key_room="confirm_room_on")

    async def _handle_power_off(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        return await self._actuate(intent, context, kind="power", device_action="off",
                                   ok_key_device="confirm_off", ok_key_room="confirm_room_off")

    async def _handle_cover_open(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        return await self._actuate(intent, context, kind="cover", device_action="open",
                                   ok_key_device="confirm_open", ok_key_room="confirm_room_open")

    async def _handle_cover_close(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        return await self._actuate(intent, context, kind="cover", device_action="close",
                                   ok_key_device="confirm_close", ok_key_room="confirm_room_close")

    async def _handle_set_setpoint(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        language = self._lang(context)
        temp = self.get_param(intent, "temp", None)
        if temp is None:
            return await self._ask_slot(intent, context, "temp")
        device, error = await self._single_capable_or_clarify(intent, context,
                                                              ("temperature", "climate"))
        if error is not None:
            return error
        assert device is not None
        catalog = self._catalog()

        # DRV-28: ACs speak `temperature.set{value}`, floors `climate.set_setpoint{temp}`
        binding = self._binding(device, self._SETPOINT_BINDINGS)
        if binding is None:
            return IntentResult(text=self._get_template("err_capability", language),
                                should_speak=True, success=False,
                                error=f"{device.id} lacks a settable temperature")
        cap_name, action_name, param_name = binding

        # contract-backed pre-validation (§5b: most param_invalid never round-trips)
        capability = device.capability(cap_name)
        action = capability.action(action_name) if capability else None
        spec = action.param(param_name) if action else None
        if spec is not None and ((spec.min is not None and temp < spec.min)
                                 or (spec.max is not None and temp > spec.max)):
            context.set_pending_clarification(intent.name, "temp", intent.raw_text)
            return IntentResult(
                text=self._get_template("err_param_range", language,
                                        min=spec.min, max=spec.max,
                                        unit=spec.unit or ""),
                should_speak=True,
                metadata={"clarification": True, "clarification_reason": "out_of_range"})

        command = DeviceCommand(device_id=device.id, capability=cap_name,
                                action=action_name, params={param_name: temp})
        delivery = await self._deliver(command, context)
        ok_text = self._get_template("confirm_setpoint", language,
                                     temp=self._speakable_number(temp),
                                     unit=self._unit_form("unit_degrees", temp, language),
                                     name=self._device_name(device, language))
        return await self._speak_outcome(delivery, ok_text, language, catalog,
                                   clarify_intent=intent, context=context)

    async def _handle_set_brightness(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        language = self._lang(context)
        level = self.get_param(intent, "level", None)
        if level is None:
            return await self._ask_slot(intent, context, "level")
        device, error = await self._single_capable_or_clarify(intent, context, "brightness")
        if error is not None:
            return error
        assert device is not None
        command = DeviceCommand(device_id=device.id, capability="brightness",
                                action="set", params={"level": level})
        delivery = await self._deliver(command, context)
        ok_text = self._get_template("confirm_brightness", language,
                                     level=self._speakable_number(level),
                                     unit=self._unit_form("unit_percent", level, language),
                                     name=self._device_name(device, language))
        return await self._speak_outcome(delivery, ok_text, language, self._catalog(),
                                   clarify_intent=intent, context=context)

    async def _handle_playback_pause(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        language = self._lang(context)
        device, error = await self._single_capable_or_clarify(intent, context, "playback")
        if error is not None:
            return error
        assert device is not None
        command = DeviceCommand(device_id=device.id, capability="playback",
                                action="pause", params=None)
        delivery = await self._deliver(command, context)
        ok_text = self._get_template("confirm_pause", language,
                                     name=self._device_name(device, language))
        return await self._speak_outcome(delivery, ok_text, language, self._catalog(),
                                   clarify_intent=intent, context=context)

    async def _handle_scenario_start(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        return await self._scenario(intent, context, start=True)

    async def _handle_scenario_stop(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        return await self._scenario(intent, context, start=False)

    async def _scenario(self, intent: Intent, context: UnifiedConversationContext, *,
                        start: bool) -> IntentResult:
        """Scenario enums ride the device form: match the spoken words against the scenario
        device's `{wire, canonical, labels}` triplets (QUAL-29 — labels are the surfaces, the
        canonical goes on the wire). Exact-ru-label matching is T1; the transliteration-tolerant
        tier («эппл ти ви» → "Apple TV") is QUAL-35 T2."""
        language = self._lang(context)
        catalog = self._catalog()
        if catalog is None:
            return self._no_catalog_result(language)

        room_id, room_error = self._requested_room(intent, context, catalog)
        if room_error is not None:
            return room_error
        scenario_devices = [d for d in (catalog.devices_in_room(room_id) if room_id else catalog.devices)
                            if d.capability("scenario") is not None]
        if not scenario_devices and room_id:
            scenario_devices = [d for d in catalog.devices if d.capability("scenario") is not None]
        if not scenario_devices:
            return IntentResult(text=self._get_template("err_nothing_capable", language),
                                should_speak=True, success=False, error="no scenario device")
        device = scenario_devices[0]
        # ARCH-69: the bridge's room is the job's unit of concurrency — the index key
        bridge_room = device.room or room_id or ""
        as_job = self.events_port is not None

        if as_job:
            running = self._jobs.get(bridge_room)
            if running is not None:
                # voice owns the room's running record → refused locally, no request (§4.4)
                return self._busy_result(running, language)

        if not start:
            command = DeviceCommand(device_id=device.id, capability="scenario",
                                    action="off", params=None, wait=False if as_job else None)
            delivery = await self._deliver(command, context)
            if as_job:
                return await self._scenario_job_result(
                    delivery, context, device=device, bridge_room=bridge_room, kind="stop",
                    target="none", label=self._get_template("scenario_generic_label", language),
                    command=command, intent=intent,
                    ok_text=self._get_template("confirm_scenario_off", language))
            return await self._speak_outcome(delivery, self._get_template("confirm_scenario_off", language),
                                       language, catalog, clarify_intent=intent, context=context)

        capability = device.capability("scenario")
        action = capability.action("set") if capability else None
        spec = action.param("value") if action else None
        values = spec.values or () if spec else ()
        best_label, best_canonical, best_score = None, None, 0
        from rapidfuzz import fuzz
        text_norm = intent.raw_text.lower().replace("ё", "е").replace("э", "е")
        for value in values:
            label = value.labels.get(language) or value.labels.get("ru") or value.canonical
            score = int(fuzz.partial_ratio(
                label.lower().replace("ё", "е").replace("э", "е"), text_norm))
            if re.search(r"[a-zA-Z]", label):
                # QUAL-35 Slice 1: a label with a Latin name («Кино с Apple TV») also matches
                # its spoken Cyrillic form («кино с эппл ти ви») via the pronunciation hint
                hint = await latin_to_cyrillic_hint(label)
                score = max(score, int(fuzz.partial_ratio(
                    hint.lower().replace("ё", "е").replace("э", "е"), text_norm)))
            if score > best_score:
                best_label, best_canonical, best_score = label, value.canonical, score
        if best_canonical is None or best_label is None or best_score < 85:
            options = ", ".join((v.labels.get(language) or v.canonical) for v in values[:5])
            context.set_pending_clarification(intent.name, "scenario", intent.raw_text)
            return IntentResult(text=self._get_template("clarify_scenario", language, options=options),
                                should_speak=True,
                                metadata={"clarification": True,
                                          "clarification_reason": "unknown_scenario"})

        command = DeviceCommand(device_id=device.id, capability="scenario",
                                action="set", params={"value": best_canonical},
                                wait=False if as_job else None)
        delivery = await self._deliver(command, context)
        ok_text = self._get_template("confirm_scenario", language, label=best_label)
        if as_job:
            return await self._scenario_job_result(
                delivery, context, device=device, bridge_room=bridge_room, kind="switch",
                target=best_canonical, label=best_label, command=command, intent=intent,
                ok_text=ok_text)
        return await self._speak_outcome(delivery, ok_text, language, catalog,
                                   clarify_intent=intent, context=context)

    # --- scenario jobs (ARCH-69; design docs/design/scenario_jobs_voice.md §3–§5) ---------------

    def _scenario_label(self, device: CatalogDevice, target: str, language: str) -> str:
        """The spoken name of a scenario id from the catalog's value labels (nouns live in
        the catalog); the generic word for a stop or an id the catalog does not list."""
        if target == "none":
            return self._get_template("scenario_generic_label", language)
        capability = device.capability("scenario")
        action = capability.action("set") if capability else None
        spec = action.param("value") if action else None
        for value in (spec.values or ()) if spec else ():
            if value.canonical == target:
                return value.labels.get(language) or value.labels.get("ru") or value.canonical
        return self._get_template("scenario_generic_label", language)

    def _busy_result(self, running: RunningJob, language: str) -> IntentResult:
        """§4.4: the room's job is still running — the honest refusal with the remaining ceiling."""
        n = remaining_seconds(running.accepted_at, running.max_duration_ms, time.time())
        key = "busy_scenario_off" if running.kind == "stop" else "busy_scenario"
        return IntentResult(text=self._get_template(key, language, label=running.label, n=n),
                            should_speak=True, success=False,
                            metadata={SCENARIO_JOB_METADATA_KEY: {
                                "job_id": running.job_id, "room_id": running.room_id,
                                "busy": True}})

    def _acceptance_text(self, kind: str, max_duration_ms: Optional[int], language: str) -> str:
        """§4.1: ARCH-67's acknowledgement + the ceiling bucket from `max_duration_ms`."""
        bucket = ceiling_bucket(max_duration_ms)
        ceiling = ""
        if bucket == "seconds":
            n = -(-int(max_duration_ms or 0) // 5000) * 5          # ceil to a multiple of 5 s
            ceiling = self._get_template("ceiling_seconds", language, n=n)
        elif bucket is not None:
            ceiling = self._get_template(f"ceiling_{bucket}", language)
        key = "ack_scenario_off_job" if kind == "stop" else "ack_scenario_job"
        return self._get_template(key, language, ceiling=ceiling)

    async def _scenario_job_result(self, delivery: Optional[Any],
                                   context: UnifiedConversationContext, *,
                                   device: CatalogDevice, bridge_room: str, kind: str,
                                   target: str, label: str, command: DeviceCommand,
                                   intent: Intent, ok_text: str) -> IntentResult:
        """What the turn says after a `wait: false` scenario request (§2.3 / §4.1 / §4.4):
        a `202` → launch the follower, reply with the acceptance; a `409 job_in_progress` →
        adopt the running job, reply «ещё переключаю»; a `200` → the bridge ran the chain
        synchronously (a pre-1.12 bridge, the mock bridge) → ARCH-67's confirmation; anything
        else → the ordinary failure speech."""
        language = self._lang(context)
        catalog = self._catalog()
        if delivery is None:
            return await self._speak_outcome(None, ok_text, language, catalog)

        if getattr(delivery, "accepted", False) and delivery.job_id:
            ceiling = delivery.max_duration_ms
            if ceiling is None and catalog is not None:
                ceiling = published_wait_ms(catalog, command)
            running = RunningJob(job_id=delivery.job_id, room_id=bridge_room, kind=kind,
                                 target=target, label=label,
                                 max_duration_ms=int(ceiling or 0), accepted_at=time.time())
            await self._launch_follower(running, context)
            meta: Dict[str, Any] = {
                SCENARIO_JOB_METADATA_KEY: {"job_id": running.job_id, "room_id": bridge_room,
                                            "max_duration_ms": running.max_duration_ms}}
            if not self.acknowledge_slow_actions:
                # flag off = silent acceptance; the terminal event is the only speech (§4.1)
                return IntentResult(text="", should_speak=False, metadata=meta)
            text = self._acceptance_text(kind, running.max_duration_ms, language)
            meta[ACKNOWLEDGEMENT_METADATA_KEY] = text
            return IntentResult(text=text, should_speak=True, metadata=meta)

        if delivery.error_code == "job_in_progress" and delivery.job_id:
            # §4.4: another client's job runs in the room — adopt it via one GET and refuse
            adopted = await self._adopt_job(delivery.job_id, bridge_room, device, context)
            if adopted is not None:
                return self._busy_result(adopted, language)
            ceiling_ms = published_wait_ms(catalog, command) if catalog is not None else None
            fallback = RunningJob(job_id=delivery.job_id, room_id=bridge_room, kind=kind,
                                  target=target, label=label,
                                  max_duration_ms=int(ceiling_ms or 0), accepted_at=time.time())
            return self._busy_result(fallback, language)

        # a 200 (synchronous outcome) or any error → exactly ARCH-67's speech
        return await self._speak_outcome(delivery, ok_text, language, catalog,
                                         clarify_intent=intent, context=context)

    async def _adopt_job(self, job_id: str, bridge_room: str, device: CatalogDevice,
                         context: UnifiedConversationContext) -> Optional[RunningJob]:
        """Read another client's running job and follow it as the room's record (§4.4)."""
        if self.events_port is None:
            return None
        lookup = await self.events_port.get_job(job_id)
        if not isinstance(lookup, JobRecord) or lookup.terminal:
            return None
        language = self._lang(context)
        kind = "stop" if lookup.kind == "stop" or lookup.target == "none" else "switch"
        running = RunningJob(job_id=lookup.job_id, room_id=bridge_room, kind=kind,
                             target=lookup.target,
                             label=self._scenario_label(device, lookup.target, language),
                             max_duration_ms=int(lookup.max_duration_ms or 0),
                             accepted_at=time.time())
        await self._launch_follower(running, context)
        return running

    async def _launch_follower(self, running: RunningJob,
                               context: UnifiedConversationContext) -> None:
        """The durable launch (§3): one record per bridge room, the requesting device's
        identity captured for the outcome's delivery, re-armed on restart even when late."""
        self._jobs[running.room_id] = running
        physical_id = resolve_physical_id(context.client_id, context.room_name, context.session_id)
        await self.execute_fire_and_forget_with_context(
            self._follow_scenario_job,
            action_name=SCENARIO_JOB_ACTION_PREFIX + running.room_id,
            domain="smart_home", context=context,
            timeout=hard_cap_seconds(running.max_duration_ms) + 5.0,
            durable=True, redeliver_on_reconnect=True, on_missed="rearm",
            # the coroutine's own kwargs (persisted re-arm params) — named apart from the
            # launch's keyword-only identity params, which flow through `**kwargs` untouched
            job_id=running.job_id, bridge_room=running.room_id, kind=running.kind,
            target=running.target, label=running.label,
            max_duration_ms=running.max_duration_ms, accepted_at=running.accepted_at,
            origin_id=physical_id, origin_session=context.session_id,
            origin_source=getattr(context, "request_source", None),
            origin_room=context.client_id or context.room_name,
            origin_language=self._lang(context), resume=False)

    async def rearm_durable_action(self, record) -> bool:
        """ARCH-28 D-3 / design §3: after a voice restart, follow the persisted job again —
        the follower's first act on resume is `GET /scenario/jobs/{id}`; a record older than
        an hour is dropped silently inside the follower."""
        params = dict((record.rearm or {}).get("params") or {})
        if not params.get("job_id") or not params.get("bridge_room"):
            return False
        params["resume"] = True
        running = RunningJob(job_id=str(params["job_id"]), room_id=str(params["bridge_room"]),
                             kind=str(params.get("kind", "switch")),
                             target=str(params.get("target", "none")),
                             label=str(params.get("label", "")),
                             max_duration_ms=int(params.get("max_duration_ms") or 0),
                             accepted_at=float(params.get("accepted_at") or record.started_at))
        self._jobs[running.room_id] = running
        metadata = record.metadata or {}
        await self.execute_fire_and_forget_action(
            self._follow_scenario_job,
            action_name=record.action_name, domain=record.domain,
            physical_id=record.physical_id, owner_session_id=record.session_id,
            room_id=record.room_id, source=record.source,
            timeout=hard_cap_seconds(running.max_duration_ms) + 5.0,
            language=metadata.get("language"), durable=True,
            redeliver_on_reconnect=record.redeliver, on_missed="rearm", **params)
        self.logger.info(f"Re-armed scenario job {running.job_id} ({running.room_id}) after restart")
        return True

    async def _follow_scenario_job(self, *, job_id: str, bridge_room: str, kind: str,
                                   target: str, label: str, max_duration_ms: int,
                                   accepted_at: float, origin_id: str,
                                   origin_session: Optional[str], origin_source: Optional[str],
                                   origin_room: Optional[str], origin_language: Optional[str],
                                   resume: bool = False) -> bool:
        """The follower — the action-store task (§5). Reads the room's events until the job's
        terminal event, with W (the watchdog) and H (the hard cap) from acceptance; every
        reconnect and every watchdog fires a GET; the bridge forgetting the job (404) is
        answered from the room's actual state. Renders and announces the outcome itself."""
        port = self.events_port
        room_id = bridge_room
        lang = origin_language or "ru"
        try:
            if port is None:
                self.logger.warning(f"scenario job {job_id}: no events port — cannot follow")
                return False
            now = time.time()
            if resume and now - accepted_at > STALE_RESUME_S:
                self.logger.info(f"scenario job {job_id}: resumed {int(now - accepted_at)} s after "
                                 "acceptance — stale, dropped silently")
                return True
            w_at = accepted_at + watchdog_seconds(max_duration_ms)
            h_at = accepted_at + hard_cap_seconds(max_duration_ms)
            outcome = await self._run_follower(port, job_id=job_id, room_id=room_id, kind=kind,
                                               target=target, label=label, lang=lang,
                                               w_at=w_at, h_at=h_at, resume=resume)
            await self._announce_outcome(outcome, action_name=SCENARIO_JOB_ACTION_PREFIX + room_id,
                                         session_id=origin_session, source=origin_source,
                                         physical_id=origin_id, voice_room=origin_room, lang=lang)
            self.mark_announced(origin_id, SCENARIO_JOB_ACTION_PREFIX + room_id)
            return True
        finally:
            if self._jobs.get(room_id) is not None and self._jobs[room_id].job_id == job_id:
                self._jobs.pop(room_id, None)

    async def _run_follower(self, port: ScenarioJobEventsPort, *, job_id: str, room_id: str,
                            kind: str, target: str, label: str, lang: str,
                            w_at: float, h_at: float, resume: bool = False) -> str:
        """The state machine proper (§5 table); returns the outcome text."""
        watchdog_done = False
        stream = port.events(room_id)
        if resume:
            # after a voice restart the first act is the GET (§3) — events seen before the
            # restart are gone and the stream never replays
            text = await self._outcome_from_lookup(await port.get_job(job_id), port,
                                                   kind=kind, target=target, label=label,
                                                   room_id=room_id, lang=lang, final=False)
            if text is not None:
                await self._close_stream(stream)
                return text
        # the next event is awaited through ONE future kept across watchdog ticks — a timed-out
        # `wait_for(stream.__anext__())` would cancel into the generator and end the subscription
        pending: Optional[asyncio.Future] = None
        try:
            while True:
                now = time.time()
                if now >= h_at:
                    text = await self._outcome_from_lookup(await port.get_job(job_id), port,
                                                           kind=kind, target=target, label=label,
                                                           room_id=room_id, lang=lang, final=True)
                    return text or self._get_template(
                        "job_stalled_off" if kind == "stop" else "job_stalled", lang, label=label)
                if now >= w_at and not watchdog_done:
                    watchdog_done = True
                    text = await self._outcome_from_lookup(await port.get_job(job_id), port,
                                                           kind=kind, target=target, label=label,
                                                           room_id=room_id, lang=lang, final=False)
                    if text is not None:
                        return text
                    continue
                budget = max(0.05, (h_at if watchdog_done else w_at) - now)
                if pending is None:
                    pending = asyncio.ensure_future(stream.__anext__())
                done, _ = await asyncio.wait({pending}, timeout=budget)
                if not done:
                    continue
                try:
                    event: JobEvent = pending.result()
                except StopAsyncIteration:
                    # the port ended the stream — treat as a reconnect cue, then re-subscribe
                    stream = port.events(room_id)
                    event = JobEvent(kind=JobEventKind.STREAM_OPEN)
                finally:
                    pending = None
                if event.kind is JobEventKind.TERMINAL and event.job_id == job_id:
                    return self._terminal_text(event.job_state, event.failures, kind=kind,
                                               label=label, lang=lang)
                if event.kind is JobEventKind.STREAM_OPEN or (
                        event.kind is JobEventKind.TERMINAL and event.job_id != job_id):
                    # no replay on reconnect → the record is the truth; a terminal of ANOTHER
                    # job in this room while ours runs = the bridge forgot ours
                    text = await self._outcome_from_lookup(await port.get_job(job_id), port,
                                                           kind=kind, target=target, label=label,
                                                           room_id=room_id, lang=lang, final=False)
                    if text is not None:
                        return text
                # PHASE / STEP for our job: liveness only, nothing said (§8 a)
        finally:
            if pending is not None and not pending.done():
                pending.cancel()
            await self._close_stream(stream)

    @staticmethod
    async def _close_stream(stream: Any) -> None:
        aclose = getattr(stream, "aclose", None)
        if aclose is not None:
            try:
                await aclose()
            except Exception:
                pass

    async def _outcome_from_lookup(self, lookup: JobLookup, port: ScenarioJobEventsPort, *,
                                   kind: str, target: str, label: str, room_id: str,
                                   lang: str, final: bool) -> Optional[str]:
        """§5: what a `GET /scenario/jobs/{id}` answer means — a text to speak, or None to
        keep following (`final` = the hard cap passed: nothing is left to wait for)."""
        off = kind == "stop"
        if isinstance(lookup, JobRecord):
            if lookup.terminal:
                return self._terminal_text(lookup.state, lookup.failures, kind=kind,
                                           label=label, lang=lang)
            return (self._get_template("job_stalled_off" if off else "job_stalled", lang,
                                       label=label) if final else None)
        if lookup.reason == "unknown":
            # the bridge restarted and forgot the job: speak the room's ACTUAL state (§4.3)
            active = await port.get_active_scenario(room_id)
            if active is None:
                return self._get_template("job_lost_off" if off else "job_lost", lang, label=label)
            reached = (active == "none") if off else (active == target)
            key = (("job_bridge_restarted_off_ok" if off else "job_bridge_restarted_ok") if reached
                   else ("job_bridge_restarted_off_failed" if off else "job_bridge_restarted_failed"))
            return self._get_template(key, lang, label=label)
        # unreachable: keep reconnecting until the hard cap, then it is lost
        return (self._get_template("job_lost_off" if off else "job_lost", lang, label=label)
                if final else None)

    def _terminal_text(self, job_state: Optional[str], failures: Tuple[JobFailure, ...], *,
                       kind: str, label: str, lang: str) -> str:
        """§4.2: the factual confirmation, with the failing devices' catalog names appended."""
        ok_text = (self._get_template("confirm_scenario_off", lang) if kind == "stop"
                   else self._get_template("confirm_scenario", lang, label=label))
        if job_state == "succeeded" or not failures:
            return ok_text
        catalog = self._catalog()
        names: List[str] = []
        for failure in failures:
            device = catalog.device(failure.device) if catalog is not None else None
            name = self._device_name(device, lang) if device else failure.device
            if name not in names:
                names.append(name)
        return self._get_template("confirm_partial", lang, ok=ok_text, failed=", ".join(names))

    async def _announce_outcome(self, text: str, *, action_name: str, session_id: Optional[str],
                                source: Optional[str], physical_id: str,
                                voice_room: Optional[str], lang: str) -> None:
        """§4.5: the outcome travels the route a timer ring takes, with redelivery."""
        service = self._notification_service
        if service is None:
            self.logger.warning(f"scenario job outcome not spoken (no notification service): {text}")
            return
        try:
            await service.send_action_outcome(
                session_id=session_id, domain="smart_home", action_name=action_name,
                message=text, source=source, physical_id=physical_id, room_name=voice_room,
                language=lang, redeliver=True)
        except Exception as e:  # the outcome must never crash the follower
            self.logger.error(f"scenario job outcome not spoken: {e}")

    # --- the read flow (ARCH-8 PR-5, §5c) --------------------------------------------------------

    def _find_readable(self, catalog: DeviceCatalog, room_id: Optional[str],
                       field_names: Tuple[str, ...]) -> Optional[Tuple[CatalogDevice, str, str]]:
        """(device, capability, field) carrying one of `field_names`, dedicated `sensor`
        capabilities first (a sensors box beats a climate unit for «какая температура»);
        field-name preference order breaks ties within a device."""
        devices = catalog.devices_in_room(room_id) if room_id else catalog.devices
        candidates: List[Tuple[int, int, CatalogDevice, str, str]] = []
        for device in devices:
            for capability in device.capabilities:
                if capability.name == "sensor":
                    effective = field_names
                else:
                    # on climate devices the bare `temperature` field is the SETPOINT
                    # («уставка») — the measured value is `room_temperature`; prefer it
                    effective = tuple(sorted(field_names,
                                             key=lambda f: 0 if f.startswith("room_") else 1))
                for rank, field_name in enumerate(effective):
                    if capability.field_spec(field_name) is not None:
                        sensor_rank = 0 if capability.name == "sensor" else 1
                        candidates.append((sensor_rank, rank, device, capability.name, field_name))
        if not candidates:
            return None
        candidates.sort(key=lambda c: (c[0], c[1]))
        _, _, device, capability_name, field_name = candidates[0]
        return device, capability_name, field_name

    async def _handle_read_state(self, intent: Intent,
                                 context: UnifiedConversationContext) -> IntentResult:
        """«какая температура в спальне» → resolve room → readable device/field →
        GET state via the read port → speak the value with the catalog's unit. A read
        never actuates and never rides the OutputManager (§13.3)."""
        language = self._lang(context)
        catalog = self._catalog()
        if catalog is None:
            return self._no_catalog_result(language)

        quantity = self.get_param(intent, "quantity", None)
        if quantity not in _QUANTITY_FIELDS:
            return await self._ask_slot(intent, context, "quantity")
        room_id, room_error = self._requested_room(intent, context, catalog)
        if room_error is not None:
            return room_error

        found = self._find_readable(catalog, room_id, _QUANTITY_FIELDS[quantity])
        if found is None and room_id is not None:
            found = self._find_readable(catalog, None, _QUANTITY_FIELDS[quantity])
        if found is None:
            return IntentResult(text=self._get_template("err_no_sensor", language),
                                should_speak=True, success=False,
                                error=f"no readable {quantity} field in scope")
        device, capability_name, field_name = found

        assert self.catalog_port is not None
        state = await self.catalog_port.read_state(device.id)
        value = state.get(field_name) if isinstance(state, dict) else None
        if value is None:
            return IntentResult(text=self._get_template("err_not_sure", language),
                                should_speak=True, success=False,
                                error=f"state read failed for {device.id}.{field_name}")
        if isinstance(value, float) and value == int(value):
            value = int(value)
        # BUG-37: sensors report raw floats (24.125); a person says «двадцать четыре градуса».
        # Integer rounding is language-agnostic and covers both quantities we read today; the
        # machine-facing metadata below keeps the raw reading.
        spoken = value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            spoken = round(float(value))
        return IntentResult(
            text=self._get_template(f"read_{quantity}", language, value=spoken,
                                    unit=self._unit_form(_QUANTITY_UNIT_KEY[quantity],
                                                         spoken, language),
                                    name=self._device_name(device, language)),
            should_speak=True,
            metadata={"read": {"device_id": device.id, "capability": capability_name,
                               "field": field_name, "value": value}})

    # --- select-form capabilities (QUAL-65, VWB-19 §11) -------------------------------------------

    @staticmethod
    def _option_score(spoken_norm: str, candidate: str) -> int:
        """One comparison leg: exact → 100, shared-stem → 90, else fuzz.ratio.
        «э» folds to «е» so transcription variants («эпел»/«эппл», «нэтфликс»/«нетфликс»)
        don't lose points to a vowel-spelling choice."""
        from rapidfuzz import fuzz
        candidate_norm = _norm(candidate).replace(" ", "").replace("э", "е")
        if candidate_norm == spoken_norm:
            return 100
        score = int(fuzz.ratio(spoken_norm, candidate_norm))
        if score < _STEM_MATCH_SCORE and _stem_match(spoken_norm, candidate_norm):
            score = _STEM_MATCH_SCORE
        return score

    async def _match_option(self, spoken: str, options: List[str]) -> Optional[str]:
        """Match a spoken value against an option set: normalized exact (case/ё/э/spacing),
        shared-stem, fuzzy — and for Latin options ALSO against their Cyrillic pronunciation
        hint (QUAL-35 Slice 1: «ютуб» ↔ "YouTube", «эппл ти ви» ↔ "Apple TV"). Technical
        identifiers stay self-matchable (the donation-choice-surfaces rule)."""
        spoken_norm = _norm(spoken).replace(" ", "").replace("э", "е")
        best, best_score = None, 0
        for option in options:
            option_str = str(option)
            score = self._option_score(spoken_norm, option_str)
            if re.search(r"[a-zA-Z]", option_str):
                hint = await latin_to_cyrillic_hint(option_str)
                score = max(score, self._option_score(spoken_norm, hint))
            if score == 100:
                return option_str
            if score > best_score:
                best, best_score = option_str, score
        return best if best_score >= _MORPH_FUZZ_THRESHOLD else None

    async def _selectable_options(self, device: CatalogDevice, capability_name: str,
                                  action_name: str, param_name: str) -> Optional[List[str]]:
        """The valid values for a select-form param: static `values` canonicals from the
        catalog (by_value), or the runtime set via `options_from` (parametric — the
        read port fetches + caches it)."""
        capability = device.capability(capability_name)
        action = capability.action(action_name) if capability else None
        spec = action.param(param_name) if action else None
        if spec is None:
            return None
        if spec.values:
            return [v.canonical for v in spec.values]
        if spec.options_from and self.catalog_port is not None:
            return await self.catalog_port.read_options(device.id, spec.options_from)
        return None

    async def _select_value(self, intent: Intent, context: UnifiedConversationContext, *,
                            capability: str, action: str, param: str, spoken: str,
                            device: CatalogDevice, ok_key: str) -> IntentResult:
        """Shared tail of input/app selection: enumerate the valid set, match the spoken
        value, emit the canonical command; a miss clarifies naming what IS available."""
        language = self._lang(context)
        options = await self._selectable_options(device, capability, action, param)
        if options is None:
            return IntentResult(text=self._get_template("err_no_options", language,
                                                        name=self._device_name(device, language)),
                                should_speak=True, success=False,
                                error=f"no option set for {device.id}.{capability}")
        matched = await self._match_option(spoken, options)
        if matched is None:
            context.set_pending_clarification(intent.name, param, intent.raw_text)
            return IntentResult(
                text=self._get_template("clarify_option", language,
                                        options=", ".join(str(o) for o in options[:6])),
                should_speak=True,
                metadata={"clarification": True, "clarification_reason": "unknown_option",
                          "options": options, "spoken": spoken})
        command = DeviceCommand(device_id=device.id, capability=capability,
                                action=action, params={param: matched})
        delivery = await self._deliver(command, context)
        ok_text = self._get_template(ok_key, language, value=matched,
                                     name=self._device_name(device, language))
        return await self._speak_outcome(delivery, ok_text, language, self._catalog(),
                                         clarify_intent=intent, context=context)

    async def _handle_input_select(self, intent: Intent,
                                   context: UnifiedConversationContext) -> IntentResult:
        """«переключи усилитель на cd» → input.set {value} (VWB-19: `set` is the reserved
        canonical action for select-form capabilities; by_value validates offline,
        parametric enumerates at resolution time)."""
        spoken = self.get_param(intent, "value", None)
        if not spoken:
            return await self._ask_slot(intent, context, "value")
        device, error = await self._single_capable_or_clarify(intent, context, "input")
        if error is not None:
            return error
        assert device is not None
        return await self._select_value(intent, context, capability="input", action="set",
                                        param="value", spoken=str(spoken), device=device,
                                        ok_key="confirm_input")

    async def _handle_app_launch(self, intent: Intent,
                                 context: UnifiedConversationContext) -> IntentResult:
        """«запусти youtube на телеке» → apps.launch {app} — the launchable set is
        runtime-dynamic (installed apps), enumerated via options_from."""
        spoken = self.get_param(intent, "app", None)
        if not spoken:
            return await self._ask_slot(intent, context, "app")
        device, error = await self._single_capable_or_clarify(intent, context, "apps")
        if error is not None:
            return error
        assert device is not None
        return await self._select_value(intent, context, capability="apps", action="launch",
                                        param="app", spoken=str(spoken), device=device,
                                        ok_key="confirm_app")


    # --- Slice 2 Part A: volume / playback / cover position ---------------------------------------

    async def _simple_capability_action(self, intent: Intent,
                                        context: UnifiedConversationContext, *,
                                        capability: str, action: str, ok_key: str,
                                        params: Optional[Dict[str, Any]] = None,
                                        fallback_action: Optional[str] = None) -> IntentResult:
        """Shared tail for single-action commands (volume up, playback stop, …): pick the
        target (named or the room's single capable device, else clarify), translate to the
        device's actual action (`fallback_action` covers e.g. `play_pause`-only devices),
        deliver, speak."""
        language = self._lang(context)
        device, error = await self._single_capable_or_clarify(intent, context, capability)
        if error is not None:
            return error
        assert device is not None
        cap = device.capability(capability)
        effective = action
        if cap is not None and cap.action(action) is None:
            if fallback_action is not None and cap.action(fallback_action) is not None:
                effective = fallback_action
            else:
                return IntentResult(text=self._get_template("err_action", language),
                                    should_speak=True, success=False,
                                    error=f"{device.id}.{capability} lacks {action}")
        command = DeviceCommand(device_id=device.id, capability=capability,
                                action=effective, params=params)
        delivery = await self._deliver(command, context)
        ok_text = self._get_template(ok_key, language,
                                     name=self._device_name(device, language),
                                     **(params or {}))
        return await self._speak_outcome(delivery, ok_text, language, self._catalog(),
                                         clarify_intent=intent, context=context)

    def _range_error(self, intent: Intent, context: UnifiedConversationContext,
                     device: CatalogDevice, capability: str, action: str, param: str,
                     value: Any) -> Optional[IntentResult]:
        """Catalog-backed pre-validation (§5b): out-of-range → clarify, never a round-trip."""
        cap = device.capability(capability)
        act = cap.action(action) if cap else None
        spec = act.param(param) if act else None
        if spec is None:
            return None
        if (spec.min is not None and value < spec.min) or \
           (spec.max is not None and value > spec.max):
            language = self._lang(context)
            context.set_pending_clarification(intent.name, param, intent.raw_text)
            return IntentResult(
                text=self._get_template("err_param_range", language,
                                        min=spec.min, max=spec.max, unit=spec.unit or ""),
                should_speak=True,
                metadata={"clarification": True, "clarification_reason": "out_of_range"})
        return None

    async def _handle_volume_up(self, intent, context):
        return await self._simple_capability_action(intent, context, capability="volume",
                                                    action="up", ok_key="confirm_volume_up")

    async def _handle_volume_down(self, intent, context):
        return await self._simple_capability_action(intent, context, capability="volume",
                                                    action="down", ok_key="confirm_volume_down")

    async def _handle_volume_mute(self, intent, context):
        return await self._simple_capability_action(intent, context, capability="volume",
                                                    action="mute_toggle", ok_key="confirm_mute")

    async def _handle_volume_set(self, intent: Intent,
                                 context: UnifiedConversationContext) -> IntentResult:
        level = self.get_param(intent, "level", None)
        if level is None:
            return await self._ask_slot(intent, context, "level")
        device, error = await self._single_capable_or_clarify(intent, context, "volume")
        if error is not None:
            return error
        assert device is not None
        range_error = self._range_error(intent, context, device, "volume", "set",
                                        "level", level)
        if range_error is not None:
            return range_error
        command = DeviceCommand(device_id=device.id, capability="volume", action="set",
                                params={"level": level})
        delivery = await self._deliver(command, context)
        language = self._lang(context)
        ok_text = self._get_template("confirm_volume_set", language, level=level,
                                     name=self._device_name(device, language))
        return await self._speak_outcome(delivery, ok_text, language, self._catalog(),
                                         clarify_intent=intent, context=context)

    async def _handle_playback_play(self, intent, context):
        return await self._simple_capability_action(intent, context, capability="playback",
                                                    action="play", ok_key="confirm_play",
                                                    fallback_action="play_pause")

    async def _handle_playback_stop(self, intent, context):
        return await self._simple_capability_action(intent, context, capability="playback",
                                                    action="stop", ok_key="confirm_stop")

    async def _handle_playback_next(self, intent, context):
        return await self._simple_capability_action(intent, context, capability="playback",
                                                    action="next", ok_key="confirm_next")

    async def _handle_playback_previous(self, intent, context):
        return await self._simple_capability_action(intent, context, capability="playback",
                                                    action="previous", ok_key="confirm_previous")

    async def _handle_playback_seek(self, intent: Intent,
                                    context: UnifiedConversationContext) -> IntentResult:
        direction = self.get_param(intent, "direction", None)
        if direction not in ("ff", "rewind"):
            return await self._ask_slot(intent, context, "direction")
        ok_key = "confirm_ff" if direction == "ff" else "confirm_rewind"
        return await self._simple_capability_action(intent, context, capability="playback",
                                                    action=direction, ok_key=ok_key)

    async def _handle_cover_position(self, intent: Intent,
                                     context: UnifiedConversationContext) -> IntentResult:
        """«шторы наполовину» / «открой жалюзи на 30 процентов» — set_position in either
        address form (VWB-23: the room endpoint accepts params)."""
        language = self._lang(context)
        catalog = self._catalog()
        if catalog is None:
            return self._no_catalog_result(language)
        pct = self.get_param(intent, "pct", None)
        if pct is None and re.search(r"половин", intent.raw_text.lower()):
            pct = 50
        if pct is None:
            return await self._ask_slot(intent, context, "pct")

        group = self._verified_group_noun(intent)
        if group == "cover":
            room_id, room_error = self._requested_room(intent, context, catalog)
            if room_error is not None:
                return room_error
            if room_id is None:
                return await self._ask_slot(intent, context, "room")
            if not catalog.group_members(room_id, "cover"):
                return IntentResult(
                    text=self._get_template("err_no_group_in_room", language,
                                            noun=self._group_noun_surface(intent, "cover", language),
                                            room=self._room_spoken_name(catalog, room_id, language)),
                    should_speak=True, success=False, error="no cover members")
            scope = GroupScope.ALL if _ALL_SCOPE_RE.search(intent.raw_text) else GroupScope.AUTO
            command = RoomGroupCommand(room_id=room_id, group="cover", action="set_position",
                                       scope=scope, params={"pct": pct})
            delivery = await self._deliver(command, context)
            ok_text = self._get_template("confirm_position_room", language,
                                         pct=self._speakable_number(pct),
                                         unit=self._unit_form("unit_percent", pct, language),
                                         noun=self._group_noun_surface(intent, "cover", language))
            return await self._speak_outcome(delivery, ok_text, language, catalog,
                                             clarify_intent=intent, context=context)

        device, error = await self._single_capable_or_clarify(intent, context, "cover")
        if error is not None:
            return error
        assert device is not None
        range_error = self._range_error(intent, context, device, "cover", "set_position",
                                        "pct", pct)
        if range_error is not None:
            return range_error
        command = DeviceCommand(device_id=device.id, capability="cover",
                                action="set_position", params={"pct": pct})
        delivery = await self._deliver(command, context)
        ok_text = self._get_template("confirm_position", language,
                                     pct=self._speakable_number(pct),
                                     unit=self._unit_form("unit_percent", pct, language),
                                     name=self._device_name(device, language))
        return await self._speak_outcome(delivery, ok_text, language, catalog,
                                         clarify_intent=intent, context=context)

    # --- Slice 2 Part B: tracks / screen / menu / household modes ----------------------------------

    def _single_global_device(self, capability: str, action: str,
                              language: str) -> Optional[CatalogDevice]:
        """The house's ONE device carrying `capability` WITH `action` — for the singleton
        household modes (presence, cleaning, the water alarm). The water_supply-vs-
        heating_control alarm split is honest here: both carry `alarm`, so the water alarm
        donation phrases name water and this helper is called with the device already
        narrowed by capability+action; if several remain we refuse rather than guess."""
        catalog = self._catalog()
        if catalog is None:
            return None
        capable = [d for d in catalog.devices
                   if (cap := d.capability(capability)) is not None
                   and cap.action(action) is not None]
        return capable[0] if len(capable) == 1 else None

    async def _handle_tracks_audio(self, intent, context):
        return await self._simple_capability_action(intent, context, capability="tracks",
                                                    action="audio", ok_key="confirm_tracks_audio")

    async def _handle_tracks_subtitles(self, intent, context):
        return await self._simple_capability_action(intent, context, capability="tracks",
                                                    action="subtitles",
                                                    ok_key="confirm_tracks_subtitles")

    async def _handle_screen_aspect(self, intent: Intent,
                                    context: UnifiedConversationContext) -> IntentResult:
        aspect = self.get_param(intent, "aspect", None)
        if aspect is None:
            return await self._ask_slot(intent, context, "aspect")
        return await self._simple_capability_action(intent, context, capability="screen",
                                                    action=aspect, ok_key="confirm_screen")

    async def _handle_menu_nav(self, intent: Intent,
                               context: UnifiedConversationContext) -> IntentResult:
        direction = self.get_param(intent, "direction", None)
        if direction is None:
            return await self._ask_slot(intent, context, "direction_menu")
        return await self._simple_capability_action(intent, context, capability="menu",
                                                    action=direction, ok_key="confirm_menu")

    async def _handle_presence_set(self, intent: Intent,
                                   context: UnifiedConversationContext) -> IntentResult:
        language = self._lang(context)
        state = self.get_param(intent, "state", None)
        if state not in ("home", "away"):
            return await self._ask_slot(intent, context, "presence")
        device = self._single_global_device("presence", state, language)
        if device is None:
            return IntentResult(text=self._get_template("err_nothing_capable", language),
                                should_speak=True, success=False, error="no presence device")
        command = DeviceCommand(device_id=device.id, capability="presence", action=state)
        delivery = await self._deliver(command, context)
        ok_text = self._get_template(f"confirm_presence_{state}", language)
        return await self._speak_outcome(delivery, ok_text, language, self._catalog(),
                                         clarify_intent=intent, context=context)

    async def _handle_cleaning_start(self, intent: Intent,
                                     context: UnifiedConversationContext) -> IntentResult:
        language = self._lang(context)
        device = self._single_global_device("cleaning", "start", language)
        if device is None:
            return IntentResult(text=self._get_template("err_nothing_capable", language),
                                should_speak=True, success=False, error="no cleaning device")
        command = DeviceCommand(device_id=device.id, capability="cleaning", action="start")
        delivery = await self._deliver(command, context)
        return await self._speak_outcome(delivery, self._get_template("confirm_cleaning", language),
                                         language, self._catalog(),
                                         clarify_intent=intent, context=context)

    async def _handle_cleaning_delay(self, intent: Intent,
                                     context: UnifiedConversationContext) -> IntentResult:
        language = self._lang(context)
        minutes = self.get_param(intent, "minutes", None)
        if minutes is None:
            return await self._ask_slot(intent, context, "minutes")
        device = self._single_global_device("cleaning", "set_delay", language)
        if device is None:
            return IntentResult(text=self._get_template("err_nothing_capable", language),
                                should_speak=True, success=False, error="no cleaning device")
        command = DeviceCommand(device_id=device.id, capability="cleaning",
                                action="set_delay", params={"minutes": minutes})
        delivery = await self._deliver(command, context)
        ok_text = self._get_template("confirm_cleaning_delay", language,
                                     minutes=self._speakable_number(minutes),
                                     unit=self._unit_form("unit_minutes", minutes, language))
        return await self._speak_outcome(delivery, ok_text, language, self._catalog(),
                                         clarify_intent=intent, context=context)

    async def _handle_water_alarm(self, intent: Intent,
                                  context: UnifiedConversationContext) -> IntentResult:
        """User decision (Slice 2): the WATER alarm only — heating_control's alarm stays off
        the voice surface. The donation phrases name water; the device is narrowed to the one
        whose LEAKS capability marks it as the water-protection controller."""
        language = self._lang(context)
        state = self.get_param(intent, "state", None)
        if state not in ("on", "off"):
            return await self._ask_slot(intent, context, "alarm_state")
        catalog = self._catalog()
        if catalog is None:
            return self._no_catalog_result(language)
        water = [d for d in catalog.devices
                 if d.capability("alarm") is not None and d.capability("leaks") is not None]
        if len(water) != 1:
            return IntentResult(text=self._get_template("err_nothing_capable", language),
                                should_speak=True, success=False,
                                error=f"water-alarm device not identifiable ({len(water)} candidates)")
        command = DeviceCommand(device_id=water[0].id, capability="alarm", action=state)
        delivery = await self._deliver(command, context)
        ok_text = self._get_template(f"confirm_water_alarm_{state}", language)
        return await self._speak_outcome(delivery, ok_text, language, catalog,
                                         clarify_intent=intent, context=context)

    # --- Slice 2a: HVAC mode/fan (VWB-24 typed values) ---------------------------------------------

    async def _hvac_choice(self, intent: Intent, context: UnifiedConversationContext, *,
                           kind: str, ok_key: str, slot_key: str = "hvac_value") -> IntentResult:
        """«кондиционер на охлаждение» — match the spoken value against the device's OWN
        typed triplets (VWB-24: canonical + ru labels), device picked binding-aware. `kind` is
        "mode", "fan", "vane" or "widevane"; per DRV-28 the ACs carry `<kind>.set{value}` (the
        old `climate.set_mode/set_fan` addressing is kept as a per-device fallback), and the
        floors' plain `climate` never carried any of them — they must not clarify into this.
        The louvers (QUAL-82) share one spoken noun across two intents, so a value both axes
        carry («качание» = `swing`) is disambiguated by the INTENT, never by the word."""
        language = self._lang(context)
        catalog = self._catalog()
        if catalog is None:
            return self._no_catalog_result(language)
        spoken = self.get_param(intent, "value", None)
        if not spoken:
            return await self._ask_slot(intent, context, slot_key)
        room_id, room_error = self._requested_room(intent, context, catalog)
        if room_error is not None:
            return room_error
        devices = catalog.devices_in_room(room_id) if room_id else catalog.devices
        bindings = self._CHOICE_BINDINGS[kind]
        capable = [(d, b) for d in devices if (b := self._binding(d, bindings)) is not None]
        if not capable:
            return IntentResult(text=self._get_template("err_nothing_capable", language),
                                should_speak=True, success=False, error=f"no {kind}-set device")
        if len(capable) > 1:
            # the room travels with each candidate so same-named ACs are told apart by room
            # (BUG-39's room-led question), not by device id
            return self._ambiguous_result(
                intent, context,
                [{"device_id": d.id, "room": d.room, "name": self._device_name(d, language)}
                 for d, _ in capable],
                "target")
        device, (cap_name, action_name, param_name) = capable[0]
        cap = device.capability(cap_name)
        act = cap.action(action_name) if cap else None
        spec = act.param(param_name) if act else None
        values = spec.values or () if spec else ()
        surfaces = {}
        for v in values:
            surfaces[v.canonical] = v.canonical
            label = v.labels.get(language) or v.labels.get("ru")
            if label:
                surfaces[label] = v.canonical
        matched_surface = await self._match_option(str(spoken), list(surfaces))
        if matched_surface is None:
            context.set_pending_clarification(intent.name, "value", intent.raw_text)
            return IntentResult(
                text=self._get_template("clarify_option", language,
                                        options=", ".join(sorted(set(surfaces)))[:120]),
                should_speak=True,
                metadata={"clarification": True, "clarification_reason": "unknown_option"})
        canonical = surfaces[matched_surface]
        command = DeviceCommand(device_id=device.id, capability=cap_name, action=action_name,
                                params={param_name: canonical})
        delivery = await self._deliver(command, context)
        ok_text = self._get_template(ok_key, language, value=matched_surface,
                                     name=self._device_name(device, language))
        return await self._speak_outcome(delivery, ok_text, language, catalog,
                                         clarify_intent=intent, context=context)

    async def _handle_hvac_mode(self, intent, context):
        return await self._hvac_choice(intent, context, kind="mode",
                                       ok_key="confirm_hvac_mode")

    async def _handle_hvac_fan(self, intent, context):
        return await self._hvac_choice(intent, context, kind="fan",
                                       ok_key="confirm_hvac_fan")

    # --- QUAL-82: the AC louvers («заслонка») -------------------------------------------------------

    async def _handle_hvac_vane(self, intent, context):
        """«заслонка в положение три», «заслонка на авто», «качай заслонку» → vane.set{value}."""
        return await self._hvac_choice(intent, context, kind="vane",
                                       ok_key="confirm_hvac_vane", slot_key="hvac_vane")

    async def _handle_hvac_widevane(self, intent, context):
        """«направь заслонку влево», «заслонка в центр», «заслонка вправо» → widevane.set{value}."""
        return await self._hvac_choice(intent, context, kind="widevane",
                                       ok_key="confirm_hvac_widevane", slot_key="hvac_widevane")
