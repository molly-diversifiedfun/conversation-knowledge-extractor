"""Tests for configuration."""

from src.config import Config


def test_default_extraction_core_max_tokens():
    config = Config()
    assert config.extraction_core_max_tokens == 8192


def test_default_extraction_patterns_max_tokens():
    config = Config()
    assert config.extraction_patterns_max_tokens == 8192


def test_legacy_extraction_max_tokens_bumped():
    config = Config()
    assert config.extraction_max_tokens == 8192


def test_config_is_frozen():
    config = Config()
    try:
        config.extraction_core_max_tokens = 999
        assert False, "Should have raised"
    except AttributeError:
        pass
