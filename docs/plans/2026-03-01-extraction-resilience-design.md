# Extraction Resilience Redesign

**Date:** 2026-03-01
**Status:** Approved
**Approach:** B — Split & Recover

## Problem

The extraction pass fails on 79% of conversations (34/43) because `extraction_max_tokens=4096` causes Sonnet's JSON responses to be truncated mid-string. The pipeline has no truncation detection, no recovery, and no retry — it silently substitutes empty data.

## Root Causes

1. **No stop_reason checking** — The API returns `stop_reason: "max_tokens"` on truncation, but `ApiResponse` doesn't capture it.
2. **extraction_max_tokens=4096 too low** — The extraction prompt demands 12 nested JSON fields. Rich conversations need 8K-16K output tokens.
3. **No retry on truncation** — JSON parse failure substitutes `_empty_extraction()` with no retry or recovery attempt.
4. **Monolithic extraction** — All 12 fields in one JSON blob. If any field is verbose, the whole response overflows.

## Design

### 1. ApiResponse + Stop Reason

Add `stop_reason: str` to `ApiResponse` (in `models.py`). Capture `response.stop_reason` in `api_client.py` and pass it through.

Fields: `"end_turn"`, `"max_tokens"`, `"stop_sequence"`.

### 2. Split Extraction Into Two Passes

Replace `build_extraction_prompt()` with two focused prompts:

**Pass 2a — Core Analysis** (`build_core_extraction_prompt`):
- problem_statement, context, approach_strategy
- key_decisions, frameworks, mistakes_and_lessons

6 fields. The most valuable, hardest-to-reconstruct knowledge. Max tokens: 8192.

**Pass 2b — Patterns & Skills** (`build_patterns_extraction_prompt`):
- reusable_patterns, tools_and_tech, templates_artifacts
- unfinished_ideas, skill_candidates, tags, connections_to_other_work

7 fields. More surface-level extraction. Receives Pass 2a output as context to avoid duplication. Max tokens: 8192.

**Merging:** Simple dict merge (non-overlapping keys). Reuse `reconcile_extractions()` for chunked conversations.

### 3. Partial JSON Recovery

Add `recover_partial_json()` in `prompts.py`:

1. Try `json.loads()` (fast path for valid JSON).
2. Try appending closing braces/brackets to repair truncation.
3. Fall back to regex extraction of complete key-value pairs.
4. Return `None` if truly unrecoverable.

Log which fields were recovered vs lost.

### 4. Retry-on-Truncation Logic

Three-tier fallback in the extraction loop:

1. **Normal parse** — response completed naturally (`stop_reason == "end_turn"`).
2. **Partial recovery** — response truncated, salvage complete fields.
3. **Retry with conciseness hint** — append "Be concise. 1-2 sentences per field." to prompt, call API again.

Only after all three fail: substitute `_empty_extraction()`.

### 5. Resume With Failed Extraction Detection

When `--resume` is used, detect extractions with empty data and re-process them:

- Check each extraction's `extraction` dict for any non-empty values.
- If all values are empty/falsy, treat as failed and include in retry set.
- On successful retry, replace the old empty extraction in state (immutably).

## Files Changed

| File | Change |
|------|--------|
| `src/models.py` | Add `stop_reason` to `ApiResponse` |
| `src/api_client.py` | Capture `response.stop_reason` |
| `src/config.py` | Bump `extraction_max_tokens` to 8192, add `extraction_core_max_tokens` and `extraction_patterns_max_tokens` |
| `src/prompts.py` | Split into `build_core_extraction_prompt()` + `build_patterns_extraction_prompt()`. Add `recover_partial_json()`. |
| `src/pipeline.py` | Two-pass extraction loop, retry logic, resume-with-failed detection |

## Cost Impact

- 2x API calls per conversation for extraction (was 1x).
- Each call uses 8192 max_tokens (was 4096 for the single call).
- Estimated additional cost for 34 failed re-extractions: ~$0.50-0.80.
- Retry calls (conciseness hint) add ~$0.01-0.02 per retry, expected rarely.

## Success Criteria

- Re-run on the 34 failed conversations with `--resume` achieves >90% extraction success rate.
- No data loss on conversations that previously succeeded.
- Total re-run cost under $1.50.
