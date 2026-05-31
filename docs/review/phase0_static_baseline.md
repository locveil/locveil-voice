# Backend code review — Phase 0: static baseline

**Date:** 2026-05-31 · **Scope:** all of `irene/` (~64k LOC, 175 files) · **Branch:** `main`

This is the deterministic ground-truth pass of a backend code review. Motivation: the project's
backend was authored largely by an older LLM and exhibits the classic hallucination signatures —
references to things that don't exist, half-built/dead code, architecture drift, and typing used as
a cover rather than a guarantee. Phase 0 establishes objective, tool-verified facts before any
interpretive (LLM-driven) review, so the semantic pass (Phase 1) can verify rather than invent.

**Verdict:** the code has substantial, real defects (not stylistic nitpicks), corroborated across
multiple independent tools. Notably, the type-checker configuration was **deliberately relaxed**,
which hid ~1,100 genuine type errors.

## Tooling

Installed into `.venv` for analysis only (not added to `pyproject.toml`):
`ruff 0.15.15`, `pyright 1.1.409`, `vulture 2.16`. Plus the project-native
`irene.tools.dependency_validator` and a custom import-graph script.

### Reproduce

```bash
# ruff — pyflakes family (undefined names, redefinitions, unused, star-imports)
.venv/bin/ruff check irene/ --select F --statistics
.venv/bin/ruff check irene/ --select F821,F811 --output-format concise

# pyright — standard mode. GOTCHA: the config MUST live in the project root so the relative
# include and venvPath resolve; an absolute include (or a config in /tmp) yields 0 files or
# false "reportMissingImports". Use typeCheckingMode "standard" (strict drowns the signal).
cat > pyright-review.json <<'JSON'
{ "include": ["irene"], "exclude": ["**/node_modules","**/__pycache__","**/.*"],
  "pythonVersion": "3.11", "venvPath": ".", "venv": ".venv", "typeCheckingMode": "standard" }
JSON
.venv/bin/pyright -p pyright-review.json --outputjson > pyright.json ; rm pyright-review.json

# native wiring validator — resolves every entry-point class + its metadata contract
.venv/bin/python -m irene.tools.dependency_validator --validate-all

# dead code
.venv/bin/vulture irene/ --min-confidence 60
```

---

## A. Confirmed phantom references — undefined names (runtime `NameError` on untested paths)

These names are used but never imported/defined in scope; the paths that hit them were clearly
never executed. (ruff `F821` = 36 incl. tests; pyright `reportUndefinedVariable` = 35.)

| File:line | Undefined name |
|---|---|
| `irene/components/intent_component.py:104` | `asyncio` |
| `irene/components/nlu_component.py:573` | `asset_loader` |
| `irene/components/text_processor_component.py:373` | `HTTPException` |
| `irene/core/assets.py:28` | `AssetConfig` (annotation) |
| `irene/intents/handlers/timer.py:383,415` | `time` |

## B. Call-signature mismatches — calling functions/params that don't exist

pyright `reportCallIssue` = 142. Representative:

- `irene/intents/orchestrator.py:216` — No parameter named `text`
- `irene/core/workflow_manager.py:461` — Expected 2 positional arguments
- `irene/providers/voice_trigger/microwakeword.py:271` — No parameter named `metadata`
- `irene/providers/nlu/hybrid_keyword_matcher.py:1067` — no matching overload for `search`

## C. Redeclarations / silent method shadowing

ruff `F811` = 30; pyright `reportRedeclaration` = 26. **Systemic:** ~9 intent handlers define
`get_python_dependencies` / `get_platform_dependencies` / `get_platform_support` **twice** in the
same class (the second definition silently wins): `audio_playback`, `greetings`, `provider_control`,
`speech_recognition`, `system_service`, `text_enhancement`, `translation`, `voice_synthesis`, …
Also `intent_component.py:92` (`shutdown` obscured), `nlu_component.py:494`
(`get_service_dependencies` obscured).

## D. Native wiring validator — 52/58 entry-points pass, 14 errors

`dependency_validator --validate-all` (platform `linux.ubuntu`) — confirms (C) bites at runtime:

