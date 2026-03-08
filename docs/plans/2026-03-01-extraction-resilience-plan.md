# Extraction Resilience Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the 79% extraction failure rate by splitting extraction into two focused API calls, adding partial JSON recovery, retry-on-truncation logic, and resume-with-failed detection.

**Architecture:** Replace the monolithic 12-field extraction prompt with two focused passes (Core Analysis: 6 fields, Patterns & Skills: 7 fields), each capped at 8192 max_tokens. Add `stop_reason` detection, partial JSON recovery, and a three-tier fallback (normal parse → partial recovery → retry with conciseness hint). Enhance `--resume` to detect and re-process empty extractions.

**Tech Stack:** Python 3.13, anthropic SDK, frozen dataclasses, pytest

---

### Task 1: Add pytest and test infrastructure

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Step 1: Add pytest to dev dependencies and configure it**

```toml
# In pyproject.toml, add after [project.scripts]:

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 2: Create test package and conftest**

```python
# tests/__init__.py
# (empty)
```

```python
# tests/conftest.py
"""Shared fixtures for the test suite."""
```

**Step 3: Install dev dependencies**

Run: `pip install -e ".[dev]"`
Expected: Successfully installed pytest

**Step 4: Verify pytest runs with no tests**

Run: `python -m pytest -v`
Expected: "no tests ran" / exit 0

**Step 5: Commit**

```bash
git add pyproject.toml tests/
git commit -m "chore: add pytest infrastructure"
```

---

### Task 2: Add `stop_reason` to `ApiResponse`

**Files:**
- Modify: `src/models.py:67-72`
- Modify: `src/api_client.py:61-65`
- Create: `tests/test_models.py`
- Create: `tests/test_api_client.py`

**Step 1: Write test for ApiResponse with stop_reason**

```python
# tests/test_models.py
"""Tests for data models."""

from src.models import ApiResponse


def test_api_response_includes_stop_reason():
    resp = ApiResponse(
        text="hello",
        input_tokens=10,
        output_tokens=5,
        stop_reason="end_turn",
    )
    assert resp.stop_reason == "end_turn"
    assert resp.text == "hello"


def test_api_response_is_frozen():
    resp = ApiResponse(text="hi", input_tokens=1, output_tokens=1, stop_reason="end_turn")
    try:
        resp.text = "changed"  # type: ignore[misc]
        assert False, "Should have raised FrozenInstanceError"
    except AttributeError:
        pass


def test_api_response_max_tokens_stop_reason():
    resp = ApiResponse(
        text='{"partial": "json',
        input_tokens=100,
        output_tokens=4096,
        stop_reason="max_tokens",
    )
    assert resp.stop_reason == "max_tokens"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL — `TypeError: ApiResponse.__init__() got an unexpected keyword argument 'stop_reason'`

**Step 3: Add `stop_reason` field to ApiResponse**

In `src/models.py`, replace:

```python
@dataclass(frozen=True)
class ApiResponse:
    """Response from an Anthropic API call."""

    text: str
    input_tokens: int
    output_tokens: int
```

With:

```python
@dataclass(frozen=True)
class ApiResponse:
    """Response from an Anthropic API call."""

    text: str
    input_tokens: int
    output_tokens: int
    stop_reason: str = "end_turn"
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_models.py -v`
Expected: 3 passed

**Step 5: Write test for api_client passing stop_reason through**

```python
# tests/test_api_client.py
"""Tests for API client stop_reason capture."""

from unittest.mock import MagicMock, patch

from src.api_client import ApiClient
from src.models import ApiResponse


def _make_mock_response(text="hello", stop_reason="end_turn", input_tokens=10, output_tokens=5):
    """Create a mock Anthropic API response."""
    resp = MagicMock()
    resp.content = [MagicMock(text=text)]
    resp.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    resp.stop_reason = stop_reason
    return resp


@patch("src.api_client.anthropic.Anthropic")
def test_call_captures_end_turn(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_mock_response(
        text='{"ok": true}', stop_reason="end_turn"
    )

    client = ApiClient(api_key="test-key")
    result = client.call(
        model="test-model", max_tokens=100, temperature=0,
        prompt="test", rate_limit_gap=0,
    )

    assert isinstance(result, ApiResponse)
    assert result.stop_reason == "end_turn"
    assert result.text == '{"ok": true}'


@patch("src.api_client.anthropic.Anthropic")
def test_call_captures_max_tokens(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = _make_mock_response(
        text='{"truncated": "js', stop_reason="max_tokens"
    )

    client = ApiClient(api_key="test-key")
    result = client.call(
        model="test-model", max_tokens=100, temperature=0,
        prompt="test", rate_limit_gap=0,
    )

    assert result.stop_reason == "max_tokens"
```

**Step 6: Run test to verify it fails**

Run: `python -m pytest tests/test_api_client.py -v`
Expected: FAIL — `stop_reason` not in ApiResponse constructor call

**Step 7: Capture stop_reason in api_client.py**

In `src/api_client.py`, replace lines 61-65:

```python
                return ApiResponse(
                    text=response.content[0].text,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                )
```

With:

```python
                return ApiResponse(
                    text=response.content[0].text,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    stop_reason=response.stop_reason,
                )
```

**Step 8: Run all tests to verify they pass**

Run: `python -m pytest tests/ -v`
Expected: 5 passed

**Step 9: Commit**

```bash
git add src/models.py src/api_client.py tests/test_models.py tests/test_api_client.py
git commit -m "feat: capture stop_reason from Anthropic API in ApiResponse"
```

---

### Task 3: Update Config with split extraction max tokens

**Files:**
- Modify: `src/config.py:33`
- Create: `tests/test_config.py`

**Step 1: Write tests for new config fields**

