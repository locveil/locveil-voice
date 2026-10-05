# wake-pack — the released wake-word pack (owned, sidecar stamp)

The artifact is the **published two-file v2 pack** (JSON manifest + sibling `.tflite`) on
Hugging Face — a third-party format (microWakeWord) that is **never forked**; this folder is
a **sidecar stamp** (`../locveil-commons/process/contracts.md` §2): `STAMP.json` carries the
pack's version, per-file URLs and sha256 content hashes, so a consumer can pin and verify
bytes without this repo re-hosting them.

- **Source of truth for what's released:** the in-code catalog
  `backend/src/locveil_voice/providers/voice_trigger/microwakeword.py::_get_default_model_urls` (ASSET-5 rung 4);
  `backend/tests/test_ws_protocol_version.py` asserts the stamp's URLs match the catalog, so
  the sidecar cannot silently drift from the code.
- **Consumer:** `../locveil-satellite` — the ESP32 flashes the pack and verifies the hashes
  at flash time (its OPS-1 carries the hash-at-publish requirement); the flashed tag comes
  back as the `wake_pack_version` register field (ARCH-47).
- **Declaration:** `STAMP.json` declares `artifacts: []` with `guard` → the catalog-mirror
  test above. This is the binary-pack sidecar shape (`process/contracts.md` §2): the STAMP is
  the whole pinned set — it travels with every pin implicitly — and the pack bytes are
  verified by the sha256 values it carries, not by a repo byte-lock.
- **Versioning (three levels):** adding a validated word extends `pack` (a minor cut);
  replacing a published model file is breaking (a major cut) — flashed hashes stop
  verifying; stamp metadata with `pack` untouched is a patch. Every level is a `version` +
  `date` bump and a `wake-pack-vX.Y.Z` tag on the same commit. Training lives in the
  `~/development/wakeword-training` factory; each new word lands as its own consume-task
  (`docs/design/wakeword_models.md`).
