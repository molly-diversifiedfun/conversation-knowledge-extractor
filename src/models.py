"""Immutable data models for the extraction pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Conversation:
    """A parsed conversation ready for processing."""

    conversation_id: str
    name: str
    created_at: str
    updated_at: str
    message_count: int
    word_count: int
    estimated_tokens: int
    is_oversized: bool
    full_text: str


@dataclass(frozen=True)
class TriageResult:
    """Result of triage scoring a single conversation."""

    conversation_id: str
    name: str
    created_at: str
    message_count: int
    estimated_tokens: int
    is_oversized: bool
    score: int
    summary: str
    topics: tuple[str, ...] = ()
    worth_saving: bool = False
    worth_building_skill: bool = False
    skill_candidate_reason: str | None = None


@dataclass(frozen=True)
class Extraction:
    """Deep extraction results for a single conversation."""

    conversation_id: str
    name: str
    created_at: str
    triage_score: int
    triage_summary: str
    triage_topics: tuple[str, ...] = ()
    problem_statement: str = ""
    context: str = ""
    approach_strategy: str = ""
    key_decisions: tuple[dict, ...] = ()
    frameworks: tuple[dict, ...] = ()
    reusable_patterns: tuple[dict, ...] = ()
    tools_and_tech: tuple[dict, ...] = ()
    templates_artifacts: tuple[dict, ...] = ()
    unfinished_ideas: tuple[dict, ...] = ()
    mistakes_and_lessons: tuple[dict, ...] = ()
    skill_candidates: tuple[dict, ...] = ()
    tags: tuple[str, ...] = ()
    connections_to_other_work: tuple[str, ...] = ()


@dataclass(frozen=True)
class ApiResponse:
    """Response from an Anthropic API call."""

    text: str
    input_tokens: int
    output_tokens: int
    stop_reason: str = "end_turn"


@dataclass(frozen=True)
class CostTracker:
    """Accumulated cost tracking across the pipeline."""

    triage_input_tokens: int = 0
    triage_output_tokens: int = 0
    extract_input_tokens: int = 0
    extract_output_tokens: int = 0
    synthesis_input_tokens: int = 0
    synthesis_output_tokens: int = 0
    total_usd: float = 0.0

    def to_dict(self) -> dict:
        return {
            "triage_input_tokens": self.triage_input_tokens,
            "triage_output_tokens": self.triage_output_tokens,
            "extract_input_tokens": self.extract_input_tokens,
            "extract_output_tokens": self.extract_output_tokens,
            "synthesis_input_tokens": self.synthesis_input_tokens,
            "synthesis_output_tokens": self.synthesis_output_tokens,
            "total_usd": self.total_usd,
        }

    @staticmethod
    def from_dict(d: dict) -> CostTracker:
        return CostTracker(
            triage_input_tokens=d.get("triage_input_tokens", 0),
            triage_output_tokens=d.get("triage_output_tokens", 0),
            extract_input_tokens=d.get("extract_input_tokens", 0),
            extract_output_tokens=d.get("extract_output_tokens", 0),
            synthesis_input_tokens=d.get("synthesis_input_tokens", 0),
            synthesis_output_tokens=d.get("synthesis_output_tokens", 0),
            total_usd=d.get("total_usd", 0.0),
        )


@dataclass(frozen=True)
class PipelineState:
    """Complete pipeline state for checkpoint/resume."""

    phase: str = "init"  # init, triage, extraction, synthesis, complete
    conversations_loaded: int = 0
    triage_results: tuple[dict, ...] = ()
    extractions: tuple[dict, ...] = ()
    synthesis: dict = field(default_factory=dict)
    cost: CostTracker = field(default_factory=CostTracker)
    skipped_count: int = 0

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "conversations_loaded": self.conversations_loaded,
            "triage_results": list(self.triage_results),
            "extractions": list(self.extractions),
            "synthesis": self.synthesis,
            "cost": self.cost.to_dict(),
            "skipped_count": self.skipped_count,
        }

    @staticmethod
    def from_dict(d: dict) -> PipelineState:
        return PipelineState(
            phase=d.get("phase", "init"),
            conversations_loaded=d.get("conversations_loaded", 0),
            triage_results=tuple(d.get("triage_results", [])),
            extractions=tuple(d.get("extractions", [])),
            synthesis=d.get("synthesis", {}),
            cost=CostTracker.from_dict(d.get("cost", {})),
            skipped_count=d.get("skipped_count", 0),
        )
