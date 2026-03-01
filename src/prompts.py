"""Prompt builders and JSON response parser — ported from n8n workflow."""

from __future__ import annotations

import json
import re


# ---------------------------------------------------------------------------
# Triage prompt (Haiku — fast & cheap)
# ---------------------------------------------------------------------------

def build_triage_prompt(
    name: str,
    message_count: int,
    estimated_tokens: int,
    full_text: str,
) -> str:
    """Build the triage scoring prompt. Truncates to ~12K chars for Haiku."""
    truncated = full_text[:12000]
    truncation_note = ""
    if len(full_text) > 12000:
        truncation_note = (
            f"\n... [TRUNCATED FOR TRIAGE - {estimated_tokens} total tokens] ..."
        )

    return f"""You are a knowledge extraction triage agent. Analyze this Claude AI conversation and score it for knowledge value.

SCORING CRITERIA:
1 = No value: Simple greetings, trivial questions, no reusable knowledge
2 = Low value: Basic information easily found elsewhere, simple how-to answers
3 = Medium: Some useful patterns, minor decisions, or general insights
4 = High value: Significant technical decisions, reusable patterns, deep problem-solving, framework development
5 = Major breakthrough: Novel solutions, architectural decisions, important lessons, unique expertise or methodology

CONVERSATION TITLE: {name}
MESSAGE COUNT: {message_count}
ESTIMATED TOKENS: {estimated_tokens}

CONVERSATION:
{truncated}{truncation_note}

Respond with ONLY a valid JSON object (no markdown fences, no explanation):
{{
  "score": <1-5 integer>,
  "summary": "<one-sentence summary of the conversation's knowledge content>",
  "topics": ["<tag1>", "<tag2>", "<tag3 max>"],
  "worth_saving": <true/false - is there any reusable knowledge?>,
  "worth_building_skill": <true/false - could this become a Claude Code skill?>,
  "skill_candidate_reason": "<if worth_building_skill is true, explain why; otherwise null>"
}}"""


# ---------------------------------------------------------------------------
# Extraction prompt (Sonnet — deep dive)
# ---------------------------------------------------------------------------

def build_extraction_prompt(
    name: str,
    triage_score: int,
    triage_summary: str,
    triage_topics: tuple[str, ...] | list[str],
    full_text: str,
    chunk_info: dict | None = None,
) -> str:
    """Build the deep extraction prompt."""
    chunk_context = ""
    if chunk_info and chunk_info.get("is_chunked"):
        chunk_context = (
            f"\n\nIMPORTANT: This is chunk {chunk_info['chunk_index'] + 1} "
            f"of {chunk_info['total_chunks']} from a large conversation "
            f"({chunk_info['original_tokens']} total tokens). "
            f"Extract knowledge from THIS chunk. Results will be merged with "
            f"other chunks later."
        )

    topics_str = ", ".join(triage_topics) if triage_topics else ""

    return f"""You are an expert knowledge extraction agent. Deep-extract all reusable knowledge from this Claude AI conversation.{chunk_context}

CONVERSATION TITLE: {name}
TRIAGE SCORE: {triage_score}/5
TRIAGE SUMMARY: {triage_summary}
TRIAGE TOPICS: {topics_str}

CONVERSATION:
{full_text}

Extract ALL of the following. Be thorough. Respond with ONLY a valid JSON object (no markdown fences):
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
  "mistakes_and_lessons": [
    {{"mistake": "<what went wrong>", "lesson": "<what was learned>", "prevention": "<how to avoid>"}}
  ],
  "skill_candidates": [
    {{"name": "<skill name>", "description": "<what the skill does>", "trigger": "<when to activate>", "inputs": ["<input1>"], "outputs": ["<output1>"], "complexity": "simple|moderate|complex"}}
  ],
  "tags": ["<tag1>", "<tag2>"],
  "connections_to_other_work": ["<related topic or conversation>"]
}}"""


# ---------------------------------------------------------------------------
# Synthesis prompt (Sonnet — combine all extractions)
# ---------------------------------------------------------------------------

