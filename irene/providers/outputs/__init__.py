"""Output-sink provider family (`irene.providers.outputs` entry-points, ARCH-8).

Request/response output adapters that are *configured*, not channel-bound: they are registered on
the OutputManager by the composition (gated by `[outputs.*]` config) and capability-routed via
`designate()`, unlike the origin-paired channel sinks in `irene/outputs/` (console, web push, local
audio) that each runner registers for its own channel. First member: the wb-mqtt-bridge actuation
adapter (`bridge`).
"""

from .bridge import BridgeClient

__all__ = ["BridgeClient"]
