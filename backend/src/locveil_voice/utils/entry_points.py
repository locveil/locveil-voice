"""Voice's process-global entry-point loader singleton (ARCH-58).

Composition module for the VENDORED shared engine `entry_point_loader.py` (locveil-commons
`packages/core-py`, pinned at `contracts/pins/core-py/` — never edit the vendored file;
the pin's byte-identity test guards it). The shared artifact ships the class only and is
state-free by design; each consumer owns its singleton — this is voice's, carrying the
process-wide `(namespace, enabled)` class cache and the per-namespace failure ledger
(BUG-36) exactly as `utils/loader.py::dynamic_loader` did before the extraction.

Group names are consumer-owned inputs to the engine — voice's live in
`utils/namespaces.py` (ARCH-57), which deliberately stays local.
"""

from .entry_point_loader import DynamicLoader

# Global dynamic loader instance
dynamic_loader = DynamicLoader()