```python
# tests/test_config.py
"""Tests for configuration."""

from src.config import Config


def test_default_extraction_core_max_tokens():
    config = Config()
    assert config.extraction_core_max_tokens == 8192


def test_default_extraction_patterns_max_tokens():
    config = Config()
    assert config.extraction_patterns_max_tokens == 8192


def test_legacy_extraction_max_tokens_bumped():
    """The old single field should be bumped to 8192 too."""
    config = Config()
    assert config.extraction_max_tokens == 8192


def test_config_is_frozen():
    config = Config()
    try:
        config.extraction_core_max_tokens = 999  # type: ignore[misc]
        assert False, "Should have raised"
    except AttributeError:
        pass
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `extraction_core_max_tokens` not found

**Step 3: Add split extraction fields and bump default**

In `src/config.py`, replace:

```python
    extraction_max_tokens: int = 4096
```

With:

```python
    extraction_max_tokens: int = 8192
    extraction_core_max_tokens: int = 8192
    extraction_patterns_max_tokens: int = 8192
```

Also add these to the `build_config` function where the defaults section is (after line 101), alongside the existing `extraction_max_tokens`:

```python
        extraction_core_max_tokens=defaults.extraction_core_max_tokens,
        extraction_patterns_max_tokens=defaults.extraction_patterns_max_tokens,
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: add split extraction max token config (core + patterns at 8192)"
```

---

### Task 4: Add `recover_partial_json()`

**Files:**
- Modify: `src/prompts.py`
- Create: `tests/test_prompts.py`

**Step 1: Write tests for partial JSON recovery**

```python
# tests/test_prompts.py
"""Tests for prompt builders and JSON recovery."""

import json

from src.prompts import parse_json_response, recover_partial_json


class TestRecoverPartialJson:
    """Test the three-tier partial JSON recovery."""

    def test_valid_json_passes_through(self):
        """Tier 1: Valid JSON returns as-is."""
        data = {"problem_statement": "test", "key_decisions": [{"decision": "A"}]}
        result = recover_partial_json(json.dumps(data))
        assert result == data

    def test_truncated_string_value(self):
        """Tier 2: JSON truncated mid-string gets closing braces appended."""
        truncated = '{"problem_statement": "some long text that got cut o'
        result = recover_partial_json(truncated)
        assert result is not None
        assert "problem_statement" in result

    def test_truncated_after_complete_fields(self):
        """Tier 2: JSON with complete fields then truncated mid-next-field."""
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
        """Tier 2: JSON truncated inside an array of objects."""
        truncated = (
            '{"problem_statement": "ok", "key_decisions": '
            '[{"decision": "A", "reasoning": "because"}, '
            '{"decision": "B", "reason'
        )
        result = recover_partial_json(truncated)
        assert result is not None
        assert result["problem_statement"] == "ok"
        # Should recover at least the first complete array item
        assert len(result.get("key_decisions", [])) >= 1

    def test_completely_unrecoverable_returns_none(self):
        """Tier 3: Gibberish returns None."""
        result = recover_partial_json("this is not json at all")
        assert result is None

    def test_empty_string_returns_none(self):
        result = recover_partial_json("")
        assert result is None

    def test_markdown_fenced_json(self):
        """Should handle markdown-fenced JSON (like parse_json_response)."""
        text = '```json\n{"problem_statement": "test"}\n```'
        result = recover_partial_json(text)
        assert result is not None
        assert result["problem_statement"] == "test"

    def test_truncated_with_markdown_fence(self):
        """Truncated JSON that started with a markdown fence."""
        text = '```json\n{"problem_statement": "test", "context": "good stu'
        result = recover_partial_json(text)
        assert result is not None
        assert result["problem_statement"] == "test"


class TestParseJsonResponse:
    """Existing parse_json_response should still work."""

    def test_clean_json(self):
        result = parse_json_response('{"a": 1}')
        assert result == {"a": 1}

    def test_markdown_fenced(self):
        result = parse_json_response('```json\n{"a": 1}\n```')
        assert result == {"a": 1}
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_prompts.py -v`
Expected: FAIL — `ImportError: cannot import name 'recover_partial_json'`

**Step 3: Implement `recover_partial_json()`**

Add this function to `src/prompts.py`, after the `parse_json_response` function:

```python
def recover_partial_json(text: str) -> dict | None:
    """Attempt to recover a usable dict from truncated JSON.

    Three-tier recovery:
    1. Try json.loads() directly (fast path for valid JSON).
    2. Try closing open braces/brackets to repair truncation.
    3. Fall back to regex extraction of complete top-level key-value pairs.

    Returns None if truly unrecoverable.
    """
    if not text or not text.strip():
        return None

    # Strip markdown fences
    cleaned = re.sub(r"^```(?:json)?\n?", "", text.strip())
    cleaned = re.sub(r"\n?```$", "", cleaned).strip()

    if not cleaned:
        return None

    # Tier 1: Try direct parse
    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
        return None
    except json.JSONDecodeError:
        pass

    # Tier 2: Try closing open structures
    repaired = _repair_truncated_json(cleaned)
    if repaired is not None:
        return repaired

    # Tier 3: Regex extraction of complete key-value pairs
    return _regex_extract_fields(cleaned)


def _repair_truncated_json(text: str) -> dict | None:
    """Try to repair truncated JSON by closing open structures."""
    # Remove any trailing incomplete string (unmatched quote)
    # Find the last complete value boundary
    # Strategy: progressively truncate from the end and try adding closers

    # First, try to find a good truncation point
    # Look for the last complete key-value separator (comma after a value)
    for trim_pattern in [
        # Remove trailing partial string value and close
        r',\s*"[^"]*":\s*"[^"]*$',
        # Remove trailing partial after colon
        r',\s*"[^"]*":\s*[^,}\]]*$',
        # Remove trailing partial array item
        r',\s*\{[^}]*$',
    ]:
        match = re.search(trim_pattern, text)
        if match:
            trimmed = text[: match.start()]
            result = _try_close(trimmed)
            if result is not None:
                return result

    # Try just adding closing characters directly
    return _try_close(text)


