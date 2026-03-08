Conversation Knowledge Extractor — n8n Workflow Spec
Overview
Build an n8n workflow that processes exported Claude.ai conversation history, triages conversations by value, deep-extracts knowledge from high-value ones, and synthesizes findings into a structured personal knowledge base.
Architecture: Hybrid Triage → Deep Dive
Why this approach: Most conversations (60-70%) are one-off questions. The gold is in ~30% where you built frameworks, strategies, and reusable patterns. Triage first with Haiku (cheap), deep-dive only high-value with Sonnet/Opus.
Estimated cost: ~500 conversations ≈ under $30 total.
Step-by-Step
Step 1: Export
Go to Claude.ai → Settings → Account → Export Data. Download ZIP, extract JSON into an input folder n8n can access.
Step 2: Pre-Processing (Code Node)
Parse raw JSON into individual conversation objects. Each gets: conversation_id, title, timestamps, message_count, estimated_tokens (word count × 1.3), and full_text (all messages concatenated with role labels). Flag anything over 180K tokens for special handling.
Step 3: Triage Pass (Haiku — fast & cheap)
Loop through every conversation. Send to claude-haiku-4-5-20251001 with temp 0, max 500 tokens.
Triage prompt asks for:

Score 1-5 (1=no value, 5=major breakthrough)
One-sentence summary
Up to 3 topic tags
worth_saving (bool)
worth_building_skill (bool)
skill_candidate_reason (if applicable)

Store results in Google Sheets. Oversized conversations (>180K tokens) auto-score as 4 minimum.
Step 4: Filter
Pull only score >= 4 conversations.
Step 5: Deep Extraction (Sonnet/Opus)
Send each high-value conversation to claude-sonnet-4-5-20250929 with temp 0, max 4096 tokens.
Deep extraction prompt pulls:

Problem statement and context
Approach/strategy developed
Key decisions with reasoning
Frameworks developed (name, description, steps, when to use)
Reusable patterns (pattern, description, example)
Tools and tech mentioned
Templates or artifacts (prompts, workflows, docs, code)
Unfinished ideas worth revisiting
Skill candidate details (name, description, trigger, inputs, outputs)
Tags and connections to other work

Chunking for oversized conversations: Split at natural breakpoints with 2000-token overlap between chunks. Each chunk includes previous chunk summary. After all chunks processed, reconciliation call merges into one coherent extraction.
Step 6: Synthesis
Send all deep extractions to Sonnet with temp 0.2, max 8192 tokens. Clusters by thematic domain, identifies frameworks/patterns/skills per domain, flags cross-domain connections, prioritizes skill candidates. Output: knowledge-map.md
Step 7: Skill Candidates Report
Code node pulls all skill candidates, generates prioritized build list with name, description, trigger, inputs/outputs, source conversations, complexity estimate, and priority ranking. Output: skill-candidates.md
n8n Node Map
Manual Trigger → Read Files → Code (Parse) → Loop (Triage w/ Haiku) → Google Sheets → Filter (score>=4) → Loop (Deep Extract w/ Sonnet, with chunking branch for oversized) → Synthesis (Sonnet) → Code (Extract Skills) → Write Files (knowledge-map.md, skill-candidates.md, triage-index.json)
Config Variables

ANTHROPIC_API_KEY, INPUT_FOLDER, OUTPUT_FOLDER, GOOGLE_SHEET_ID
TRIAGE_MODEL (haiku), EXTRACTION_MODEL (sonnet), SYNTHESIS_MODEL (sonnet)
MIN_SCORE_FOR_DEEP (4), RATE_LIMIT_SECONDS (1)
MAX_TOKENS for triage (500), extraction (4096), synthesis (8192)

Error Handling

Exponential backoff on 429s
Smart chunking with overlap for oversized conversations
Try/catch with 3 retries on malformed JSON
Skip conversations with <4 messages
Cost guardrail: pause if spend exceeds $50

Output Files

triage-index.json — searchable index of ALL conversations
knowledge-map.md — master knowledge base by domain
skill-candidates.md — prioritized skills to build
deep-extractions/ — individual JSON files per conversation
Google Sheet — browsable triage index