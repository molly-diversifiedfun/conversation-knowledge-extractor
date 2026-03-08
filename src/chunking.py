"""Token estimation and smart text chunking for oversized conversations."""

from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Estimate token count: word_count * 1.3 (per spec)."""
    word_count = len(text.split())
    return int(word_count * 1.3)


def chunk_text(
    text: str,
    target_tokens: int,
    overlap_tokens: int,
) -> list[str]:
    """Split text into chunks at paragraph boundaries with overlap.

    Args:
        text: Full conversation text to split
        target_tokens: Target tokens per chunk (e.g. 75% of 180K = 135K)
        overlap_tokens: Token overlap between consecutive chunks (e.g. 2000)

    Returns:
        List of text chunks with overlap and context summaries prepended.
    """
    chars_per_token = 4  # rough estimate
    chunk_size_chars = target_tokens * chars_per_token
    overlap_chars = overlap_tokens * chars_per_token

    chunks: list[str] = []
    start = 0
    prev_summary = ""

    while start < len(text):
        end = min(start + chunk_size_chars, len(text))

        # Try to break at a natural paragraph boundary
        if end < len(text):
            search_start = max(end - 2000, start)
            last_break = text.rfind("\n\n", search_start, end)
            if last_break > search_start:
                end = last_break

        chunk_text_str = text[start:end]

        # Prepend previous chunk summary for context continuity
        if prev_summary:
            chunk_text_str = (
                f"[PREVIOUS CHUNK SUMMARY: {prev_summary}]\n\n{chunk_text_str}"
            )

        chunks.append(chunk_text_str)

        # Generate a brief summary marker for next chunk
        tail = text[max(start, end - 500) : end]
        prev_summary = (
            "Conversation continued from: "
            + tail[:150].replace("\n", " ")
            + "..."
        )

        start = end - overlap_chars
        if start >= len(text) or end >= len(text):
            break

    return chunks


def reconcile_extractions(chunk_results: list[dict]) -> dict:
    """Merge extraction results from multiple chunks into one.

    Concatenates string fields with ' | ' separator.
    Merges array fields, deduplicating by JSON representation.
    """
    if len(chunk_results) == 1:
        return chunk_results[0]

    import json

    # String fields to concatenate
    string_fields = ("problem_statement", "context", "approach_strategy")
    # Array fields to merge and deduplicate
    array_fields = (
        "key_decisions", "frameworks", "reusable_patterns",
        "tools_and_tech", "templates_artifacts", "unfinished_ideas",
        "mistakes_and_lessons", "skill_candidates",
    )
    # Set fields (simple string arrays)
    set_fields = ("tags", "connections_to_other_work")

    merged: dict = {}

    for field_name in string_fields:
        parts = [r.get(field_name, "") for r in chunk_results if r.get(field_name)]
        merged[field_name] = " | ".join(parts)

    for field_name in array_fields:
        seen: set[str] = set()
        items: list[dict] = []
        for r in chunk_results:
            for item in r.get(field_name, []):
                key = json.dumps(item, sort_keys=True)
                if key not in seen:
                    seen.add(key)
                    items.append(item)
        merged[field_name] = items

    for field_name in set_fields:
        all_values: set[str] = set()
        for r in chunk_results:
            all_values.update(r.get(field_name, []))
        merged[field_name] = sorted(all_values)

    return merged