def _try_close(text: str) -> dict | None:
    """Try adding closing braces/brackets to make valid JSON."""
    # Count open/close pairs
    for suffix in [
        '"}',       # close string + object
        "}",        # close object
        '"]}',      # close string + array + object
        "]}",       # close array + object
        '"]}]}',    # close nested
        "}]}",      # close object + array + object
        '"]}}',     # close string + array + nested objects
        "}}",       # close nested objects
    ]:
        try:
            result = json.loads(text + suffix)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            continue
    return None


def _regex_extract_fields(text: str) -> dict | None:
    """Last resort: extract complete key-value pairs with regex."""
    result = {}

    # Match "key": "string_value" pairs
    string_pairs = re.findall(
        r'"(\w+)"\s*:\s*"((?:[^"\\]|\\.)*)"',
        text,
    )
    for key, value in string_pairs:
        if key not in result:
            result[key] = value

    # Match "key": [...] complete array pairs
    # Find arrays by matching balanced brackets
    array_pattern = re.finditer(r'"(\w+)"\s*:\s*(\[)', text)
    for match in array_pattern:
        key = match.group(1)
        if key in result:
            continue
        start = match.start(2)
        depth = 0
        end = start
        for idx in range(start, len(text)):
            if text[idx] == "[":
                depth += 1
            elif text[idx] == "]":
                depth -= 1
                if depth == 0:
                    end = idx + 1
                    break
        if depth == 0 and end > start:
            try:
                arr = json.loads(text[start:end])
                result[key] = arr
            except json.JSONDecodeError:
                pass

    return result if result else None
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_prompts.py -v`
Expected: All tests pass (some Tier 2/3 recovery tests may need adjustment)

**Step 5: Iterate on any failing recovery tests**

If a specific truncation pattern isn't recovered, adjust `_repair_truncated_json` suffix list. The goal is pragmatic recovery, not perfection.

**Step 6: Commit**

```bash
git add src/prompts.py tests/test_prompts.py
git commit -m "feat: add recover_partial_json with three-tier truncation recovery"
```

---

### Task 5: Split extraction prompt into two passes

**Files:**
- Modify: `src/prompts.py:58-120`
- Modify: `tests/test_prompts.py`

**Step 1: Write tests for split prompt builders**

Add to `tests/test_prompts.py`:

```python
from src.prompts import (
    build_core_extraction_prompt,
    build_patterns_extraction_prompt,
)


class TestCoreExtractionPrompt:
    """Tests for the core analysis prompt (6 fields)."""

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
        # These belong in the patterns prompt, not core
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
    """Tests for the patterns & skills prompt (7 fields)."""

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
        """Should include the core extraction output as context."""
        prompt = build_patterns_extraction_prompt(
            name="Test", triage_score=4, triage_summary="test",
            triage_topics=(), full_text="text",
            core_extraction={"problem_statement": "building a widget"},
        )
        assert "building a widget" in prompt

    def test_does_not_contain_core_fields(self):
        prompt = build_patterns_extraction_prompt(
            name="Test", triage_score=4, triage_summary="test",
            triage_topics=(), full_text="text",
            core_extraction={},
        )
        # These belong in core, not patterns
        assert '"problem_statement"' not in prompt
        assert '"approach_strategy"' not in prompt
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_prompts.py::TestCoreExtractionPrompt -v`
Expected: FAIL — `ImportError: cannot import name 'build_core_extraction_prompt'`

**Step 3: Implement split prompt builders**

Add after the existing `build_extraction_prompt` function in `src/prompts.py` (keep the old one for backward compatibility during transition):

```python
def build_core_extraction_prompt(
    name: str,
    triage_score: int,
    triage_summary: str,
    triage_topics: tuple[str, ...] | list[str],
    full_text: str,
    chunk_info: dict | None = None,
) -> str:
    """Build Pass 2a: Core Analysis extraction prompt (6 fields)."""
    chunk_context = ""
    if chunk_info and chunk_info.get("is_chunked"):
        chunk_context = (
            f"\n\nIMPORTANT: This is chunk {chunk_info['chunk_index'] + 1} "
            f"of {chunk_info['total_chunks']} from a large conversation "
            f"({chunk_info['original_tokens']} total tokens). "
            f"Extract knowledge from THIS chunk. Results will be merged later."
        )

    topics_str = ", ".join(triage_topics) if triage_topics else ""

    return f"""You are an expert knowledge extraction agent. Extract the CORE ANALYSIS from this Claude AI conversation.{chunk_context}

CONVERSATION TITLE: {name}
TRIAGE SCORE: {triage_score}/5
TRIAGE SUMMARY: {triage_summary}
TRIAGE TOPICS: {topics_str}

CONVERSATION:
{full_text}

Extract the following core analysis fields. Be thorough but concise. Respond with ONLY a valid JSON object (no markdown fences):
{{
  "problem_statement": "<what problem or goal initiated this conversation>",
  "context": "<relevant background and constraints>",
  "approach_strategy": "<high-level approach or strategy developed>",
  "key_decisions": [
    {{"decision": "<what was decided>", "reasoning": "<why>", "alternatives_considered": ["<alt1>"]}}
  ],
  "frameworks": [
    {{"name": "<framework name>", "description": "<what it does>", "steps": ["<step1>", "<step2>"], "when_to_use": "<conditions>"}}
  ],
  "mistakes_and_lessons": [
    {{"mistake": "<what went wrong>", "lesson": "<what was learned>", "prevention": "<how to avoid>"}}
  ]
}}"""


