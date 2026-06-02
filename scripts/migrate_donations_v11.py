#!/usr/bin/env python3
"""QUAL-29 — migrate donation assets from v1.0 (per-language files duplicating the ParameterSpec
core) to v1.1 (a language-neutral ``contract.json`` + per-language phrasing files).

Layout (user decision):
    assets/donations/<handler>/contract.json   <- language-neutral core (ONE home)
    assets/donations/<handler>/<lang>.json      <- phrasing only (joined by method_name#intent_suffix + param name)

Tie-break (user decision): on any en/ru divergence in a NEUTRAL field, **Russian wins** — EXCEPT structural
identifiers that must stay canonical (``handler_domain``), which take the ASCII value (ru had localised bugs:
``таймер``/``случайно``). New fields defaulted: ``entity_type="generic"`` per param, ``room_context="none"`` per method.

``choices`` is the **canonical (language-neutral) token list** in the contract; per-language **surface forms** go to the
``ru.json`` file as ``choice_surfaces: {canonical: [spoken forms]}`` (English canonical is self-matching, so en.json
carries none). Per-CHOICE-param decisions are encoded in CHOICE_DECISIONS (see docs/review/qual29_choices_decisions.md);
clean parallel params auto-derive by index. ``default_value`` lives in the per-language files (user decision).

Idempotent: skips a handler whose contract.json already exists.
    python3 scripts/migrate_donations_v11.py            # migrate
    python3 scripts/migrate_donations_v11.py --check     # dry-run
"""
import json
import sys
from pathlib import Path

DONATIONS_DIR = Path("assets/donations")
PRIMARY_LANG = "ru"

NEUTRAL_HANDLER_KEYS = [
    "schema_version", "donation_version", "handler_domain",
    "intent_name_patterns", "domain_patterns", "fallback_conditions", "action_domain_priority",
]
PER_LANG_HANDLER_KEYS = [
    "description", "stop_command_patterns", "action_patterns",
    "additional_recognition_patterns", "negative_patterns", "language_detection", "train_keywords",
]
NEUTRAL_METHOD_KEYS = ["method_name", "intent_suffix", "boost"]
PER_LANG_METHOD_KEYS = ["description", "phrases", "lemmas", "token_patterns", "slot_patterns", "examples"]
# choices handled specially (canonical); choice_surfaces emitted per-language
NEUTRAL_PARAM_KEYS = ["name", "type", "required", "min_value", "max_value", "pattern"]
PER_LANG_PARAM_KEYS = ["description", "extraction_patterns", "aliases", "default_value"]

GLOBAL = "__global__"

# Per-CHOICE-param decisions (QUAL-29 interactive cases). Key = (handler, method_key, param) or (handler, param).
# Value: {"canonical": [...], "ru_surfaces": {canonical: [forms]}} | {"drop": True}
CHOICE_DECISIONS = {
    # Case 1 — datetime.format (dead; canonical = en per-method; ru surfaces deferred to handler-wiring follow-up)
    ("datetime_handler", "_handle_time_request#current_time", "format"):
        {"canonical": ["12hour", "24hour", "verbose"], "ru_surfaces": {}},
    ("datetime_handler", "_handle_date_request#current_date", "format"):
        {"canonical": ["short", "full", "iso", "verbose"], "ru_surfaces": {}},
    ("datetime_handler", "_handle_datetime_request#current_datetime", "format"):
        {"canonical": ["iso", "readable", "unix", "verbose"], "ru_surfaces": {}},
    # Case 2 — system.info_type (dead; canonical = en category; ru surfaces deferred)
    ("system_handler", "info_type"):
        {"canonical": ["system", "performance", "configuration", "logs"], "ru_surfaces": {}},
    # Case 3 — speech.language (canonical = all 5; ru gets испанский)
    ("speech_recognition_handler", "language"):
        {"canonical": ["spanish", "russian", "english", "german", "french"],
         "ru_surfaces": {"spanish": ["испанский"], "russian": ["русский"], "english": ["английский"],
                          "german": ["немецкий"], "french": ["французский"]}},
    # Case 4 — translation.target_language (open-ended LLM; drop enum → free entity)
    ("translation_handler", "target_language"): {"drop": True},
    # provider_control.component — misaligned by order → semantic remap; per-method (switch lacks 'all')
    ("provider_control_handler", "_handle_switch_provider#switch", "component"):
        {"canonical": ["audio", "llm", "asr", "tts"],
         "ru_surfaces": {"audio": ["аудио"], "llm": ["модель"], "asr": ["распознавание"], "tts": ["голос"]}},
    ("provider_control_handler", "_handle_list_providers#list", "component"):
        {"canonical": ["audio", "llm", "asr", "tts", "all"],
         "ru_surfaces": {"audio": ["аудио"], "llm": ["модель"], "asr": ["распознавание"], "tts": ["голос"], "all": ["все"]}},
    # Case 5 — text_enhancement.improvement_type (union of 5)
    ("text_enhancement_handler", "improvement_type"):
        {"canonical": ["grammar", "style", "clarity", "general", "vocabulary"],
         "ru_surfaces": {"grammar": ["грамматика"], "style": ["стиль"], "general": ["общее"],
                          "clarity": ["ясность"], "vocabulary": ["словарь"]}},
}


