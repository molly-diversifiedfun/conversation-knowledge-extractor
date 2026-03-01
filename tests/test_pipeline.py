"""Tests for pipeline extraction logic: helpers, single-pass fallback, two-pass, and resume."""

from __future__ import annotations

import json
from dataclasses import replace
from unittest.mock import MagicMock, patch

import pytest

from src.models import ApiResponse, CostTracker, PipelineState
from src.pipeline import (
    _empty_extraction,
    _is_empty_extraction,
    _merge_core_and_patterns,
    _extract_single_pass,
    run_extraction_pass,
)
from src.config import Config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**overrides) -> Config:
    """Create a Config with sensible test defaults."""
    defaults = {
        "api_key": "test-key",
        "input_path": "/tmp/test.json",
        "min_score": 4,
        "extraction_model": "claude-sonnet-4-5-20250929",
        "extraction_core_max_tokens": 8192,
        "extraction_patterns_max_tokens": 8192,
        "extraction_delay": 0.0,
        "sonnet_input_cost": 3.00,
        "sonnet_output_cost": 15.00,
        "cost_limit": 50.0,
        "output_path": "/tmp/output",
        "oversized_threshold": 180_000,
        "chunk_overlap_tokens": 2000,
    }
    defaults.update(overrides)
    return Config(**defaults)


def _make_api_response(
    text: str = "{}",
    input_tokens: int = 100,
    output_tokens: int = 200,
    stop_reason: str = "end_turn",
) -> ApiResponse:
    return ApiResponse(
        text=text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        stop_reason=stop_reason,
    )


# ---------------------------------------------------------------------------
# TestIsEmptyExtraction
# ---------------------------------------------------------------------------


class TestIsEmptyExtraction:
    """Tests for _is_empty_extraction helper."""

    def test_all_empty_returns_true(self):
        """A default empty extraction should be detected as empty."""
        result = _is_empty_extraction(_empty_extraction())
        assert result is True

    def test_with_data_returns_false(self):
        """An extraction with problem_statement set should NOT be empty."""
        extraction = _empty_extraction()
        extraction = {**extraction, "problem_statement": "Build a REST API"}
        result = _is_empty_extraction(extraction)
        assert result is False

    def test_with_only_empty_lists_returns_true(self):
        """All empty strings + empty lists should be empty."""
        extraction = {
            "problem_statement": "",
            "context": "",
            "approach_strategy": "",
            "key_decisions": [],
            "frameworks": [],
            "tags": [],
        }
        result = _is_empty_extraction(extraction)
        assert result is True

    def test_with_nonempty_list_returns_false(self):
        """An extraction with tags: ['python'] should NOT be empty."""
        extraction = _empty_extraction()
        extraction = {**extraction, "tags": ["python"]}
        result = _is_empty_extraction(extraction)
        assert result is False


# ---------------------------------------------------------------------------
# TestMergeCoreAndPatterns
# ---------------------------------------------------------------------------


class TestMergeCoreAndPatterns:
    """Tests for _merge_core_and_patterns helper."""

    def test_non_overlapping_keys_merge(self):
        """Core + patterns merge correctly when keys don't overlap."""
        core = {
            "problem_statement": "Build API",
            "context": "Python project",
            "approach_strategy": "REST",
        }
        patterns = {
            "reusable_patterns": [{"pattern": "decorator"}],
            "tags": ["python", "api"],
        }
        merged = _merge_core_and_patterns(core, patterns)
        assert merged["problem_statement"] == "Build API"
        assert merged["context"] == "Python project"
        assert merged["reusable_patterns"] == [{"pattern": "decorator"}]
        assert merged["tags"] == ["python", "api"]

    def test_handles_none_core(self):
        """None core still produces valid merged dict with patterns applied."""
        patterns = {"tags": ["python"], "reusable_patterns": [{"p": "x"}]}
        merged = _merge_core_and_patterns(None, patterns)
        # Should have _empty_extraction as base, then patterns overlay
        assert merged["tags"] == ["python"]
        assert merged["reusable_patterns"] == [{"p": "x"}]
        # Base fields from _empty_extraction should still be present
        assert "problem_statement" in merged
        assert merged["problem_statement"] == ""

    def test_handles_none_patterns(self):
        """None patterns still produces valid merged dict with core applied."""
        core = {"problem_statement": "Build API", "key_decisions": [{"d": "A"}]}
        merged = _merge_core_and_patterns(core, None)
        assert merged["problem_statement"] == "Build API"
        assert merged["key_decisions"] == [{"d": "A"}]
        # Base fields from _empty_extraction should still be present
        assert "tags" in merged