def build_patterns_extraction_prompt(
    name: str,
    triage_score: int,
    triage_summary: str,
    triage_topics: tuple[str, ...] | list[str],
    full_text: str,
    core_extraction: dict,
    chunk_info: dict | None = None,
) -> str:
    """Build Pass 2b: Patterns & Skills extraction prompt (7 fields)."""
    chunk_context = ""
    if chunk_info and chunk_info.get("is_chunked"):
        chunk_context = (
            f"\n\nIMPORTANT: This is chunk {chunk_info['chunk_index'] + 1} "
            f"of {chunk_info['total_chunks']} from a large conversation "
            f"({chunk_info['original_tokens']} total tokens). "
            f"Extract knowledge from THIS chunk. Results will be merged later."
        )

    topics_str = ", ".join(triage_topics) if triage_topics else ""
    core_context = json.dumps(core_extraction, indent=1) if core_extraction else "{}"

    return f"""You are an expert knowledge extraction agent. Extract PATTERNS, TOOLS, and SKILLS from this Claude AI conversation.{chunk_context}

CONVERSATION TITLE: {name}
TRIAGE SCORE: {triage_score}/5
TRIAGE SUMMARY: {triage_summary}
TRIAGE TOPICS: {topics_str}

ALREADY EXTRACTED (do not duplicate):
{core_context}

CONVERSATION:
{full_text}

Extract the following pattern and skill fields. Do NOT duplicate information already extracted above. Respond with ONLY a valid JSON object (no markdown fences):
{{
  "reusable_patterns": [
    {{"pattern": "<pattern name>", "description": "<what it is>", "example": "<brief example>", "reusability": "high|medium|low"}}
  ],
  "tools_and_tech": [
    {{"name": "<tool/technology>", "usage": "<how it was used>", "proficiency": "learning|competent|proficient|expert"}}
  ],
  "templates_artifacts": [
    {{"type": "prompt|workflow|document|code|config", "name": "<artifact name>", "description": "<what it does>", "content_summary": "<brief content>"}}
  ],
  "unfinished_ideas": [
    {{"idea": "<what was started but not completed>", "potential": "<why it is worth revisiting>", "next_steps": ["<step1>"]}}
  ],
  "skill_candidates": [
    {{"name": "<skill name>", "description": "<what the skill does>", "trigger": "<when to activate>", "inputs": ["<input1>"], "outputs": ["<output1>"], "complexity": "simple|moderate|complex"}}
  ],
  "tags": ["<tag1>", "<tag2>"],
  "connections_to_other_work": ["<related topic or conversation>"]
}}"""
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_prompts.py -v`
Expected: All tests pass

**Step 5: Commit**

```bash
git add src/prompts.py tests/test_prompts.py
git commit -m "feat: add split extraction prompts (core + patterns)"
```

---

### Task 6: Two-pass extraction with retry logic in pipeline

**Files:**
- Modify: `src/pipeline.py:273-397`
- Modify: `src/pipeline.py:28-33` (imports)
- Create: `tests/test_pipeline.py`

**Step 1: Write tests for the extraction helper functions**

```python
# tests/test_pipeline.py
"""Tests for pipeline extraction logic."""

import json
from unittest.mock import MagicMock, patch

from src.models import ApiResponse
from src.pipeline import (
    _empty_extraction,
    _extract_single_pass,
    _is_empty_extraction,
    _merge_core_and_patterns,
)


class TestIsEmptyExtraction:
    """Test detection of failed/empty extractions."""

    def test_all_empty_returns_true(self):
        extraction = _empty_extraction()
        assert _is_empty_extraction(extraction) is True

    def test_with_data_returns_false(self):
        extraction = _empty_extraction()
        extraction = {**extraction, "problem_statement": "a real problem"}
        assert _is_empty_extraction(extraction) is False

    def test_with_only_empty_lists_returns_true(self):
        extraction = {
            "problem_statement": "",
            "context": "",
            "approach_strategy": "",
            "key_decisions": [],
            "frameworks": [],
            "reusable_patterns": [],
            "tools_and_tech": [],
            "templates_artifacts": [],
            "unfinished_ideas": [],
            "mistakes_and_lessons": [],
            "skill_candidates": [],
            "tags": [],
            "connections_to_other_work": [],
        }
        assert _is_empty_extraction(extraction) is True

    def test_with_nonempty_list_returns_false(self):
        extraction = {**_empty_extraction(), "tags": ["python"]}
        assert _is_empty_extraction(extraction) is False


class TestMergeCoreAndPatterns:
    """Test merging of two-pass extraction results."""

    def test_non_overlapping_keys_merge(self):
        core = {"problem_statement": "test", "context": "bg", "frameworks": []}
        patterns = {"reusable_patterns": [{"pattern": "X"}], "tags": ["py"]}
        merged = _merge_core_and_patterns(core, patterns)
        assert merged["problem_statement"] == "test"
        assert merged["reusable_patterns"] == [{"pattern": "X"}]
        assert merged["tags"] == ["py"]

    def test_handles_none_core(self):
        patterns = {"tags": ["a"]}
        merged = _merge_core_and_patterns(None, patterns)
        assert merged["tags"] == ["a"]
        assert merged["problem_statement"] == ""

    def test_handles_none_patterns(self):
        core = {"problem_statement": "test"}
        merged = _merge_core_and_patterns(core, None)
        assert merged["problem_statement"] == "test"
        assert merged["tags"] == []
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: FAIL — `ImportError: cannot import name '_is_empty_extraction'`

