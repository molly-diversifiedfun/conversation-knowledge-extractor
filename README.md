# Conversation Knowledge Extractor

Turn your Claude.ai conversation history into a structured, searchable knowledge base.

If you've had hundreds of conversations with Claude — building frameworks, solving problems, developing strategies — this tool mines that history for the gold. It triages every conversation by value, deep-extracts knowledge from the best ones, and synthesizes everything into a personal knowledge map.

## What You Get

| Output File | What It Contains |
|---|---|
| `knowledge-map.md` | Your knowledge organized by domain — frameworks, patterns, tools, cross-domain connections, and gaps |
| `skill-candidates.md` | Prioritized list of reusable skills worth building, with triggers, inputs/outputs, and complexity |
| `triage-index.json` | Every conversation scored 1-5 with summaries and topic tags |
| `deep-extractions/*.json` | Per-conversation extraction with decisions, patterns, templates, and unfinished ideas |

## How It Works

The extractor runs a three-pass pipeline using Claude's API:

```
┌─────────────────────────────────────────────────────────────┐
│  Pass 1: Triage (Haiku)                                     │
│  Score every conversation 1-5 for knowledge value            │
│  ~60-70% are one-off questions, ~30% contain real gold       │
├─────────────────────────────────────────────────────────────┤
│  Pass 2: Extraction (Sonnet)                                │
│  Deep-extract knowledge from high-scoring conversations      │
│  Two-pass per conversation: core analysis + patterns/skills  │
├─────────────────────────────────────────────────────────────┤
│  Pass 3: Synthesis (Sonnet)                                 │
│  Combine all extractions into a unified knowledge map        │
│  Cluster by domain, find cross-connections, rank skills      │
└─────────────────────────────────────────────────────────────┘
```

**Cost estimate:** ~500 conversations costs under $30.

## Quickstart

### 1. Export your Claude conversations

