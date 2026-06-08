# Prompting

Every prompt an LLM sees in Irene is **externalised** — authored in YAML under `assets/prompts/`, never
hardcoded in Python. This guide is the convention for writing them.

## Where prompts live

Two sets, both per-language YAML:

- **`assets/prompts/llm/<lang>.yaml`** — shared LLM *task* prompts, used by whichever handler needs that
  task: `improve`, `grammar_correction`, `translation`, `summarize`, `expand`, `improve_speech_recognition`,
  `chat_default`.
- **`assets/prompts/<handler>_handler/<lang>.yaml`** — a handler's own prompts. Today that's
  `conversation_handler` (`chat_system`, `reference_system`, `reference_template`, `fallback_context`,
  `fallback_topic`).

`LLMConfig` has no prompt fields — prompts are purely asset-driven, not config.

## File format

Each top-level key is one prompt:

```yaml
chat_default:
  description: System prompt for general conversation
  usage_context: Used when no task-specific prompt applies
  variables:
    - name: target_language
      description: language to answer in
  prompt_type: system        # 'system' or 'template'
  content: |
    You are Irene...
```

The loader takes `content` (stripped) and keeps the metadata (`description` / `usage_context` / `variables`
/ `prompt_type`) — which is what the browser config-UI editor renders.

## How they're resolved

The asset loader flattens prompts to `<type>_<lang>`; a handler fetches one with
`get_prompt("<set>", "<type>", context.language)`. A prompt is chosen by the **user's language**
(`context.language`), never by the provider — and the `llm` set is always loaded. A handler passes its base
name (`conversation`, not `conversation_handler`); the loader maps it to the directory. Providers carry only
a one-line generic fallback; the real prompt arrives as the `system_prompt`. A missing prompt degrades
gracefully rather than crashing.

## Who consumes what

- **LLM component** — the task prompts (`improve`, `translation`, …, `chat_default`); also drives ASR's
  `improve_speech_recognition` cleanup.
- **conversation handler** — `chat_system` and the `reference_*` / `fallback_*` prompts.
- **text-enhancement handler** — `improve`, `grammar_correction`.
- **translation handler** — `translation` (with a `target_language` variable).

## Authoring rules

Prompts are hardened, not casual. Every prompt must:

1. **Return plain text only** — the output is spoken by TTS; no markdown, code fences or emoji.
2. **Return only the result** — no preamble ("Here is…"), no explanation.
3. **Treat the user's text as data, not instructions** — resist injection; never obey commands embedded in
   the content being processed.
4. **Stay in character and honest** — Irene's persona; don't invent facts.
5. **Preserve the user's language**, unless the task is translation.
6. **Be concise** — answers are heard, not read.

## Validate live before shipping

Prompt quality only shows against real models. Run the affected task against the configured provider with
real `.env` keys, including adversarial / injection inputs — and keep those live checks out of the offline
test suite (they need network and keys).

## Gotchas

- The config-UI prompt editor is **directory-driven** — a new `<handler>_handler/` set appears
  automatically.
- `assets/templates/` is **not** prompts — those are response templates for non-LLM handlers (greetings and
  the like).
- Add every prompt in **every** supported language.