**Step 3: Implement helper functions**

Add these new functions to `src/pipeline.py` in the Helpers section (after `_empty_extraction`):

```python
def _is_empty_extraction(extraction: dict) -> bool:
    """Check if an extraction has no meaningful data (all values empty/falsy)."""
    for value in extraction.values():
        if isinstance(value, str) and value.strip():
            return False
        if isinstance(value, (list, tuple)) and len(value) > 0:
            return False
    return True


def _merge_core_and_patterns(
    core: dict | None,
    patterns: dict | None,
) -> dict:
    """Merge core analysis and patterns extraction into a single dict."""
    base = _empty_extraction()
    if core:
        base = {**base, **core}
    if patterns:
        base = {**base, **patterns}
    return base
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: 7 passed

**Step 5: Write test for `_extract_single_pass` (the retry-aware extraction)**

Add to `tests/test_pipeline.py`:

```python
class TestExtractSinglePass:
    """Test the single-pass extraction with three-tier fallback."""

    @patch("src.pipeline.ApiClient")
    def test_normal_parse_on_end_turn(self, _mock_cls):
        """Tier 1: stop_reason=end_turn with valid JSON."""
        mock_client = MagicMock()
        mock_client.call.return_value = ApiResponse(
            text='{"problem_statement": "test"}',
            input_tokens=100, output_tokens=50,
            stop_reason="end_turn",
        )
        from src.models import CostTracker
        result, cost = _extract_single_pass(
            client=mock_client,
            prompt="test prompt",
            model="test-model",
            max_tokens=8192,
            delay=0,
            cost=CostTracker(),
            input_cost_per_m=3.0,
            output_cost_per_m=15.0,
            conversation_id="test-id",
            pass_name="core",
        )
        assert result is not None
        assert result["problem_statement"] == "test"
        assert mock_client.call.call_count == 1

    @patch("src.pipeline.ApiClient")
    def test_partial_recovery_on_max_tokens(self, _mock_cls):
        """Tier 2: stop_reason=max_tokens, recover partial JSON."""
        mock_client = MagicMock()
        mock_client.call.return_value = ApiResponse(
            text='{"problem_statement": "recovered value", "context": "some conte',
            input_tokens=100, output_tokens=4096,
            stop_reason="max_tokens",
        )
        from src.models import CostTracker
        result, cost = _extract_single_pass(
            client=mock_client,
            prompt="test prompt",
            model="test-model",
            max_tokens=8192,
            delay=0,
            cost=CostTracker(),
            input_cost_per_m=3.0,
            output_cost_per_m=15.0,
            conversation_id="test-id",
            pass_name="core",
        )
        assert result is not None
        assert result["problem_statement"] == "recovered value"
```

**Step 6: Run test to verify it fails**

Run: `python -m pytest tests/test_pipeline.py::TestExtractSinglePass -v`
Expected: FAIL — `ImportError: cannot import name '_extract_single_pass'`

**Step 7: Implement `_extract_single_pass` with three-tier fallback**

Add to `src/pipeline.py`, and update imports at the top:

```python
# Add to imports section:
from .prompts import (
    build_core_extraction_prompt,
    build_extraction_prompt,
    build_patterns_extraction_prompt,
    build_synthesis_prompt,
    build_triage_prompt,
    parse_json_response,
    recover_partial_json,
)
```

Then add the function in the Helpers section:

```python
def _extract_single_pass(
    *,
    client: ApiClient,
    prompt: str,
    model: str,
    max_tokens: int,
    delay: float,
    cost: CostTracker,
    input_cost_per_m: float,
    output_cost_per_m: float,
    conversation_id: str,
    pass_name: str,
) -> tuple[dict | None, CostTracker]:
    """Run one extraction call with three-tier fallback.

    Returns (parsed_dict_or_None, updated_cost).
    Tiers:
      1. Normal parse (stop_reason == end_turn, valid JSON).
      2. Partial recovery (stop_reason == max_tokens, salvage complete fields).
      3. Retry with conciseness hint.
    """
    # Tier 1: Normal call
    resp = client.call(
        model=model,
        max_tokens=max_tokens,
        temperature=0,
        prompt=prompt,
        rate_limit_gap=delay,
    )
    call_cost = (
        resp.input_tokens * input_cost_per_m
        + resp.output_tokens * output_cost_per_m
    ) / 1_000_000
    cost = replace(
        cost,
        extract_input_tokens=cost.extract_input_tokens + resp.input_tokens,
        extract_output_tokens=cost.extract_output_tokens + resp.output_tokens,
        total_usd=cost.total_usd + call_cost,
    )

    # Try normal parse first
    try:
        parsed = parse_json_response(resp.text)
        if resp.stop_reason == "end_turn":
            logger.debug("Extraction %s/%s: clean parse (end_turn)", conversation_id, pass_name)
            return parsed, cost
        # Got valid JSON despite max_tokens — lucky, use it
        logger.info(
            "Extraction %s/%s: valid JSON despite stop_reason=%s",
            conversation_id, pass_name, resp.stop_reason,
        )
        return parsed, cost
    except (json.JSONDecodeError, ValueError):
        pass

    # Tier 2: Partial recovery (likely stop_reason == max_tokens)
    if resp.stop_reason == "max_tokens":
        logger.info(
            "Extraction %s/%s: truncated (max_tokens), attempting recovery",
            conversation_id, pass_name,
        )
        recovered = recover_partial_json(resp.text)
        if recovered:
            logger.info(
                "Extraction %s/%s: recovered %d fields from truncated response",
                conversation_id, pass_name, len(recovered),
            )
            return recovered, cost

    # Tier 3: Retry with conciseness hint
    logger.info(
        "Extraction %s/%s: retrying with conciseness hint",
        conversation_id, pass_name,
    )
    concise_prompt = prompt + "\n\nIMPORTANT: Be very concise. Use 1-2 sentences per field. Keep arrays short (max 3 items each)."
    try:
        resp2 = client.call(
            model=model,
            max_tokens=max_tokens,
            temperature=0,
            prompt=concise_prompt,
            rate_limit_gap=delay,
        )
        call_cost2 = (
            resp2.input_tokens * input_cost_per_m
            + resp2.output_tokens * output_cost_per_m
        ) / 1_000_000
        cost = replace(
            cost,
            extract_input_tokens=cost.extract_input_tokens + resp2.input_tokens,
            extract_output_tokens=cost.extract_output_tokens + resp2.output_tokens,
            total_usd=cost.total_usd + call_cost2,
        )

        try:
            parsed2 = parse_json_response(resp2.text)
            logger.info("Extraction %s/%s: concise retry succeeded", conversation_id, pass_name)
            return parsed2, cost
        except (json.JSONDecodeError, ValueError):
            # Try partial recovery on retry too
            recovered2 = recover_partial_json(resp2.text)
            if recovered2:
                logger.info("Extraction %s/%s: recovered from concise retry", conversation_id, pass_name)
                return recovered2, cost
    except Exception as e:
        logger.warning("Extraction %s/%s: concise retry failed: %s", conversation_id, pass_name, e)

    logger.warning("Extraction %s/%s: all three tiers failed", conversation_id, pass_name)
    return None, cost
