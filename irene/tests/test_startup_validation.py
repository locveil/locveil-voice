"""Unit tests for QUAL-23 startup provider-name validation.

Fast, offline, deterministic — drives `validate_provider_configuration` with
synthetic config dicts (no boot). Relies on the real registered entry-points
in the installed venv (llm: openai/vsegpt/anthropic; nlu: hybrid_keyword_matcher/
spacy_nlu; tts: console/...).
"""

from irene.core.startup_validation import validate_provider_configuration


def test_flags_phantom_llm_console():
    """The `console` LLM provider is configured but unregistered (QUAL-14/15)."""
    cfg = {
        "llm": {
            "enabled": True,
            "default_provider": "openai",
            "fallback_providers": ["console"],
            "providers": {"openai": {"enabled": True}, "console": {"enabled": True}},
        }
    }
    issues = validate_provider_configuration(cfg)
    assert any("provider 'console'" in i and i.startswith("llm.") for i in issues), issues
    # a real provider must NOT be flagged (note: it still appears in the "available: [...]" list)
    assert not any("provider 'openai'" in i for i in issues), issues


def test_all_good_names_no_issues():
    cfg = {
        "llm": {"enabled": True, "default_provider": "openai", "fallback_providers": []},
        "nlu": {"enabled": True, "provider_cascade_order": ["hybrid_keyword_matcher", "spacy_nlu"]},
        # tts `console` IS a registered entry-point — must not be flagged
        "tts": {"enabled": True, "default_provider": "console", "fallback_providers": ["console"]},
    }
    assert validate_provider_configuration(cfg) == []


def test_disabled_component_is_skipped():
    cfg = {"llm": {"enabled": False, "fallback_providers": ["does_not_exist"]}}
    assert validate_provider_configuration(cfg) == []


def test_flags_bad_nlu_cascade_name():
    """The historical bad cascade default name (QUAL-10) must be caught when configured."""
    cfg = {"nlu": {"enabled": True, "provider_cascade_order": ["keyword_matcher", "spacy_nlu"]}}
    issues = validate_provider_configuration(cfg)
    assert any("provider 'keyword_matcher'" in i for i in issues), issues
    assert not any("provider 'spacy_nlu'" in i for i in issues), issues
