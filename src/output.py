"""Output file writers for all pipeline artifacts."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from .models import PipelineState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Triage index
# ---------------------------------------------------------------------------

def write_triage_index(state: PipelineState, config: object) -> None:
    """Write triage-index.json sorted by score with distribution stats."""
    results = sorted(state.triage_results, key=lambda r: r.get("score", 0), reverse=True)

    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in results:
        score = r.get("score", 0)
        if 1 <= score <= 5:
            distribution[score] += 1

    index = {
        "generated_at": _now_iso(),
        "total_conversations": len(results),
        "skipped_too_short": state.skipped_count,
        "score_distribution": distribution,
        "estimated_cost_so_far_usd": round(state.cost.total_usd, 4),
        "conversations": [
            {
                "conversation_id": r["conversation_id"],
                "name": r["name"],
                "created_at": r.get("created_at", ""),
                "message_count": r.get("message_count", 0),
                "estimated_tokens": r.get("estimated_tokens", 0),
                "is_oversized": r.get("is_oversized", False),
                "triage_score": r.get("score", 0),
                "triage_summary": r.get("summary", ""),
                "triage_topics": r.get("topics", []),
                "worth_saving": r.get("worth_saving", False),
                "worth_building_skill": r.get("worth_building_skill", False),
                "skill_candidate_reason": r.get("skill_candidate_reason"),
            }
            for r in results
        ],
    }

    path = os.path.join(config.output_path, "triage-index.json")
    _write_json(path, index)
    logger.info("Wrote %s (%d conversations)", path, len(results))


# ---------------------------------------------------------------------------
# Deep extractions
# ---------------------------------------------------------------------------

def write_deep_extractions(state: PipelineState, config: object) -> None:
    """Write individual JSON files in deep-extractions/ directory."""
    out_dir = os.path.join(config.output_path, "deep-extractions")
    os.makedirs(out_dir, exist_ok=True)

    for ext in state.extractions:
        cid = ext["conversation_id"]
        path = os.path.join(out_dir, f"{cid}.json")
        _write_json(path, ext)

    logger.info("Wrote %d deep extraction files to %s", len(state.extractions), out_dir)


# ---------------------------------------------------------------------------
# Knowledge map (markdown)
# ---------------------------------------------------------------------------

def write_knowledge_map(state: PipelineState, config: object) -> None:
    """Generate knowledge-map.md from synthesis results."""
    s = state.synthesis
    if not s:
        logger.warning("No synthesis data, skipping knowledge map.")
        return

    lines: list[str] = [
        "# Personal Knowledge Map\n",
        f"*Generated: {_now_iso()}*",
        f"*Conversations analyzed: {len(state.extractions)}*",
        f"*Processing cost: ${state.cost.total_usd:.2f}*\n",
        "---\n",
    ]

    # Domains
    domains = s.get("domains", [])
    if domains:
        lines.append("## Knowledge Domains\n")
        for domain in domains:
            lines.append(f"### {domain.get('name', 'Unknown')}\n")
            desc = domain.get("description")
            if desc:
                lines.append(f"{desc}\n")

            insights = domain.get("key_insights", [])
            if insights:
                lines.append("**Key Insights:**")
                lines.extend(f"- {insight}" for insight in insights)
                lines.append("")

            frameworks = domain.get("frameworks", [])
            if frameworks:
                lines.append("**Frameworks:**")
                for fw in frameworks:
                    lines.append(f"- **{fw.get('name', '?')}**: {fw.get('description', '')}")
                lines.append("")

            patterns = domain.get("patterns", [])
            if patterns:
                lines.append("**Patterns:**")
                for p in patterns:
                    freq = p.get("frequency", "?")
                    lines.append(f"- **{p.get('name', '?')}** (seen {freq}x): {p.get('description', '')}")
                lines.append("")

            skills = domain.get("skills", [])
            if skills:
                lines.append("**Skills:**")
                for sk in skills:
                    lines.append(f"- {sk.get('name', '?')} [{sk.get('level', '?')}]: {sk.get('evidence', '')}")
                lines.append("")

            tools = domain.get("tools", [])
            if tools:
                lines.append(f"**Tools:** {', '.join(tools)}\n")

            lines.append("---\n")

    # Cross-domain connections
    connections = s.get("cross_domain_connections", [])
    if connections:
        lines.append("## Cross-Domain Connections\n")
        for conn in connections:
            domains_str = " <-> ".join(conn.get("domains", []))
            lines.append(f"- **{domains_str}**: {conn.get('connection', '')}")
            insight = conn.get("insight")
            if insight:
                lines.append(f"  - *Insight: {insight}*")
        lines.append("")

    # Meta-patterns
    meta = s.get("meta_patterns", [])
    if meta:
        lines.append("## Meta-Patterns\n")
        lines.extend(f"- {mp}" for mp in meta)
        lines.append("")

    # Knowledge gaps
    gaps = s.get("knowledge_gaps", [])
    if gaps:
        lines.append("## Knowledge Gaps\n")
        for gap in gaps:
            line = f"- **{gap.get('area', '?')}**: {gap.get('evidence', '')}"
            rec = gap.get("recommendation")
            if rec:
                line += f" → *{rec}*"
            lines.append(line)
        lines.append("")

    # Statistics
    stats = s.get("statistics", {})
    if stats:
        lines.append("## Statistics\n")
        lines.append("| Metric | Count |")
        lines.append("|--------|-------|")
        for key, val in stats.items():
            lines.append(f"| {key.replace('_', ' ')} | {val} |")
        lines.append("")

    path = os.path.join(config.output_path, "knowledge-map.md")
    _write_text(path, "\n".join(lines))
    logger.info("Wrote %s", path)


# ---------------------------------------------------------------------------
# Skill candidates (markdown)
# ---------------------------------------------------------------------------

def write_skill_candidates(state: PipelineState, config: object) -> None:
    """Generate skill-candidates.md from extractions + synthesis."""
    # Collect from individual extractions
    skill_map: dict[str, dict] = {}

    for ext in state.extractions:
        extraction = ext.get("extraction", {})
        for skill in extraction.get("skill_candidates", []):
            key = (skill.get("name") or "").lower().strip()
            if not key:
                continue
            if key in skill_map:
                skill_map[key]["source_conversations"].append(ext["conversation_id"])
                skill_map[key]["occurrences"] += 1
            else:
                skill_map[key] = {
                    **skill,
                    "source_conversations": [ext["conversation_id"]],
                    "occurrences": 1,
                }

    # Merge with synthesis skill candidates (higher priority info)
    for ss in state.synthesis.get("top_skill_candidates", []):
        key = (ss.get("name") or "").lower().strip()
        if key in skill_map:
            existing = skill_map[key]
            existing["priority"] = ss.get("priority", existing.get("priority"))
            existing["priority_reason"] = ss.get("priority_reason", existing.get("priority_reason"))
            src = ss.get("source_conversations", [])
            if src:
                existing["source_conversations"] = list(set(
                    existing["source_conversations"] + src
                ))
        else:
            skill_map[key] = {
                **ss,
                "source_conversations": ss.get("source_conversations", []),
                "occurrences": 1,
            }

    # Sort by priority (highest first), then occurrences
    skills = sorted(
        skill_map.values(),
        key=lambda s: (s.get("priority", 5), s.get("occurrences", 0)),
        reverse=True,
    )

    lines: list[str] = [
        "# Skill Candidates — Prioritized Build List\n",
        f"*Generated: {_now_iso()}*",
        f"*Total candidates: {len(skills)}*\n",
        "---\n",
    ]

    for i, sk in enumerate(skills, 1):
        lines.append(f"## {i}. {sk.get('name', 'Unnamed Skill')}\n")
        priority_line = f"**Priority:** {sk.get('priority', 'unranked')}/10"
        reason = sk.get("priority_reason")
        if reason:
            priority_line += f" — {reason}"
        lines.append(priority_line)
        lines.append(f"**Complexity:** {sk.get('complexity', 'unknown')}")
        lines.append(f"**Seen in:** {sk.get('occurrences', 1)} conversation(s)\n")

        desc = sk.get("description")
        if desc:
            lines.append(f"**Description:** {desc}\n")

        trigger = sk.get("trigger")
        if trigger:
            lines.append(f"**Trigger:** {trigger}\n")

        inputs = sk.get("inputs", [])
        if inputs:
            lines.append("**Inputs:**")
            lines.extend(f"- {inp}" for inp in inputs)
            lines.append("")

        outputs = sk.get("outputs", [])
        if outputs:
            lines.append("**Outputs:**")
            lines.extend(f"- {out}" for out in outputs)
            lines.append("")

        sources = sk.get("source_conversations", [])
        if sources:
            lines.append(f"**Source conversations:** {', '.join(sources)}\n")

        lines.append("---\n")

    path = os.path.join(config.output_path, "skill-candidates.md")
    _write_text(path, "\n".join(lines))
    logger.info("Wrote %s (%d candidates)", path, len(skills))


# ---------------------------------------------------------------------------
# Cost report (stdout)
# ---------------------------------------------------------------------------

def write_cost_report(state: PipelineState) -> None:
    """Print final cost summary to stdout."""
    c = state.cost
    print("\n=== KNOWLEDGE EXTRACTOR COMPLETE ===")
    print(f"Status: {state.phase}")
    print(f"Conversations triaged: {len(state.triage_results)}")
    print(f"Conversations extracted: {len(state.extractions)}")
    print(f"Conversations skipped: {state.skipped_count}")
    print(f"\nToken usage:")
    print(f"  Triage:     {c.triage_input_tokens:>8} in / {c.triage_output_tokens:>8} out")
    print(f"  Extraction: {c.extract_input_tokens:>8} in / {c.extract_output_tokens:>8} out")
    print(f"  Synthesis:  {c.synthesis_input_tokens:>8} in / {c.synthesis_output_tokens:>8} out")
    print(f"\nEstimated cost: ${c.total_usd:.4f}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: str, data: object) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
