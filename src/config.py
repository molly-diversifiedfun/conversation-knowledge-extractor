"""Configuration management with CLI > env > default priority."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """All pipeline settings. Frozen for immutability."""

    # Paths
    input_path: str = ""
    output_path: str = "./output"

    # API
    api_key: str = ""

    # Models
    triage_model: str = "claude-haiku-4-5-20251001"
    extraction_model: str = "claude-sonnet-4-5-20250929"
    synthesis_model: str = "claude-sonnet-4-5-20250929"

    # Thresholds
    min_score: int = 4
    min_messages: int = 4
    oversized_threshold: int = 180_000
    chunk_overlap_tokens: int = 2000

    # Max tokens per API call
    triage_max_tokens: int = 500
    extraction_max_tokens: int = 8192
    extraction_core_max_tokens: int = 8192
    extraction_patterns_max_tokens: int = 8192
    synthesis_max_tokens: int = 16384

    # Rate limiting (seconds between calls)
    triage_delay: float = 1.0
    extraction_delay: float = 2.0

    # Cost (per million tokens)
    haiku_input_cost: float = 1.00
    haiku_output_cost: float = 5.00
    sonnet_input_cost: float = 3.00
    sonnet_output_cost: float = 15.00

    # Guardrails
    cost_limit: float = 50.0

    # Behavior
    skip_triage: bool = False
    resume: bool = False


def build_config(args: object) -> Config:
    """Build Config from argparse namespace, falling back to env vars, then defaults.

    Priority: CLI arg > environment variable > default value.
    """
    defaults = Config()

    def _resolve(cli_val: object, env_key: str, default: object) -> object:
        if cli_val is not None:
            return cli_val
        env_val = os.environ.get(env_key)
        if env_val is not None:
            return env_val
        return default

    return Config(
        input_path=str(_resolve(
            getattr(args, "input_path", None), "INPUT_PATH", defaults.input_path
        )),
        output_path=str(_resolve(
            getattr(args, "output_path", None), "OUTPUT_PATH", defaults.output_path
        )),
        api_key=str(_resolve(
            getattr(args, "api_key", None), "ANTHROPIC_API_KEY", defaults.api_key
        )),
        triage_model=str(_resolve(
            getattr(args, "triage_model", None), "TRIAGE_MODEL", defaults.triage_model
        )),
        extraction_model=str(_resolve(
            getattr(args, "extraction_model", None), "EXTRACTION_MODEL", defaults.extraction_model
        )),
        synthesis_model=str(_resolve(
            getattr(args, "synthesis_model", None), "SYNTHESIS_MODEL", defaults.synthesis_model
        )),
        min_score=int(_resolve(
            getattr(args, "min_score", None), "MIN_SCORE", defaults.min_score
        )),
        cost_limit=float(_resolve(
            getattr(args, "cost_limit", None), "COST_LIMIT", defaults.cost_limit
        )),
        skip_triage=bool(getattr(args, "skip_triage", defaults.skip_triage)),
        resume=bool(getattr(args, "resume", defaults.resume)),
        # These use defaults only (not typically overridden via CLI)
        min_messages=defaults.min_messages,
        oversized_threshold=defaults.oversized_threshold,
        chunk_overlap_tokens=defaults.chunk_overlap_tokens,
        triage_max_tokens=defaults.triage_max_tokens,
        extraction_max_tokens=defaults.extraction_max_tokens,
        extraction_core_max_tokens=defaults.extraction_core_max_tokens,
        extraction_patterns_max_tokens=defaults.extraction_patterns_max_tokens,
        synthesis_max_tokens=defaults.synthesis_max_tokens,
        triage_delay=defaults.triage_delay,
        extraction_delay=defaults.extraction_delay,
        haiku_input_cost=defaults.haiku_input_cost,
        haiku_output_cost=defaults.haiku_output_cost,
        sonnet_input_cost=defaults.sonnet_input_cost,
        sonnet_output_cost=defaults.sonnet_output_cost,
    )


def validate_config(config: Config) -> None:
    """Fail fast on invalid configuration."""
    if not config.api_key:
        raise SystemExit(
            "Error: ANTHROPIC_API_KEY not set. "
            "Pass --api-key or set ANTHROPIC_API_KEY environment variable."
        )
    if not config.input_path:
        raise SystemExit(
            "Error: --input-path is required. "
            "Pass a path to conversations.json or a ZIP export."
        )
    if not os.path.exists(config.input_path):
        raise SystemExit(f"Error: Input path does not exist: {config.input_path}")
