"""CLI entry point — argparse, validation, orchestration."""

from __future__ import annotations

import argparse
import logging
import sys

from .config import Config, build_config, validate_config
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with all CLI flags."""
    parser = argparse.ArgumentParser(
        prog="extract-knowledge",
        description=(
            "Extract reusable knowledge from Claude.ai conversation exports. "
            "Triages conversations by value, deep-extracts high-value ones, "
            "and synthesizes findings into a structured knowledge base."
        ),
    )

    parser.add_argument(
        "--input-path",
        help="Path to conversations.json or Claude export ZIP file. "
        "Env: INPUT_PATH",
    )
    parser.add_argument(
        "--output-path",
        help="Directory for output files (default: ./output). "
        "Env: OUTPUT_PATH",
    )
    parser.add_argument(
        "--api-key",
        help="Anthropic API key. Env: ANTHROPIC_API_KEY",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        help="Minimum triage score for deep extraction (default: 4). "
        "Env: MIN_SCORE",
    )
    parser.add_argument(
        "--cost-limit",
        type=float,
        help="Stop if estimated cost exceeds this USD amount (default: 50). "
        "Env: COST_LIMIT",
    )
    parser.add_argument(
        "--triage-model",
        help=f"Model for triage pass (default: {Config.triage_model}). "
        "Env: TRIAGE_MODEL",
    )
    parser.add_argument(
        "--extraction-model",
        help=f"Model for extraction pass (default: {Config.extraction_model}). "
        "Env: EXTRACTION_MODEL",
    )
    parser.add_argument(
        "--synthesis-model",
        help=f"Model for synthesis pass (default: {Config.synthesis_model}). "
        "Env: SYNTHESIS_MODEL",
    )
    parser.add_argument(
        "--skip-triage",
        action="store_true",
        default=None,
        help="Skip triage pass and extract all conversations.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=None,
        help="Resume from last checkpoint if available.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging.",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Set up logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    config = build_config(args)
    validate_config(config)

    logging.getLogger(__name__).info(
        "Starting extraction: input=%s, output=%s, min_score=%d, cost_limit=$%.2f",
        config.input_path, config.output_path, config.min_score, config.cost_limit,
    )

    try:
        run_pipeline(config)
    except KeyboardInterrupt:
        print("\nInterrupted. Progress saved to checkpoint. Use --resume to continue.")
        sys.exit(130)
    except SystemExit:
        raise
    except Exception as e:
        logging.getLogger(__name__).error("Pipeline failed: %s", e, exc_info=True)
        print(f"\nError: {e}")
        print("Progress may be saved. Use --resume to retry.")
        sys.exit(1)


if __name__ == "__main__":
    main()