def _ordered(langs):
    keys = sorted(langs.keys(), key=lambda l: (l != PRIMARY_LANG, l))
    return [langs[k] for k in keys]


def _pick(key, sources):
    for src in sources:
        if key in src and src[key] not in (None, []):
            return src[key]
    for src in sources:
        if key in src:
            return src[key]
    return None


def _pick_handler_domain(ordered_langs_dict):
    """handler_domain must stay canonical/ASCII (ru had localised bugs таймер/случайно)."""
    vals = [d.get("handler_domain") for d in _ordered(ordered_langs_dict) if d.get("handler_domain")]
    ascii_vals = [v for v in vals if v.isascii()]
    return ascii_vals[0] if ascii_vals else (vals[0] if vals else None)


def resolve_choice(handler, method_key, pname, param_by_lang):
    """Return {'canonical': [...], 'ru_surfaces': {...}} | {'drop': True} | None (not a choice param)."""
    dec = CHOICE_DECISIONS.get((handler, method_key, pname)) or CHOICE_DECISIONS.get((handler, pname))
    if dec:
        return dec
    enc = (param_by_lang.get("en") or {}).get("choices")
    ruc = (param_by_lang.get("ru") or {}).get("choices")
    if not enc and not ruc:
        return None
    canonical = enc or ruc
    ru_surfaces = {}
    if enc and ruc and len(enc) == len(ruc):  # clean parallel → map by index
        ru_surfaces = {enc[i]: [ruc[i]] for i in range(len(enc))}
    return {"canonical": list(canonical), "ru_surfaces": ru_surfaces}


def _param_index(donations_by_lang, method_key):
    """For a method key (or GLOBAL), collect {param_name: {lang: param_dict}} and first-seen order."""
    order, by_name = [], {}
    for lang, d in donations_by_lang.items():
        plists = ([m.get("parameters", []) for m in d.get("method_donations", [])
                   if f"{m['method_name']}#{m['intent_suffix']}" == method_key]
                  if method_key != GLOBAL else [d.get("global_parameters", [])])
        for plist in plists:
            for p in plist:
                by_name.setdefault(p["name"], {})
                if p["name"] not in order:
                    order.append(p["name"])
                by_name[p["name"]][lang] = p
    return order, by_name


def build_choice_map(handler, langs):
    """Precompute choice resolution per (method_key, param) using ALL languages (so index-alignment works)."""
    cmap = {}
    method_keys = {f"{m['method_name']}#{m['intent_suffix']}"
                   for d in langs.values() for m in d.get("method_donations", [])}
    for mk in list(method_keys) + [GLOBAL]:
        _, pidx = _param_index(langs, mk)
        for pname, param_by_lang in pidx.items():
            res = resolve_choice(handler, mk, pname, param_by_lang)
            if res is not None:
                cmap[(mk, pname)] = res
    return cmap


def _contract_param(pname, method_key, param_by_lang, choice_map):
    ordered = [param_by_lang[l] for l in sorted(param_by_lang, key=lambda l: (l != PRIMARY_LANG, l))]
    out = {}
    for k in NEUTRAL_PARAM_KEYS:
        v = _pick(k, ordered)
        if v is not None:
            out[k] = v
    ch = choice_map.get((method_key, pname))
    if ch and ch.get("drop"):
        out["type"] = "entity"  # free entity, no enum
        out.pop("choices", None)
    elif ch:
        out["choices"] = ch["canonical"]
    out["entity_type"] = "generic"
    return out


