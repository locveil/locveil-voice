"""DeviceCommandDispatcher — awaited DEVICE_COMMAND delivery for the smart-home handler (ARCH-8 PR-4).

Implements the domain's `DeviceCommandDeliveryPort` over the OutputManager (typed `Any` — core
keeps no import edge to `locveil_voice.outputs`, same convention as `NotificationService`). One command
in, one rich `DeliveryResult` out:

- wraps the command into a `device_command`-modality `IntentResult` (`mqtt_integration.md` §13.2)
  and routes it through the OutputManager's designated bridge output — no fan-out, no
  double-actuation (D-2);
- bounds the wait ABOVE the request's own timeout (ARCH-67): the command carries the timeout the
  handler sized from the catalog's published bound (`DeviceCommand.timeout_seconds`), or none —
  then the configured fallback applies (`[outputs.bridge] timeout_seconds`, the same number the
  bridge adapter falls back to); a grace margin on top lets the transport layer's own failure
  surface as a `DeliveryResult` (error_code) instead of being cut off mid-request here. Past that
  the handler gets `None` and speaks the degraded confirmation («не уверена, что получилось»)
  instead of blocking the turn;
- `None` also means no designated output (bridge disabled) — same spoken degradation path.
"""

import asyncio
import logging
from typing import Any, Optional

from ..intents.device_commands import DEVICE_COMMAND_METADATA_KEY
from ..intents.models import IntentResult
from ..intents.ports import DeviceCommandDeliveryPort
from .interfaces.output import OutputModality

logger = logging.getLogger(__name__)

# The fallback when the composition passes none (tests, a bridge-less profile): matches the
# `BridgeOutputConfig.timeout_seconds` default so the two layers agree by construction.
DEFAULT_FALLBACK_TIMEOUT_S = 20.0
# Added on top of the request timeout so the HTTP layer times out FIRST and reports it.
DISPATCH_GRACE_S = 2.0


class DeviceCommandDispatcher(DeviceCommandDeliveryPort):
    """Routes one canonical command through the OutputManager and returns the rich outcome."""

    def __init__(self, output_manager: Any,
                 fallback_timeout_seconds: float = DEFAULT_FALLBACK_TIMEOUT_S) -> None:
        self._output_manager = output_manager
        self._fallback = fallback_timeout_seconds

    def wait_seconds(self, command: Any) -> float:
        """The bounded wait for `command`: its sized timeout (or the fallback) + grace."""
        sized: Optional[float] = getattr(command, "timeout_seconds", None)
        return (sized if sized is not None else self._fallback) + DISPATCH_GRACE_S

    async def deliver_device_command(self, command: Any, context: Any) -> Optional[Any]:
        if self._output_manager is None:
            logger.warning("device command emitted but no OutputManager is wired")
            return None
        carrier = IntentResult(text="", should_speak=False,
                               metadata={DEVICE_COMMAND_METADATA_KEY: command})
        wait = self.wait_seconds(command)
        try:
            results = await asyncio.wait_for(
                self._output_manager.deliver(carrier, context, OutputModality.DEVICE_COMMAND),
                timeout=wait)
        except asyncio.TimeoutError:
            logger.warning(f"device command delivery timed out after {wait}s: {command!r}")
            return None
        if not results:
            # no designated DEVICE_COMMAND output — bridge disabled or not registered
            logger.warning("device command had no delivery target (bridge output not designated)")
            return None
        return results[0]
