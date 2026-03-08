# Conversation Knowledge Extractor

Extract reusable knowledge from Claude.ai conversation exports. Triages conversations by value, deep-extracts high-value ones, and synthesizes findings into a structured knowledge base.

## Requirements

- Python 3.11+
- Anthropic API key

## Install

```bash
pip install .
```

Or run directly:

```bash
pip install anthropic>=0.40.0
```

## Usage

```bash
# Basic usage
extract-knowledge --input-path conversations.json --api-key sk-ant-...

# From a Claude export ZIP
extract-knowledge --input-path claude-export.zip --output-path ./results/

# Skip triage (extract all conversations)
extract-knowledge --input-path conversations.json --skip-triage

# Resume after interruption
extract-knowledge --input-path conversations.json --resume

# Custom thresholds
extract-knowledge --input-path conversations.json --min-score 3 --cost-limit 10.00

# Or run as module
python -m src.cli --input-path conversations.json
```

## Environment Variables

All CLI flags can be set via environment variables:

| Variable | CLI Flag | Default |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | `--api-key` | — |
| `INPUT_PATH` | `--input-path` | — |
| `OUTPUT_PATH` | `--output-path` | `./output` |
| `MIN_SCORE` | `--min-score` | `4` |
| `COST_LIMIT` | `--cost-limit` | `50.00` |
| `TRIAGE_MODEL` | `--triage-model` | `claude-haiku-4-5-20251001` |
| `EXTRACTION_MODEL` | `--extraction-model` | `claude-sonnet-4-5-20250929` |
| `SYNTHESIS_MODEL` | `--synthesis-model` | `claude-sonnet-4-5-20250929` |

CLI arguments take priority over environment variables.

## Pipeline

The extractor runs a three-pass pipeline:

1. **Triage** (Haiku) — scores every conversation 1–5 for knowledge value
2. **Extraction** (Sonnet) — deep-extracts knowledge from high-scoring conversations
3. **Synthesis** (Sonnet) — combines all extractions into a unified knowledge map

Progress is checkpointed after each conversation. Use `--resume` to continue after interruption.

## Output Files

| File | Description |
|------|-------------|
| `triage-index.json` | All conversations with scores, sorted by value |
| `deep-extractions/*.json` | Per-conversation extraction results |
| `knowledge-map.md` | Synthesized knowledge organized by domain |
| `skill-candidates.md` | Prioritized list of potential Claude Code skills |

## Cost Controls

- Default cost limit: $50 USD
- Triage uses Haiku (~$1/$5 per M input/output tokens)
- Extraction and synthesis use Sonnet (~$3/$15 per M input/output tokens)
- Pipeline stops immediately if the cost limit is reached
- Use `--cost-limit` to adjust
