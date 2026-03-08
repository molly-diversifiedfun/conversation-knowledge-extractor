# Conversation Knowledge Extractor

Turn your Claude.ai conversation history into a structured, searchable knowledge base.

If you've had hundreds of conversations with Claude — building frameworks, solving problems, developing strategies — this tool mines that history for the gold. It triages every conversation by value, deep-extracts knowledge from the best ones, and synthesizes everything into a personal knowledge map.

**Real results from 80 conversations:** 7 knowledge domains identified, 67 frameworks extracted, 156 reusable patterns found, 89 skill candidates ranked — for $8.26.

## What You Get

| Output File | What It Contains |
|---|---|
| `knowledge-map.md` | Your knowledge organized by domain — frameworks, patterns, tools, cross-domain connections, and gaps |
| `skill-candidates.md` | Prioritized list of reusable skills worth building, with triggers, inputs/outputs, and complexity |
| `triage-index.json` | Every conversation scored 1-5 with summaries and topic tags |
| `deep-extractions/*.json` | Per-conversation extraction with decisions, patterns, templates, and unfinished ideas |

### Example: Knowledge Map

The knowledge map organizes everything you've built across conversations into domains. Here's a real excerpt:

```markdown
## Knowledge Domains

### AI-Assisted Content Creation & Brand Voice

Systems for generating, humanizing, and maintaining consistent brand voice across
marketing content using AI tools while avoiding generic outputs

**Key Insights:**
- Brand voice differentiation requires explicit forbidden word lists and anti-patterns,
  not just positive examples
- Humanization requires multi-pass approach addressing vocabulary, rhythm, specificity,
  voice, and speech patterns separately
- Platform-specific content transformation beats one-size-fits-all approaches

**Frameworks:**
- **Five-Pass Humanization Framework**: Systematic process for converting AI-generated
  content into natural human voice by addressing vocabulary, structure, specificity,
  personality, and speech patterns in separate passes
- **Hook Bank Categories (8 Types)**: Eight tested hook patterns with fill-in-the-blank
  templates for rapid variation generation across content types

**Patterns:**
- **Forbidden Words as Brand Voice Guardrails** (seen 8x): Creating explicit lists of
  banned words/phrases to prevent AI copy from slipping into generic marketing language
- **Burstiness Engineering** (seen 6x): Deliberately varying sentence and paragraph
  length to create natural rhythm that mimics human writing patterns
```

It also finds cross-domain connections you might not have noticed:

```markdown
## Cross-Domain Connections

- **Coaching & Transformation Design <-> Product Development**:
  Transformation frameworks become productized offerings, with friction points
  mapped to product tiers in the ladder
  - *Insight: Stage 2 scope lock (hardest friction point) becomes the core
    value of mid-tier product, while full transformation requires premium tier*

## Knowledge Gaps

- **Video content production and editing**: Multiple mentions of video needs
  but limited technical implementation details beyond script generation
  → Develop frameworks for video production workflows and editing automation
```

### Example: Skill Candidates

The tool identifies reusable skills buried in your conversations and ranks them:

```markdown
## 1. humanize-ai-content

**Priority:** 10/10 — Appears in 8+ conversations, addresses critical pain point
  (AI-sounding content), has proven 5-pass framework, applicable across all content types
**Complexity:** moderate
**Seen in:** 3 conversation(s)

**Description:** Five-pass framework for converting AI-generated content into natural
  human voice by addressing vocabulary, rhythm, specificity, personality, and speech patterns

**Trigger:** User asks to humanize content, says something sounds like AI,
  or requests rewrite to sound more natural

**Inputs:**
- AI-generated content to humanize
- Target voice/personality (optional)
- Content type (DM, email, social post, sales copy)

**Outputs:**
- Humanized content with AI artifacts removed
- Explanation of changes made in each pass
- Voice consistency check
```

## How It Works

The extractor runs a three-pass pipeline using Claude's API:

```
┌─────────────────────────────────────────────────────────────┐
│  Pass 1: Triage (Haiku — fast & cheap)                      │
│  Score every conversation 1-5 for knowledge value            │
│  ~60-70% are one-off questions, ~30% contain real gold       │
├─────────────────────────────────────────────────────────────┤
│  Pass 2: Extraction (Sonnet — thorough)                     │
│  Deep-extract knowledge from high-scoring conversations      │
│  Two-pass per conversation: core analysis + patterns/skills  │
├─────────────────────────────────────────────────────────────┤
│  Pass 3: Synthesis (Sonnet — connects the dots)             │
│  Combine all extractions into a unified knowledge map        │
│  Cluster by domain, find cross-connections, rank skills      │
└─────────────────────────────────────────────────────────────┘
```