def build_synthesis_prompt(
    all_extractions: list[dict],
    total_extractions: int,
) -> str:
    """Build the synthesis prompt from all deep extractions."""
    extraction_text = json.dumps(all_extractions, indent=1)
    # Rough truncation if extremely large (180K tokens * ~4 chars/token)
    max_chars = 180_000 * 4
    if len(extraction_text) > max_chars:
        extraction_text = extraction_text[:max_chars] + "\n... [TRUNCATED]"

    return f"""You are a knowledge synthesis agent. You have received deep extractions from {total_extractions} high-value Claude AI conversations. Synthesize them into a coherent personal knowledge map.

ALL DEEP EXTRACTIONS:
{extraction_text}

Synthesize into a comprehensive knowledge map. Group by thematic domain. Identify cross-domain connections. Prioritize skill candidates.

Respond with ONLY a valid JSON object (no markdown fences):
{{
  "domains": [
    {{
      "name": "<domain name>",
      "description": "<what this domain covers>",
      "key_insights": ["<insight1>", "<insight2>"],
      "frameworks": [{{"name": "<name>", "description": "<desc>", "source_conversations": ["<conv_id>"]}}],
      "patterns": [{{"name": "<name>", "description": "<desc>", "frequency": <count>}}],
      "skills": [{{"name": "<name>", "level": "<beginner|intermediate|advanced|expert>", "evidence": "<brief>"}}],
      "tools": ["<tool1>", "<tool2>"]
    }}
  ],
  "cross_domain_connections": [
    {{"domains": ["<domain1>", "<domain2>"], "connection": "<how they relate>", "insight": "<what this means>"}}
  ],
  "top_skill_candidates": [
    {{
      "name": "<skill name>",
      "description": "<what it does>",
      "trigger": "<when to use>",
      "inputs": ["<input1>"],
      "outputs": ["<output1>"],
      "source_conversations": ["<conv_id>"],
      "complexity": "simple|moderate|complex",
      "priority": <1-10>,
      "priority_reason": "<why this priority>"
    }}
  ],
  "knowledge_gaps": [{{"area": "<gap area>", "evidence": "<why it is a gap>", "recommendation": "<what to do>"}}],
  "meta_patterns": ["<overarching pattern across all conversations>"],
  "statistics": {{
    "total_conversations_analyzed": {total_extractions},
    "total_frameworks_found": 0,
    "total_patterns_found": 0,
    "total_skill_candidates": 0,
    "unique_tools_mentioned": 0
  }}
}}"""


# ---------------------------------------------------------------------------
# JSON response parser
# ---------------------------------------------------------------------------

def parse_json_response(text: str) -> dict:
    """Parse a JSON response, stripping markdown fences if present."""
    cleaned = re.sub(r"^```(?:json)?\n?", "", text.strip())
    cleaned = re.sub(r"\n?```$", "", cleaned).strip()
    return json.loads(cleaned)


# ---------------------------------------------------------------------------
# Partial JSON recovery (three-tier)
# ---------------------------------------------------------------------------

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
    # Strategy: find the last complete value boundary and close from there
    for trim_pattern in [
        r',\s*"[^"]*":\s*"[^"]*$',
        r',\s*"[^"]*":\s*[^,}\]]*$',
        r',\s*\{[^}]*$',
    ]:
        match = re.search(trim_pattern, text)
        if match:
            trimmed = text[: match.start()]
            result = _try_close(trimmed)
            if result is not None:
                return result

    return _try_close(text)


def _try_close(text: str) -> dict | None:
    """Try adding closing braces/brackets to make valid JSON."""
    for suffix in [
        '"}',
        "}",
        '"]}',
        "]}",
        '"]}]}',
        "}]}",
        '"]}}',
        "}}",
        '"}}',
        '"}]}',
        '"}]}}',
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
    result: dict = {}

    # Match "key": "string_value" pairs
    string_pairs = re.findall(
        r'"(\w+)"\s*:\s*"((?:[^"\\]|\\.)*)"',
        text,
    )
    for key, value in string_pairs:
        if key not in result:
            result[key] = value

    # Match "key": [...] complete array pairs
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
