"""Tests for prompt builders and JSON recovery."""

import json

from src.prompts import (
    build_core_extraction_prompt,
    build_patterns_extraction_prompt,
    parse_json_response,
    recover_partial_json,
)


class TestRecoverPartialJson:
    """Test the three-tier partial JSON recovery."""

    def test_valid_json_passes_through(self):
        data = {"problem_statement": "test", "key_decisions": [{"decision": "A"}]}
        result = recover_partial_json(json.dumps(data))
        assert result == data

    def test_truncated_string_value(self):
        truncated = '{"problem_statement": "some long text that got cut o'
        result = recover_partial_json(truncated)
        assert result is not None
        assert "problem_statement" in result

    def test_truncated_after_complete_fields(self):
        truncated = (
            '{"problem_statement": "test problem", '
            '"context": "some context", '
            '"approach_strategy": "the approach'
        )
        result = recover_partial_json(truncated)
        assert result is not None
        assert result["problem_statement"] == "test problem"
        assert result["context"] == "some context"

    def test_truncated_inside_array(self):
        truncated = (
            '{"problem_statement": "ok", "key_decisions": '
            '[{"decision": "A", "reasoning": "because"}, '
            '{"decision": "B", "reason'
        )
        result = recover_partial_json(truncated)
        assert result is not None
        assert result["problem_statement"] == "ok"
        assert len(result.get("key_decisions", [])) >= 1

    def test_completely_unrecoverable_returns_none(self):
        result = recover_partial_json("this is not json at all")
        assert result is None

    def test_empty_string_returns_none(self):
        result = recover_partial_json("")
        assert result is None

    def test_markdown_fenced_json(self):
        text = '```json\n{"problem_statement": "test"}\n```'
        result = recover_partial_json(text)
        assert result is not None
        assert result["problem_statement"] == "test"

    def test_truncated_with_markdown_fence(self):
        text = '```json\n{"problem_statement": "test", "context": "good stu'
        result = recover_partial_json(text)
        assert result is not None
        assert result["problem_statement"] == "test"


class TestParseJsonResponse:
    def test_clean_json(self):
        result = parse_json_response('{"a": 1}')
        assert result == {"a": 1}

    def test_markdown_fenced(self):
        result = parse_json_response('```json\n{"a": 1}\n```')
        assert result == {"a": 1}


class TestCoreExtractionPrompt:

    def test_contains_required_fields(self):
        prompt = build_core_extraction_prompt(
            name="Test Conv",
            triage_score=4,
            triage_summary="A test conversation",
            triage_topics=("python", "testing"),
            full_text="[HUMAN]: hello\n[ASSISTANT]: hi",
        )
        for field in [
            "problem_statement", "context", "approach_strategy",
            "key_decisions", "frameworks", "mistakes_and_lessons",
        ]:
            assert field in prompt

    def test_does_not_contain_patterns_fields(self):
        prompt = build_core_extraction_prompt(
            name="Test", triage_score=4, triage_summary="test",
            triage_topics=(), full_text="text",
        )
        assert '"reusable_patterns"' not in prompt
        assert '"tools_and_tech"' not in prompt
        assert '"skill_candidates"' not in prompt

    def test_includes_chunk_info(self):
        prompt = build_core_extraction_prompt(
            name="Test", triage_score=4, triage_summary="test",
            triage_topics=(), full_text="text",
            chunk_info={"is_chunked": True, "chunk_index": 0, "total_chunks": 3, "original_tokens": 200000},
        )
        assert "chunk 1 of 3" in prompt


class TestPatternsExtractionPrompt:

    def test_contains_required_fields(self):
        prompt = build_patterns_extraction_prompt(
            name="Test Conv",
            triage_score=4,
            triage_summary="A test conversation",
            triage_topics=("python",),
            full_text="[HUMAN]: hello",
            core_extraction={"problem_statement": "test problem", "approach_strategy": "test approach"},
        )
        for field in [
            "reusable_patterns", "tools_and_tech", "templates_artifacts",
            "unfinished_ideas", "skill_candidates", "tags", "connections_to_other_work",
        ]:
            assert field in prompt

    def test_includes_core_context(self):
        prompt = build_patterns_extraction_prompt(
            name="Test", triage_score=4, triage_summary="test",
            triage_topics=(), full_text="text",
            core_extraction={"problem_statement": "building a widget"},
        )
        assert "building a widget" in prompt

    def test_does_not_contain_core_fields_in_json_schema(self):
        prompt = build_patterns_extraction_prompt(
            name="Test", triage_score=4, triage_summary="test",
            triage_topics=(), full_text="text",
            core_extraction={},
        )
        # The JSON schema section should NOT have core fields
        # Find the JSON schema part (after "Respond with ONLY")
        schema_start = prompt.find("Respond with ONLY")
        schema_section = prompt[schema_start:] if schema_start >= 0 else prompt
        assert '"problem_statement"' not in schema_section
        assert '"approach_strategy"' not in schema_section