# ---------------------------------------------------------------------------
# TestExtractSinglePass
# ---------------------------------------------------------------------------


class TestExtractSinglePass:
    """Tests for _extract_single_pass three-tier fallback."""

    def test_normal_parse_on_end_turn(self):
        """stop_reason=end_turn with valid JSON returns parsed result, 1 API call."""
        valid_json = json.dumps({"problem_statement": "test", "context": "ctx"})
        mock_client = MagicMock()
        mock_client.call.return_value = _make_api_response(
            text=valid_json, stop_reason="end_turn",
        )

        result, cost = _extract_single_pass(
            client=mock_client,
            prompt="test prompt",
            model="claude-sonnet-4-5-20250929",
            max_tokens=8192,
            delay=0.0,
            cost=CostTracker(),
            input_cost_per_m=3.0,
            output_cost_per_m=15.0,
            conversation_id="conv-1",
            pass_name="core",
        )

        assert result == {"problem_statement": "test", "context": "ctx"}
        # Only 1 API call should have been made (no retry needed)
        assert mock_client.call.call_count == 1
        # Cost should be tracked
        assert cost.extract_input_tokens == 100
        assert cost.extract_output_tokens == 200

    def test_partial_recovery_on_max_tokens(self):
        """stop_reason=max_tokens with truncated JSON recovers partial fields."""
        truncated_json = '{"problem_statement": "some problem", "context": "some ctx'
        mock_client = MagicMock()
        mock_client.call.return_value = _make_api_response(
            text=truncated_json, stop_reason="max_tokens",
        )

        result, cost = _extract_single_pass(
            client=mock_client,
            prompt="test prompt",
            model="claude-sonnet-4-5-20250929",
            max_tokens=8192,
            delay=0.0,
            cost=CostTracker(),
            input_cost_per_m=3.0,
            output_cost_per_m=15.0,
            conversation_id="conv-1",
            pass_name="core",
        )

        assert result is not None
        assert result["problem_statement"] == "some problem"
        # Only 1 API call — partial recovery succeeds without retry
        assert mock_client.call.call_count == 1


# ---------------------------------------------------------------------------
# TestRunExtractionPassTwoPass
# ---------------------------------------------------------------------------


class TestRunExtractionPassTwoPass:
    """Tests for run_extraction_pass with two-pass (core + patterns)."""

    @patch("src.pipeline.save_checkpoint")
    def test_two_api_calls_per_conversation(self, mock_save):
        """Each conversation should generate 2 API calls (core + patterns), merged correctly."""
        core_json = json.dumps({
            "problem_statement": "Build a widget",
            "context": "Python project",
            "approach_strategy": "iterative",
            "key_decisions": [{"decision": "use Flask"}],
            "frameworks": [],
            "mistakes_and_lessons": [],
        })
        patterns_json = json.dumps({
            "reusable_patterns": [{"pattern": "factory", "description": "factory pattern"}],
            "tools_and_tech": [{"name": "Flask", "usage": "web framework"}],
            "templates_artifacts": [],
            "unfinished_ideas": [],
            "skill_candidates": [],
            "tags": ["python", "flask"],
            "connections_to_other_work": [],
        })

        mock_client = MagicMock()
        # First call returns core, second returns patterns
        mock_client.call.side_effect = [
            _make_api_response(text=core_json, stop_reason="end_turn"),
            _make_api_response(text=patterns_json, stop_reason="end_turn"),
        ]

        from src.models import Conversation

        conv = Conversation(
            conversation_id="conv-1",
            name="Test Conversation",
            created_at="2024-01-01",
            updated_at="2024-01-01",
            message_count=10,
            word_count=500,
            estimated_tokens=650,
            is_oversized=False,
            full_text="[HUMAN]: hello\n[ASSISTANT]: hi there",
        )

        config = _make_config()
        state = PipelineState(
            phase="triage",
            triage_results=(
                {
                    "conversation_id": "conv-1",
                    "name": "Test Conversation",
                    "score": 5,
                    "summary": "Great conversation",
                    "topics": ["python"],
                },
            ),
        )

        result_state = run_extraction_pass(config, mock_client, [conv], state)

        # Should have made exactly 2 API calls (core + patterns)
        assert mock_client.call.call_count == 2

        # Should have 1 extraction result
        assert len(result_state.extractions) == 1
        extraction = result_state.extractions[0]["extraction"]

        # Core fields present
        assert extraction["problem_statement"] == "Build a widget"
        assert extraction["context"] == "Python project"

        # Pattern fields present
        assert len(extraction["reusable_patterns"]) == 1
        assert extraction["tags"] == ["python", "flask"]