def build_contract(handler, langs, choice_map):
    ordered = _ordered(langs)
    contract = {"$schema": "../../donation_contract_v1.1.json"}
    for k in NEUTRAL_HANDLER_KEYS:
        v = _pick(k, ordered)
        if v is not None:
            contract[k] = v
    contract["handler_domain"] = _pick_handler_domain(langs)
    contract["schema_version"] = "1.1"
    contract["donation_version"] = "1.1.0"

    # method union by key, ru wins on neutral core
    order, by_key = [], {}
    for d in ordered:
        for m in d.get("method_donations", []):
            key = f"{m['method_name']}#{m['intent_suffix']}"
            by_key.setdefault(key, [])
            by_key[key].append(m)
            if key not in order:
                order.append(key)
    methods = []
    for key in order:
        cm = {}
        for k in NEUTRAL_METHOD_KEYS:
            v = _pick(k, by_key[key])
            if v is not None:
                cm[k] = v
        cm["room_context"] = "none"
        porder, pidx = _param_index(langs, key)
        cm["parameters"] = [_contract_param(pn, key, pidx[pn], choice_map) for pn in porder]
        methods.append(cm)
    contract["method_donations"] = methods

    gorder, gidx = _param_index(langs, GLOBAL)
    contract["global_parameters"] = [_contract_param(pn, GLOBAL, gidx[pn], choice_map) for pn in gorder]
    return contract


def _lang_param(method_key, p, lang, choice_map):
    out = {"name": p["name"]}
    for k in PER_LANG_PARAM_KEYS:
        if k in p:
            out[k] = p[k]
    if lang == "ru":
        ch = choice_map.get((method_key, p["name"]))
        # only emit ru surfaces when this param has a decision/choices and non-empty surfaces
        if ch and not ch.get("drop") and ch.get("ru_surfaces"):
            out["choice_surfaces"] = ch["ru_surfaces"]
    return out


def build_language_file(handler, lang, donation, choice_map):
    out = {"$schema": "../../donation_language_v1.1.json", "schema_version": "1.1",
           "handler_domain": donation.get("handler_domain"), "language": lang}
    for k in PER_LANG_HANDLER_KEYS:
        if k in donation:
            out[k] = donation[k]
    methods = []
    for m in donation.get("method_donations", []):
        mk = f"{m['method_name']}#{m['intent_suffix']}"
        lm = {"method_name": m["method_name"], "intent_suffix": m["intent_suffix"]}
        for k in PER_LANG_METHOD_KEYS:
            if k in m:
                lm[k] = m[k]
        params = [_lang_param(mk, p, lang, choice_map) for p in m.get("parameters", [])]
        params = [p for p in params if len(p) > 1]  # drop name-only params (no phrasing)
        if params:
            lm["parameters"] = params
        methods.append(lm)
    out["method_donations"] = methods
    gparams = [_lang_param(GLOBAL, p, lang, choice_map) for p in donation.get("global_parameters", [])]
    gparams = [p for p in gparams if len(p) > 1]
    if gparams:
        out["global_parameters"] = gparams
    return out


def migrate_handler(hdir, check=False):
    h = hdir.name
    if (hdir / "contract.json").exists():
        return f"  SKIP {h} (contract.json exists)"
    lang_files = sorted(p for p in hdir.glob("*.json") if p.name != "contract.json")
    if not lang_files:
        return f"  SKIP {h} (no language files)"
    langs = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in lang_files}
    choice_map = build_choice_map(h, langs)
    contract = build_contract(h, langs, choice_map)
    lang_outputs = {lang: build_language_file(h, lang, langs[lang], choice_map) for lang in langs}
    if check:
        return f"  DRY  {h}: {len(contract['method_donations'])} methods, langs={list(langs)}"
    (hdir / "contract.json").write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for lang, out in lang_outputs.items():
        (hdir / f"{lang}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return f"  OK   {h}: contract + {len(lang_outputs)} langs ({len(contract['method_donations'])} methods)"


def main():
    check = "--check" in sys.argv
    if not DONATIONS_DIR.is_dir():
        print(f"ERROR: {DONATIONS_DIR} not found (run from repo root)", file=sys.stderr)
        return 1
    handlers = sorted(d for d in DONATIONS_DIR.iterdir() if d.is_dir())
    print(f"== migrate_donations_v11 ({'DRY-RUN' if check else 'WRITE'}) — {len(handlers)} handlers ==")
    for hdir in handlers:
        print(migrate_handler(hdir, check=check))
    return 0


if __name__ == "__main__":
    sys.exit(main())
