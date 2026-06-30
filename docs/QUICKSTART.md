# Quickstart & Tester Guide

How to install, run, and exercise Irene. Aimed at a tester doing a first pass; no models or cloud
keys are required for the basic text flows.

> **Run from the repository root** (`wb-mqtt-voice/`). All paths below are relative to it.

---

## 1. Install

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # if you don't have uv
uv sync                                           # creates the venv + installs deps
```

## 2. (Optional) `.env` — only for cloud providers

The basic text flows need **no** API keys. Only create `.env` if you'll test cloud TTS/ASR/LLM
(OpenAI, Anthropic, ElevenLabs, Google):

```bash
cp docs/env-example.txt .env      # then fill in the keys you need
```

> Leave the `IRENE_COMPONENTS__*` lines **commented** (they are by default). Components belong in your
> config file, not `.env`; setting them in `.env` overrides the config and can produce an invalid combo
> (e.g. TTS on / Audio off).

## 3. Pick a config

Start from the documented reference and trim it: `cp configs/config-master.toml config.toml`, then pass
it with `-c config.toml`. The shipped configs:

| Config | Use for |
|---|---|
| `configs/config-master.toml` | the documented reference (every option) — copy and trim it |
| `configs/full.toml` | everything enabled (heavy) |
| `configs/embedded-armv7.toml` / `configs/embedded-aarch64.toml` | ESP32 satellite controllers (WB7 / WB8) |
| `configs/standalone-x86_64.toml` | a standalone x86 voice box |

> **Lightweight first run (no model downloads):** in your `config.toml` set `[components]` `tts = false`,
> `audio = false`, `asr = false`. The text pipeline (NLU + intents) needs no models — perfect for the CLI
> and WebAPI flows below. The **`[components]`** flags are what actually load a component (a sub-section's
> `enabled = true` is ignored when its `[components]` flag is off).
>
> For **voice**, leave `asr`/`tts`/`audio` **on** in `[components]` and install the matching models — that's
> heavier than the text flows.

---

## 4. Run it

### CLI (interactive text)
```bash
uv run python -m irene.runners.cli -c config.toml          # text-only: asr/tts/audio off in [components]
```
Then type, e.g.:
- `привет` → a greeting
- `который час` / `какое сегодня число` → date/time
- `поставь таймер на 5 минут` → sets a timer (confirms "5 мин")
- `расскажи что-нибудь` → conversation (degrades gracefully offline)
- `help`, `status` → system info; `quit` to exit

### WebAPI (REST + WebSocket + the config-ui backend)
```bash
uv run python -m irene.runners.webapi_runner -c config.toml --host 0.0.0.0 --port 8000
```
Smoke-check:
```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/execute/command -H 'Content-Type: application/json' \
     -d '{"command":"привет"}'
```
Interactive API docs: open `http://localhost:8000/docs`.

### Voice (microphone)
The full spoken pipeline from a local microphone — **Microphone → VAD → [wake word] → ASR → intent →
spoken reply**:
```bash
uv run python -m irene.runners.voice_runner -c config.toml   # voice config (asr/tts/audio on) + models; or `irene-voice`
```
It always uses microphone-only input (other inputs are overridden), but is otherwise **config-driven**:
the ASR engine is whatever **`[asr] default_provider`** selects (`vosk` / `whisper` / `sherpa_onnx` / …)
— there's no hardcoded model. The wake word runs only if `voice_trigger` is configured (otherwise audio
goes straight to ASR), and VAD is required (the runner turns it on). This needs a **voice-capable config
plus the matching ASR model installed**, so it's heavier than the text flows above. Useful flags:
`--list-devices` (pick a microphone), `--check-deps`, and `--trace` (see [tracing & replay](guides/tracing.md)).

### config-ui (browser config editor)
Needs the WebAPI backend running (step above), which it talks to at `http://localhost:8000`.
```bash
cd config-ui
npm ci
npm run dev          # opens a Vite dev server (printed URL, usually http://localhost:3000)
```

---

## 5. What's in scope for this build

**Test these:**
- Text commands via CLI and `POST /execute/command`: greetings, date/time, timers, conversation, system (`help`/`status`/`version`).
- WebAPI endpoints: `/health`, `/status`, `/execute/command`, `/docs`.
- config-ui: browse + edit config sections (incl. the new **Output Channels** `[outputs]` section), donation/prompt editors, language switch.

**NOT in this build (don't file these as bugs):**
- **Smart-home / device control** ("включи свет в гостиной") — the MQTT/bridge integration is designed but **not implemented** (ARCH-8). Device/room commands will report a resolution failure by design.
- **ESP32 voice satellite** and the wake-word path.
- **Voice/ASR** end-to-end unless you deliberately enable `asr`/`tts`/`audio` in `[components]` + install models.
- **Docker** packaging (release-phase item).

## 6. Tests & coverage

Run the backend test suite (it's green, and a hard CI gate):
```bash
uv run --extra dev python -m pytest irene/tests/
```

**Coverage needs a one-time sqlite shim.** Coverage (`pytest --cov`) keeps its data in a SQLite file,
but the CPython this project runs on (the same build `wb-mqtt-bridge` uses) is compiled **without** the
stdlib `_sqlite3` module — so `coverage.py` can't start and you'd see `No module named '_sqlite3'`. We
ship `pysqlite3-binary` and a tiny installer that aliases it onto `sqlite3` at interpreter startup. Run
it **once after `uv sync`** — a sync rewrites the venv, so re-run it whenever you (re)create the venv:
```bash
bash scripts/install_sqlite_shim.sh                                   # enables coverage on this Python
uv run --extra dev python -m pytest irene/tests/ --cov=irene --cov-report=term
```
You only need it for **coverage** runs — plain `pytest` never touches SQLite, so it works without the
shim. And on a Python that already has stdlib `sqlite3`, the installer is a harmless no-op (the shim
checks first and only aliases when native sqlite is missing).

## 7. Known state (so you can calibrate)
- The **test suite is green** (~890 passing) and enforced in CI (`backend-health`); the user-facing
  flows above are verified working (see `irene/tests/test_smoke_e2e.py`).
- If a **core text flow** (greeting, time, timer, conversation, a WebAPI endpoint, or config-ui editing)
  misbehaves — **that** is worth reporting.

## 8. Reporting findings
For each issue, include: the **mode** (CLI / WebAPI / config-ui), the **config** used (`-c …`), the
**exact input** (command or request), what you **expected** vs **saw**, and the relevant **log lines**
(`logs/irene.log`). A copy-pasteable repro beats a description.