Go to [claude.ai](https://claude.ai) → **Settings** → **Account** → **Export Data**. You'll receive a ZIP file via email containing your `conversations.json`.

### 2. Install

```bash
pip install .
```

Or install the dependency directly:

```bash
pip install anthropic>=0.40.0
```

### 3. Run

```bash
# Using the installed CLI
extract-knowledge --input-path ~/Downloads/claude-export.zip --api-key sk-ant-...

# Or use an environment variable for the API key
export ANTHROPIC_API_KEY=sk-ant-...
extract-knowledge --input-path ~/Downloads/claude-export.zip
```

That's it. The pipeline will triage all your conversations, extract knowledge from the high-value ones, and write everything to `./output/`.

### 4. Check your results

```
output/
├── knowledge-map.md          # Start here — your personal knowledge base
├── skill-candidates.md       # Skills worth building
├── triage-index.json         # All conversations scored and summarized
└── deep-extractions/         # Individual extraction JSONs
    ├── abc123.json
    ├── def456.json
    └── ...
```

## CLI Reference

```
extract-knowledge [OPTIONS]
```

| Flag | Description | Default |
|---|---|---|
| `--input-path` | Path to `conversations.json` or Claude export ZIP | *required* |
| `--output-path` | Directory for output files | `./output` |
| `--api-key` | Anthropic API key | — |
| `--min-score` | Minimum triage score for deep extraction (1-5) | `4` |
| `--cost-limit` | Stop if estimated cost exceeds this USD amount | `50.00` |
| `--triage-model` | Model for triage pass | `claude-haiku-4-5-20251001` |
| `--extraction-model` | Model for extraction pass | `claude-sonnet-4-5-20250929` |
| `--synthesis-model` | Model for synthesis pass | `claude-sonnet-4-5-20250929` |
| `--skip-triage` | Skip triage and extract all conversations | `false` |
| `--resume` | Resume from last checkpoint after interruption | `false` |
| `--verbose, -v` | Enable debug logging | `false` |

## Environment Variables

Every CLI flag can also be set via an environment variable. CLI arguments take priority.

| Variable | Equivalent Flag |
|---|---|
| `ANTHROPIC_API_KEY` | `--api-key` |
| `INPUT_PATH` | `--input-path` |
| `OUTPUT_PATH` | `--output-path` |
| `MIN_SCORE` | `--min-score` |
| `COST_LIMIT` | `--cost-limit` |
| `TRIAGE_MODEL` | `--triage-model` |
| `EXTRACTION_MODEL` | `--extraction-model` |
| `SYNTHESIS_MODEL` | `--synthesis-model` |

## Handling Interruptions

Progress is checkpointed after every conversation. If the process is interrupted (Ctrl+C, crash, cost limit hit), just re-run with `--resume`:

```bash
extract-knowledge --input-path conversations.json --resume
```

It picks up exactly where it left off — no re-processing of already-triaged or already-extracted conversations. Failed extractions from previous runs are automatically detected and retried.

## How Triage Scoring Works

Each conversation is scored 1-5 by Haiku:

| Score | Meaning | Action |
|---|---|---|
| 1 | No reusable value (quick question, simple lookup) | Skipped |
| 2 | Minor value (basic how-to, standard advice) | Skipped |
| 3 | Moderate value (useful techniques, some insights) | Skipped (default) |
| 4 | High value (frameworks, strategies, reusable patterns) | Extracted |
| 5 | Major breakthrough (novel approaches, deep expertise) | Extracted |

- Conversations with fewer than 4 messages are skipped entirely
- Oversized conversations (>180K tokens) automatically get a minimum score of 4, since long sessions tend to represent deep work
- Lower `--min-score` to 3 to cast a wider net (extracts more, costs more)

## What Gets Extracted

For each high-scoring conversation, the extractor pulls:

**Core Analysis (Pass 2a):**
- Problem statement and context
- Approach and strategy developed
- Key decisions with reasoning
- Frameworks (name, steps, when to use)
- Mistakes and lessons learned

**Patterns & Skills (Pass 2b):**
- Reusable patterns with examples
- Tools and technologies mentioned
- Templates and artifacts (prompts, workflows, code)
- Unfinished ideas worth revisiting
- Skill candidates (trigger, inputs, outputs, complexity)

Oversized conversations are automatically chunked with overlap and reconciled after extraction.

## Cost Controls

| Guard | Detail |
|---|---|
| Default limit | $50 USD — pipeline stops immediately if exceeded |
| Triage model | Haiku (~$1 / $5 per M input/output tokens) |
| Extraction model | Sonnet (~$3 / $15 per M input/output tokens) |
| Rate limiting | 1s between triage calls, 2s between extraction calls |

Adjust with `--cost-limit`:

```bash
# Budget run
extract-knowledge --input-path conversations.json --cost-limit 10.00

# Deep dive on everything
extract-knowledge --input-path conversations.json --cost-limit 100.00 --min-score 3
```

A cost summary is printed at the end of every run:

```
=== KNOWLEDGE EXTRACTOR COMPLETE ===
Status: complete
Conversations triaged: 487
Conversations extracted: 142
Conversations skipped: 23

Token usage:
  Triage:       892410 in /    48230 out
  Extraction:  4210038 in /  1120445 out
  Synthesis:    340221 in /    15884 out

Estimated cost: $22.4130
```

## Resilience

The extraction pipeline is designed to handle failures gracefully:

- **Three-tier fallback** for each extraction call:
  1. Normal parse (clean JSON response)
  2. Partial recovery (salvage complete fields from truncated responses)
  3. Retry with conciseness hint (ask the model to be more brief)
- **Per-conversation checkpointing** — no work is lost on interruption
- **Resume detection** — automatically retries empty/failed extractions
- **Exponential backoff** on rate limit errors (429s)
- **Graceful degradation** — a single failed conversation doesn't crash the pipeline

## Requirements

- Python 3.11+
- [Anthropic API key](https://console.anthropic.com/)

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## License

MIT