```

**Step 8: Run tests to verify they pass**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: All tests pass

**Step 9: Commit**

```bash
git add src/pipeline.py tests/test_pipeline.py
git commit -m "feat: add extraction helpers (empty detection, merge, three-tier fallback)"
```

---

### Task 7: Rewrite `run_extraction_pass` to use two-pass extraction

**Files:**
- Modify: `src/pipeline.py:273-397`

**Step 1: Write integration test for two-pass extraction loop**

Add to `tests/test_pipeline.py`:

```python
from src.config import Config
from src.models import CostTracker, PipelineState
from src.pipeline import run_extraction_pass


class TestRunExtractionPassTwoPass:
    """Integration test: extraction loop uses two passes."""

    @patch("src.pipeline.ApiClient")
    def test_two_api_calls_per_conversation(self, _mock_cls):
        """Each conversation should generate two API calls (core + patterns)."""
        mock_client = MagicMock()
        # First call: core extraction
        # Second call: patterns extraction
        mock_client.call.side_effect = [
            ApiResponse(
                text='{"problem_statement": "test", "context": "", "approach_strategy": "", "key_decisions": [], "frameworks": [], "mistakes_and_lessons": []}',
                input_tokens=1000, output_tokens=200, stop_reason="end_turn",
            ),
            ApiResponse(
                text='{"reusable_patterns": [], "tools_and_tech": [], "templates_artifacts": [], "unfinished_ideas": [], "skill_candidates": [], "tags": ["python"], "connections_to_other_work": []}',
                input_tokens=1000, output_tokens=200, stop_reason="end_turn",
            ),
        ]

        from src.models import Conversation
        config = Config(api_key="test", input_path="test.json")
        conversations = [
            Conversation(
                conversation_id="conv-1", name="Test Conv",
                created_at="2026-01-01", updated_at="2026-01-01",
                message_count=10, word_count=500, estimated_tokens=650,
                is_oversized=False, full_text="[HUMAN]: hello\n[ASSISTANT]: hi",
            ),
        ]
        state = PipelineState(
            phase="triage",
            triage_results=(
                {"conversation_id": "conv-1", "score": 4, "name": "Test Conv",
                 "summary": "test", "topics": ["python"]},
            ),
        )

        result = run_extraction_pass(config, mock_client, conversations, state)

        assert len(result.extractions) == 1
        extraction = result.extractions[0]
        assert extraction["extraction"]["problem_statement"] == "test"
        assert extraction["extraction"]["tags"] == ["python"]
        assert mock_client.call.call_count == 2
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pipeline.py::TestRunExtractionPassTwoPass -v`
Expected: FAIL — still uses old single-call extraction

**Step 3: Rewrite `run_extraction_pass` for two-pass extraction**

Replace the entire `run_extraction_pass` function in `src/pipeline.py`:

```python
def run_extraction_pass(
    config: Config,
    client: ApiClient,
    conversations: list[Conversation],
    state: PipelineState,
) -> PipelineState:
    """Deep-extract knowledge from high-score conversations using two-pass extraction."""
    state = replace(state, phase="extraction")

    # Build lookup for full text
    conv_map = {c.conversation_id: c for c in conversations}

    # Filter to high-score conversations
    high_score = [
        r for r in state.triage_results
        if r.get("score", 0) >= config.min_score
    ]
    if not high_score:
        logger.warning(
            "No conversations scored >= %d. Skipping extraction.", config.min_score
        )
        return replace(state, phase="extraction")

    extracted_ids = {e["conversation_id"] for e in state.extractions}
    results = list(state.extractions)
    cost = state.cost
    total = len(high_score)

    for i, triage in enumerate(high_score):
        cid = triage["conversation_id"]
        if cid in extracted_ids:
            continue

        conv = conv_map.get(cid)
        if not conv:
            logger.warning("Conversation %s not found in loaded data, skipping.", cid)
            continue

        _check_cost(cost, config.cost_limit)

        # Chunk if oversized
        if conv.is_oversized:
            target_tokens = int(config.oversized_threshold * 0.75)
            chunks = chunk_text(
                conv.full_text, target_tokens, config.chunk_overlap_tokens
            )
            logger.info(
                "Extraction %d/%d: %s — chunked into %d parts",
                i + 1, total, conv.name[:50], len(chunks),
            )
        else:
            chunks = [conv.full_text]

        chunk_results: list[dict] = []
        for ci, chunk in enumerate(chunks):
            chunk_info = {
                "is_chunked": len(chunks) > 1,
                "chunk_index": ci,
                "total_chunks": len(chunks),
                "original_tokens": conv.estimated_tokens,
            } if len(chunks) > 1 else None

            # Pass 2a: Core Analysis
            core_prompt = build_core_extraction_prompt(
                name=conv.name,
                triage_score=triage["score"],
                triage_summary=triage["summary"],
                triage_topics=triage.get("topics", []),
                full_text=chunk,
                chunk_info=chunk_info,
            )

            try:
                core_result, cost = _extract_single_pass(
                    client=client,
                    prompt=core_prompt,
                    model=config.extraction_model,
                    max_tokens=config.extraction_core_max_tokens,
                    delay=config.extraction_delay,
                    cost=cost,
                    input_cost_per_m=config.sonnet_input_cost,
                    output_cost_per_m=config.sonnet_output_cost,
                    conversation_id=cid,
                    pass_name=f"core-chunk{ci}",
                )
            except Exception as e:
                logger.warning("Core extraction failed for %s chunk %d: %s", cid, ci, e)
                core_result = None

            # Pass 2b: Patterns & Skills
            patterns_prompt = build_patterns_extraction_prompt(
                name=conv.name,
                triage_score=triage["score"],
                triage_summary=triage["summary"],
                triage_topics=triage.get("topics", []),
                full_text=chunk,
                core_extraction=core_result or {},
                chunk_info=chunk_info,
            )

            try:
                patterns_result, cost = _extract_single_pass(
                    client=client,
                    prompt=patterns_prompt,
                    model=config.extraction_model,
                    max_tokens=config.extraction_patterns_max_tokens,
                    delay=config.extraction_delay,
                    cost=cost,
                    input_cost_per_m=config.sonnet_input_cost,
                    output_cost_per_m=config.sonnet_output_cost,
                    conversation_id=cid,
                    pass_name=f"patterns-chunk{ci}",
                )
            except Exception as e:
                logger.warning("Patterns extraction failed for %s chunk %d: %s", cid, ci, e)
                patterns_result = None

            merged = _merge_core_and_patterns(core_result, patterns_result)
            chunk_results.append(merged)

        # Reconcile chunks
        final = reconcile_extractions(chunk_results)

        extraction = {
            "conversation_id": cid,
            "name": conv.name,
            "created_at": conv.created_at,
            "triage_score": triage["score"],
            "triage_summary": triage["summary"],
            "triage_topics": triage.get("topics", []),
            "extraction": final,
        }
        results.append(extraction)

        logger.info(
            "Extraction %d/%d: %s — done (cost so far: $%.2f)",
            i + 1, total, conv.name[:50], cost.total_usd,
        )

        # Checkpoint after each conversation
        state = replace(state, extractions=tuple(results), cost=cost)
        save_checkpoint(state, config.output_path)

    state = replace(state, phase="extraction", extractions=tuple(results), cost=cost)
    save_checkpoint(state, config.output_path)
    return state