**Typical cost:** 80 conversations cost ~$8. 500 conversations cost under $30.

**Typical runtime:** Depends on how many conversations score high enough for extraction. For 80 conversations (44 extracted), expect ~30-60 minutes. The tool logs progress as it goes so you can see it's working.

## Prerequisites

Before you start, you'll need two things:

### Python 3.11 or newer

Check if you have it:

```bash
python3 --version
```

If you don't have Python 3.11+, install it:
- **Mac:** `brew install python` (requires [Homebrew](https://brew.sh))
- **Windows:** Download from [python.org](https://www.python.org/downloads/)
- **Linux:** `sudo apt install python3.11` (Ubuntu/Debian) or `sudo dnf install python3.11` (Fedora)

### An Anthropic API key

This tool calls the Claude API directly, which is separate from a Claude Pro subscription. You'll need:

1. Create an account at [console.anthropic.com](https://console.anthropic.com/)
2. Go to **API Keys** and create a new key
3. Add credits to your account (under **Billing**) — $10 is plenty for most runs

Your API key will look like `sk-ant-api03-...`. Keep it secret — anyone with this key can make API calls on your account.

## Quickstart

### 1. Export your Claude conversations

1. Go to [claude.ai](https://claude.ai)
2. Click your name in the bottom-left → **Settings**
3. Go to the **Account** tab
4. Click **Export Data**
5. Check your email — Anthropic will send a download link within a few minutes
6. Download the ZIP file (it will be named something like `claude-export-2026-03-08.zip`)

You don't need to unzip it — the tool can read the ZIP directly.

### 2. Clone and install

```bash
git clone https://github.com/molly-diversifiedfun/conversation-knowledge-extractor.git
cd conversation-knowledge-extractor
pip install .
```

This installs the `extract-knowledge` command and the one dependency (`anthropic` Python SDK).

### 3. Run

```bash
extract-knowledge \
  --input-path ~/Downloads/claude-export-2026-03-08.zip \
  --api-key sk-ant-api03-your-key-here
```

Or, if you prefer to keep your API key out of your terminal history:

```bash
export ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
extract-knowledge --input-path ~/Downloads/claude-export-2026-03-08.zip
```

You'll see progress logged as it runs:

```
14:02:31 INFO     Starting extraction: input=conversations.zip, output=./output, min_score=4, cost_limit=$50.00
14:02:31 INFO     Loaded 80 conversations (0 skipped for < 4 messages)
14:02:33 INFO     Triage 1/80: Brand voice development — Score: 5, Topics: branding, AI, copywriting
14:02:35 INFO     Triage 2/80: Quick question about Python — Score: 1, Topics: python
...
14:15:42 INFO     Extraction 1/44: Brand voice development -- done (cost so far: $0.34)
...
14:42:10 INFO     Pipeline complete.
```

### 4. Check your results

```
output/
├── knowledge-map.md          # Start here — your personal knowledge base
├── skill-candidates.md       # Skills worth building, ranked by priority
├── triage-index.json         # All conversations scored and summarized
└── deep-extractions/         # Individual extraction JSONs
    ├── abc123.json
    ├── def456.json
    └── ...
```

Open `knowledge-map.md` first — it's the main deliverable. It reads like a structured overview of everything valuable you've built across all your conversations.

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

## Common Recipes

```bash
# Budget run — lower the cost limit
extract-knowledge --input-path conversations.zip --cost-limit 10.00

# Cast a wider net — extract score 3+ instead of just 4+
extract-knowledge --input-path conversations.zip --min-score 3

# Deep dive on everything — skip triage, extract all conversations
extract-knowledge --input-path conversations.zip --skip-triage --cost-limit 100.00

# Resume after interruption or cost limit hit
extract-knowledge --input-path conversations.zip --resume

# Use a raw JSON file instead of a ZIP
extract-knowledge --input-path conversations.json

# See detailed logging
extract-knowledge --input-path conversations.zip --verbose
```

## Handling Interruptions

Progress is checkpointed after every single conversation. If the process is interrupted — Ctrl+C, crash, cost limit hit, laptop closed — just re-run with `--resume`:

```bash
extract-knowledge --input-path conversations.zip --resume
```

It picks up exactly where it left off. Already-triaged conversations aren't re-triaged. Already-extracted conversations aren't re-extracted. Failed extractions from previous runs are automatically detected and retried.

## How Triage Scoring Works

Each conversation is scored 1-5 by Haiku:

| Score | Meaning | Action |
|---|---|---|
| 1 | No reusable value (quick question, simple lookup) | Skipped |
| 2 | Minor value (basic how-to, standard advice) | Skipped |
| 3 | Moderate value (useful techniques, some insights) | Skipped (default) |
| 4 | High value (frameworks, strategies, reusable patterns) | Extracted |
| 5 | Major breakthrough (novel approaches, deep expertise) | Extracted |

- Conversations with fewer than 4 messages are skipped entirely (too short to contain meaningful knowledge)
- Oversized conversations (>180K tokens) automatically get a minimum score of 4, since long sessions almost always represent deep work
- Lower `--min-score` to 3 to cast a wider net (extracts more conversations, costs more)
- The triage also tags whether each conversation is `worth_saving` and `worth_building_skill`

## What Gets Extracted

For each high-scoring conversation, the extractor makes two focused API calls:

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

Oversized conversations are automatically chunked with overlap and reconciled after extraction — you don't need to do anything special.

## Cost Controls

This tool calls the Claude API, which costs real money. Here's how costs break down and how to control them:

| Component | Model | Cost per M tokens (input / output) |
|---|---|---|
| Triage | Haiku | ~$1 / $5 |
| Extraction | Sonnet | ~$3 / $15 |
| Synthesis | Sonnet | ~$3 / $15 |

**Built-in safety net:** The pipeline tracks cost in real-time and stops immediately if it exceeds the cost limit (default: $50). You won't get a surprise bill.

```bash
# Set a lower limit if you want to be cautious
extract-knowledge --input-path conversations.zip --cost-limit 10.00
```

If the cost limit is hit mid-run, use `--resume` to continue after raising the limit:

```bash
extract-knowledge --input-path conversations.zip --cost-limit 25.00 --resume
```

A cost summary is printed at the end of every run:

```
=== KNOWLEDGE EXTRACTOR COMPLETE ===
Status: complete
Conversations triaged: 80
Conversations extracted: 44
Conversations skipped: 0

Token usage:
  Triage:       892410 in /    48230 out
  Extraction:  4210038 in /  1120445 out
  Synthesis:    340221 in /    15884 out

Estimated cost: $8.2588
```

## Resilience

The extraction pipeline is designed to handle failures gracefully:

- **Three-tier fallback** for each extraction call:
  1. Normal parse (clean JSON response)
  2. Partial recovery (salvage complete fields from truncated responses)
  3. Retry with conciseness hint (ask the model to be more brief)
- **Per-conversation checkpointing** — no work is lost on interruption
- **Resume detection** — automatically retries empty/failed extractions from previous runs
- **Rate limiting** — built-in delays between API calls to avoid hitting rate limits
- **Graceful degradation** — a single failed conversation doesn't crash the pipeline

## Troubleshooting

**"Error: ANTHROPIC_API_KEY not set"**
Pass your API key with `--api-key` or set the environment variable: `export ANTHROPIC_API_KEY=sk-ant-...`

**"No conversations found with >= 4 messages"**
Your export file might be in an unexpected format, or all your conversations are very short. Try `--verbose` to see what's being parsed. If you have a raw JSON file, make sure it's an array of conversation objects or has a `conversations` key.

**"Cost guardrail hit"**
The pipeline stopped to protect your budget. Your progress is saved. Raise the limit and resume: `extract-knowledge --input-path conversations.zip --cost-limit 75.00 --resume`

**The process seems frozen**
Extraction calls to Sonnet can take 10-30 seconds each, especially for long conversations. Use `--verbose` to see detailed progress. If it's truly stuck, Ctrl+C and `--resume`.

**"Input path does not exist"**
Double-check the path to your ZIP or JSON file. Common mistake: the file is in `~/Downloads/` but you're referencing a different directory.

**Empty or sparse knowledge map**
This usually means most conversations scored below the extraction threshold. Try `--min-score 3` to extract more, or check `triage-index.json` to see how your conversations scored.

**Python version error**
This tool requires Python 3.11+. Check with `python3 --version`. If you have an older version, see the [Prerequisites](#prerequisites) section.

## Requirements

- Python 3.11+
- [Anthropic API key](https://console.anthropic.com/) with billing credits

## Development

```bash
# Clone the repo
git clone https://github.com/molly-diversifiedfun/conversation-knowledge-extractor.git
cd conversation-knowledge-extractor

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## License

MIT
