"""Canonical device commands — the Irene↔bridge boundary object (ARCH-8 PR-1).

The domain-typed command the smart-home handlers emit: capability-shaped and
convention-blind — no topic, no broker, no native command name
(`docs/design/mqtt_integration.md` §4/§14.1). The boundary is **address-form
polymorphic** (`canonical_first.md` §10, VWB-23): a named device resolves to a
`DeviceCommand` (scenarios ride this form via their `scenario_manager_*`
device); a bare capability noun («включи свет») resolves only as deep as the
utterance specifies — a `RoomGroupCommand`, where the BRIDGE picks the target
device via the room's `group_defaults` (that pick is policy, not NLU
heuristics).

A command travels as a `device_command`-modality `IntentResult`: the handler
places it in `result.metadata[DEVICE_COMMAND_METADATA_KEY]` and the
OutputManager capability-routes the result to the single designated bridge
output (§13.2), which serializes it onto the REST contract.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Union

from .device_catalog import DeviceCatalog

# The IntentResult.metadata key a device_command-modality result carries its
# canonical command under — shared by the emitting handlers and the delivering
# output adapters.
DEVICE_COMMAND_METADATA_KEY = "device_command"

# --- request sizing from the catalog's published timing (contract v1.11 "Timing";
# board PROD-18 round 2, decision 8) ------------------------------------------------------
#
# The bridge publishes, beside each action, how long IT will wait for the device:
# `confirm_timeout_ms` on a capability, `max_duration_ms` on a scenario value. Voice sizes
# its request timeout ABOVE that bound — never below, never from a conversation — and
# the configured constant (`[outputs.bridge] timeout_seconds`) is the FALLBACK for an
# action the catalog publishes nothing for (absent = the bridge's 500 ms echo window).
TIMEOUT_MARGIN_FACTOR = 1.25
TIMEOUT_MARGIN_SECONDS = 2.0
# Above this published bound the action is "slow": the handler speaks an immediate
# acknowledgement that claims nothing, then the honest outcome at the echo (decision 8).
# Strict: a 3 000 ms input switch is not slow; the 5 000 ms Apple TV power is.
SLOW_ACTION_THRESHOLD_MS = 3000


def size_request_timeout(published_ms: int) -> float:
    """The request timeout, in seconds, for a published bound: `× 1.25 + 2 s`
    (15 000 → 20.75 s; 25 000 → 33.25 s; 61 500 → 78.875 s)."""
    return published_ms / 1000.0 * TIMEOUT_MARGIN_FACTOR + TIMEOUT_MARGIN_SECONDS


def is_slow_action(published_ms: Optional[int]) -> bool:
    """Whether an action's published bound earns the acknowledgement (absent = fast)."""
    return published_ms is not None and published_ms > SLOW_ACTION_THRESHOLD_MS


class GroupScope(Enum):
    """Room-group targeting (`RoomCanonicalRequest.scope`).

    - AUTO: the room's configured default device for the group, else fan-out —
      the bare-noun case («включи свет»).
    - ALL: force fan-out — the plural/«весь» signal («весь свет»).
    - ONE: default device required (the bridge 409s if the room declares none).
    """
    AUTO = "auto"
    ALL = "all"
    ONE = "one"


@dataclass(frozen=True)
class DeviceCommand:
    """Device-form canonical command → `POST /devices/{device_id}/canonical`.

    `timeout_seconds` is the request timeout the handler sized from the catalog's
    published bound (`size_request_timeout`); None = nothing published, the delivery
    layer applies its configured fallback. Not part of the command's identity
    (`compare=False`): fixtures and captures compare WHAT is sent, not how long we wait.
    """
    device_id: str
    capability: str
    action: str
    params: Optional[Dict[str, Any]] = None
    timeout_seconds: Optional[float] = field(default=None, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        """The capture/fixture shape (`locveil-commons/contracts/pins/crossover-fixtures/crossover_fixtures.json`)."""
        return {"kind": "actuate", "device_id": self.device_id,
                "capability": self.capability, "action": self.action,
                "params": self.params}

    def request_body(self) -> Dict[str, Any]:
        """The wire body of the device endpoint (`CanonicalActionRequest`)."""
        return {"capability": self.capability, "action": self.action,
                "params": self.params}


@dataclass(frozen=True)
class RoomGroupCommand:
    """Room-form canonical command → `POST /rooms/{room_id}/canonical` (VWB-23)."""
    room_id: str
    group: str
    action: str
    scope: GroupScope = GroupScope.AUTO
    params: Optional[Dict[str, Any]] = None
    timeout_seconds: Optional[float] = field(default=None, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        """The capture/fixture shape (`locveil-commons/contracts/pins/crossover-fixtures/crossover_fixtures.json`)."""
        return {"kind": "room-group", "room_id": self.room_id, "group": self.group,
                "action": self.action, "scope": self.scope.value}

    def request_body(self) -> Dict[str, Any]:
        """The wire body of the room endpoint (`RoomCanonicalRequest`)."""
        body: Dict[str, Any] = {"group": self.group, "action": self.action,
                                "scope": self.scope.value}
        if self.params is not None:
            body["params"] = self.params
        return body


# Everything downstream of the boundary handles either address form.
CanonicalCommand = Union[DeviceCommand, RoomGroupCommand]


def published_wait_ms(catalog: DeviceCatalog, command: CanonicalCommand) -> Optional[int]:
    """The bridge's published bound for `command` (contract v1.11 "Timing"), or None when
    the catalog publishes nothing for it.

    - device form: the capability's bound for that action — a scenario value's
      `max_duration_ms` (`set(value)`; `off` = the `none` entry), else `confirm_timeout_ms`;
    - room form: the MAX over the room's capabilities tagged `group` — the bridge picks the
      member (`group_defaults`) or fans out, and the honest ceiling is the slowest member.
    """
    if isinstance(command, DeviceCommand):
        device = catalog.device(command.device_id)
        cap = device.capability(command.capability) if device else None
        return cap.published_wait_ms(command.action, command.params) if cap else None
    bounds = [cap.published_wait_ms(command.action, command.params)
              for device in catalog.group_members(command.room_id, command.group)
              for cap in device.capabilities if cap.group == command.group]
    present = [b for b in bounds if b is not None]
    return max(present) if present else None
