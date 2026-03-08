# Architectural Decisions

## 1. Single Extraction Path (No IF Branching for Token Count)

**Decision:** Handle oversized vs. normal conversations inside a single Code node ("Smart Prep & Chunk") rather than using an n8n IF node with separate branches.

**Why:** In n8n, when an IF node branches to two paths that must later converge via a Merge node, the Merge waits for BOTH inputs. If one branch receives zero items (e.g., no oversized conversations), the Merge waits forever and the workflow hangs. The standard n8n workarounds (alwaysOutputData, empty arrays) are unreliable across versions.

**Impact:** The IF node check is performed internally in the Code node. A sticky note in the workflow explains the 180K token threshold. The result is identical: oversized conversations get chunked, normal ones pass through, all go through one extraction loop.

## 2. Claude.ai Export Format Assumptions

**Decision:** Support multiple export format variations with fallback parsing.

**Assumptions about the export:**
- ZIP contains `conversations.json` (array of conversation objects)
- Conversation fields: `uuid`/`id`, `name`/`title`, `created_at`, `updated_at`, `chat_messages`/`messages`
- Message fields: `uuid`/`id`, `text`/`content`, `sender`/`role`, `created_at`

**Impact:** The Parse Conversations Code node tries multiple field names with fallbacks. If Anthropic changes the format, only this one node needs updating.

## 3. Token Estimation Method

**Decision:** Use `word_count * 1.3` as specified in the spec (not chars/4).

**Why:** The spec explicitly states this formula. Word-based estimation better handles mixed content (code, prose, lists).

## 4. Rate Limiting via Wait Nodes

**Decision:** Use n8n Wait nodes inside SplitInBatches loops for rate limiting.

**Why:** The spec calls for configurable delay between API calls. Wait nodes pause the workflow execution, saving state and resuming after the delay. This is the standard n8n pattern for rate limiting.

**Alternative:** n8n HTTP Request batching (`batchInterval`) could also work but is less visible in the workflow UI and less portable across n8n versions.

## 5. Config via Set Node (Not Workflow Variables)

**Decision:** Store all configuration in a "Set Config" node at the start, accessed via `$('Set Config').first().json` in downstream nodes.

**Why:** n8n's workflow-level Variables feature (`$vars`) requires manual setup in the n8n instance Settings UI and cannot be embedded in the workflow JSON file. A Set node exports cleanly, is visible in the workflow, and works on any n8n instance without additional setup.

## 6. Cost Tracking via Workflow Static Data

**Decision:** Use `$getWorkflowStaticData('global')` to accumulate cost estimates across loop iterations.

**Why:** Workflow static data persists across items in the same execution. Each API call's token usage is added to a running total. A cost guardrail checks the total before each extraction call.

## 7. Retry Logic

**Decision:** Set `retryOnFail: true`, `maxTries: 3`, `waitBetweenTries: 5000` on HTTP Request nodes, plus `continueOnFail: true` to prevent workflow crashes.

**Why:** The spec requires 3 retries with exponential backoff. n8n's built-in retry handles transient failures (429 rate limits, 500 errors). `continueOnFail` ensures a single bad conversation doesn't crash the entire pipeline. The Parse Code nodes detect and handle errors gracefully.

## 8. Prompts Written from Spec

**Decision:** Triage, extraction, and synthesis prompts are written to match the spec's described output fields exactly.

**Fields match spec:**
- Triage: score (1-5), summary, topic tags, worth_saving, worth_building_skill, skill_candidate_reason
- Extraction: problem statement, approach/strategy, key decisions, frameworks, patterns, tools/tech, templates/artifacts, unfinished ideas, skill candidates, tags
- Synthesis: thematic domain clustering, frameworks/patterns/skills per domain, cross-domain connections, prioritized skill candidates

## 9. Oversized Auto-Score

**Decision:** Conversations over 180K tokens automatically receive a minimum triage score of 4.

**Why:** Per the spec, oversized conversations represent extended deep work sessions that are inherently valuable. They still go through triage for metadata extraction but are guaranteed to reach deep extraction.

## 10. Deep Extraction File Output

**Decision:** Individual deep extraction JSON files are written during the extraction loop (one per conversation), in addition to the aggregated outputs.

**Why:** The spec lists `deep-extractions/` as an output directory. Writing per-conversation files provides granular access to extraction results and enables re-running synthesis without re-extracting.

## 11. Chunk Reconciliation Strategy

**Decision:** After extracting all chunks, a Code node groups by conversation_id and merges arrays (deduplicating by content hash where possible).

**Why:** Each chunk may extract overlapping knowledge (due to 2000-token overlap). The reconciliation merges all arrays (key_decisions, patterns, etc.) and removes near-duplicates.

## 12. Google Sheets Authentication

**Decision:** The Google Sheets node uses a credential reference (`Google Sheets account`). Users must set up OAuth2 or Service Account credentials in their n8n instance.

**Why:** Google API credentials cannot be embedded in workflow JSON files for security reasons. The node references a credential by type; users connect their own Google account through n8n's credential management UI.
