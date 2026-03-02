# instagram-reels-framework Skill Design

## Summary

Single-file Claude Code skill that generates production-ready Instagram Reel scripts with research-backed hook taxonomy, beat structures, emotional arcs, and a 12-point scoring rubric. Brand-first workflow: shows known brands, user picks one (or creates new), then the skill researches the niche before generating. Three-phase: Brand + Niche Research → Strategy Selection → Script Generation + Scoring. Brand-agnostic core with Unstuck preset. Delegates voice to brand-voice-router and text quality to humanize-ai-writing.

## Decisions

- **Scope:** Brand-agnostic core with Unstuck preset (auto-applies when brand = Unstuck)
- **Architecture:** Single SKILL.md file, no reference files
- **Output:** Single Reel per invocation (not batch)
- **Workflow:** Three-phase (Brand + Niche Research → Strategy Selection → Script + Scoring)
- **Hooks:** 4 core + 3 advanced optional (7 total)
- **Scoring:** 12-point rubric shown to user with full breakdown after generation
- **Voice:** Delegates to brand-voice-router + humanize-ai-writing
- **Brand opener:** Skill presents known brands first, user picks or creates new

## Trigger Conditions

Activate when user:
- Wants to create an Instagram Reel or short-form video script
- Mentions Reels performance, engagement, or content strategy
- Says "Reel script," "hook for a Reel," "filming notes," "content for Instagram"
- Wants to improve Reels quality or asks why Reels aren't performing
- Requests a content scoring rubric or quality check on a Reel idea

## Process

### Phase 1: Brand + Niche Research

**Step 1: Brand Check**
- Check for known brands (brand-voice-router, brand-guidelines)
- Present known brands: "Here are the brands I know about: [list]. Which one is this Reel for? Or is this a new brand?"
- Existing brand → pull niche, audience, voice, vocabulary constraints
- New brand → ask 3 quick questions (brand, audience, voice) or delegate to brand-voice-router

**Step 2: Topic + Goal**
- "What topic is this Reel about?" (or suggest based on brand context)
- "What's the primary goal?" (Follows, Shares, Saves, Comments, DM conversions)

**Step 3: Niche Research**
- Research trending content in the brand's niche
- Summarize: competitor approaches, trending hooks, engagement patterns

**Phase 1 Output:** Strategy brief with brand context, research findings, recommended direction. User reviews and approves.

### Phase 2: Strategy Selection

Present options based on research:

**Hook Types (4 core + 3 advanced):**
1. Identity Call-Out — Drives follows
2. Contrarian Reframe — Drives shares
3. Painfully Accurate Observation — Drives shares + saves
4. Framework Drop — Drives saves
5. (Advanced) Story Opening — Drives watch time
6. (Advanced) Data/Stat Lead — Drives saves
7. (Advanced) Question Hook — Drives comments

**Beat Structures (5 options):**
1. Rant to Reframe (40s)
2. Story to System (45-60s)
3. Problem-Agitate-Solve (30s)
4. Listicle with Twist (45s)
5. Before/After Reveal (50s)

**Emotional Arcs (3 patterns):**
1. Frustration → Validation → Agency
2. Confusion → Clarity → Confidence
3. Shame → Permission → Pride

Recommend combination based on niche research + goal. User selects or accepts recommendation. User approves before Phase 3.

### Phase 3: Script Generation + 12-Point Scoring

Generate complete Reel package:
- Timed script (Time | Script | Visual/Filming Notes)
- Screenshot line (engineered for Story sharing)
- Caption (Hook, Body, CTA matched to goal, Hashtags)
- Filming notes (energy, setting, pauses, props)

Then score with 12-point rubric:
1. Hook Strength — stops scroll in 3 seconds?
2. Identity Mirror — reflects audience gap?
3. Brand Voice — matches constraints, no banned words?
4. Shareability — screenshot-worthy moment?
5. Emotional Arc — clear state movement?
6. Timing — fits target length?
7. Specificity — real anchor, not generic?
8. Ending Quality — clean landing, no preaching?
9. CTA Alignment — matches Reel goal?
10. Vulnerability/Authenticity — genuine, not performed?
11. System Visibility — if mentioning system, steps shown?
12. Differentiation — could only come from this brand?

Flag any dimension below 7 with specific fix suggestions.

### Unstuck Preset

When brand = "Unstuck," auto-apply:
- Audience: High-earning PMs, founders, operators stuck on side projects
- Banned words: journey, unlock, transform, elevate, generic coaching language
- Voice: PM terminology, vulnerability over motivation, systems over willpower
- Identity mirrors: Gap between team advice and personal project behavior
- Differentiation test: "Could a fitness coach say this? If yes, too generic."

## Guardrails

- Brand voice constraints are hard filters — banned words are banned, not suggestions
- Never fabricate engagement data or competitor stats in niche research
- CTA must match Reel goal (no "DM me" on vulnerability Reels)
- Script timing must be realistic (150 words/minute, ~2.5 words/second)
- Screenshot line must work standalone (extracted from context)
- Self-scoring must be honest — don't inflate scores above 8 without justification
- Filming notes must be specific enough to execute
- Humanize all text output (humanize-ai-writing)
- Apply brand voice when available (brand-voice-router)

## What This Skill Does NOT Do

- Edit or produce actual video content
- Schedule or post to Instagram
- Manage ad campaigns (that's funnel-ad-creator)
- Write carousel or static post copy (Reels/short-form video only)
- Replace a content strategy (creates individual Reels, not a content calendar)

## Source Knowledge

Extracted from conversations:
- "Creator Reels Performance Framework" (a7c1dae5) — primary source

Key frameworks: Hook Taxonomy (4 core types), Beat Structures (5 types), Emotional Arc Patterns (3 designs), 12-Point Scoring Rubric, Brand Filter System, Vulnerability Reel Protocol, Screenshot Line Engineering, CTA-to-Goal Matching.
