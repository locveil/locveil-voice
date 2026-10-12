# crossover-fixtures — the bidirectional test fixtures (owned)

`crossover_fixtures.json` is the **single source of truth** for the Irene ↔ bridge
canonical-command crossover suite: `{utterance → expected canonical command}`, authored by
this repo, bound to one version of the bridge's catalog. Voice's producer tests assert the
command it *emits* for the utterance equals `expect`; the bridge's consumer tests replay the
*expected* command against its native layer. Because both suites read the same file, device
ids, capabilities and actions cannot drift apart between the two products.

Owned here since `crossover-fixtures-v1.0.0` (2026-10-12, board PROD-29 — owner decision
"Option 1"). Before that the file lived in `../locveil-commons/contracts/pins/crossover-fixtures/`
as a "co-owned" copy with no owner STAMP; from this cut on that folder is an ordinary pin
of this family. **Every move happens here, in a ledger task, as a version cut.**

## What is in the document

| Key | Meaning |
|---|---|
| `catalog_version` | the **content hash** (`version`) of the bridge catalog golden the fixtures were authored against — ONE document-level binding |
| `expect_kinds` | the four shapes an `expect` can take: `actuate` (device-form POST), `room-group` (room-form POST), `read` (state read; `any_of` lists equally-correct targets), `clarify` (no command — a clarification naming `candidates`) |
| `tiers` | `1` = the green gate with the current baseline; `2` = the hard-phrasing scoreboard (LLM NLU tier / deferred builds) |
| `excluded_by_design` | phrasings deliberately out of scope for this release, with the reason |
| `fixtures[]` | `id` (`F01`…), `tier`, `utterance.ru` (`utterance.en` when TEST-19 lands), `context.room`, `expect`, optional `note` |

## The catalog binding rule

The fixtures are only meaningful against **one** catalog: every `device_id`, `capability`,
`action`, `params` value (enum tokens, numeric ranges), `room_id`, `group` and `field` a
fixture names must exist in the golden whose `version` equals the document's
`catalog_version`. `STAMP.json` records that binding twice — `catalog_tag` (the bridge's
family tag) and `catalog_version` (the hash) — and both must agree with this repo's catalog
pin (`contracts/pins/catalog/STAMP.json` + `PIN.json`) at all times. The owner guard
`backend/tests/test_crossover_fixtures_contract.py` asserts all of it on every push:

1. the document parses; its `catalog_version` == the STAMP's == the catalog pin's == the
   pinned golden's `version` (the pin-of-a-pin made explicit); `catalog_tag` == the pin's tag;
2. every fixture binds to real catalog entities (the TEST-18 Slice A rules: actuate / room-group /
   read / clarify each checked against the golden; required params present, enum values
   canonical, numeric values in range; clarifications genuine — one room, ≥2 candidates that
   all carry the capability);
3. the STAMP enumerates exactly the one artifact and its `guard` is this test.

**Consequence (the accepted cost, owner 2026-10-12):** a catalog re-pin here that changes the
golden's hash makes this guard fail until the fixtures are re-bound — so a re-pin is followed
by a fixtures **minor** cut (re-bound `catalog_version`, re-authored fixtures where the guard
points), and the commons re-pins the fixtures after that. One extra hop, by design. A re-pin
whose golden is byte-identical (the catalog-v1.12.0 case) moves nothing here.

## Versioning (three levels, `../locveil-commons/process/contracts.md` §3)

| Level | When |
|---|---|
| **major** | a shape change of the `expect` kinds — a kind added or removed, or a kind's fields reshaped (consumers' assertion code breaks) |
| **minor** | fixtures added or retired, or the set **re-bound** to a new `catalog_version` (what consumers replay changed) |
| **patch** | notes, descriptions, tier prose, STAMP metadata — bytes moved, no fixture's utterance or `expect` did |

Cutting a version: edit `crossover_fixtures.json` + bump `STAMP.json` (`version`, `tag`,
`date`, and `catalog_tag`/`catalog_version` when re-binding) in ONE commit, tag that commit
`crossover-fixtures-vX.Y.Z`, push commit and tag together; the completion entry records
`contracts: crossover-fixtures-vX.Y.Z cut; re-pin owed: commons (+ bridge once it pins)`.

## Consumers

- **This repo** — `eval/Makefile` `FIXTURES_JSON` → `make device-tests` generates
  `eval/device.tests.yaml` from the file (the producer suite `device.promptfooconfig.yaml`,
  `make device-auto`); `backend/tests/test_smart_home_handler.py` mirrors the fixtures in
  unit form; `intents/device_commands.py` `to_dict()` IS the capture/fixture shape.
- **locveil-commons** — pins the family at `contracts/pins/crossover-fixtures/` (strict
  `PIN.json` derived from this STAMP by repin; IMPL-28); the eval framework's generator
  (`eval_commons/fixtures_to_tests.py`) and assertion (`device_command_assert.py`) read the
  pinned copy; its layer-2 test `eval/tests/test_crossover_fixtures.py` checks the pin against
  the commons catalog pin.
- **locveil-bridge** — pins the family when its consumer contract test (VWB-16) lands: first
  consumption, never before, and never the commons copy.

## Moves (newest first)

- **v1.0.0 — 2026-10-12 (BUILD-60, board PROD-29):** first cut. The commons file taken
  byte-for-byte (61 fixtures, 53 tier 1 / 8 tier 2; bound to `catalog-v1.12.0`,
  `4deb84ae88da6caa`). History before the cut is the commons pin README's and the voice
  journal's: TEST-18 Slice A authored the first 23 (2026-07-05) and the set grew with the
  MQTT arc (room-groups with VWB-23, reads with ARCH-8, the QUAL-35 Slice-3 colloquial set
  F90–F98, the deferred relative adjustments F100–F102); TEST-24 (2026-10-06) added F82–F86,
  the AC louvers, the last move before ownership.
