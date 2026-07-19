"""Tests for configuration schema synchronization

This module tests the Phase 2 implementation of configuration schema
synchronization and auto-generation functionality.

Tests:
- Schema synchronization across all registries
- Component schema coverage completeness
- Auto-generated registry functionality
- Configuration widget generation for all sections
- Schema validation report generation
"""

import pytest
import inspect
from typing import Type
from pydantic import BaseModel

from locveil_voice.config.auto_registry import AutoSchemaRegistry
from locveil_voice.config.models import CoreConfig, ComponentConfig


class TestSchemaSync:
    """Test schema synchronization across all registries"""

    def test_section_models_completeness(self):
        """Verify all CoreConfig fields have corresponding section models"""
        section_models = AutoSchemaRegistry.get_section_models()
        core_config_fields = set(CoreConfig.model_fields.keys())

        expected_sections = set()
        for field_name, field_info in CoreConfig.model_fields.items():
            if hasattr(field_info, 'annotation'):
                annotation = field_info.annotation
                if (inspect.isclass(annotation) and
                    issubclass(annotation, BaseModel) and
                    annotation != BaseModel):
                    expected_sections.add(field_name)

        section_model_fields = set(section_models.keys())

        missing_sections = expected_sections - section_model_fields
        assert not missing_sections, f"Missing section models: {missing_sections}"

        extra_sections = section_model_fields - expected_sections
        assert not extra_sections, f"Extra section models: {extra_sections}"

    def test_component_schema_coverage(self):
        """Verify all components have corresponding schemas (QUAL-85: minus the ones that
        have no config section by design)"""
        component_schemas = AutoSchemaRegistry.get_component_schemas()
        component_fields = set(ComponentConfig.model_fields.keys())
        schema_fields = set(component_schemas.keys())

        missing_schemas = (component_fields - schema_fields
                           - AutoSchemaRegistry._SECTIONLESS_COMPONENTS)
        assert not missing_schemas, f"Components without schemas: {missing_schemas}"

    def test_no_manual_sync_required(self):
        """Verify auto-generated registries work correctly"""
        section_models = AutoSchemaRegistry.get_section_models()

        # Verify critical sections are auto-discovered
        assert "vad" in section_models, "VADConfig should be auto-discovered"
        assert "monitoring" in section_models, "MonitoringConfig should be auto-discovered"
        assert "nlu_analysis" in section_models, "NLUAnalysisConfig should be auto-discovered"

    def test_schema_validation_report(self):
        """Verify schema validation report generation"""
        report = AutoSchemaRegistry.validate_schema_coverage()

        assert isinstance(report, dict)
        assert "valid" in report
        assert "warnings" in report
        assert "errors" in report
        assert "recommendations" in report

        # After Phase 2, schema validation should pass
        assert report["valid"], f"Schema validation failed: {report}"


class TestConfigurationWidgetGeneration:
    """Test configuration widget generation for all sections"""

    def test_widget_generation_coverage(self):
        """Verify widgets can be generated for all configuration sections"""
        from locveil_voice.components.configuration_component import ConfigurationComponent

        config_component = ConfigurationComponent()
        section_models = AutoSchemaRegistry.get_section_models()

        for section_name in section_models.keys():
            model = config_component._get_section_model(section_name)
            assert model is not None, f"Widget generation failed for: {section_name}"

    def test_schema_extraction(self):
        """Verify schema extraction works for all sections"""
        from locveil_voice.components.configuration_component import ConfigurationComponent

        config_component = ConfigurationComponent()
        schema = config_component._extract_config_schema()

        assert isinstance(schema, dict)
        assert len(schema) > 0, "Schema extraction returned empty result"

        # Verify critical sections are present
        required_sections = ["system", "vad", "monitoring", "nlu_analysis"]
        for section in required_sections:
            assert section in schema, f"Required section missing: {section}"