```

**Step 4: Update imports at the top of pipeline.py**

Replace the prompts import block:

```python
from .prompts import (
    build_core_extraction_prompt,
    build_extraction_prompt,
    build_patterns_extraction_prompt,
    build_synthesis_prompt,
    build_triage_prompt,
    parse_json_response,
    recover_partial_json,
)
```

**Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: All tests pass

**Step 6: Commit**

```bash
git add src/pipeline.py tests/test_pipeline.py
git commit -m "feat: rewrite extraction pass to use two-pass split with retry"
```

---

### Task 8: Resume with failed extraction detection

**Files:**
- Modify: `src/pipeline.py:296` (the `extracted_ids` logic)
- Modify: `tests/test_pipeline.py`

**Step 1: Write test for resume detecting empty extractions**

Add to `tests/test_pipeline.py`:

```python
class TestResumeWithFailedDetection:
    """Test that --resume detects and re-processes empty extractions."""

    @patch("src.pipeline.ApiClient")
    def test_empty_extraction_included_in_retry_set(self, _mock_cls):
        """An extraction with all-empty data should be re-processed."""
        mock_client = MagicMock()
        mock_client.call.side_effect = [
            ApiResponse(
                text='{"problem_statement": "now works", "context": "", "approach_strategy": "", "key_decisions": [], "frameworks": [], "mistakes_and_lessons": []}',
                input_tokens=100, output_tokens=50, stop_reason="end_turn",
            ),
            ApiResponse(
                text='{"reusable_patterns": [], "tools_and_tech": [], "templates_artifacts": [], "unfinished_ideas": [], "skill_candidates": [], "tags": [], "connections_to_other_work": []}',
                input_tokens=100, output_tokens=50, stop_reason="end_turn",
            ),
        ]

        from src.models import Conversation
        config = Config(api_key="test", input_path="test.json", resume=True)
        conversations = [
            Conversation(
                conversation_id="conv-1", name="Test Conv",
                created_at="2026-01-01", updated_at="2026-01-01",
                message_count=10, word_count=500, estimated_tokens=650,
                is_oversized=False, full_text="[HUMAN]: hello\n[ASSISTANT]: hi",
            ),
        ]
        # State with a previously failed (empty) extraction
        state = PipelineState(
            phase="extraction",
            triage_results=(
                {"conversation_id": "conv-1", "score": 4, "name": "Test Conv",
                 "summary": "test", "topics": []},
            ),
            extractions=(
                {
                    "conversation_id": "conv-1",
                    "name": "Test Conv",
                    "created_at": "2026-01-01",
                    "triage_score": 4,
                    "triage_summary": "test",
                    "triage_topics": [],
                    "extraction": _empty_extraction(),
                },
            ),
        )

        result = run_extraction_pass(config, mock_client, conversations, state)

        assert len(result.extractions) == 1
        # Should have replaced the empty extraction
        assert result.extractions[0]["extraction"]["problem_statement"] == "now works"
        # Should have made API calls (not skipped)
        assert mock_client.call.call_count == 2


    @patch("src.pipeline.ApiClient")
    def test_successful_extraction_not_retried(self, _mock_cls):
        """An extraction with real data should be skipped on resume."""
        mock_client = MagicMock()

        from src.models import Conversation
        config = Config(api_key="test", input_path="test.json", resume=True)
        conversations = [
            Conversation(
                conversation_id="conv-1", name="Test Conv",
                created_at="2026-01-01", updated_at="2026-01-01",
                message_count=10, word_count=500, estimated_tokens=650,
                is_oversized=False, full_text="[HUMAN]: hello\n[ASSISTANT]: hi",
            ),
        ]
        state = PipelineState(
            phase="extraction",
            triage_results=(
                {"conversation_id": "conv-1", "score": 4, "name": "Test Conv",
                 "summary": "test", "topics": []},
            ),
            extractions=(
                {
                    "conversation_id": "conv-1",
                    "name": "Test Conv",
                    "created_at": "2026-01-01",
                    "triage_score": 4,
                    "triage_summary": "test",
                    "triage_topics": [],
                    "extraction": {**_empty_extraction(), "problem_statement": "real data"},
                },
            ),
        )

        result = run_extraction_pass(config, mock_client, conversations, state)

        # Should NOT have made any API calls
        assert mock_client.call.call_count == 0
        # Should keep the existing extraction
        assert result.extractions[0]["extraction"]["problem_statement"] == "real data"
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pipeline.py::TestResumeWithFailedDetection -v`
Expected: FAIL — empty extractions are skipped (existing `extracted_ids` logic)

**Step 3: Update `run_extraction_pass` to detect failed extractions**

In the `run_extraction_pass` function, replace the `extracted_ids` and skip logic near the top of the loop. Change:

```python
    extracted_ids = {e["conversation_id"] for e in state.extractions}
    results = list(state.extractions)
