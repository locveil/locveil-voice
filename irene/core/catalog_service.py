"""CatalogService — the application-layer holder of the device catalog (ARCH-8 PR-1).

Implements the domain's `DeviceCatalogPort` (QUAL-24 pattern: the application
inherits the port and is injected inward). Holds the current `DeviceCatalog`
snapshot and the ARCH-26 lazy-refresh seam: a `fetcher` coroutine — wired by
the composition root once the `BridgeClient` adapter exists (PR-2) — pulls
`GET /system/catalog` and this service swaps the snapshot atomically. Until a
fetcher is wired (or while the bridge is unreachable) the service simply serves
the last good snapshot; a refresh failure never discards it (fail-loud in the
log, fail-soft on the data — `mqtt_integration.md` §9).
"""

import asyncio
import logging
from typing import Awaitable, Callable, Optional

from ..intents.device_catalog import DeviceCatalog
from ..intents.ports import DeviceCatalogPort

logger = logging.getLogger(__name__)

# The PR-2 BridgeClient supplies this: pull + parse one catalog snapshot.
CatalogFetcher = Callable[[], Awaitable[DeviceCatalog]]


class CatalogService(DeviceCatalogPort):
    """Holds the catalog snapshot; refreshes lazily through the wired fetcher."""

    def __init__(self, fetcher: Optional[CatalogFetcher] = None) -> None:
        self._fetcher = fetcher
        self._catalog: Optional[DeviceCatalog] = None
        # serialize concurrent lazy refreshes (two misses in flight → one pull)
        self._refresh_lock = asyncio.Lock()

    def set_fetcher(self, fetcher: CatalogFetcher) -> None:
        """Wire the catalog source (composition root, once the adapter exists)."""
        self._fetcher = fetcher

    def set_catalog(self, catalog: DeviceCatalog) -> None:
        """Install a snapshot directly (startup pull result, or tests)."""
        self._catalog = catalog

    # --- DeviceCatalogPort ----------------------------------------------------------------------

    def catalog(self) -> Optional[DeviceCatalog]:
        return self._catalog

    async def refresh(self) -> Optional[DeviceCatalog]:
        if self._fetcher is None:
            logger.debug("catalog refresh requested but no fetcher is wired (pre-PR-2 / no bridge)")
            return None
        async with self._refresh_lock:
            try:
                fresh = await self._fetcher()
            except Exception as e:
                logger.warning(f"catalog refresh failed; keeping the previous snapshot: {e}")
                return None
            previous = self._catalog
            self._catalog = fresh
            if previous is None or previous.version != fresh.version:
                logger.info(
                    f"device catalog refreshed: version "
                    f"{previous.version if previous else '(none)'} -> {fresh.version}, "
                    f"{len(fresh.devices)} devices / {len(fresh.rooms)} rooms")
            return fresh