class TestComponentSchemas:
    """QUAL-85: component schemas are DERIVED — each component flag maps to its real
    CoreConfig section model, so drift between the two is structurally impossible."""

    def test_component_schemas_are_the_section_models(self):
        component_schemas = AutoSchemaRegistry.get_component_schemas()
        section_models = AutoSchemaRegistry.get_section_models()

        for name, schema in component_schemas.items():
            assert schema is section_models[name], (
                f"component '{name}' schema must BE its CoreConfig section model")

        # the ones the old hand-written tree covered are still covered
        assert "monitoring" in component_schemas
        assert "nlu_analysis" in component_schemas

    def test_sectionless_component_is_deliberate(self):
        """`configuration` has no config section by design (the flag is its entire config)."""
        component_schemas = AutoSchemaRegistry.get_component_schemas()
        assert "configuration" not in component_schemas
        assert "configuration" in AutoSchemaRegistry._SECTIONLESS_COMPONENTS

    def test_component_validation_uses_real_models(self):
        """validate_component_config now validates against models.py truth."""
        assert AutoSchemaRegistry.validate_component_config(
            "monitoring", {"metrics_enabled": True})

        # a type error the real model catches (a REAL field — the old hand-written stubs
        # carried fields like dashboard_enabled that models.py deleted long ago)
        assert not AutoSchemaRegistry.validate_component_config(
            "monitoring", {"metrics_enabled": "not_a_boolean"})

        # unknown component
        assert not AutoSchemaRegistry.validate_component_config(
            "no_such_component", {"enabled": True})

    def test_voice_trigger_schema_speaks_wake_word_spec(self):
        """The old hand tree declared wake_words as a string list, predating WakeWordSpec —
        the derived schema is the real model, so the real shape is enforced."""
        schema = AutoSchemaRegistry.get_component_schemas()["voice_trigger"]
        assert not AutoSchemaRegistry.validate_component_config(
            "voice_trigger", {"wake_words": ["irene", "jarvis"]}), \
            "bare-string wake words must not validate (WakeWordSpec objects required)"
        assert AutoSchemaRegistry.validate_component_config(
            "voice_trigger",
            {"wake_words": [{"name": "irene", "model": "irina"}]})
        assert schema.__name__ == "VoiceTriggerConfig"


class TestMasterConfigCompleteness:
    """Test master configuration completeness validation"""

    def test_master_config_coverage_reporting(self):
        """Test master config completeness reporting"""
        report = AutoSchemaRegistry.get_master_config_completeness()

        assert isinstance(report, dict)
        assert "missing_sections" in report
        assert "orphaned_sections" in report
        assert "coverage_percentage" in report
        assert "valid" in report

        # Coverage should be a valid percentage
        assert 0 <= report["coverage_percentage"] <= 100

    def test_schema_coverage_after_phase2(self):
        """Test that schema coverage improves after Phase 2"""
        report = AutoSchemaRegistry.validate_schema_coverage()

        # After Phase 2, component schema coverage should be complete
        assert report["valid"], f"Schema validation should pass after Phase 2: {report}"

        # Should not have component schema errors anymore
        for error in report.get("errors", []):
            assert "Components without schemas" not in error, f"Component schema error still exists: {error}"


if __name__ == "__main__":
    pytest.main([__file__])


class TestConfigurableComponentSections:
    """UI-16 (review E7): the backend-owned component roster the frontend derives from."""

    def test_map_keys_are_real_sections_and_component_flags(self):
        from locveil_voice.components.configuration_component import CONFIGURABLE_COMPONENT_SECTIONS
        section_models = AutoSchemaRegistry.get_section_models()
        component_flags = set(ComponentConfig.model_fields.keys())
        for section in CONFIGURABLE_COMPONENT_SECTIONS:
            assert section in section_models, f"{section} is not a CoreConfig section"
            assert section in component_flags, f"{section} has no ComponentConfig flag"

    def test_widget_hints_survive_schema_extraction(self):
        """The declared widget hints must reach the payload config-ui consumes (E9)."""
        schema = AutoSchemaRegistry._extract_model_schema(
            AutoSchemaRegistry.get_section_model('tts'))
        assert schema['fields']['default_provider'].get('widget') == 'provider_select'
        mic_inputs = AutoSchemaRegistry._extract_model_schema(
            AutoSchemaRegistry.get_section_model('inputs'))
        mic = mic_inputs['fields']['microphone_config']['properties']
        assert mic['device_id'].get('widget') == 'microphone_select'
        assert mic['sample_rate'].get('widget') == 'readonly'
        assert mic_inputs['fields']['default_input'].get('widget') == 'input_select'