```

To:

```python
    # Separate successful extractions from failed ones (empty data)
    successful_ids: set[str] = set()
    failed_ids: set[str] = set()
    for e in state.extractions:
        if _is_empty_extraction(e.get("extraction", {})):
            failed_ids.add(e["conversation_id"])
        else:
            successful_ids.add(e["conversation_id"])

    if failed_ids:
        logger.info(
            "Resume: found %d failed extractions to retry: %s",
            len(failed_ids),
            ", ".join(sorted(failed_ids)[:5]) + ("..." if len(failed_ids) > 5 else ""),
        )

    # Start with only successful extractions
    results = [e for e in state.extractions if e["conversation_id"] not in failed_ids]
```

And change the skip condition in the loop from:

```python
        if cid in extracted_ids:
            continue
```

To:

```python
        if cid in successful_ids:
            continue
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: All tests pass

**Step 5: Commit**

```bash
git add src/pipeline.py tests/test_pipeline.py
git commit -m "feat: resume detects and re-processes failed (empty) extractions"
```

---

### Task 9: Run full test suite and verify

**Step 1: Run all tests**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All tests pass

**Step 2: Verify no import errors**

Run: `python -c "from src.pipeline import run_pipeline; print('OK')"`
Expected: `OK`

**Step 3: Dry run with test data (if test-input.json available)**

Run: `python -m src.cli --input-path test-input.json --api-key $ANTHROPIC_API_KEY --output-path ./output-test --cost-limit 1.0`
Expected: Pipeline runs, uses two-pass extraction, no truncation errors

**Step 4: Commit any test fixes**

```bash
git add -A
git commit -m "test: fix any integration issues from full test run"
```

---

### Task 10: Re-run on failed conversations with --resume

**Step 1: Run pipeline with --resume on real data**

Run:
```bash
python -m src.cli \
  --input-path data-2026-02-27-14-24-25-batch-0000/conversations.json \
  --api-key $ANTHROPIC_API_KEY \
  --output-path ./output \
  --resume \
  --cost-limit 3.0
```

Expected:
- Detects 34 failed extractions
- Re-processes each with two-pass extraction
- >90% success rate (>30/34 succeed)
- Total additional cost under $1.50

**Step 2: Verify extraction quality**

Run: `python -c "import json, glob; files=glob.glob('output/deep-extractions/*.json'); empty=sum(1 for f in files if all(not v for v in json.load(open(f))['extraction'].values() if isinstance(v, (str, list)))); print(f'{len(files) - empty}/{len(files)} extractions have data')"`

Expected: >39/43 extractions have data (was 9/43 before)

**Step 3: Compare knowledge maps**

Review `output/knowledge-map.md` — should have richer content across all domains.

---

## Summary of Changes

| Task | File(s) | What |
|------|---------|------|
| 1 | `pyproject.toml`, `tests/` | Test infrastructure |
| 2 | `src/models.py`, `src/api_client.py` | `stop_reason` in `ApiResponse` |
| 3 | `src/config.py` | Split max token config |
| 4 | `src/prompts.py` | `recover_partial_json()` |
| 5 | `src/prompts.py` | Split prompt builders |
| 6-7 | `src/pipeline.py` | Two-pass extraction + retry |
| 8 | `src/pipeline.py` | Resume with failed detection |
| 9 | — | Full test suite verification |
| 10 | — | Re-run on real data |
