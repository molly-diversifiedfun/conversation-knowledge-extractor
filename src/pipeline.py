"""Three-pass pipeline: triage -> extract -> synthesize."""

from __future__ import annotations

import json
import logging
import os
import zipfile
from dataclasses import replace

from .api_client import ApiClient
from .chunking import chunk_text, estimate_tokens, reconcile_extractions
from .config import Config
from .models import (
    Conversation,
    CostTracker,
    Extraction,
    PipelineState,
    TriageResult,
)
from .output import (
    write_cost_report,
    write_deep_extractions,
    write_knowledge_map,
    write_skill_candidates,
    write_triage_index,
)
from .prompts import (
    build_core_extraction_prompt,
    build_extraction_prompt,
    build_patterns_extraction_prompt,
    build_synthesis_prompt,
    build_triage_prompt,
    parse_json_response,
    recover_partial_json,
)
from .state import clear_checkpoint, load_checkpoint, save_checkpoint

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def run_pipeline(config: Config) -> None:
    """Run the full extraction pipeline."""
    os.makedirs(config.output_path, exist_ok=True)
    client = ApiClient(config.api_key)

    # Resume from checkpoint if requested
    state = PipelineState()
    if config.resume:
        saved = load_checkpoint(config.output_path)
        if saved:
            state = saved
            logger.info(
                "Resumed from checkpoint: phase=%s, triage=%d, extractions=%d",
                state.phase, len(state.triage_results), len(state.extractions),
            )
        else:
            logger.info("No checkpoint found, starting fresh.")

    # Load conversations
    conversations = load_conversations(config)
    state = replace(state, conversations_loaded=len(conversations))
    logger.info(
        "Loaded %d conversations (%d skipped for < %d messages)",
        len(conversations), state.skipped_count, config.min_messages,
    )

    # Pass 1: Triage
    if state.phase in ("init", "triage") and not config.skip_triage:
        state = run_triage_pass(config, client, conversations, state)

    # Pass 2: Extraction
    if state.phase in ("triage", "extraction"):
        state = run_extraction_pass(config, client, conversations, state)

    # Pass 3: Synthesis
    if state.phase in ("extraction", "synthesis"):
        state = run_synthesis_pass(config, client, state)

    # Write all outputs
    write_triage_index(state, config)
    write_deep_extractions(state, config)
    write_knowledge_map(state, config)
    write_skill_candidates(state, config)
    write_cost_report(state)

    clear_checkpoint(config.output_path)
    logger.info("Pipeline complete.")


# ---------------------------------------------------------------------------
# Load conversations from ZIP or JSON
# ---------------------------------------------------------------------------

def load_conversations(config: Config) -> list[Conversation]:
    """Parse conversations from a ZIP or JSON file."""
    path = config.input_path

    if path.endswith(".zip"):
        raw = _read_from_zip(path)
    else:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)

    # Handle wrapped formats
    if not isinstance(raw, list):
        raw = raw.get("conversations") or raw.get("data") or [raw]

    conversations: list[Conversation] = []
    for conv in raw:
        messages = conv.get("chat_messages") or conv.get("messages") or []
        if len(messages) < config.min_messages:
            continue

        full_text = "\n\n".join(
            f"[{(m.get('sender') or m.get('role') or 'unknown').upper()}]: "
            f"{m.get('text') or m.get('content') or ''}"
            for m in messages
        )

        word_count = len(full_text.split())
        tokens = int(word_count * 1.3)

        conversations.append(Conversation(
            conversation_id=(
                conv.get("uuid")
                or conv.get("id")
                or conv.get("conversation_id")
                or f"conv_{len(conversations)}"
            ),
            name=conv.get("name") or conv.get("title") or "Untitled Conversation",
            created_at=conv.get("created_at") or conv.get("create_time") or "",
            updated_at=conv.get("updated_at") or conv.get("update_time") or "",
            message_count=len(messages),
            word_count=word_count,
            estimated_tokens=tokens,
            is_oversized=tokens > config.oversized_threshold,
            full_text=full_text,
        ))

    if not conversations:
        raise SystemExit(
            f"No conversations found with >= {config.min_messages} messages. "
            f"Total in file: {len(raw)}"
        )

    return conversations


def _read_from_zip(path: str) -> list:
    """Extract conversations.json from a ZIP file."""
    with zipfile.ZipFile(path, "r") as zf:
        # Look for conversations.json inside the ZIP
        candidates = [
            n for n in zf.namelist()
            if n.endswith("conversations.json")
        ]
        if not candidates:
            raise SystemExit(
                f"No conversations.json found in ZIP: {path}. "
                f"Files: {zf.namelist()[:10]}"
            )
        with zf.open(candidates[0]) as f:
            return json.load(f)


# ---------------------------------------------------------------------------
# Pass 1: Triage (Haiku)
# ---------------------------------------------------------------------------

