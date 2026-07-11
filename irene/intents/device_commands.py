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

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Union

# The IntentResult.metadata key a device_command-modality result carries its
# canonical command under — shared by the emitting handlers and the delivering
# output adapters.
DEVICE_COMMAND_METADATA_KEY = "device_command"


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
    """Device-form canonical command → `POST /devices/{device_id}/canonical`."""
    device_id: str
    capability: str
    action: str
    params: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """The capture/fixture shape (`locveil-commons/contracts/crossover_fixtures.json`)."""
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

    def to_dict(self) -> Dict[str, Any]:
        """The capture/fixture shape (`locveil-commons/contracts/crossover_fixtures.json`)."""
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
