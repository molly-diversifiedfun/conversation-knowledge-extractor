"""Tests for prompt builders and JSON recovery."""

import json

from src.prompts import parse_json_response, recover_partial_json


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