def run_triage_pass(
    config: Config,
    client: ApiClient,
    conversations: list[Conversation],
    state: PipelineState,
) -> PipelineState:
    """Score every conversation with Haiku."""
    state = replace(state, phase="triage")
    triaged_ids = {r["conversation_id"] for r in state.triage_results}
    total = len(conversations)
    results = list(state.triage_results)
    cost = state.cost

    for i, conv in enumerate(conversations):
        if conv.conversation_id in triaged_ids:
            continue

        _check_cost(cost, config.cost_limit)

        prompt = build_triage_prompt(
            name=conv.name,
            message_count=conv.message_count,
            estimated_tokens=conv.estimated_tokens,
            full_text=conv.full_text,
        )

        try:
            resp = client.call(
                model=config.triage_model,
                max_tokens=config.triage_max_tokens,
                temperature=0,
                prompt=prompt,
                rate_limit_gap=config.triage_delay,
            )
            parsed = parse_json_response(resp.text)

            # Track cost
            call_cost = (
                resp.input_tokens * config.haiku_input_cost
                + resp.output_tokens * config.haiku_output_cost
            ) / 1_000_000
            cost = replace(
                cost,
                triage_input_tokens=cost.triage_input_tokens + resp.input_tokens,
                triage_output_tokens=cost.triage_output_tokens + resp.output_tokens,
                total_usd=cost.total_usd + call_cost,
            )
        except Exception as e:
            logger.warning("Triage failed for %s: %s", conv.conversation_id, e)
            parsed = {
                "score": 0,
                "summary": f"Triage failed: {e}",
                "topics": [],
                "worth_saving": False,
                "worth_building_skill": False,
                "skill_candidate_reason": None,
            }

        score = parsed.get("score", 0)
        summary = parsed.get("summary", "")

        # Auto-score: oversized conversations get minimum score of 4
        if conv.is_oversized and score < 4:
            score = 4
            summary = f"[AUTO-SCORED: oversized] {summary}"

        result = {
            "conversation_id": conv.conversation_id,
            "name": conv.name,
            "created_at": conv.created_at,
            "message_count": conv.message_count,
            "estimated_tokens": conv.estimated_tokens,
            "is_oversized": conv.is_oversized,
            "score": score,
            "summary": summary,
            "topics": parsed.get("topics", []),
            "worth_saving": parsed.get("worth_saving", False),
            "worth_building_skill": parsed.get("worth_building_skill", False),
            "skill_candidate_reason": parsed.get("skill_candidate_reason"),
        }
        results.append(result)

        logger.info(
            "Triage %d/%d: %s — Score: %d, Topics: %s",
            i + 1, total, conv.name[:50], score,
            ", ".join(parsed.get("topics", [])),
        )

        # Checkpoint after each conversation
        state = replace(state, triage_results=tuple(results), cost=cost)
        save_checkpoint(state, config.output_path)

    state = replace(state, phase="triage", triage_results=tuple(results), cost=cost)
    save_checkpoint(state, config.output_path)
    return state


# ---------------------------------------------------------------------------
# Pass 2: Extraction (Sonnet)
# ---------------------------------------------------------------------------

def run_extraction_pass(
    config: Config,
    client: ApiClient,
    conversations: list[Conversation],
    state: PipelineState,
) -> PipelineState:
    """Deep-extract knowledge from high-score conversations (two-pass).

    For each conversation, makes two focused API calls:
      Pass 2a: Core Analysis (problem, context, strategy, decisions, frameworks, lessons)
      Pass 2b: Patterns & Skills (patterns, tools, templates, ideas, skills, tags)

    On --resume, detects empty extractions (failed previous runs) and retries them.
    """
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
            ", ".join(sorted(failed_ids)[:5])
            + ("..." if len(failed_ids) > 5 else ""),
        )

    # Start with only successful extractions
    results = [
        e for e in state.extractions if e["conversation_id"] not in failed_ids
    ]
    cost = state.cost
    total = len(high_score)

    for i, triage in enumerate(high_score):
        cid = triage["conversation_id"]
        if cid in successful_ids:
            continue

        conv = conv_map.get(cid)
        if not conv:
            logger.warning(
                "Conversation %s not found in loaded data, skipping.", cid,
            )
            continue

        _check_cost(cost, config.cost_limit)

        if cid in failed_ids:
            logger.info(
                "Retrying previously failed extraction for %s", cid,
            )

        # Chunk if oversized
        if conv.is_oversized:
            target_tokens = int(config.oversized_threshold * 0.75)
            chunks = chunk_text(
                conv.full_text, target_tokens, config.chunk_overlap_tokens,
            )
            logger.info(
                "Extraction %d/%d: %s -- chunked into %d parts",
                i + 1, total, conv.name[:50], len(chunks),
            )
        else:
            chunks = [conv.full_text]

        chunk_results: list[dict] = []
        for ci, chunk in enumerate(chunks):
            chunk_info = (
                {
                    "is_chunked": len(chunks) > 1,
                    "chunk_index": ci,
                    "total_chunks": len(chunks),
                    "original_tokens": conv.estimated_tokens,
                }
                if len(chunks) > 1
                else None
            )

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
                logger.warning(
                    "Core extraction failed for %s chunk %d: %s", cid, ci, e,
                )
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
                logger.warning(
                    "Patterns extraction failed for %s chunk %d: %s",
                    cid, ci, e,
                )
                patterns_result = None

            merged = _merge_core_and_patterns(core_result, patterns_result)
            chunk_results.append(merged)

        # Reconcile chunks
        final_merged = reconcile_extractions(chunk_results)

        extraction = {
            "conversation_id": cid,
            "name": conv.name,
            "created_at": conv.created_at,
            "triage_score": triage["score"],
            "triage_summary": triage["summary"],
            "triage_topics": triage.get("topics", []),
            "extraction": final_merged,
        }
        results.append(extraction)

        logger.info(
            "Extraction %d/%d: %s -- done (cost so far: $%.2f)",
            i + 1, total, conv.name[:50], cost.total_usd,
        )

        # Checkpoint after each conversation
        state = replace(state, extractions=tuple(results), cost=cost)
        save_checkpoint(state, config.output_path)

    state = replace(
        state, phase="extraction", extractions=tuple(results), cost=cost,
    )
    save_checkpoint(state, config.output_path)
    return state