# ---------------------------------------------------------------------------
# TestResumeWithFailedDetection
# ---------------------------------------------------------------------------


class TestResumeWithFailedDetection:
    """Tests for resume logic that detects and retries empty extractions."""

    @patch("src.pipeline.save_checkpoint")
    def test_empty_extraction_included_in_retry_set(self, mock_save):
        """An empty extraction gets re-processed on resume."""
        # Set up a state with one empty extraction (all fields blank)
        empty_ext = _empty_extraction()
        existing_extractions = (
            {
                "conversation_id": "conv-failed",
                "name": "Failed Conversation",
                "created_at": "2024-01-01",
                "triage_score": 5,
                "triage_summary": "Should have data",
                "triage_topics": ["python"],
                "extraction": empty_ext,
            },
        )

        core_json = json.dumps({
            "problem_statement": "Now it works",
            "context": "retry success",
            "approach_strategy": "retried",
            "key_decisions": [],
            "frameworks": [],
            "mistakes_and_lessons": [],
        })
        patterns_json = json.dumps({
            "reusable_patterns": [],
            "tools_and_tech": [],
            "templates_artifacts": [],
            "unfinished_ideas": [],
            "skill_candidates": [],
            "tags": ["retry"],
            "connections_to_other_work": [],
        })

        mock_client = MagicMock()
        mock_client.call.side_effect = [
            _make_api_response(text=core_json, stop_reason="end_turn"),
            _make_api_response(text=patterns_json, stop_reason="end_turn"),
        ]

        from src.models import Conversation

        conv = Conversation(
            conversation_id="conv-failed",
            name="Failed Conversation",
            created_at="2024-01-01",
            updated_at="2024-01-01",
            message_count=10,
            word_count=500,
            estimated_tokens=650,
            is_oversized=False,
            full_text="[HUMAN]: hello\n[ASSISTANT]: world",
        )

        config = _make_config()
        state = PipelineState(
            phase="extraction",
            triage_results=(
                {
                    "conversation_id": "conv-failed",
                    "name": "Failed Conversation",
                    "score": 5,
                    "summary": "Should have data",
                    "topics": ["python"],
                },
            ),
            extractions=existing_extractions,
        )

        result_state = run_extraction_pass(config, mock_client, [conv], state)

        # Should have retried (2 API calls for core + patterns)
        assert mock_client.call.call_count == 2

        # The extraction should now have real data
        assert len(result_state.extractions) == 1
        extraction = result_state.extractions[0]["extraction"]
        assert extraction["problem_statement"] == "Now it works"

    @patch("src.pipeline.save_checkpoint")
    def test_successful_extraction_not_retried(self, mock_save):
        """An extraction with real data is skipped on resume."""
        good_extraction = {
            **_empty_extraction(),
            "problem_statement": "Build a REST API",
            "tags": ["python", "api"],
        }
        existing_extractions = (
            {
                "conversation_id": "conv-good",
                "name": "Good Conversation",
                "created_at": "2024-01-01",
                "triage_score": 5,
                "triage_summary": "Already extracted",
                "triage_topics": ["python"],
                "extraction": good_extraction,
            },
        )

        mock_client = MagicMock()

        from src.models import Conversation

        conv = Conversation(
            conversation_id="conv-good",
            name="Good Conversation",
            created_at="2024-01-01",
            updated_at="2024-01-01",
            message_count=10,
            word_count=500,
            estimated_tokens=650,
            is_oversized=False,
            full_text="[HUMAN]: hello\n[ASSISTANT]: world",
        )

        config = _make_config()
        state = PipelineState(
            phase="extraction",
            triage_results=(
                {
                    "conversation_id": "conv-good",
                    "name": "Good Conversation",
                    "score": 5,
                    "summary": "Already extracted",
                    "topics": ["python"],
                },
            ),
            extractions=existing_extractions,
        )

        result_state = run_extraction_pass(config, mock_client, [conv], state)

        # Should NOT have made any API calls — extraction was already successful
        assert mock_client.call.call_count == 0

        # Should still have the same extraction
        assert len(result_state.extractions) == 1
        extraction = result_state.extractions[0]["extraction"]
        assert extraction["problem_statement"] == "Build a REST API"
