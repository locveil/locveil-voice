#!/usr/bin/env python3
"""QUAL-51 — live evaluation harness for the LLM NLU classifier.

Loads the REAL donation taxonomy, drives `LLMNLUProvider` against a real DeepSeek model (key from
`.env`), and scores it on the bilingual fixture (`scripts/eval_llm_nlu_cases.yaml`). Use it to iterate on
the classifier prompt: tighten `_build_system_prompt`, rerun, compare the scorecard.

NOT a pytest test — it makes live API calls (costs money, needs a key), so it lives in scripts/ and is
run by hand:  .venv/bin/python scripts/eval_llm_nlu.py [--lang ru|en] [--show-prompt]
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from irene.core.intent_asset_loader import IntentAssetLoader, AssetLoaderConfig  # noqa: E402
from irene.providers.nlu.llm import LLMNLUProvider  # noqa: E402
from irene.providers.llm.deepseek import DeepSeekLLMProvider  # noqa: E402
from irene.intents.context_models import UnifiedConversationContext  # noqa: E402


def _ctx(language: str) -> UnifiedConversationContext:
    ctx = UnifiedConversationContext(session_id="eval")
    ctx.language = language
    return ctx


def load_dotenv(path: Path) -> None:
    """Minimal .env loader (no dependency) — only sets keys not already in the environment."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


class DeepSeekPort:
    """Adapt DeepSeekLLMProvider to the tiny LLMPort surface the NLU provider uses."""
    def __init__(self):
        self.p = DeepSeekLLMProvider({"default_model": "deepseek-chat"})

    async def is_available(self) -> bool:
        return await self.p.is_available()

    async def generate_response(self, messages, model=None, provider=None, **kwargs) -> str:
        return await self.p.chat_completion(messages, model=model)


async def build_provider() -> "tuple[LLMNLUProvider, int]":
    handlers = sorted(p.name for p in (ROOT / "assets/donations").iterdir() if p.is_dir())
    loader = IntentAssetLoader(ROOT / "assets", AssetLoaderConfig(strict_mode=False))
    await loader.load_all_assets(handlers)
    donations = loader.convert_to_keyword_donations()
    provider = LLMNLUProvider({})
    await provider._initialize_from_donations(donations)
    provider.set_llm_component(DeepSeekPort())  # type: ignore[arg-type]  # duck-typed dev adapter
    return provider, len(donations)


def score(case: dict, intent) -> tuple[bool, str]:
    """Return (passed, detail). `intent` is the returned Intent or None."""
    expect = case.get("expect_intent")
    if expect is None:  # abstain case
        return (intent is None,
                "abstained" if intent is None else f"got {intent.name} (should abstain)")
    if intent is None:
        return False, "abstained (should have recognised)"
    if intent.name != expect:
        return False, f"got {intent.name}, wanted {expect}"
    miss = [k for k in case.get("expect_params", []) if k not in intent.entities]
    if miss:
        return False, f"{intent.name} ok but missing params {miss} (entities={intent.entities})"
    present_but_should_be_absent = [k for k in case.get("expect_missing", []) if k in intent.entities]
    if present_but_should_be_absent:
        return False, f"{intent.name} but {present_but_should_be_absent} should be ABSENT (clarify path)"
    extra = f" params={intent.entities}" if intent.entities else ""
    return True, f"{intent.name} (conf {intent.confidence}){extra}"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=["ru", "en"], help="run only one language")
    ap.add_argument("--show-prompt", action="store_true", help="print the system prompt once and exit")
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    if not os.environ.get("DEEPSEEK_API_KEY"):
        sys.exit("DEEPSEEK_API_KEY not found (.env or environment).")

    provider, n = await build_provider()
    print(f"taxonomy: {n} intents loaded\n")
    if args.show_prompt:
        print(provider._build_system_prompt(args.lang or "ru"))
        return

    cases = yaml.safe_load((ROOT / "scripts/eval_llm_nlu_cases.yaml").read_text())["cases"]
    if args.lang:
        cases = [c for c in cases if c["lang"] == args.lang]

    by_cat: dict = {}
    fails = []
    for c in cases:
        intent = await provider.recognize_with_parameters(c["text"], _ctx(c["lang"]))
        passed, detail = score(c, intent)
        cat = c.get("category", "other")
        by_cat.setdefault(cat, [0, 0])
        by_cat[cat][0] += int(passed)
        by_cat[cat][1] += 1
        mark = "✓" if passed else "✗"
        print(f"  {mark} [{c['lang']}/{cat:13s}] {c['text'][:48]:48s} → {detail}")
        if not passed:
            fails.append(c["text"])

    print("\nScorecard:")
    total_ok = total = 0
    for cat, (ok, tot) in sorted(by_cat.items()):
        print(f"  {cat:14s} {ok}/{tot}")
        total_ok += ok
        total += tot
    print(f"  {'TOTAL':14s} {total_ok}/{total}  ({100*total_ok//max(total,1)}%)")


if __name__ == "__main__":
    asyncio.run(main())