# ---------------------------------------------------------------------------
# Pass 3: Synthesis (Sonnet)
# ---------------------------------------------------------------------------

def run_synthesis_pass(
    config: Config,
    client: ApiClient,
    state: PipelineState,
) -> PipelineState:
    """Synthesize all extractions into a knowledge map."""
    state = replace(state, phase="synthesis")

    if not state.extractions:
        logger.warning("No extractions to synthesize.")
        return replace(state, phase="complete")

    _check_cost(state.cost, config.cost_limit)

    all_extractions = [
        {
            "conversation_id": e["conversation_id"],
            "name": e["name"],
            "triage_score": e["triage_score"],
            "extraction": e["extraction"],
        }
        for e in state.extractions
    ]

    prompt = build_synthesis_prompt(all_extractions, len(all_extractions))

    cost = state.cost
    try:
        resp = client.call(
            model=config.synthesis_model,
            max_tokens=config.synthesis_max_tokens,
            temperature=0.2,
            prompt=prompt,
            rate_limit_gap=config.extraction_delay,
        )
        synthesis = parse_json_response(resp.text)

        call_cost = (
            resp.input_tokens * config.sonnet_input_cost
            + resp.output_tokens * config.sonnet_output_cost
        ) / 1_000_000
        cost = replace(
            cost,
            synthesis_input_tokens=cost.synthesis_input_tokens + resp.input_tokens,
            synthesis_output_tokens=cost.synthesis_output_tokens + resp.output_tokens,
            total_usd=cost.total_usd + call_cost,
        )
    except Exception as e:
        logger.error("Synthesis failed: %s", e)
        synthesis = {
            "domains": [],
            "cross_domain_connections": [],
            "top_skill_candidates": [],
            "knowledge_gaps": [],
            "meta_patterns": [f"Synthesis failed: {e}"],
            "statistics": {"total_conversations_analyzed": len(state.extractions)},
        }

    state = replace(state, phase="complete", synthesis=synthesis, cost=cost)
    save_checkpoint(state, config.output_path)
    return state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_cost(cost: CostTracker, limit: float) -> None:
    """Raise if accumulated cost exceeds the limit."""
    if cost.total_usd >= limit:
        raise SystemExit(
            f"Cost guardrail hit: ${cost.total_usd:.2f} exceeds ${limit:.2f} limit. "
            f"Stopping. Use --cost-limit to increase."
        )


def _empty_extraction() -> dict:
    """Return an empty extraction dict for error cases."""
    return {
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
            logger.debug(
                "Extraction %s/%s: clean parse (end_turn)",
                conversation_id, pass_name,
            )
            return parsed, cost
        # Got valid JSON despite max_tokens - lucky, use it
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
    concise_prompt = (
        prompt
        + "\n\nIMPORTANT: Be very concise. Use 1-2 sentences per field. "
        "Keep arrays short (max 3 items each)."
    )
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
            logger.info(
                "Extraction %s/%s: concise retry succeeded",
                conversation_id, pass_name,
            )
            return parsed2, cost
        except (json.JSONDecodeError, ValueError):
            # Try partial recovery on retry too
            recovered2 = recover_partial_json(resp2.text)
            if recovered2:
                logger.info(
                    "Extraction %s/%s: recovered from concise retry",
                    conversation_id, pass_name,
                )
                return recovered2, cost
    except Exception as e:
        logger.warning(
            "Extraction %s/%s: concise retry failed: %s",
            conversation_id, pass_name, e,
        )

    logger.warning(
        "Extraction %s/%s: all three tiers failed",
        conversation_id, pass_name,
    )
    return None, cost