- `MonitoringComponent` / `ConfigurationComponent` `.get_python_dependencies()` — defined as
  instance methods but called unbound (`missing 1 required positional argument: 'self'`).
- Runners `cli` / `vosk` / `webapi` / `settings` — missing the required metadata methods
  (`get_python_dependencies` / `get_platform_dependencies` / `get_platform_support`).

## E. Type-safety debt hidden by a deliberately-relaxed config

`mypy.ini` and `pyrightconfig.json` were loosened (`disallow_untyped_defs=False`,
`strict_optional=False`, pyright `typeCheckingMode="basic"`). At plain **standard** mode, pyright
reports **1,107 errors across 105 files**:

| Count | Rule | Meaning |
|---|---|---|
| 274 | `reportAttributeAccessIssue` | phantom attributes on real classes (e.g. `audio_component.py:377` `.core` on `AudioComponent`; `llm_component.py:542` `.get_capabilities` on `LLMProvider`) |
| 229 | `reportOptionalMemberAccess` | missing None-checks → `AttributeError`-on-None |
| 219 | `reportArgumentType` | wrong argument types |
| 142 | `reportCallIssue` | see (B) |
| 45 + 42 | `reportIncompatible{Method,Variable}Override` | implementations diverging from their ABC/base contracts |
| 35 / 30 / 26 | undefined / possibly-unbound / redeclaration | see (A), (C) |

`reportMissingImports = 0` — all third-party deps resolve (an earlier non-zero count was a
venv-config artifact, since corrected).

## F. Architecture / layer isolation — none

Package-level import graph (with **relative** imports resolved):

- **One giant strongly-connected component** spanning
  `components ↔ config ↔ core ↔ inputs ↔ intents ↔ plugins ↔ providers ↔ utils ↔ workflows`.
- **11 mutual 2-cycles**; **13 backwards (upward) edges**, worst offenders:
  - `utils → core` / `utils → intents` — the lowest layer reaching up (`utils/vad.py` imports `intents`)
  - `components → web_api` — a component importing the web layer (same place the phantom `HTTPException` lives)
  - `config → components` (`config/auto_registry.py`)
  - `core → components` / `workflows` / `inputs` — partly expected (orchestrator), but statically coupled rather than via entry-points

Dynamic entry-point loading hides only part of the coupling; the static relative-import graph is a
big ball of mud. (No package-level acyclicity — needs Phase-1 judgement on which cycles are real vs.
import-grouping artifacts.)

## G. Dead code / cruft

- ruff `F401` unused-import = **360**; `F841` unused-var = 22; `F403`/`F405` star-imports = **62**
  (star-imports actively defeat static checking).
- vulture (conf ≥ 60): **483** candidates (318 method, 129 function, 28 class, 8 property) — **noisy**
  due to dynamic dispatch / entry-point dispatch; the 28 unused classes + 129 unused functions are a
  candidate pool to verify in Phase 1, not confirmed dead.

## H. Config schema gap

Importing `irene` warns: `CoreConfig` fields without section models —
`{debug, language, version, log_level, name, max_concurrent_commands, context_timeout_minutes,
timezone, command_timeout_seconds}`.

## Tests

The test suite is itself partly broken — it references removed/renamed symbols
(`ConversationContext` → now `UnifiedConversationContext`, `TTLCache`,
`ContextualCommandPerformanceManager`, `initialize_performance_manager`) in
`test_phase4_*`, `test_phase6_integration`, `test_component_trace_integration`. So "are the tests
trustworthy" is its own open question for Phase 1.

## Meta

58 entry-points across 12 groups (confirms the docs' "77" figure was wrong — already corrected).

---

## Next: Phase 1 (semantic, multi-agent) — not yet run

Per-layer reviewer agents seeded with these confirmed facts, hunting what static tools can't
(config keys never read, donation JSON referencing nonexistent handlers/methods, registered-but-unwired
providers, half-built/fake features, real vs. artifact cycles), with an adversarial verification pass
(the reviewer LLM can hallucinate too) and a synthesized, prioritized report.
